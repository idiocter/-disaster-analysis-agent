"""Google Earth Engine client: service-account auth + dataset querying with
local+PostGIS caching.

Not live-verified in this environment -- no GEE service account is
configured. GEE_SERVICE_ACCOUNT_EMAIL / GEE_SERVICE_ACCOUNT_JSON must be
set, AND that service account must additionally be registered for Earth
Engine access in the GEE console (a manual one-time GCP setup step, not
something this code can do). Unit-tested with the `ee` calls monkeypatched
out; the caching, size-guard, and GeoTIFF-writing logic around those calls
is real and independently verified.
"""

from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.data.cache import cache_file_path, cache_raster, get_cached_raster
from src.data.gee_datasets import HANSEN_GFC, HANSEN_TREECOVER_BAND, select_dataset_for_analysis

# Rough guard against Earth Engine's synchronous computePixels payload
# limit (~32-50MB depending on API version/dtype). AOIs larger than this
# need the async Export.image.toDrive + polling path instead -- not
# implemented here, see plan.md's GEE risk note.
_MAX_SYNC_PIXELS = 3_000_000

_initialized = False


def ensure_initialized() -> None:
    global _initialized
    if _initialized:
        return
    if not settings.gee_service_account_email or not settings.gee_service_account_json:
        raise RuntimeError(
            "GEE_SERVICE_ACCOUNT_EMAIL / GEE_SERVICE_ACCOUNT_JSON not set in .env -- the "
            "service account must also be registered for Earth Engine access in the GEE "
            "console separately from generic GCP credentials (a one-time manual setup step)."
        )

    import ee

    credentials = ee.ServiceAccountCredentials(
        settings.gee_service_account_email, settings.gee_service_account_json
    )
    ee.Initialize(credentials)
    _initialized = True


def _estimate_pixel_count(bounds: tuple[float, float, float, float], resolution_m: float) -> int:
    width_m = (bounds[2] - bounds[0]) * 111_320  # deg -> m at the equator; adequate for a size guard
    height_m = (bounds[3] - bounds[1]) * 110_540
    return int((width_m / resolution_m) * (height_m / resolution_m))


async def fetch_landcover_raster(
    session: AsyncSession,
    *,
    analysis_type: str,
    bounds: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
) -> str:
    """Returns a local file path to the (cached-or-freshly-fetched) raster
    for the given AOI/date range -- same shape whether or not a real GEE
    call ends up happening.
    """
    dataset = select_dataset_for_analysis(analysis_type, date_start)

    cached = await get_cached_raster(
        session, dataset_id=dataset.asset_id, bounds=bounds, date_start=date_start, date_end=date_end
    )
    if cached is not None:
        return cached

    pixel_count = _estimate_pixel_count(bounds, dataset.native_resolution_m)
    if pixel_count > _MAX_SYNC_PIXELS:
        raise ValueError(
            f"AOI too large for a synchronous GEE fetch (~{pixel_count:,} pixels > "
            f"{_MAX_SYNC_PIXELS:,}); this needs the async Export.image.toDrive + polling "
            f"path, not implemented here -- see plan.md's GEE risk note."
        )

    ensure_initialized()
    array = _fetch_pixels(dataset.asset_id, dataset.band, bounds)

    out_path = cache_file_path(dataset.asset_id, bounds, date_start, date_end)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    _write_geotiff(array, bounds, out_path)

    await cache_raster(
        session,
        dataset_id=dataset.asset_id,
        bounds=bounds,
        date_start=date_start,
        date_end=date_end,
        resolution_m=dataset.native_resolution_m,
        file_path=out_path,
    )
    return out_path


def _fetch_pixels(asset_id: str, band: str, bounds: tuple[float, float, float, float]) -> np.ndarray:
    """Synchronous small-AOI fetch via ee.data.computePixels. Isolated into
    its own function specifically so tests can monkeypatch just this call
    without needing a real `ee` module or credentials.
    """
    import ee

    region = ee.Geometry.Rectangle(list(bounds))
    image: Any = ee.Image(asset_id).select(band).clip(region)
    request = {
        "expression": image,
        "fileFormat": "NUMPY_NDARRAY",
        "grid": {"dimensions": {"width": 512, "height": 512}, "crsCode": "EPSG:4326"},
    }
    result = ee.data.computePixels(request)
    # Real computePixels output is a structured array with one named field
    # per band; unwrap to a plain 2D array for the single-band case this
    # project needs.
    if getattr(result, "dtype", None) is not None and result.dtype.names:
        return result[result.dtype.names[0]]
    return result


def _write_geotiff(array: np.ndarray, bounds: tuple[float, float, float, float], out_path: str) -> None:
    height, width = array.shape[0], array.shape[1] if array.ndim > 1 else array.shape[0]
    transform = from_bounds(*bounds, width, height)
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": str(array.dtype),
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": 255 if array.dtype == np.uint8 else None,
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(array, 1)


async def fetch_hansen_bands(
    session: AsyncSession,
    *,
    bounds: tuple[float, float, float, float],
    date_start: str,
    date_end: str,
) -> tuple[str, str]:
    """Fetch Hansen's lossyear and treecover2000 bands as two local GeoTIFFs.

    Returned in the order detect_forest_loss_hansen expects. Both are cached
    under the same AOI/date key but distinct dataset ids, so the two bands
    never collide in raster_cache_index.
    """
    dataset = HANSEN_GFC
    paths: list[str] = []

    for band in (dataset.band, HANSEN_TREECOVER_BAND):
        dataset_id = f"{dataset.asset_id}#{band}"
        cached = await get_cached_raster(
            session, dataset_id=dataset_id, bounds=bounds, date_start=date_start, date_end=date_end
        )
        if cached is not None:
            paths.append(cached)
            continue

        pixel_count = _estimate_pixel_count(bounds, dataset.native_resolution_m)
        if pixel_count > _MAX_SYNC_PIXELS:
            raise ValueError(
                f"AOI too large for a synchronous GEE fetch (~{pixel_count:,} pixels > "
                f"{_MAX_SYNC_PIXELS:,}); needs the async Export.image.toDrive path."
            )

        ensure_initialized()
        array = _fetch_pixels(dataset.asset_id, band, bounds)

        out_path = cache_file_path(dataset_id, bounds, date_start, date_end)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        _write_geotiff(array, bounds, out_path)

        await cache_raster(
            session,
            dataset_id=dataset_id,
            bounds=bounds,
            date_start=date_start,
            date_end=date_end,
            resolution_m=dataset.native_resolution_m,
            file_path=out_path,
        )
        paths.append(out_path)

    return paths[0], paths[1]

"""Forest-loss / land-cover-change detection.

Two algorithms, because the two data sources encode change differently:

- `detect_forest_loss` compares two co-registered classification snapshots
  (t1 vs t2). Suits Dynamic World / ESA WorldCover and the synthetic sample
  rasters, where "loss" is a pixel that was forest at t1 and isn't at t2.

- `detect_forest_loss_hansen` reads Hansen Global Forest Change, which has
  no t1/t2 pair at all: `lossyear` is a single static band holding the year
  each pixel was cleared (0 = never, N = year 2000+N), with `treecover2000`
  giving the baseline canopy percentage. Loss over a window is therefore a
  range filter on one band, not a diff of two -- which is why the snapshot
  algorithm cannot be pointed at Hansen and why `forest_loss` queries used
  to silently fall back to sample data.
"""

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import box, shape

from src.graph.state import GisResults
from src.utils.geo_utils import to_equal_area

# Hansen encodes lossyear as an offset from this year.
HANSEN_EPOCH = 2000
# Canopy-cover percentage at or above which a pixel counts as forest in 2000.
# 30% is the threshold most commonly used in the literature built on this
# dataset; exposed so a caller can vary it.
DEFAULT_TREECOVER_THRESHOLD = 30


def _pixel_area_ha(transform, crs) -> float:
    """Area of a single pixel in hectares, via an equal-area reprojection of
    one pixel-sized cell -- never computed in a geographic CRS, where degree
    'areas' vary with latitude.
    """
    pixel_w, pixel_h = abs(transform.a), abs(transform.e)
    cell = gpd.GeoDataFrame(
        geometry=[box(transform.c, transform.f - pixel_h, transform.c + pixel_w, transform.f)],
        crs=crs,
    )
    return to_equal_area(cell).geometry.iloc[0].area / 10_000  # m^2 -> ha


def _write_change_polygons(loss_mask: np.ndarray, transform, crs) -> str | None:
    if not loss_mask.any():
        return None
    polygons = [
        shape(geom)
        for geom, value in shapes(loss_mask.astype("uint8"), transform=transform)
        if value == 1
    ]
    change_gdf = gpd.GeoDataFrame(geometry=polygons, crs=crs)
    path = "data/cache/change_polygons.geojson"
    change_gdf.to_file(path, driver="GeoJSON")
    return path


def _build_results(loss_mask: np.ndarray, baseline_forest_mask: np.ndarray, transform, crs) -> GisResults:
    pixel_area_ha = _pixel_area_ha(transform, crs)
    loss_px = int(loss_mask.sum())
    baseline_px = int(baseline_forest_mask.sum())
    return GisResults(
        forest_loss_ha=round(loss_px * pixel_area_ha, 4),
        forest_loss_pct=round(100.0 * loss_px / baseline_px, 2) if baseline_px else 0.0,
        change_polygons_path=_write_change_polygons(loss_mask, transform, crs),
        zonal_stats={},  # populated by zonal_stats.py when per-subzone boundaries exist
    )


def detect_forest_loss(t1_path: str, t2_path: str, boundary: gpd.GeoDataFrame) -> GisResults:
    """Two-snapshot diff: forest at t1, non-forest at t2."""
    with rasterio.open(t1_path) as src1, rasterio.open(t2_path) as src2:
        t1 = src1.read(1)
        t2 = src2.read(1)
        transform = src1.transform
        crs = src1.crs

    if t1.shape != t2.shape:
        raise ValueError(f"t1/t2 raster shapes differ: {t1.shape} vs {t2.shape}")

    baseline_forest = t1 == 1
    loss_mask = baseline_forest & (t2 == 0)
    return _build_results(loss_mask, baseline_forest, transform, crs)


def detect_forest_loss_hansen(
    lossyear_path: str,
    treecover_path: str,
    boundary: gpd.GeoDataFrame,
    *,
    year_start: int,
    year_end: int,
    treecover_threshold: int = DEFAULT_TREECOVER_THRESHOLD,
) -> GisResults:
    """Range-filter Hansen's lossyear band over [year_start, year_end].

    Baseline forest is `treecover2000 >= treecover_threshold`; a pixel counts
    as lost only if it was forest in 2000 AND its loss year falls inside the
    window. Percentage is loss area over that baseline area, so it answers
    "what fraction of this area's year-2000 forest was cleared in the window".
    """
    with rasterio.open(lossyear_path) as ly_src, rasterio.open(treecover_path) as tc_src:
        lossyear = ly_src.read(1)
        treecover = tc_src.read(1)
        transform = ly_src.transform
        crs = ly_src.crs

    if lossyear.shape != treecover.shape:
        raise ValueError(
            f"lossyear/treecover raster shapes differ: {lossyear.shape} vs {treecover.shape}"
        )

    # Hansen starts at 2000; a query reaching further back can only be
    # answered from 2000 onward, so clamp rather than silently returning zero.
    start_offset = max(year_start - HANSEN_EPOCH, 1)
    end_offset = year_end - HANSEN_EPOCH
    if end_offset < 1:
        raise ValueError(
            f"Hansen Global Forest Change covers {HANSEN_EPOCH} onward; "
            f"requested window ends {year_end}"
        )

    baseline_forest = treecover >= treecover_threshold
    in_window = (lossyear >= start_offset) & (lossyear <= end_offset)
    loss_mask = baseline_forest & in_window

    return _build_results(loss_mask, baseline_forest, transform, crs)

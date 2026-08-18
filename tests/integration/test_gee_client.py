"""Exercises gee_client.fetch_landcover_raster's caching + GeoTIFF-writing
logic against the real PostGIS container, with the actual Earth Engine
network call (_fetch_pixels) monkeypatched out -- there's no GEE service
account configured in this environment. Everything downstream of that one
call (pixel-count size guard, cache lookup/record, file writing) is real.
"""

import random

import numpy as np
import pytest
import rasterio

from src.data import gee_client
from src.data.postgis_repo import async_session_factory

_BOUNDS = (87.20, 26.60, 87.30, 26.68)  # matches the Madhuban sample fixture


def _unique_bounds() -> tuple[float, float, float, float]:
    # A tiny random jitter keeps each test invocation's cache key unique --
    # otherwise a raster_cache_index row (and its on-disk file) from a
    # PREVIOUS run of this exact test can still be a genuine, correct cache
    # hit, since the DB persists across test runs.
    jitter = random.uniform(0, 0.01)
    return (_BOUNDS[0] + jitter, _BOUNDS[1], _BOUNDS[2] + jitter, _BOUNDS[3])


def test_ensure_initialized_raises_without_credentials(monkeypatch):
    from src.config import settings

    monkeypatch.setattr(settings, "gee_service_account_email", "")
    monkeypatch.setattr(settings, "gee_service_account_json", "")
    gee_client._initialized = False

    with pytest.raises(RuntimeError, match="GEE_SERVICE_ACCOUNT"):
        gee_client.ensure_initialized()


def test_pixel_count_guard_rejects_oversized_aoi():
    # A country-scale AOI at 30m resolution -- should trip the sync-fetch
    # size guard before ever touching `ee`.
    huge_bounds = (80.0, 26.0, 88.0, 30.0)
    count = gee_client._estimate_pixel_count(huge_bounds, resolution_m=30.0)
    assert count > gee_client._MAX_SYNC_PIXELS


async def test_fetch_landcover_raster_caches_after_first_fetch(monkeypatch, tmp_path):
    from src.config import settings

    monkeypatch.setattr(settings, "gee_service_account_email", "test@example.iam.gserviceaccount.com")
    monkeypatch.setattr(settings, "gee_service_account_json", str(tmp_path / "fake-creds.json"))
    monkeypatch.setattr(settings, "data_cache_dir", str(tmp_path))
    gee_client._initialized = False

    monkeypatch.setattr(gee_client, "ensure_initialized", lambda: None)

    call_count = {"n": 0}

    def fake_fetch_pixels(asset_id, band, bounds):
        call_count["n"] += 1
        return np.zeros((64, 64), dtype=np.uint8)

    monkeypatch.setattr(gee_client, "_fetch_pixels", fake_fetch_pixels)

    bounds = _unique_bounds()
    async with async_session_factory() as session:
        path1 = await gee_client.fetch_landcover_raster(
            session, analysis_type="forest_loss", bounds=bounds, date_start="2005-01-01", date_end="2020-12-31"
        )
        path2 = await gee_client.fetch_landcover_raster(
            session, analysis_type="forest_loss", bounds=bounds, date_start="2005-01-01", date_end="2020-12-31"
        )

    assert path1 == path2
    assert call_count["n"] == 1  # second call hit the cache, no re-fetch

    with rasterio.open(path1) as src:
        assert src.crs.to_string() == "EPSG:4326"
        arr = src.read(1)
        assert arr.shape == (64, 64)

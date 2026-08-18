from pathlib import Path

import geopandas as gpd
import pytest

from src.models.features import _normalize_rainfall, build_zone_features

_HAS_SAMPLE_DATA = Path("data/sample/dem.tif").exists() and Path("data/sample/rainfall.tif").exists()


def test_normalize_rainfall_clips_to_0_1_range():
    assert _normalize_rainfall(0) == 0.0
    assert _normalize_rainfall(10_000) == 1.0
    assert 0.0 < _normalize_rainfall(2000) < 1.0


def test_build_zone_features_uses_placeholders_without_boundary():
    gis_results = {"forest_loss_ha": 10.0, "forest_loss_pct": 5.0, "change_polygons_path": None, "zonal_stats": {}}
    features = build_zone_features("TestZone", gis_results, boundary=None)

    assert features[0]["mean_slope_deg"] == 12.0
    assert features[0]["rainfall_intensity_norm"] == 0.6


@pytest.mark.skipif(not _HAS_SAMPLE_DATA, reason="sample DEM/rainfall rasters not generated")
def test_build_zone_features_computes_real_values_with_boundary():
    boundary = gpd.read_file("tests/fixtures/sample_boundary.geojson")
    gis_results = {"forest_loss_ha": 10.0, "forest_loss_pct": 5.0, "change_polygons_path": None, "zonal_stats": {}}

    features = build_zone_features("Madhuban", gis_results, boundary=boundary)

    # Real computed values shouldn't exactly equal the Phase 1 placeholders
    # (extraordinarily unlikely by coincidence for a randomly-seeded
    # synthetic surface) -- proof the real path executed, not the fallback.
    assert features[0]["mean_slope_deg"] != 12.0
    assert features[0]["rainfall_intensity_norm"] != 0.6
    assert features[0]["mean_slope_deg"] >= 0
    assert 0.0 <= features[0]["rainfall_intensity_norm"] <= 1.0

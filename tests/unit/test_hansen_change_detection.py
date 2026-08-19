"""Tests for the Hansen lossyear algorithm -- the path that previously did
not exist, forcing forest_loss queries to fall back to sample rasters even
with GEE credentials configured.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from src.gis.change_detection import HANSEN_EPOCH, detect_forest_loss_hansen

_BOUNDS = (87.20, 26.60, 87.30, 26.68)
_SIZE = 40


def _write(path, array, dtype="uint8"):
    profile = {
        "driver": "GTiff", "height": array.shape[0], "width": array.shape[1], "count": 1,
        "dtype": dtype, "crs": "EPSG:4326",
        "transform": from_bounds(*_BOUNDS, array.shape[1], array.shape[0]), "nodata": 255,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array, 1)
    return str(path)


@pytest.fixture
def hansen_pair(tmp_path):
    """All-forest baseline; loss in 2005 (row 0-9) and 2018 (row 10-19)."""
    treecover = np.full((_SIZE, _SIZE), 80, dtype="uint8")
    lossyear = np.zeros((_SIZE, _SIZE), dtype="uint8")
    lossyear[0:10, :] = 5    # 2005
    lossyear[10:20, :] = 18  # 2018
    return (
        _write(tmp_path / "ly.tif", lossyear),
        _write(tmp_path / "tc.tif", treecover),
    )


@pytest.fixture
def boundary():
    return gpd.read_file("tests/fixtures/sample_boundary.geojson")


def test_window_includes_only_loss_within_date_range(hansen_pair, boundary):
    ly, tc = hansen_pair
    # 2004-2010 should catch the 2005 block (10 of 40 rows = 25%) and not 2018
    res = detect_forest_loss_hansen(ly, tc, boundary, year_start=2004, year_end=2010)
    assert res["forest_loss_pct"] == pytest.approx(25.0, abs=0.5)


def test_wider_window_catches_both_loss_events(hansen_pair, boundary):
    ly, tc = hansen_pair
    res = detect_forest_loss_hansen(ly, tc, boundary, year_start=2000, year_end=2020)
    assert res["forest_loss_pct"] == pytest.approx(50.0, abs=0.5)


def test_window_after_all_loss_finds_nothing(hansen_pair, boundary):
    ly, tc = hansen_pair
    res = detect_forest_loss_hansen(ly, tc, boundary, year_start=2019, year_end=2023)
    assert res["forest_loss_ha"] == 0.0
    assert res["forest_loss_pct"] == 0.0


def test_treecover_threshold_defines_the_baseline(tmp_path, boundary):
    """Pixels below the canopy threshold aren't forest, so clearing them
    isn't forest loss -- and they don't inflate the denominator either."""
    treecover = np.full((_SIZE, _SIZE), 10, dtype="uint8")  # all below 30%
    lossyear = np.full((_SIZE, _SIZE), 8, dtype="uint8")    # all "cleared" in 2008
    ly = _write(tmp_path / "ly.tif", lossyear)
    tc = _write(tmp_path / "tc.tif", treecover)

    res = detect_forest_loss_hansen(ly, tc, boundary, year_start=2000, year_end=2020)
    assert res["forest_loss_ha"] == 0.0


def test_lower_threshold_admits_sparser_canopy(tmp_path, boundary):
    treecover = np.full((_SIZE, _SIZE), 20, dtype="uint8")
    lossyear = np.full((_SIZE, _SIZE), 8, dtype="uint8")
    ly = _write(tmp_path / "ly.tif", lossyear)
    tc = _write(tmp_path / "tc.tif", treecover)

    strict = detect_forest_loss_hansen(ly, tc, boundary, year_start=2000, year_end=2020)
    lenient = detect_forest_loss_hansen(
        ly, tc, boundary, year_start=2000, year_end=2020, treecover_threshold=15
    )
    assert strict["forest_loss_ha"] == 0.0
    assert lenient["forest_loss_pct"] == pytest.approx(100.0, abs=0.5)


def test_window_ending_before_dataset_coverage_is_rejected(hansen_pair, boundary):
    ly, tc = hansen_pair
    with pytest.raises(ValueError, match="covers 2000 onward"):
        detect_forest_loss_hansen(ly, tc, boundary, year_start=1990, year_end=1995)


def test_start_before_epoch_is_clamped_not_silently_zero(hansen_pair, boundary):
    """A 1995-2010 query can only be answered from 2000, but should still
    report the 2005 loss rather than returning nothing."""
    ly, tc = hansen_pair
    res = detect_forest_loss_hansen(ly, tc, boundary, year_start=1995, year_end=2010)
    assert res["forest_loss_pct"] > 0


def test_mismatched_raster_shapes_raise(tmp_path, boundary):
    ly = _write(tmp_path / "ly.tif", np.zeros((_SIZE, _SIZE), dtype="uint8"))
    tc = _write(tmp_path / "tc.tif", np.full((10, 10), 80, dtype="uint8"))
    with pytest.raises(ValueError, match="shapes differ"):
        detect_forest_loss_hansen(ly, tc, boundary, year_start=2000, year_end=2020)


def test_hansen_epoch_constant():
    assert HANSEN_EPOCH == 2000


@pytest.mark.skipif(
    not Path("data/sample/hansen_lossyear.tif").exists(),
    reason="run scripts/generate_sample_data.py",
)
def test_runs_against_the_generated_sample_rasters(boundary):
    res = detect_forest_loss_hansen(
        "data/sample/hansen_lossyear.tif",
        "data/sample/hansen_treecover.tif",
        boundary,
        year_start=2005,
        year_end=2020,
    )
    assert res["forest_loss_ha"] > 0
    assert 0 < res["forest_loss_pct"] <= 100

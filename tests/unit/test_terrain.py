"""Requires gdaldem on PATH (part of the conda-forge gdal package already
in this project's environment) and the sample DEM
(scripts/generate_sample_data.py). Skipped if either is missing.
"""

import shutil
from pathlib import Path

import pytest
import rasterio

from src.gis.terrain import compute_slope_raster

pytestmark = pytest.mark.skipif(shutil.which("gdaldem") is None, reason="gdaldem not on PATH")

_DEM_PATH = "data/sample/dem.tif"


@pytest.mark.skipif(not Path(_DEM_PATH).exists(), reason="sample DEM not generated")
def test_compute_slope_raster_produces_real_variation(tmp_path):
    out_path = str(tmp_path / "slope.tif")
    result_path = compute_slope_raster(_DEM_PATH, out_path)

    assert result_path == out_path
    with rasterio.open(out_path) as src:
        arr = src.read(1, masked=True)

    # The synthetic DEM has a ridge, not a flat plane -- slope should vary
    # across the raster, not be a uniform constant.
    assert arr.std() > 0
    assert arr.min() >= 0  # slope in degrees is non-negative by definition

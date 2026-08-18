"""Generates synthetic sample rasters for the Madhuban fixture, standing in
for real GEE/SRTM/CHIRPS data:
  - t1/t2_landcover.tif: 1 = forest, 0 = non-forest. A block of pixels
    flips from forest (t1) to non-forest (t2) to simulate forest loss.
  - dem.tif: a synthetic elevation surface (a ridge running NW-SE) so slope
    derivation (src/gis/terrain.py, Phase 4) has real terrain variation to
    work with, not a flat plane.
  - rainfall.tif: a synthetic annual-rainfall-mm surface, standing in for a
    CHIRPS zonal mean.

Usage:
    python scripts/generate_sample_data.py
"""

import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Matches tests/fixtures/sample_boundary.geojson
BOUNDS = (87.20, 26.60, 87.30, 26.68)
SIZE = 60
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    transform = from_bounds(*BOUNDS, SIZE, SIZE)

    rng = np.random.default_rng(seed=42)
    t1 = (rng.random((SIZE, SIZE)) > 0.35).astype("uint8")  # ~65% forest at t1

    t2 = t1.copy()
    # Simulate forest loss in a contiguous block (e.g. clearing), not just
    # random noise, so change-detection has something structured to find.
    t2[10:30, 15:40] = 0

    profile = {
        "driver": "GTiff",
        "height": SIZE,
        "width": SIZE,
        "count": 1,
        "dtype": "uint8",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": 255,
    }

    for name, arr in (("t1_landcover.tif", t1), ("t2_landcover.tif", t2)):
        path = OUT_DIR / name
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(arr, 1)
        print(f"wrote {path}")

    _write_dem(transform)
    _write_rainfall(transform, rng)


def _write_dem(transform) -> None:
    # A ridge running NW-SE plus mild noise -- gives gdaldem slope real
    # variation to compute rather than a uniform flat surface (which would
    # trivially slope to 0 everywhere and not exercise the derivation at all).
    x = np.linspace(0, 1, SIZE)
    y = np.linspace(0, 1, SIZE)
    xx, yy = np.meshgrid(x, y)
    ridge = 200 + 400 * np.exp(-((xx - yy) ** 2) / 0.05) + 50 * np.sin(xx * 6) * np.cos(yy * 6)
    dem = ridge.astype("float32")

    profile = {
        "driver": "GTiff",
        "height": SIZE,
        "width": SIZE,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": -9999.0,
    }
    path = OUT_DIR / "dem.tif"
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(dem, 1)
    print(f"wrote {path}")


def _write_rainfall(transform, rng: np.random.Generator) -> None:
    # Smooth-ish synthetic annual rainfall surface (mm/year), roughly in a
    # plausible Terai-region range, standing in for a CHIRPS zonal mean.
    base = 1800 + 400 * rng.standard_normal((SIZE, SIZE))
    rainfall = np.clip(base, 800, 3500).astype("float32")

    profile = {
        "driver": "GTiff",
        "height": SIZE,
        "width": SIZE,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": -9999.0,
    }
    path = OUT_DIR / "rainfall.tif"
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(rainfall, 1)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

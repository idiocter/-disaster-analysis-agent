"""Builds the risk model's per-zone feature table.

Phase 4: slope is derived from a real DEM via gdaldem (src/gis/terrain.py),
rainfall from a zonal mean of a rainfall raster (data/sample/rainfall.tif in
this build, standing in for a real CHIRPS zonal mean -- no GEE credentials
configured here). Falls back to the Phase 1 placeholder constants if the
DEM/rainfall rasters or a boundary aren't available, so a missing
sample-data file degrades gracefully rather than crashing the node.
"""

from pathlib import Path

from src.gis.terrain import compute_slope_raster
from src.gis.zonal_stats import zonal_mean
from src.graph.state import GisResults
from src.models.risk_model import ZoneFeatures

_PLACEHOLDER_SLOPE_DEG = 12.0
_PLACEHOLDER_RAINFALL_NORM = 0.6

_DEM_PATH = "data/sample/dem.tif"
_RAINFALL_PATH = "data/sample/rainfall.tif"
_SLOPE_CACHE_PATH = "data/cache/slope.tif"

# Nepal Terai/hills annual rainfall roughly spans this range; used only to
# normalize a raw mm/year value into the risk model's expected 0-1 scale.
_RAINFALL_MIN_MM = 800.0
_RAINFALL_MAX_MM = 3500.0


def _normalize_rainfall(mm: float) -> float:
    clipped = max(_RAINFALL_MIN_MM, min(_RAINFALL_MAX_MM, mm))
    return (clipped - _RAINFALL_MIN_MM) / (_RAINFALL_MAX_MM - _RAINFALL_MIN_MM)


def build_zone_features(zone_name: str, gis_results: GisResults, boundary=None) -> list[ZoneFeatures]:
    mean_slope_deg = _PLACEHOLDER_SLOPE_DEG
    rainfall_intensity_norm = _PLACEHOLDER_RAINFALL_NORM

    if boundary is not None and Path(_DEM_PATH).exists():
        slope_path = compute_slope_raster(_DEM_PATH, _SLOPE_CACHE_PATH)
        slope_mean = zonal_mean(slope_path, boundary, nodata=-9999.0)
        if slope_mean is not None:
            mean_slope_deg = slope_mean

    if boundary is not None and Path(_RAINFALL_PATH).exists():
        rainfall_mm = zonal_mean(_RAINFALL_PATH, boundary, nodata=-9999.0)
        if rainfall_mm is not None:
            rainfall_intensity_norm = _normalize_rainfall(rainfall_mm)

    return [
        ZoneFeatures(
            zone_name=zone_name,
            forest_loss_pct=gis_results["forest_loss_pct"],
            mean_slope_deg=round(mean_slope_deg, 2),
            rainfall_intensity_norm=round(rainfall_intensity_norm, 3),
        )
    ]

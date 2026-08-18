"""Zonal statistics: per-boundary-zone summaries of a raster.

Phase 1 has a single zone (the whole Madhuban fixture boundary), so this
mostly proves the plumbing; Phase 3+ (real GADM municipality/ward
boundaries) is where per-subzone breakdown actually matters for the risk
model's per-zone feature table.
"""

from rasterstats import zonal_stats

from src.utils.geo_utils import to_equal_area


def zonal_forest_stats(raster_path: str, boundary) -> list[dict]:
    boundary_equal_area = to_equal_area(boundary)
    stats = zonal_stats(
        boundary_equal_area,
        raster_path,
        categorical=True,
        nodata=255,
    )
    results = []
    for row, stat in zip(boundary_equal_area.itertuples(), stats):
        forest_px = stat.get(1, 0)
        non_forest_px = stat.get(0, 0)
        total = forest_px + non_forest_px
        results.append(
            {
                "zone_name": getattr(row, "name", "unknown"),
                "forest_pixel_count": forest_px,
                "non_forest_pixel_count": non_forest_px,
                "forest_pct": round(100.0 * forest_px / total, 2) if total else 0.0,
            }
        )
    return results


def zonal_mean(raster_path: str, boundary, *, nodata: float | None = None) -> float | None:
    """Mean value of a continuous raster (slope, rainfall) over a boundary
    -- boundary is expected to already be a single dissolved zone (the
    caller is responsible for splitting multi-row GeoDataFrames if
    per-subzone means are needed; Phase 1/3 both operate on one zone at a
    time). Returns None if the raster has no valid pixels under the
    boundary at all.
    """
    stats = zonal_stats(boundary, raster_path, stats=["mean"], nodata=nodata)
    if not stats:
        return None
    return stats[0]["mean"]

"""Forest-loss / land-cover-change detection between two aligned rasters.

Phase 1 inputs are the synthetic t1/t2 rasters from
scripts/generate_sample_data.py (already co-registered, same grid/CRS/shape
by construction). Phase 2's real GEE-derived rasters will need explicit
reprojection to a common grid before this will apply -- see plan.md's Hansen
lossyear note for the real-data path.
"""

import geopandas as gpd
import rasterio
from rasterio.features import shapes
from shapely.geometry import box, shape

from src.graph.state import GisResults
from src.utils.geo_utils import to_equal_area


def detect_forest_loss(t1_path: str, t2_path: str, boundary: gpd.GeoDataFrame) -> GisResults:
    with rasterio.open(t1_path) as src1, rasterio.open(t2_path) as src2:
        t1 = src1.read(1)
        t2 = src2.read(1)
        transform = src1.transform
        crs = src1.crs

    if t1.shape != t2.shape:
        raise ValueError(f"t1/t2 raster shapes differ: {t1.shape} vs {t2.shape}")

    loss_mask = (t1 == 1) & (t2 == 0)

    # Pixel area via an equal-area reprojection of the boundary's bounding
    # box scale factor is overkill for a small synthetic AOI; instead derive
    # pixel size directly from the transform and the equal-area CRS in one
    # step by building a 1-pixel-cell GeoDataFrame and reprojecting it.
    pixel_w, pixel_h = abs(transform.a), abs(transform.e)
    cell = gpd.GeoDataFrame(
        geometry=[box(transform.c, transform.f - pixel_h, transform.c + pixel_w, transform.f)],
        crs=crs,
    )
    cell_equal_area = to_equal_area(cell)
    pixel_area_ha = cell_equal_area.geometry.iloc[0].area / 10_000  # m^2 -> ha

    loss_pixel_count = int(loss_mask.sum())
    forest_loss_ha = loss_pixel_count * pixel_area_ha
    total_t1_forest_px = int((t1 == 1).sum())
    forest_loss_pct = (
        100.0 * loss_pixel_count / total_t1_forest_px if total_t1_forest_px > 0 else 0.0
    )

    change_polygons_path = None
    if loss_pixel_count > 0:
        polygons = [
            shape(geom)
            for geom, value in shapes(loss_mask.astype("uint8"), transform=transform)
            if value == 1
        ]
        change_gdf = gpd.GeoDataFrame(geometry=polygons, crs=crs)
        change_polygons_path = "data/cache/change_polygons.geojson"
        change_gdf.to_file(change_polygons_path, driver="GeoJSON")

    return GisResults(
        forest_loss_ha=round(forest_loss_ha, 4),
        forest_loss_pct=round(forest_loss_pct, 2),
        change_polygons_path=change_polygons_path,
        zonal_stats={},  # populated by zonal_stats.py when per-subzone boundaries exist
    )

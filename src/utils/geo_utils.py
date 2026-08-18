"""CRS discipline lives here, and only here: every module that computes an
area/distance must go through `to_equal_area` first. CRS mismatch between
boundary sources, raster sources, and basemaps is the single most likely bug
class in this project (see plan.md's risk section) -- centralizing the
conversion is what keeps that from spreading everywhere.
"""

import geopandas as gpd

# UTM 45N covers Nepal; used whenever we need accurate area/distance in
# meters. Web Mercator (EPSG:3857) is used separately, only for contextily
# basemap rendering.
EQUAL_AREA_CRS = "EPSG:32645"
WEB_MERCATOR_CRS = "EPSG:3857"
WGS84 = "EPSG:4326"


def to_equal_area(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    return gdf.to_crs(EQUAL_AREA_CRS)


def to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs(WGS84)
    return gdf.to_crs(WGS84)

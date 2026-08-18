"""Phase 3: resolves against the real PostGIS-backed admin_boundaries table
with rapidfuzz fuzzy matching, replacing the Phase 1 hardcoded-fixture stub
(kept as resolve_boundary_fixture for local-only runs/tests that shouldn't
need a running Postgres). Same return shape (GeoDataFrame + source string)
so resolve_boundary_node barely changed.
"""

import geopandas as gpd
from geoalchemy2.shape import to_shape
from rapidfuzz import fuzz, process
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.postgis_repo import AdminBoundary, all_boundaries, exact_match_boundaries

_FIXTURE_PATH = "tests/fixtures/sample_boundary.geojson"
_FUZZY_THRESHOLD = 85
_AMBIGUITY_MARGIN = 5  # score gap below which two matches are "too close to call"


def resolve_boundary_fixture(place_name: str) -> tuple[gpd.GeoDataFrame, str]:
    """Phase 1 stub: single hardcoded fixture boundary. Also the fallback
    when Postgres has no boundaries loaded yet."""
    gdf = gpd.read_file(_FIXTURE_PATH)
    normalized = place_name.strip().lower()
    match = gdf[gdf["name_normalized"] == normalized]
    if match.empty:
        match = gdf
    return match, "sample_fixture"


async def resolve_boundary(session: AsyncSession, place_name: str) -> tuple[gpd.GeoDataFrame, str]:
    """Exact match on name_normalized first, then rapidfuzz fuzzy match
    across whatever admin levels are loaded. Nepal has real name-collision
    risk (directly relevant to "Madhuban" -- multiple municipalities share
    names across different provinces/districts post-2017 restructuring), so
    close-scoring multiple matches are flagged as "gadm_ambiguous" rather
    than silently picking the top one.
    """
    normalized = place_name.strip().lower()

    exact_matches = await exact_match_boundaries(session, normalized)
    if len(exact_matches) == 1:
        return _boundaries_to_gdf(exact_matches), "gadm_exact"
    if len(exact_matches) > 1:
        # Same name, different district(s) -- e.g. two municipalities both
        # called "Madhuban". An "exact" name match isn't actually
        # unambiguous here, so it gets the same treatment as a close fuzzy
        # match rather than silently picking whichever row came back first.
        return _boundaries_to_gdf(exact_matches), "gadm_ambiguous"

    candidates = await all_boundaries(session)
    if not candidates:
        return resolve_boundary_fixture(place_name)

    by_name = {b.name_normalized: b for b in candidates}
    matches = process.extract(normalized, list(by_name.keys()), scorer=fuzz.WRatio, limit=3)
    good_matches = [(by_name[name], score) for name, score, _ in matches if score >= _FUZZY_THRESHOLD]

    if not good_matches:
        return resolve_boundary_fixture(place_name)

    if len(good_matches) > 1 and good_matches[0][1] - good_matches[1][1] < _AMBIGUITY_MARGIN:
        return _boundaries_to_gdf([b for b, _ in good_matches]), "gadm_ambiguous"

    return _boundaries_to_gdf([good_matches[0][0]]), "gadm_fuzzy"


def _boundaries_to_gdf(boundaries: list[AdminBoundary]) -> gpd.GeoDataFrame:
    records = [
        {
            "name": b.name,
            "name_normalized": b.name_normalized,
            "admin_level": b.admin_level,
            "gadm_uid": b.gadm_uid,
            "geometry": to_shape(b.geom),
        }
        for b in boundaries
    ]
    return gpd.GeoDataFrame(records, crs="EPSG:4326")

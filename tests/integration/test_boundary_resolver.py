"""Exercises the real PostGIS-backed boundary resolver against the live
gis-disaster-agent-postgis container (docker/docker-compose.yml), loaded
with the synthetic fixture set from scripts/load_gadm_nepal.py -- including
two municipalities both named "Madhuban" in different districts, which is
exactly the kind of real Nepal name-collision this resolver has to handle
without silently guessing.
"""

from src.data.boundary_resolver import resolve_boundary
from src.data.postgis_repo import async_session_factory


async def test_exact_match_single_name_resolves_directly():
    async with async_session_factory() as session:
        gdf, source = await resolve_boundary(session, "Itahari")

    assert source == "gadm_exact"
    assert len(gdf) == 1
    assert gdf.iloc[0]["name"] == "Itahari"


async def test_ambiguous_name_returns_all_matches_not_a_silent_pick():
    async with async_session_factory() as session:
        gdf, source = await resolve_boundary(session, "Madhuban")

    assert source == "gadm_ambiguous"
    assert len(gdf) == 2
    assert set(gdf["name"]) == {"Madhuban"}


async def test_fuzzy_match_catches_a_typo():
    async with async_session_factory() as session:
        gdf, source = await resolve_boundary(session, "Itahri")  # dropped a letter

    assert source == "gadm_fuzzy"
    assert gdf.iloc[0]["name"] == "Itahari"


async def test_unknown_name_falls_back_to_fixture():
    async with async_session_factory() as session:
        gdf, source = await resolve_boundary(session, "Kathmandu")

    assert source == "sample_fixture"
    assert len(gdf) >= 1

"""Phase 2: fetches real GEE-derived rasters when GEE credentials are
configured, falling back to the Phase 1 synthetic sample rasters otherwise
(no credentials in this environment -- see plan.md's credential status).

Only "land_cover_change" analysis (Dynamic World) fits the existing t1/t2
snapshot-diff algorithm in src/gis/change_detection.py, which expects two
classification rasters to compare pixel-by-pixel. Hansen Global Forest
Change (used for "forest_loss") encodes loss year in a single static image
rather than two before/after snapshots -- adapting change_detection.py to
Hansen's lossyear semantics is a documented follow-up, not implemented
here, so "forest_loss" requests always use the sample-data path regardless
of credentials.
"""

import asyncio
from pathlib import Path

import geopandas as gpd

from src.config import settings
from src.data.gee_client import fetch_landcover_raster
from src.data.postgis_repo import async_session_factory
from src.graph.state import AgentState

_SAMPLE_DIR = Path("data/sample")


def _use_sample_data(state: AgentState) -> dict:
    t1 = _SAMPLE_DIR / "t1_landcover.tif"
    t2 = _SAMPLE_DIR / "t2_landcover.tif"
    if not t1.exists() or not t2.exists():
        return {
            "errors": state["errors"]
            + ["sample rasters not found -- run scripts/generate_sample_data.py first"],
            "status": "failed",
        }
    return {
        "raster_refs": {"t1_landcover": str(t1), "t2_landcover": str(t2)},
        "status": "analyzing",
    }


def retrieve_gee_data_node(state: AgentState) -> dict:
    intent = state["parsed_intent"]
    has_credentials = bool(settings.gee_service_account_email and settings.gee_service_account_json)

    if not has_credentials or intent["analysis_type"] != "land_cover_change":
        return _use_sample_data(state)

    try:
        boundary = gpd.read_file(state["boundary_path"])
        bounds = tuple(boundary.total_bounds)

        async def _fetch():
            async with async_session_factory() as session:
                t1_path = await fetch_landcover_raster(
                    session,
                    analysis_type=intent["analysis_type"],
                    bounds=bounds,
                    date_start=intent["date_start"],
                    date_end=intent["date_start"],
                )
                t2_path = await fetch_landcover_raster(
                    session,
                    analysis_type=intent["analysis_type"],
                    bounds=bounds,
                    date_start=intent["date_end"],
                    date_end=intent["date_end"],
                )
                return t1_path, t2_path

        t1_path, t2_path = asyncio.run(_fetch())
    except Exception as exc:  # noqa: BLE001 -- routed to error_handler_node, not raised
        return {"errors": state["errors"] + [f"retrieve_gee_data failed: {exc}"], "status": "failed"}

    return {
        "raster_refs": {"t1_landcover": t1_path, "t2_landcover": t2_path},
        "status": "analyzing",
    }

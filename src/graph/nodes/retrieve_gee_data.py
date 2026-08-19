"""Fetches the rasters the analysis step needs, from real GEE when
credentials are configured and from the synthetic sample rasters otherwise.

Which rasters depends on the analysis type, because the two datasets encode
change differently:

  forest_loss       -> Hansen lossyear + treecover2000 (two bands, one epoch)
  land_cover_change -> Dynamic World t1 + t2 (two dated snapshots)

raster_refs carries a `mode` key so gis_analysis_node knows which algorithm
to dispatch to rather than inferring it from filenames.
"""

import asyncio
from pathlib import Path

import geopandas as gpd

from src.config import settings
from src.data.gee_client import fetch_hansen_bands, fetch_landcover_raster
from src.data.postgis_repo import async_session_factory
from src.graph.state import AgentState

_SAMPLE_DIR = Path("data/sample")


def _has_gee_credentials() -> bool:
    return bool(settings.gee_service_account_email and settings.gee_service_account_json)


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
        "raster_refs": {"mode": "snapshot", "t1_landcover": str(t1), "t2_landcover": str(t2)},
        "status": "analyzing",
    }


def retrieve_gee_data_node(state: AgentState) -> dict:
    intent = state["parsed_intent"]

    if not _has_gee_credentials():
        return _use_sample_data(state)

    try:
        boundary = gpd.read_file(state["boundary_path"])
        bounds = tuple(boundary.total_bounds)

        if intent["analysis_type"] == "forest_loss":

            async def _fetch():
                async with async_session_factory() as session:
                    return await fetch_hansen_bands(
                        session,
                        bounds=bounds,
                        date_start=intent["date_start"],
                        date_end=intent["date_end"],
                    )

            lossyear_path, treecover_path = asyncio.run(_fetch())
            return {
                "raster_refs": {
                    "mode": "hansen",
                    "lossyear": lossyear_path,
                    "treecover": treecover_path,
                },
                "status": "analyzing",
            }

        async def _fetch_snapshots():
            async with async_session_factory() as session:
                t1 = await fetch_landcover_raster(
                    session,
                    analysis_type=intent["analysis_type"],
                    bounds=bounds,
                    date_start=intent["date_start"],
                    date_end=intent["date_start"],
                )
                t2 = await fetch_landcover_raster(
                    session,
                    analysis_type=intent["analysis_type"],
                    bounds=bounds,
                    date_start=intent["date_end"],
                    date_end=intent["date_end"],
                )
                return t1, t2

        t1_path, t2_path = asyncio.run(_fetch_snapshots())
    except Exception as exc:  # noqa: BLE001 -- routed to error_handler_node, not raised
        return {"errors": state["errors"] + [f"retrieve_gee_data failed: {exc}"], "status": "failed"}

    return {
        "raster_refs": {"mode": "snapshot", "t1_landcover": t1_path, "t2_landcover": t2_path},
        "status": "analyzing",
    }

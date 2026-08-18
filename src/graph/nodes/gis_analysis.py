import asyncio

import geopandas as gpd

from src.data.postgis_repo import async_session_factory, record_gis_result
from src.gis.change_detection import detect_forest_loss
from src.graph.state import AgentState


def gis_analysis_node(state: AgentState) -> dict:
    try:
        boundary = gpd.read_file(state["boundary_path"])
        results = detect_forest_loss(
            state["raster_refs"]["t1_landcover"],
            state["raster_refs"]["t2_landcover"],
            boundary,
        )
    except Exception as exc:  # noqa: BLE001 -- routed to error_handler_node, not raised
        return {"errors": state["errors"] + [f"gis_analysis failed: {exc}"], "status": "failed"}

    zone_name = boundary.iloc[0].get("name") or state["parsed_intent"]["place_name"]

    async def _record():
        async with async_session_factory() as session:
            await record_gis_result(
                session,
                job_id=state["job_id"],
                zone_name=zone_name,
                forest_loss_ha=results["forest_loss_ha"],
                forest_loss_pct=results["forest_loss_pct"],
                landcover_stats=results["zonal_stats"],
            )

    asyncio.run(_record())

    return {"gis_results": results, "status": "predicting_risk"}

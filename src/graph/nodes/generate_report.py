import asyncio
from datetime import UTC, datetime
from pathlib import Path

from src.config import settings
from src.data.postgis_repo import async_session_factory, upsert_job_history
from src.graph.state import AgentState
from src.reports.report_builder import render_report

_LIMITATIONS_NOTE = (
    "The disaster risk score is a heuristic weighted composite index (forest-loss %, "
    "slope, rainfall intensity), not a model trained on labeled historical disaster "
    "outcomes -- no such dataset exists at municipality granularity for this area yet. "
    "Treat risk classes as indicative, not predictive. Boundary resolution uses a "
    "synthetic fixture set of Nepal municipalities (standing in for a full GADM v4.1 "
    "download) with real fuzzy-matching and ambiguity detection. Land-cover, slope, and "
    "rainfall inputs use synthetic sample rasters unless real Google Earth Engine "
    "credentials are configured (GEE_SERVICE_ACCOUNT_EMAIL/_JSON), in which case "
    "land-cover-change analysis draws on live Dynamic World imagery."
)


def _dataset_note(state: AgentState) -> str:
    t1_path = state["raster_refs"].get("t1_landcover", "")
    using_real_gee = bool(settings.gee_service_account_email) and "data/sample" not in t1_path
    landcover_source = "Google Earth Engine (Dynamic World)" if using_real_gee else "synthetic sample rasters"

    using_real_terrain = Path("data/sample/dem.tif").exists()
    terrain_source = (
        "gdaldem-derived slope + synthetic rainfall surface"
        if using_real_terrain
        else "placeholder slope/rainfall constants"
    )
    return f"Land cover: {landcover_source}. Terrain/rainfall: {terrain_source}."


def generate_report_node(state: AgentState) -> dict:
    intent = state["parsed_intent"]
    paths = render_report(
        job_id=state["job_id"],
        zone_name=intent["place_name"],
        date_start=intent["date_start"],
        date_end=intent["date_end"],
        narrative_text=state["narrative_text"],
        boundary_source=state["boundary_source"],
        dataset_note=_dataset_note(state),
        gis_results=state["gis_results"],
        risk_results=state["zone_risks"],
        risk_explanations=state["rag_context"],
        static_map_path=state["map_paths"]["static_png"] if state["map_paths"] else None,
        limitations_note=_LIMITATIONS_NOTE,
        out_dir=settings.outputs_dir,
    )

    async def _record():
        async with async_session_factory() as session:
            await upsert_job_history(
                session,
                state["job_id"],
                status="done",
                report_path=paths["html"],
                map_paths_json=state["map_paths"] or {},
                completed_at=datetime.now(UTC),
            )

    asyncio.run(_record())

    return {"report_path": paths["html"], "status": "done"}

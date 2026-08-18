import asyncio
from pathlib import Path

from src.data.boundary_resolver import resolve_boundary
from src.data.postgis_repo import async_session_factory
from src.graph.state import AgentState


def resolve_boundary_node(state: AgentState) -> dict:
    place_name = state["parsed_intent"]["place_name"]

    async def _run():
        async with async_session_factory() as session:
            return await resolve_boundary(session, place_name)

    try:
        # graph.invoke() always runs off the asyncio event loop (a plain
        # script's main thread has none), so asyncio.run() here is safe --
        # same reasoning as autonomous-dev-agent's rag_tools.py.
        boundary, source = asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001 -- routed to error_handler_node, not raised
        return {"errors": state["errors"] + [f"resolve_boundary failed: {exc}"], "status": "failed"}

    if source == "gadm_ambiguous":
        names = ", ".join(boundary["name"].tolist())
        return {
            "errors": state["errors"] + [f"boundary name '{place_name}' is ambiguous: {names}"],
            "status": "failed",
        }

    boundary_path = "data/cache/resolved_boundary.geojson"
    Path("data/cache").mkdir(parents=True, exist_ok=True)
    boundary.to_file(boundary_path, driver="GeoJSON")
    return {
        "boundary_path": boundary_path,
        "boundary_source": source,
        "status": "retrieving_data",
    }

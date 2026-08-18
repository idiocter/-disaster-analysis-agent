import asyncio

from src.config import settings
from src.data.postgis_repo import async_session_factory, upsert_job_history
from src.graph.state import AgentState, ParsedIntent
from src.utils.llm import call_structured

_SYSTEM = """Extract a structured query from a natural-language GIS disaster
analysis request. If a year range is given (e.g. "2005-2020"), use Jan 1 of
the start year and Dec 31 of the end year as ISO dates."""

_SCHEMA = {
    "type": "object",
    "properties": {
        "place_name": {"type": "string"},
        "date_start": {"type": "string", "description": "ISO date YYYY-MM-DD"},
        "date_end": {"type": "string", "description": "ISO date YYYY-MM-DD"},
        "analysis_type": {"type": "string", "enum": ["forest_loss", "land_cover_change"]},
    },
    "required": ["place_name", "date_start", "date_end", "analysis_type"],
}


def parse_query_node(state: AgentState) -> dict:
    result = call_structured(
        model=settings.parser_model,
        system=_SYSTEM,
        user_content=state["raw_query"],
        output_schema=_SCHEMA,
        output_tool_name="submit_parsed_query",
    )
    parsed_intent: ParsedIntent = {
        "place_name": result["place_name"],
        "date_start": result["date_start"],
        "date_end": result["date_end"],
        "analysis_type": result["analysis_type"],
    }

    async def _record():
        async with async_session_factory() as session:
            await upsert_job_history(
                session,
                state["job_id"],
                raw_query=state["raw_query"],
                parsed_intent_json=dict(parsed_intent),
                status="resolving_boundary",
            )

    asyncio.run(_record())

    return {"parsed_intent": parsed_intent, "status": "resolving_boundary"}

"""Reached when a fallible I/O node (resolve_boundary, retrieve_gee_data,
gis_analysis) sets status="failed". Phase 1: terminates the run with the
accumulated error log. Later phases can make this smarter -- e.g. still
render a partial report from whatever succeeded -- but failing loudly with a
clear error list beats silently producing a wrong report.
"""

import asyncio
from datetime import UTC, datetime

from src.data.postgis_repo import async_session_factory, upsert_job_history
from src.graph.state import AgentState


def error_handler_node(state: AgentState) -> dict:
    async def _record():
        async with async_session_factory() as session:
            await upsert_job_history(
                session,
                state["job_id"],
                raw_query=state["raw_query"],
                status="failed",
                errors_json={"errors": state["errors"]},
                completed_at=datetime.now(UTC),
            )

    asyncio.run(_record())

    return {"status": "failed"}

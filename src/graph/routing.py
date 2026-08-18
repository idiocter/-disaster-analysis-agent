"""Conditional-edge routing. Fallible I/O nodes (resolve_boundary,
retrieve_gee_data, gis_analysis) set status="failed" on error instead of
raising; this routes those runs to error_handler_node instead of letting an
exception crash the whole graph invocation.
"""

from typing import Literal

from src.graph.state import AgentState

RouteAfterFallible = Literal["ok", "error"]


def route_after_fallible(state: AgentState) -> RouteAfterFallible:
    return "error" if state["status"] == "failed" else "ok"

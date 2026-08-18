"""Phase 6: real pgvector similarity search over rag_corpus/ (methodology
docs, historical/reference risk-factor material), replacing the Phase 1
pass-through. Retrieved snippets are appended to rag_context alongside the
risk model's own explain() output from predict_risk_node, so
generate_narrative_node sees both without needing to know where either
came from.
"""

import asyncio

from src.data.postgis_repo import async_session_factory
from src.graph.state import AgentState
from src.rag.retriever import rag_retrieve


def rag_retrieve_node(state: AgentState) -> dict:
    intent = state["parsed_intent"]
    top_risk_class = state["zone_risks"][0]["risk_class"] if state["zone_risks"] else ""
    query = (
        f"{intent['analysis_type']} disaster risk factors for {intent['place_name']}, "
        f"{top_risk_class} risk"
    )

    async def _run():
        async with async_session_factory() as session:
            return await rag_retrieve(session, query, k=3)

    # graph.invoke() always runs off the asyncio event loop (a plain
    # script's main thread has none), so asyncio.run() here is safe -- same
    # reasoning as resolve_boundary_node.
    retrieved = asyncio.run(_run())

    return {"rag_context": state["rag_context"] + retrieved, "status": "narrating"}

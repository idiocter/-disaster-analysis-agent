import asyncio

from src.data.postgis_repo import async_session_factory, record_risk_result
from src.graph.state import AgentState
from src.models.risk_model import RuleBasedRiskModel

_model = RuleBasedRiskModel()


def predict_risk_node(state: AgentState) -> dict:
    zone_risks = _model.predict(state["zone_features"])
    explanations = [_model.explain(risk) for risk in zone_risks]

    async def _record():
        async with async_session_factory() as session:
            for risk in zone_risks:
                await record_risk_result(
                    session,
                    job_id=state["job_id"],
                    zone_name=risk["zone_name"],
                    risk_score=risk["risk_score"],
                    risk_class=risk["risk_class"],
                    contributions=risk["contributions"],
                    model_version=_model.model_version,
                )

    asyncio.run(_record())

    return {
        "zone_risks": zone_risks,
        "rag_context": state["rag_context"] + explanations,  # cheap Phase-1 stand-in for real RAG
        "status": "visualizing",
    }

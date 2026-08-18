from src.config import settings
from src.graph.state import AgentState
from src.utils.llm import call_text

_SYSTEM = """You are the Report Narrative agent in a GIS disaster analysis
pipeline. Given computed land-cover-change and disaster-risk statistics,
plus retrieved background/methodology context, write a concise (3-5
sentence) executive-summary paragraph for a report. Be factual and
specific with numbers. Where the retrieved context explains *why* a factor
matters (e.g. why deforestation on slopes raises landslide risk), work
that reasoning into the paragraph rather than just restating the score --
that's the whole point of having it available. Do not overstate confidence
in the risk score -- it is a heuristic composite index, not a validated
predictive model, and the paragraph should reflect that."""


def generate_narrative_node(state: AgentState) -> dict:
    gis = state["gis_results"]
    context_lines = "\n\n".join(state["rag_context"])
    intent = state["parsed_intent"]

    user_content = (
        f"Area: {intent['place_name']}\n"
        f"Period: {intent['date_start']} to {intent['date_end']}\n"
        f"Forest loss: {gis['forest_loss_ha']} ha ({gis['forest_loss_pct']}% of {intent['place_name']}'s "
        f"t1 forest cover)\n\n"
        f"Risk assessment breakdown and retrieved background context:\n{context_lines}"
    )
    narrative_text = call_text(model=settings.narrative_model, system=_SYSTEM, user_content=user_content)
    return {"narrative_text": narrative_text, "status": "reporting"}

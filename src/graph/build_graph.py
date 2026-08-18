from langgraph.graph import END, StateGraph

from src.graph.nodes.error_handler import error_handler_node
from src.graph.nodes.feature_engineering import feature_engineering_node
from src.graph.nodes.generate_narrative import generate_narrative_node
from src.graph.nodes.generate_report import generate_report_node
from src.graph.nodes.gis_analysis import gis_analysis_node
from src.graph.nodes.parse_query import parse_query_node
from src.graph.nodes.predict_risk import predict_risk_node
from src.graph.nodes.rag_retrieve import rag_retrieve_node
from src.graph.nodes.resolve_boundary import resolve_boundary_node
from src.graph.nodes.retrieve_gee_data import retrieve_gee_data_node
from src.graph.nodes.visualize import visualize_node
from src.graph.routing import route_after_fallible
from src.graph.state import AgentState


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("parse_query", parse_query_node)
    graph.add_node("resolve_boundary", resolve_boundary_node)
    graph.add_node("retrieve_gee_data", retrieve_gee_data_node)
    graph.add_node("gis_analysis", gis_analysis_node)
    graph.add_node("feature_engineering", feature_engineering_node)
    graph.add_node("predict_risk", predict_risk_node)
    graph.add_node("visualize", visualize_node)
    graph.add_node("rag_retrieve", rag_retrieve_node)
    graph.add_node("generate_narrative", generate_narrative_node)
    graph.add_node("generate_report", generate_report_node)
    graph.add_node("error_handler", error_handler_node)

    graph.set_entry_point("parse_query")
    graph.add_edge("parse_query", "resolve_boundary")

    graph.add_conditional_edges(
        "resolve_boundary", route_after_fallible, {"ok": "retrieve_gee_data", "error": "error_handler"}
    )
    graph.add_conditional_edges(
        "retrieve_gee_data", route_after_fallible, {"ok": "gis_analysis", "error": "error_handler"}
    )
    graph.add_conditional_edges(
        "gis_analysis", route_after_fallible, {"ok": "feature_engineering", "error": "error_handler"}
    )

    graph.add_edge("feature_engineering", "predict_risk")
    graph.add_edge("predict_risk", "visualize")
    graph.add_edge("visualize", "rag_retrieve")
    graph.add_edge("rag_retrieve", "generate_narrative")
    graph.add_edge("generate_narrative", "generate_report")
    graph.add_edge("generate_report", END)
    graph.add_edge("error_handler", END)

    return graph.compile()

import geopandas as gpd

from src.graph.state import AgentState
from src.models.features import build_zone_features


def feature_engineering_node(state: AgentState) -> dict:
    boundary = gpd.read_file(state["boundary_path"])
    zone_name = boundary.iloc[0].get("name") or state["parsed_intent"]["place_name"]
    zone_features = build_zone_features(zone_name, state["gis_results"], boundary=boundary)
    return {"zone_features": zone_features, "status": "predicting_risk"}

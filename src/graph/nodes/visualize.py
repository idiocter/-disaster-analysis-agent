import geopandas as gpd

from src.config import settings
from src.graph.state import AgentState
from src.viz.map_builder import build_interactive_map
from src.viz.static_map import build_static_map


def visualize_node(state: AgentState) -> dict:
    boundary = gpd.read_file(state["boundary_path"])
    risk_by_zone = {r["zone_name"]: r for r in state["zone_risks"]}
    change_path = state["gis_results"]["change_polygons_path"]

    out_dir = f"{settings.outputs_dir}/{state['job_id']}/maps"
    interactive_path = build_interactive_map(
        boundary, change_path, risk_by_zone, f"{out_dir}/interactive_map.html"
    )
    static_path = build_static_map(
        boundary, change_path, f"{out_dir}/static_map.png", risk_by_zone=risk_by_zone
    )

    return {
        "map_paths": {"interactive_html": interactive_path, "static_png": static_path},
        "status": "narrating",
    }

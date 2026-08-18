from typing import Literal, TypedDict


class ParsedIntent(TypedDict):
    place_name: str
    date_start: str  # ISO date, e.g. "2005-01-01"
    date_end: str
    analysis_type: str  # e.g. "forest_loss", "land_cover_change"


class GisResults(TypedDict):
    forest_loss_ha: float
    forest_loss_pct: float
    change_polygons_path: str | None
    zonal_stats: dict


class MapPaths(TypedDict):
    interactive_html: str
    static_png: str | None


JobStatus = Literal[
    "parsing",
    "resolving_boundary",
    "retrieving_data",
    "analyzing",
    "predicting_risk",
    "visualizing",
    "narrating",
    "reporting",
    "done",
    "failed",
]


class AgentState(TypedDict):
    job_id: str
    raw_query: str

    parsed_intent: ParsedIntent | None
    boundary_path: str | None  # path to a cached GeoJSON of the resolved boundary
    boundary_source: str  # "sample_fixture" | "gadm" | "osm"

    # Raster paths, not arrays -- keeps state small/serializable. Populated by
    # retrieve_gee_data_node (Phase 2+); Phase 1 points these at data/sample/.
    raster_refs: dict[str, str]

    gis_results: GisResults | None
    # Raw per-zone feature/risk breakdowns. Phase 1 keeps these in-memory;
    # Phase 3 additionally persists them to PostGIS gis_results/risk_results
    # tables (see plan.md), which is a storage concern layered on top of
    # this, not a replacement for it.
    zone_features: list[dict]
    zone_risks: list[dict]
    map_paths: MapPaths | None

    rag_context: list[str]
    narrative_text: str | None
    report_path: str | None

    errors: list[str]
    status: JobStatus

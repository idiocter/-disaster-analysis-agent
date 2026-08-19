"""Phase 1 CLI: runs the full pipeline against local sample data (no GEE or
PostGIS required yet).

Usage:
    python -m src.main run-query "Analyze forest loss in Madhuban from 2005-2020"
"""

import uuid

import typer

from src.graph.build_graph import build_graph
from src.utils.usage import format_usage
from src.graph.state import AgentState
from src.utils.logging_config import configure_logging

app = typer.Typer()


@app.command("run-query")
def run_query(query: str) -> None:
    configure_logging()

    initial_state: AgentState = {
        "job_id": str(uuid.uuid4()),
        "raw_query": query,
        "parsed_intent": None,
        "boundary_path": None,
        "boundary_source": "",
        "raster_refs": {},
        "gis_results": None,
        "zone_features": [],
        "zone_risks": [],
        "map_paths": None,
        "rag_context": [],
        "narrative_text": None,
        "report_path": None,
        "errors": [],
        "status": "parsing",
    }

    graph = build_graph()
    final_state = graph.invoke(initial_state, config={"recursion_limit": 25})

    print(f"\n--- status: {final_state['status']} ---")
    if final_state["errors"]:
        print("errors:")
        for err in final_state["errors"]:
            print(f"  - {err}")
        raise typer.Exit(code=1)

    print(f"\nparsed intent: {final_state['parsed_intent']}")
    print(f"\ngis results: {final_state['gis_results']}")
    print("\nrisk assessment:")
    for line in final_state["rag_context"]:
        print(f"  {line}")
    print(f"\nnarrative:\n{final_state['narrative_text']}")
    print(f"\n--- token usage ---\n{format_usage()}")
    print(f"\nreport: {final_state['report_path']}")
    if final_state["map_paths"]:
        print(f"interactive map: {final_state['map_paths']['interactive_html']}")


if __name__ == "__main__":
    app()

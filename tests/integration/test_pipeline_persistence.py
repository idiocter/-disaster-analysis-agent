"""Exercises the DB-writing pipeline nodes (gis_analysis, feature_engineering,
predict_risk, error_handler) against the real PostGIS container, using the
Phase 1 sample rasters and fixture boundary so no GEE/LLM credentials are
needed to run this chain end-to-end.

Test functions here are plain `def`, NOT `async def`: the nodes bridge
their own async DB calls internally via asyncio.run() (safe from a genuine
sync caller, e.g. graph.invoke() running in a script's main thread or a
worker thread -- see resolve_boundary_node's docstring), but that bridge
breaks if called from inside a pytest-asyncio test's already-running event
loop. Calling the sync node functions from sync tests matches how
production actually invokes them.
"""

import asyncio
import uuid

from sqlalchemy import select

from src.data.models import GisResultRow, JobHistory, RiskResultRow
from src.data.postgis_repo import async_session_factory
from src.graph.nodes.error_handler import error_handler_node
from src.graph.nodes.feature_engineering import feature_engineering_node
from src.graph.nodes.gis_analysis import gis_analysis_node
from src.graph.nodes.predict_risk import predict_risk_node


def _base_state(job_id: str) -> dict:
    return {
        "job_id": job_id,
        "raw_query": "Analyze forest loss in Madhuban from 2005-2020",
        "parsed_intent": {
            "place_name": "Madhuban",
            "date_start": "2005-01-01",
            "date_end": "2020-12-31",
            "analysis_type": "forest_loss",
        },
        "boundary_path": "tests/fixtures/sample_boundary.geojson",
        "boundary_source": "sample_fixture",
        "raster_refs": {
            "t1_landcover": "data/sample/t1_landcover.tif",
            "t2_landcover": "data/sample/t2_landcover.tif",
        },
        "gis_results": None,
        "zone_features": [],
        "zone_risks": [],
        "map_paths": None,
        "rag_context": [],
        "narrative_text": None,
        "report_path": None,
        "errors": [],
        "status": "analyzing",
    }


def test_gis_analysis_and_predict_risk_persist_rows():
    job_id = str(uuid.uuid4())
    state = _base_state(job_id)

    state.update(gis_analysis_node(state))
    state.update(feature_engineering_node(state))
    state.update(predict_risk_node(state))

    async def _verify():
        async with async_session_factory() as session:
            gis_result = (
                (await session.execute(select(GisResultRow).where(GisResultRow.job_id == job_id)))
                .scalars()
                .first()
            )
            risk_result = (
                (await session.execute(select(RiskResultRow).where(RiskResultRow.job_id == job_id)))
                .scalars()
                .first()
            )
            return gis_result, risk_result

    gis_result, risk_result = asyncio.run(_verify())

    assert gis_result is not None
    assert gis_result.zone_name == "Madhuban"
    assert gis_result.forest_loss_ha > 0

    assert risk_result is not None
    assert risk_result.zone_name == "Madhuban"
    assert risk_result.risk_class in {"Low", "Medium", "High", "Very High"}


def test_error_handler_persists_failed_job_history():
    job_id = str(uuid.uuid4())
    state = _base_state(job_id)
    state["errors"] = ["gis_analysis failed: synthetic test error"]

    error_handler_node(state)

    async def _verify():
        async with async_session_factory() as session:
            return await session.get(JobHistory, job_id)

    job = asyncio.run(_verify())

    assert job is not None
    assert job.status == "failed"
    assert "synthetic test error" in str(job.errors_json)
    assert job.completed_at is not None

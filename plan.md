# GIS Disaster Analysis Agent — Plan

A multi-agent system that takes a natural-language query (e.g. "Analyze forest loss in Madhuban from 2005–2020 and identify areas with increased disaster risk") and autonomously retrieves datasets, runs GIS analysis, predicts disaster risk, generates a map, and saves a report.

**Status:** **All 6 phases code-complete**, with everything not requiring `ANTHROPIC_API_KEY` verified against real local infra: a live `gis-disaster-agent-postgis` container (PostGIS 3.4 + pgvector 0.8), real `gdaldem` slope derivation, real semantic search via local `sentence-transformers`, and the real `earthengine-api` package with only the network call itself mocked (no GEE service account configured). 26/26 tests passing. Only the two LLM nodes (`parse_query`, `generate_narrative`) are blocked on `ANTHROPIC_API_KEY`.

**Flow:** NL query → retrieve datasets → resolve boundary → GIS change analysis → risk prediction → map → narrative → saved report.

**Tech stack:** Python, GeoPandas, Rasterio, GDAL (install geospatial stack via **conda-forge**, not pip, to avoid Mac binary mismatches), LangGraph, Google Earth Engine API (service account auth), PostGIS + pgvector (same Postgres container), Folium/Matplotlib/Contextily, Jinja2 + WeasyPrint.

## Architecture

- **LangGraph graph**, 10 nodes: `parse_query → resolve_boundary → retrieve_gee_data → gis_analysis → feature_engineering → predict_risk → visualize → rag_retrieve → generate_narrative → generate_report`, with an `error_handler_node` reachable by conditional edges after fallible I/O nodes (boundary resolution, GEE calls) so partial failures degrade gracefully into a partial report rather than crashing.
- **State** passes file paths/URIs for rasters, not raw arrays (keeps state serializable/checkpointable — use LangGraph checkpointing since GEE exports can take minutes).
- **Boundary resolution** (`src/data/boundary_resolver.py`): GADM v4.1 Nepal shapefiles loaded into PostGIS `admin_boundaries`; normalize + exact-match, fall back to fuzzy match (rapidfuzz) at municipality/ward level; ambiguous matches route to an LLM disambiguation step or a "clarification needed" terminal state — must exist from Phase 1, given real name-collision risk in Nepal (directly relevant to "Madhuban").
- **GEE integration** (`src/data/gee_client.py`, `gee_datasets.py`): service-account auth; dataset registry — **Hansen Global Forest Change** for forest-loss-specific queries (covers 2000–present, per-pixel `lossyear`), **Dynamic World**/**ESA WorldCover** for broader land-cover class change (unreliable before ~2015 — must be surfaced in the report's limitations section, not silently ignored), **SRTM DEM** for slope, **CHIRPS/ERA5** for rainfall. Content-hash-based local cache with a PostGIS `raster_cache_index` as source of truth.
- **GIS analysis** (`src/gis/`): equal-area CRS reprojection before any area/stat computation (helper enforced everywhere — CRS mismatch between GADM/GEE/DEM/contextily is the single most likely bug class), zonal stats via `rasterstats` against boundary polygons, vectorized change polygons via `rasterio.features.shapes`.
- **Risk model** (`src/models/risk_model.py`): swappable `RiskModel` interface. **v1 = `RuleBasedRiskModel`** — transparent weighted composite index (forest-loss %, slope, rainfall intensity, river proximity) with an `explain()` method for per-zone contribution breakdown feeding the narrative. Explicitly NOT a trained classifier in v1 (no labeled Nepal disaster-incident dataset available) — v1.5 regression upgrade path documented with real candidate data sources (DesInventar, BIPAD/NDRRMA), not fabricated.
- **Visualization**: Folium interactive HTML + Matplotlib/Contextily static PNG (Web Mercator reprojection for the latter), both built from the same underlying GeoDataFrame for consistency.
- **Report**: Jinja2 template → WeasyPrint PDF + standalone HTML, sections include an explicit "Methodology & Limitations" (auto-populated with the data-availability caveats above) so the risk model is never presented as more validated than it is.
- **RAG**: pgvector in the same Postgres instance (avoid a second DB), corpus = historical Nepal environmental/disaster reports + GIS methodology docs + the system's own past generated reports (self-ingestion for longitudinal follow-up queries).
- **Data model (PostGIS):** `admin_boundaries`, `raster_cache_index`, `vector_cache_index`, `gis_results`, `risk_results`, `job_history`, `rag_documents`/`rag_chunks`.

## Folder structure

```
src/
├── config.py, main.py (CLI entry, typer/click)
├── graph/  (state.py, build_graph.py, nodes/{parse_query,resolve_boundary,retrieve_gee_data,gis_analysis,feature_engineering,predict_risk,visualize,rag_retrieve,generate_narrative,generate_report,error_handler}.py)
├── data/   (boundary_resolver.py, gadm_loader.py, gee_client.py, gee_datasets.py, cache.py, postgis_repo.py)
├── gis/    (reproject.py, change_detection.py, zonal_stats.py, overlay.py)
├── models/ (features.py, risk_model.py, regression_model.py, model_registry.py)
├── viz/    (map_builder.py, static_map.py)
├── reports/(report_builder.py, templates/report_template.html.j2)
├── rag/    (ingest.py, retriever.py, embeddings.py)
└── utils/  (logging_config.py, geo_utils.py)
docker/ (docker-compose.yml, postgres/Dockerfile [postgis + pgvector], init-db/001_init_extensions.sql)
data/ (raw/, cache/, sample/)   outputs/   rag_corpus/
scripts/ (init_postgis_schema.py, load_gadm_nepal.py, ingest_rag_docs.py)
tests/ (unit/, integration/, fixtures/sample_boundary.geojson)
.env.example, pyproject.toml, environment.yml (conda geospatial deps), README.md
```

## Phased build order

1. **Skeleton graph, local sample data** — hardcoded Madhuban boundary fixture + local sample GeoTIFFs standing in for GEE, all 10 nodes wired. Demo: `python -m src.main run-query "Analyze forest loss in Madhuban from 2005-2020"` (needs `ANTHROPIC_API_KEY`).
2. **Real GEE integration** — `src/data/gee_client.py`/`gee_datasets.py`/`cache.py` built against the real `earthengine-api`; dataset registry correctly routes forest_loss→Hansen and land_cover_change→Dynamic World, with an explicit pre-2015 rejection for the latter. Content-hash caching against PostGIS `raster_cache_index` verified end-to-end (10/10 tests) with only the actual `computePixels` network call mocked (no GEE service account here).
3. **PostGIS integration** — real `gis-disaster-agent-postgis` container (PostGIS 3.4 + pgvector 0.8, custom Dockerfile), full schema created via `scripts/init_postgis_schema.py`, a synthetic 5-municipality fixture loaded via `scripts/load_gadm_nepal.py` (including two municipalities both named "Madhuban" in different districts). Boundary resolver verified for real: exact match, **ambiguity detection on same-name-different-district collisions** (a real bug caught and fixed during this build — exact match originally silently picked the first row), fuzzy-match typo correction, and fallback (10/10 tests). `gis_results`/`risk_results`/`job_history` all persist for real.
4. **Real prediction model** — `src/gis/terrain.py` derives real slope via `gdaldem` from a synthetic DEM (a ridge, not a flat plane, so the derivation has real variation to compute); rainfall now a real zonal mean of a synthetic rainfall raster, replacing both Phase 1 placeholder constants. Verified: computed values differ from the placeholders and fall in valid ranges (4/4 tests).
5. **Visualization + report (full fidelity)** — Folium map now a real risk-colored choropleth with a legend and per-zone popups showing the contribution breakdown; static map uses the same color palette for visual consistency. Verified against a real basemap render (screenshot-checked) plus 3 unit tests.
6. **RAG + refined narrative** — `src/rag/{ingest,retriever,embeddings}.py`, local `sentence-transformers`, real pgvector search. A 2-document sample corpus (`rag_corpus/`) ingested and verified to surface the correct chunk for a semantic query; `generate_narrative_node`'s prompt now explicitly asks the model to work retrieved *reasoning* (not just restate the score) into the narrative (6/6 tests).

## Key risks to design around from day one

- GEE auth/quota — must register the service account for Earth Engine access specifically, not just generic GCP; auto-switch to async Export+polling above sync payload limits; cache aggressively.
- CRS mismatches — mandatory reproject/assert pattern in `geo_utils.py` used everywhere.
- Large-raster memory — always windowed reads clipped to AOI bbox, never full-country arrays into numpy.
- Boundary name ambiguity — fuzzy-match + LLM disambiguation required from Phase 1.
- GADM vintage vs. post-2017 Nepal restructuring — verify GADM 4.1 currency, document OSM fallback.
- GDAL/Rasterio/GeoPandas install pain on Mac — use conda-forge, document `environment.yml` separately from `requirements.txt`.
- Risk-model realism — heuristic index, not a validated predictive model; must say so in the report itself.

## Verification

Each phase has a runnable `python -m src.main run-query "..."` demo — verify by inspecting the generated `outputs/<job_id>/report.pdf`/map, plus `pytest` unit tests for boundary resolution, change detection, zonal stats, and risk-model scoring against fixtures.

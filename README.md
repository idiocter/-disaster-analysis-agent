# GIS Disaster Analysis Agent

Takes a natural-language query (e.g. "Analyze forest loss in Madhuban from 2005-2020
and identify areas with increased disaster risk") and autonomously retrieves
datasets, runs GIS change-detection analysis, predicts disaster risk, generates
a map, and saves a report.

See [`plan.md`](./plan.md) for the full architecture and phased build order. All 6 phases
are code-complete; see plan.md for exactly what's been verified against real local infra
vs. what's blocked on `ANTHROPIC_API_KEY`/GEE credentials.

## Setup

The geospatial stack (GDAL/rasterio/geopandas/WeasyPrint) is installed via conda-forge,
not pip, to avoid the Mac binary-mismatch issues those packages are notorious for.

```bash
mamba env create -f environment.yml
mamba activate gis-disaster-agent
cp .env.example .env
# fill in ANTHROPIC_API_KEY (required for everything), GEE_SERVICE_ACCOUNT_EMAIL/_JSON
# (Phase 2+, optional -- falls back to sample data without it) in .env
python scripts/generate_sample_data.py   # synthetic t1/t2 land-cover, DEM, rainfall rasters
```

### PostGIS + pgvector

```bash
cd docker && docker-compose build postgis && docker-compose up -d postgis && cd ..
python scripts/init_postgis_schema.py
python scripts/load_gadm_nepal.py        # synthetic Nepal municipality fixture set
python scripts/ingest_rag_docs.py        # Phase 6: sample RAG corpus
```

## Demos

**Phase 1/2/3/4/5 -- full pipeline, sample data + real PostGIS boundary resolution:**
```bash
python -m src.main run-query "Analyze forest loss in Madhuban from 2005-2020"
```
Produces `outputs/<job_id>/report.pdf` (risk-colored map + narrative) and
`outputs/<job_id>/maps/interactive_map.html`.

**Phase 2 with real GEE** (needs `GEE_SERVICE_ACCOUNT_EMAIL`/`_JSON` and the service account
registered for Earth Engine access in the GEE console):
```bash
python -m src.main run-query "Analyze land cover change in Itahari from 2018-2023"
```
`land_cover_change` queries with real credentials configured fetch live Dynamic World
imagery instead of sample rasters; `forest_loss` queries always use sample data for now
(see plan.md's note on why Hansen's lossyear encoding doesn't fit the current
change-detection algorithm).

## Tests

```bash
pytest
```
Needs the `gis-disaster-agent-postgis` container running for the integration suite;
GEE/Docker-independent unit tests run regardless.

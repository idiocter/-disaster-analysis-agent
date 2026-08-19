# GIS Disaster Analysis Agent

> **Branch note:** this `openai` branch runs on the OpenAI API (GPT models).
> The `main` branch is the Anthropic/Claude version. Only the LLM layer differs.

An AI agent that turns a natural-language query — e.g. "Analyze forest loss in Madhuban
from 2005-2020 and identify areas with increased disaster risk" — into a full geospatial
analysis: it resolves the place name, retrieves land-cover and terrain data, runs
change-detection and slope/rainfall analysis, scores disaster risk, and produces an
interactive map plus a PDF report.

## What it does

You ask a question in plain English — *"Analyze forest loss in Itahari from 2005-2020 and
identify areas with increased disaster risk."* It then:

1. **Parses the sentence** into a place, a date range, and an analysis type
2. **Finds the place** in a PostGIS boundary database, with fuzzy matching for typos — and
   refuses to guess when two municipalities share a name
3. **Pulls satellite data** (Hansen Global Forest Change, Dynamic World) for that exact area
4. **Measures forest loss** in hectares and percentage, computed in an equal-area projection
   so the figures aren't distorted by latitude
5. **Derives terrain features** — slope from a DEM, rainfall averages over the zone
6. **Scores disaster risk** from those factors, with a per-factor contribution breakdown
7. **Draws maps** — an interactive HTML one and a static render for the report
8. **Writes a PDF report**, drawing on a reference-document corpus so it explains *why* a
   factor matters rather than only reporting the number

The risk score is a transparent weighted index, presented as an indicative screening tool
rather than a validated prediction — the report says so explicitly.

## Features

- **Natural-language queries** — parses place name, date range, and analysis type from free text
- **Boundary resolution** — PostGIS-backed, with fuzzy matching and ambiguity detection for same-named locations
- **Remote sensing** — Google Earth Engine integration (Hansen Global Forest Change, Dynamic World) with local caching
- **GIS analysis** — forest-loss/land-cover change detection, slope derivation, zonal statistics
- **Transparent risk scoring** — a weighted composite index with a per-factor explanation, not a black-box model
- **Retrieval-grounded reporting** — narrative generation draws on a reference-document corpus via RAG
- **Interactive + static maps** and a PDF report with an explicit methodology/limitations section

## Tech stack

Python, LangGraph, GeoPandas, Rasterio, GDAL, PostGIS + pgvector, Google Earth Engine API, Folium, WeasyPrint.

## Setup

Requires Docker Desktop running. The geospatial stack is installed via conda-forge to avoid
platform binary-compatibility issues.

```bash
mamba env create -f environment.yml
mamba activate gis-disaster-agent
cp .env.example .env
# add OPENAI_API_KEY; GEE credentials are optional (falls back to sample data)
```

Then the one-time data setup — results persist in the Docker volume:

```bash
python scripts/generate_sample_data.py     # synthetic land-cover, DEM, rainfall rasters

cd docker && docker-compose up -d postgis && cd ..   # host port 5434
python scripts/init_postgis_schema.py      # create tables
python scripts/load_gadm_nepal.py          # load municipality boundaries
python scripts/ingest_rag_docs.py          # embed rag_corpus/ into pgvector
```

## Usage

```bash
python -m src.main run-query "Analyze forest loss in Itahari from 2005-2020"
```

Writes to `outputs/<job_id>/`:

| File | Contents |
|---|---|
| `report.pdf` / `report.html` | narrative, statistics, risk breakdown, methodology & limitations |
| `maps/interactive_map.html` | Folium map, risk-colored with per-zone popups |
| `maps/static_map.png` | Contextily basemap render, embedded in the report |

The run also prints the resolved intent, forest-loss figures, the risk breakdown, and a
token/cost table. Results are persisted to the `job_history`, `gis_results`, and
`risk_results` tables.

### Using real Earth Engine data

Set `GEE_SERVICE_ACCOUNT_EMAIL` and `GEE_SERVICE_ACCOUNT_JSON`, and register that service
account for Earth Engine access in the GEE console (a separate step from creating the GCP
credentials).

Note that only `land_cover_change` queries currently use live imagery. `forest_loss` queries
always fall back to sample rasters, because Hansen Global Forest Change encodes loss-year in
a single static band rather than the two before/after snapshots the change-detection
algorithm compares.

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `PARSER_MODEL` / `NARRATIVE_MODEL` | `gpt-4o-mini` / `gpt-4o` | model used for query parsing and narrative writing |
| `DATABASE_URL` | localhost:5434 | PostGIS connection |
| `DATA_CACHE_DIR` / `OUTPUTS_DIR` | `data/cache` / `outputs` | where rasters and reports land |

## Tests

```bash
pytest
```

The integration suite needs the `gis-disaster-agent-postgis` container running; unit tests
run without it.

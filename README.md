# GIS Disaster Analysis Agent

An AI agent that turns a natural-language query — e.g. "Analyze forest loss in Madhuban
from 2005-2020 and identify areas with increased disaster risk" — into a full geospatial
analysis: it resolves the place name, retrieves land-cover and terrain data, runs
change-detection and slope/rainfall analysis, scores disaster risk, and produces an
interactive map plus a PDF report.

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

The geospatial stack is installed via conda-forge to avoid platform binary-compatibility issues.

```bash
mamba env create -f environment.yml
mamba activate gis-disaster-agent
cp .env.example .env
# add ANTHROPIC_API_KEY at minimum; GEE credentials are optional (falls back to sample data)

python scripts/generate_sample_data.py

cd docker && docker-compose build postgis && docker-compose up -d postgis && cd ..
python scripts/init_postgis_schema.py
python scripts/load_gadm_nepal.py
python scripts/ingest_rag_docs.py
```

## Usage

```bash
python -m src.main run-query "Analyze forest loss in Madhuban from 2005-2020"
```

Produces `outputs/<job_id>/report.pdf` and an interactive map at
`outputs/<job_id>/maps/interactive_map.html`.

## Tests

```bash
pytest
```

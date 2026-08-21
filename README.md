# GIS Disaster Analysis Agent

Ask a question about a place in plain English. Get back a map and a PDF report about forest
loss and disaster risk there.

You type something like *"Analyze forest loss in Itahari from 2005-2020 and identify areas
with increased disaster risk."* The agent works out which place you mean, pulls satellite
data for it, measures how much forest was lost, checks the terrain and rainfall, scores the
disaster risk, draws maps, and writes a report explaining what it found.

## What it does, step by step

1. **Reads your question** and pulls out the place, the dates, and what you want analysed
2. **Finds the place** on a map — it copes with typos, and if two towns share a name it stops
   and says so rather than guessing the wrong one
3. **Gets satellite data** for that exact area
4. **Measures the forest loss** in hectares and as a percentage
5. **Checks the terrain** — how steep the land is, and how much rain it gets
6. **Scores the disaster risk** and shows which factor contributed what
7. **Draws the maps** — one you can click around, one for the report
8. **Writes the PDF report**, explaining *why* each factor matters, not just the numbers

The risk score is a simple weighted calculation, not a scientifically validated prediction.
The report says so plainly.

## Before you start

You need three things:

| | Why |
|---|---|
| **Docker Desktop** — open and running | the map database runs in a container |
| **mamba or conda** | installs the mapping libraries, which don't install cleanly with pip |
| **An Anthropic API key** | the AI that reads your question and writes the report |

Google Earth Engine credentials are optional. Without them the agent uses built-in sample
data, which is enough to see everything working.

## Quick version

If you have `make`, these are all you need:

```bash
make install                                              # create environment, install everything
make up                                                   # start the map database, load its data
make run Q="Analyze forest loss in Itahari from 2005-2020"
```

`make` on its own lists every command, and none of them need `mamba activate` first. The
longer form is below if you'd rather run the steps yourself.

## Setup — do this once

**1. Create the environment and install everything**

```bash
mamba env create -f environment.yml
mamba activate gis-disaster-agent
```

**2. Add your key**

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...
```

**3. Make the sample map data**

```bash
python scripts/generate_sample_data.py
```

**4. Start the map database and fill it**

```bash
cd docker && docker-compose up -d postgis && cd ..
python scripts/init_postgis_schema.py     # create the tables
python scripts/load_gadm_nepal.py         # load the town boundaries
python scripts/ingest_rag_docs.py         # load the reference documents
```

Setup is done. You won't need steps 3 and 4 again — the data stays in the container.

## How to run it

```bash
make run Q="Analyze forest loss in Itahari from 2005-2020"
```

`make` handles the environment for you. If you'd rather run it directly, activate first:

```bash
mamba activate gis-disaster-agent
python -m src.main run-query "Analyze forest loss in Itahari from 2005-2020"
```

Towns you can ask about right now: **Itahari**, **Butwal**, **Dhangadhi**, **Madhuban**.

### What you get

Everything lands in a new folder under `outputs/`:

| File | What it is |
|---|---|
| `report.pdf` | the full written report |
| `report.html` | same thing, opens in a browser |
| `maps/interactive_map.html` | a map you can click around — open it in your browser |
| `maps/static_map.png` | a picture of the map, used inside the report |

The terminal also prints the forest-loss figures, the risk score with its breakdown, and what
the run cost.

## Common problems

**`command not found: python` or missing packages**
You forgot to activate the environment. Run `mamba activate gis-disaster-agent` first.

**`Connect call failed ... 5434`**
The map database isn't running. Start it with `cd docker && docker-compose up -d postgis`.

**`Cannot connect to the Docker daemon`**
Docker Desktop isn't open. Start it and wait for the whale icon to settle.

**"boundary name is ambiguous"**
Two towns share that name. This is deliberate — the agent won't guess. Ask about a different
town for now.

**`sample rasters not found`**
Run `python scripts/generate_sample_data.py`.

**`Got unexpected extra argument`**
You left out `run-query`. The command is `python -m src.main run-query "your question"`.

## Using real satellite data

By default the agent uses sample data. For real Google Earth Engine imagery, add to `.env`:

```
GEE_SERVICE_ACCOUNT_EMAIL=...
GEE_SERVICE_ACCOUNT_JSON=/path/to/key.json
```

You also have to register that service account for Earth Engine in the Google Earth Engine
console — that's a separate step from creating the Google Cloud credentials.

## Running the tests

```bash
make test
```

The map database needs to be running for the full set.

## Two versions

- **`anthropic`** (this branch) — uses Claude (Anthropic)
- **`openai`** — the same agent, using GPT instead

Only the AI layer differs. Switch with `git checkout openai`, then re-run
`pip install -r requirements.txt`. The `main` branch holds no code — just an
index pointing at these two.

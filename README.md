# GIS Disaster Analysis Agent

Ask a question about a place in plain English. Get back a map and a PDF report about forest
loss and disaster risk there.

> *"Analyze forest loss in Itahari from 2005-2020 and identify areas with increased disaster
> risk."*

The agent works out which place you mean, pulls satellite data for it, measures how much
forest was lost, checks the terrain and rainfall, scores the disaster risk, draws maps, and
writes a report explaining what it found — including what the numbers don't tell you.

**This branch holds no code.** The agent exists as two implementations that differ only in
which model does the thinking:

| Branch | Model layer | |
|---|---|---|
| [**`anthropic`**](https://github.com/idiocter/-disaster-analysis-agent/tree/anthropic) | Claude | `git checkout anthropic` |
| [**`openai`**](https://github.com/idiocter/-disaster-analysis-agent/tree/openai) | GPT | `git checkout openai` |

Everything else is identical — the geospatial pipeline, the boundary resolution, the risk
model, the report generation — so the two can be run against the same question and compared.
Each branch has its own README with setup instructions.

## What it does

1. **Reads your question** and pulls out the place, the dates, and what you want analysed
2. **Finds the place** on a map — it copes with typos, and if two towns share a name it stops
   and says so rather than guessing the wrong one
3. **Gets satellite data** for that exact area
4. **Measures the forest loss** in hectares and as a percentage
5. **Checks the terrain** — how steep the land is, and how much rain it gets
6. **Scores the disaster risk** and shows which factor contributed what
7. **Draws the maps** — one you can click around, one for the report
8. **Writes the PDF report**, explaining *why* each factor matters, not just the numbers

## On honesty about uncertainty

The risk score is a weighted composite of forest loss, slope and rainfall — a first-pass
screening tool, not a validated predictive model. Validating it would need ground-truth
incident data, which is sparse for the region.

The report says so on its own face, every time. An agent that overstates its own confidence
is worse than no agent, and in disaster risk that gap has consequences beyond a wrong number
in a table.

Sample output, Itahari 2005–2020: 766.5 ha of canopy lost (13.45% of initial cover), risk
score 42.4/100 — 20.0 points from forest loss, 15.0 from slope, 7.4 from rainfall.

## Getting started

```bash
git clone https://github.com/idiocter/-disaster-analysis-agent.git
cd -disaster-analysis-agent
git checkout anthropic   # or: git checkout openai
```

Then follow that branch's README. You'll need Docker Desktop, mamba or conda (the mapping
libraries don't install cleanly with pip), and an API key for whichever provider the branch
uses. Google Earth Engine credentials are optional — without them the agent runs on built-in
sample data, which is enough to see everything working.

# Short commands for everyday use. Run `make` on its own to see them all.
#
# Every command runs through `conda run`, so you never need to
# `mamba activate` first -- the environment is picked up automatically.

ENV = gis-disaster-agent
RUN = conda run -n $(ENV) --no-capture-output
DB_CONTAINER = gis-disaster-agent-postgis

.DEFAULT_GOAL := help
.PHONY: help install up down run test clean

help:  ## show these commands
	@echo "Commands:"
	@grep -hE '^[a-z][a-z-]*:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  make %-9s %s\n", $$1, $$2}'
	@echo ""
	@echo "First time:  make install && make up && make run Q=\"Analyze forest loss in Itahari from 2005-2020\""

install:  ## create the environment and install everything
	mamba env create -f environment.yml
	$(RUN) pip install -r requirements.txt

up:  ## start the map database and load its data (safe to re-run)
	cd docker && docker-compose up -d postgis
	@printf "waiting for database"
	@until docker exec $(DB_CONTAINER) pg_isready -U gis >/dev/null 2>&1; do printf "."; sleep 1; done
	@echo " ready"
	$(RUN) python scripts/generate_sample_data.py
	$(RUN) python scripts/init_postgis_schema.py
	$(RUN) python scripts/load_gadm_nepal.py
	$(RUN) python scripts/ingest_rag_docs.py
	@echo 'ready -- try: make run Q="Analyze forest loss in Itahari from 2005-2020"'

down:  ## stop the map database
	cd docker && docker-compose down

run:  ## ask a question: make run Q="Analyze forest loss in Itahari from 2005-2020"
	@test -n "$(Q)" || (echo 'Usage: make run Q="Analyze forest loss in Itahari from 2005-2020"'; \
		echo 'Towns available: Itahari, Butwal, Dhangadhi, Madhuban'; exit 1)
	$(RUN) python -m src.main run-query "$(Q)"

test:  ## run the tests
	$(RUN) pytest

clean:  ## delete generated reports and maps
	rm -rf outputs/*
	@echo "cleared outputs/"

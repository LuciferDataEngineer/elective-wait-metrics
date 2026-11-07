ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
export PYTHONPATH := $(ROOT)/src
export ELECTIVE_DUCKDB_PATH := $(ROOT)/data/warehouse/elective.duckdb
export ELECTIVE_BRONZE_DIR := $(ROOT)/data/bronze
export DBT_PROFILES_DIR := $(ROOT)/transform
export DBT_SEND_ANONYMOUS_USAGE_STATS := false
export DO_NOT_TRACK := 1
export GX_ANALYTICS_ENABLED := false

PY := $(ROOT)/.venv/bin/python
RUFF := $(ROOT)/.venv/bin/ruff
PYTEST := $(ROOT)/.venv/bin/pytest
DAGSTER := $(ROOT)/.venv/bin/dagster

.PHONY: setup ingest transform metrics docs dashboard test check orchestration all

setup:
	python3 -m venv $(ROOT)/.venv
	$(ROOT)/.venv/bin/pip install --upgrade pip
	$(ROOT)/.venv/bin/pip install -r $(ROOT)/requirements.txt

ingest:
	$(PY) -m elective_wait.ingest

transform:
	$(PY) -m elective_wait.transform

metrics:
	$(PY) -m elective_wait.metrics_export

docs:
	$(PY) -m elective_wait.quality

dashboard: metrics

test: check

check:
	$(RUFF) check src tests
	$(PYTEST) -q

orchestration:
	mkdir -p $(ROOT)/data/warehouse $(ROOT)/data/bronze
	$(DAGSTER) asset materialize -m elective_wait.definitions --select "*" -d $(ROOT)

all: orchestration check

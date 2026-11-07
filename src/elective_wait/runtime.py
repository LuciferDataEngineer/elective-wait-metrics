"""Shared paths and process environment for the local DuckDB project."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
SNAPSHOT = REPO / "data" / "snapshot"
BRONZE = REPO / "data" / "bronze"
WAREHOUSE_DIR = REPO / "data" / "warehouse"
WAREHOUSE = WAREHOUSE_DIR / "elective.duckdb"
MANIFEST = REPO / "data" / "manifest.json"
PUBLISHED = REPO / "data" / "reference" / "published_national.json"
TRANSFORM = REPO / "transform"
SITE = REPO / "site"
SITE_DATA = SITE / "data" / "metrics.json"
DATA_DOCS = SITE / "data-docs"
GX_ROOT = REPO
VENV_BIN = REPO / ".venv" / "bin"

SNAPSHOT_FILES = {
    "waiting": SNAPSHOT / "elective_surgery_waiting_times.parquet",
    "specialty": SNAPSHOT / "elective_surgery_by_specialty.parquet",
    "procedure": SNAPSHOT / "elective_surgery_by_procedure.parquet",
}


def tool(name: str) -> str:
    path = VENV_BIN / name
    return str(path if path.exists() else name)


def project_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env["ELECTIVE_DUCKDB_PATH"] = str(WAREHOUSE)
    env["ELECTIVE_BRONZE_DIR"] = str(BRONZE)
    env["DBT_PROFILES_DIR"] = str(TRANSFORM)
    env["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
    env["DO_NOT_TRACK"] = "1"
    env["GX_ANALYTICS_ENABLED"] = "false"
    return env

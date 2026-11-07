"""Run the saved MetricFlow queries and write the stakeholder JSON."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from elective_wait.runtime import (
    PUBLISHED,
    SITE,
    SITE_DATA,
    TRANSFORM,
    WAREHOUSE_DIR,
    project_env,
    tool,
)
from elective_wait.site_payload import build_payload

SAVED_QUERIES = [
    "hospital_urgency_national",
    "hospital_urgency_state",
    "hospital_state",
    "hospital_peer",
    "hospital_listing",
    "specialty_national",
    "specialty_state",
    "specialty_breakdown",
    "procedure_breakdown",
]


def _normalise(name: str) -> str:
    return name.strip().split("__")[-1].lower()


def _read_query(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"MetricFlow wrote no header to {path}")
        rows = []
        for raw in reader:
            row = {_normalise(key): value for key, value in raw.items() if key}
            rows.append(row)
    if not rows:
        raise RuntimeError(f"MetricFlow query returned no rows: {path.name}")
    return rows


def _run_saved_query(name: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    completed = subprocess.run(
        [
            tool("mf"),
            "query",
            "--saved-query",
            name,
            "--csv",
            str(destination),
            "--decimals",
            "8",
            "--quiet",
        ],
        cwd=TRANSFORM,
        env=project_env(),
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0 or not destination.exists():
        raise RuntimeError(
            f"MetricFlow query failed for {name}\n{completed.stdout}\n{completed.stderr}"
        )


def export_metrics() -> str:
    query_dir = WAREHOUSE_DIR / "mf"
    frames = {}
    for name in SAVED_QUERIES:
        path = query_dir / f"{name}.csv"
        _run_saved_query(name, path)
        frames[name] = _read_query(path)
        print(f"{name}: {len(frames[name])} rows, columns={sorted(frames[name][0])}")
    published = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    generated_at = datetime.now(ZoneInfo("Australia/Melbourne")).isoformat(timespec="seconds")
    payload = build_payload(frames, published, generated_at)
    SITE_DATA.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {SITE_DATA.relative_to(SITE.parent)}")
    return str(SITE_DATA)


def main() -> None:
    export_metrics()


if __name__ == "__main__":
    main()

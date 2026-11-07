import json

from elective_wait.runtime import REPO, SITE_DATA

SITE = REPO / "site"
FORBIDDEN = [
    "metricflow",
    "dbt",
    "dagster",
    "duckdb",
    "great expectations",
    "polars",
    "schema",
    "percentile",
    "warehouse",
    "parquet",
    "pipeline",
]


def test_page_uses_plain_language():
    blob = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in [SITE / "index.html", SITE / "styles.css", SITE / "app.js"]
    )
    for word in FORBIDDEN:
        assert word not in blob


def test_metrics_json_anchors():
    payload = json.loads(SITE_DATA.read_text(encoding="utf-8"))
    audit = payload["audit"]
    assert audit["specialty_admissions_2024_25"] == 790528
    assert audit["share_waited_over_year_pct"] == 5.9
    assert audit["specialty_weighted_average_of_published_waits_days"] == 52.9
    assert audit["tas_urgent_on_time_pct"] == 65.7
    assert audit["vic_urgent_on_time_pct"] == 100.0
    assert audit["act_semi_on_time_pct"] == 51.7
    assert audit["listings_past_recommended_wait"] == {
        "Urgent": 3,
        "Semi-urgent": 16,
        "Non-urgent": 10,
    }
    assert payload["kpis"][0]["value"] == "45 days"
    assert payload["kpis"][1]["value"] == "6%"
    assert "45" in payload["banner"]["dek"]
    assert "Tasmania" in payload["banner"]["dek"]
    assert payload["timezone"] == "Australia/Melbourne"
    joined = json.dumps(payload["means"]) + payload["banner"]["dek"]
    for word in ["metricflow", "dagster", "duckdb", "dbt"]:
        assert word not in joined.lower()


def test_data_docs_index_exists():
    index = SITE / "data-docs" / "index.html"
    assert index.exists()
    text = index.read_text(encoding="utf-8", errors="ignore").lower()
    assert "expectation" in text

"""Build bronze parquet from the pinned AIHW snapshots.

Polars owns type cleaning and the financial-year calendar. dbt owns grain,
additive components, and tests. The snapshot checksums are verified before
any row is rewritten so a silent file swap fails the run.
"""

from __future__ import annotations

import hashlib
import json
import re

import polars as pl

from elective_wait.runtime import BRONZE, MANIFEST, SNAPSHOT_FILES

STATE_NAMES = {
    "ACT": "Australian Capital Territory",
    "NSW": "New South Wales",
    "NT": "Northern Territory",
    "Qld": "Queensland",
    "SA": "South Australia",
    "Tas": "Tasmania",
    "Vic": "Victoria",
    "WA": "Western Australia",
    "NAT": "Australia",
}

URGENCY = {
    "Urgent elective surgery": ("1", "Urgent", 30),
    "Semi-urgent elective surgery": ("2", "Semi-urgent", 90),
    "Non-urgent elective surgery": ("3", "Non-urgent", 365),
}

UNIT_TYPES = {"Hospital", "Local Hospital Network", "State", "National"}
YEAR_RE = re.compile(r"^(\d{4})\D+(\d{2})$")


def verify_manifest() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = MANIFEST.parents[1] / item["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise SystemExit(f"Checksum mismatch for {item['path']}")
        rows = pl.scan_parquet(path).select(pl.len()).collect().item()
        if rows != item["rows"]:
            raise SystemExit(f"Row-count mismatch for {item['path']}: {rows} != {item['rows']}")
    return manifest


def _blank_to_null(column: str) -> pl.Expr:
    return (
        pl.when(pl.col(column).str.strip_chars() == "")
        .then(pl.lit(None, dtype=pl.Utf8))
        .otherwise(pl.col(column))
        .alias(column)
    )


def _year_fields(frame: pl.DataFrame) -> pl.DataFrame:
    parsed = frame.with_columns(
        pl.col("year").str.extract(r"^(\d{4})", 1).alias("_year_start"),
        pl.col("year").str.extract(r"^\d{4}\D+(\d{2})$", 1).alias("_year_end"),
    )
    bad = parsed.filter(pl.col("_year_start").is_null() | pl.col("_year_end").is_null())
    if bad.height:
        raise SystemExit(f"Unparsed financial year values: {bad['year'].unique().to_list()}")
    return parsed.with_columns(
        (pl.col("_year_start") + pl.lit("-") + pl.col("_year_end")).alias("financial_year"),
        (pl.col("_year_start") + pl.lit("-07-01")).str.to_date("%Y-%m-%d").alias("report_date"),
    ).drop("_year_start", "_year_end")


def _state_fields(frame: pl.DataFrame) -> pl.DataFrame:
    unknown = set(frame["state"].unique().to_list()) - set(STATE_NAMES)
    if unknown:
        raise SystemExit(f"Unexpected state codes: {sorted(unknown)}")
    return frame.with_columns(
        pl.when(pl.col("state") == "NAT")
        .then(pl.lit("AUS"))
        .otherwise(pl.col("state"))
        .alias("state_code"),
        pl.col("state").replace_strict(STATE_NAMES).alias("state_name"),
    )


def _suppressed(frame: pl.DataFrame) -> pl.DataFrame:
    joined = pl.col("suppressed").list.join("; ")
    return frame.with_columns(
        pl.when(joined == "").then(pl.lit(None, dtype=pl.Utf8)).otherwise(joined).alias(
            "suppressed_fields"
        )
    )


def _common(frame: pl.DataFrame) -> pl.DataFrame:
    unknown_units = set(frame["reporting_unit_type"].unique().to_list()) - UNIT_TYPES
    if unknown_units:
        raise SystemExit(f"Unexpected reporting unit types: {sorted(unknown_units)}")
    frame = frame.with_columns(
        _blank_to_null("peer_group"),
        _blank_to_null("reporting_unit"),
        pl.col("surgeries").cast(pl.Int64).alias("admissions"),
        pl.col("median_wait_days").cast(pl.Int64).alias("published_wait_days"),
    )
    frame = _year_fields(frame)
    frame = _state_fields(frame)
    frame = _suppressed(frame)
    return frame.with_columns(
        pl.when(pl.col("reporting_unit_type").is_in(["State", "National"]))
        .then(pl.col("reporting_unit_type"))
        .otherwise(pl.lit("Provider"))
        .alias("reporting_level")
    )


def build_waiting(path) -> pl.DataFrame:
    frame = _common(pl.read_parquet(path))
    unknown = set(frame["urgency_category"].drop_nulls().unique().to_list()) - set(URGENCY)
    if unknown:
        raise SystemExit(f"Unexpected urgency categories: {sorted(unknown)}")
    codes = pl.DataFrame(
        {
            "urgency_category": list(URGENCY),
            "urgency_code": [value[0] for value in URGENCY.values()],
            "urgency_label": [value[1] for value in URGENCY.values()],
            "recommended_days": [value[2] for value in URGENCY.values()],
        }
    )
    return (
        frame.join(codes, on="urgency_category", how="left")
        .select(
            pl.col("reporting_unit").alias("hospital_name"),
            "reporting_unit_type",
            "reporting_level",
            "state_code",
            "state_name",
            "peer_group",
            "financial_year",
            "report_date",
            "urgency_code",
            "urgency_label",
            "recommended_days",
            "admissions",
            "published_wait_days",
            pl.col("share_within_recommended_time").alias("share_on_time"),
            "peer_group_median_days",
            pl.col("peer_group_average").alias("peer_group_on_time"),
            "suppressed_fields",
        )
        .sort(["state_code", "hospital_name", "financial_year", "urgency_code"])
    )


def build_specialty(path) -> pl.DataFrame:
    frame = _common(pl.read_parquet(path))
    return frame.select(
        "reporting_unit",
        "reporting_unit_type",
        "reporting_level",
        "state_code",
        "state_name",
        "peer_group",
        "financial_year",
        "report_date",
        "surgical_specialty",
        "admissions",
        "published_wait_days",
        pl.col("share_waited_over_365_days").alias("share_waited_over_year"),
        "suppressed_fields",
    ).sort(["reporting_level", "state_code", "financial_year", "surgical_specialty"])


def build_procedure(path) -> pl.DataFrame:
    frame = _common(pl.read_parquet(path))
    return frame.select(
        "reporting_unit",
        "reporting_unit_type",
        "reporting_level",
        "state_code",
        "state_name",
        "peer_group",
        "financial_year",
        "report_date",
        "intended_procedure",
        "admissions",
        "published_wait_days",
        pl.col("share_waited_over_365_days").alias("share_waited_over_year"),
        "suppressed_fields",
    ).sort(["reporting_level", "state_code", "financial_year", "intended_procedure"])


def build_bronze() -> dict[str, int]:
    verify_manifest()
    BRONZE.mkdir(parents=True, exist_ok=True)
    outputs = {
        "waiting": build_waiting(SNAPSHOT_FILES["waiting"]),
        "specialty": build_specialty(SNAPSHOT_FILES["specialty"]),
        "procedure": build_procedure(SNAPSHOT_FILES["procedure"]),
    }
    counts = {}
    for name, frame in outputs.items():
        destination = BRONZE / f"{name}.parquet"
        frame.write_parquet(destination)
        counts[name] = frame.height
    print(
        "Bronze rows: "
        + ", ".join(f"{name}={count}" for name, count in counts.items())
    )
    return counts


def main() -> None:
    build_bronze()


if __name__ == "__main__":
    main()

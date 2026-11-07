"""Validate bronze tables and publish Great Expectations data docs."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")

import great_expectations as gx
import pandas as pd
import polars as pl
from great_expectations.core.expectation_suite import ExpectationSuite
from great_expectations.core.validation_definition import ValidationDefinition
from great_expectations.expectations import (
    ExpectColumnValuesToBeBetween,
    ExpectColumnValuesToBeInSet,
    ExpectColumnValuesToMatchRegex,
    ExpectColumnValuesToNotBeNull,
    ExpectCompoundColumnsToBeUnique,
    ExpectTableRowCountToEqual,
)

from elective_wait.runtime import BRONZE, DATA_DOCS, GX_ROOT

TABLES = {
    "waiting": {
        "rows": 12159,
        "key": ["hospital_name", "reporting_unit_type", "financial_year", "urgency_label"],
        "extras": [
            ExpectColumnValuesToBeInSet(
                column="urgency_label",
                value_set=["Urgent", "Semi-urgent", "Non-urgent"],
            ),
            ExpectColumnValuesToBeInSet(column="recommended_days", value_set=[30, 90, 365]),
            ExpectColumnValuesToBeBetween(column="share_on_time", min_value=0, max_value=1),
        ],
    },
    "specialty": {
        "rows": 27902,
        "key": ["reporting_unit", "reporting_unit_type", "financial_year", "surgical_specialty"],
        "extras": [
            ExpectColumnValuesToBeBetween(
                column="share_waited_over_year", min_value=0, max_value=1
            ),
        ],
    },
    "procedure": {
        "rows": 183929,
        "key": ["reporting_unit", "reporting_unit_type", "financial_year", "intended_procedure"],
        "extras": [
            ExpectColumnValuesToBeBetween(
                column="share_waited_over_year", min_value=0, max_value=1
            ),
        ],
    },
}

STATES = ["ACT", "NSW", "NT", "Qld", "SA", "Tas", "Vic", "WA", "AUS"]
LEVELS = ["State", "National", "Provider"]


def _delete(factory, name: str) -> None:
    try:
        factory.delete(name)
    except Exception:
        return


def _suite(context, name: str, expectations: list) -> ExpectationSuite:
    _delete(context.suites, name)
    suite = ExpectationSuite(name=name)
    for expectation in expectations:
        suite.add_expectation(expectation)
    return context.suites.add(suite)


def _expectations(spec: dict) -> list:
    expectations = [
        ExpectTableRowCountToEqual(value=spec["rows"]),
        ExpectCompoundColumnsToBeUnique(column_list=spec["key"]),
        ExpectColumnValuesToNotBeNull(column="financial_year"),
        ExpectColumnValuesToNotBeNull(column="state_code"),
        ExpectColumnValuesToMatchRegex(column="financial_year", regex=r"^\d{4}-\d{2}$"),
        ExpectColumnValuesToBeInSet(column="state_code", value_set=STATES),
        ExpectColumnValuesToBeInSet(column="reporting_level", value_set=LEVELS),
        ExpectColumnValuesToBeBetween(column="admissions", min_value=0),
        ExpectColumnValuesToBeBetween(column="published_wait_days", min_value=0),
    ]
    expectations.extend(spec["extras"])
    return expectations


def _index_dir(built: dict[str, str]) -> Path:
    if not built:
        raise RuntimeError("Great Expectations did not build a data docs site")
    raw = next(iter(built.values()))
    if raw.startswith("file://"):
        raw = raw.removeprefix("file://")
    elif raw.startswith("file:"):
        raw = raw.removeprefix("file:")
    index = Path(raw)
    if index.is_file():
        return index.parent
    if not index.exists():
        raise RuntimeError(f"Data docs path does not exist: {raw}")
    return index


def build_data_docs() -> str:
    if not (BRONZE / "waiting.parquet").exists():
        raise SystemExit("Bronze parquet is missing. Run ingest first.")
    context = gx.get_context(mode="file", project_root_dir=str(GX_ROOT))
    try:
        context.data_sources.delete_pandas("bronze")
    except Exception:
        pass
    source = context.data_sources.add_pandas("bronze")
    validations = []
    for name, spec in TABLES.items():
        frame = pd.DataFrame(pl.read_parquet(BRONZE / f"{name}.parquet").to_dicts())
        asset = source.add_dataframe_asset(name)
        batch = asset.add_batch_definition_whole_dataframe("full")
        suite = _suite(context, f"{name}_suite", _expectations(spec))
        _delete(context.validation_definitions, f"{name}_check")
        validation = context.validation_definitions.add(
            ValidationDefinition(name=f"{name}_check", data=batch, suite=suite)
        )
        result = validation.run(batch_parameters={"dataframe": frame})
        if not result.success:
            failed = [
                item.expectation_config.type
                for item in result.results
                if not item.success
            ]
            raise RuntimeError(f"{name} failed expectations: {failed}")
        validations.append(name)
        del frame
    source_dir = _index_dir(context.build_data_docs())
    if DATA_DOCS.exists():
        shutil.rmtree(DATA_DOCS)
    shutil.copytree(source_dir, DATA_DOCS)
    index = DATA_DOCS / "index.html"
    if not index.exists():
        raise RuntimeError(f"Data docs index was not written to {index}")
    print(f"Data docs: {index} ({', '.join(validations)} tables)")
    return str(index)


def main() -> None:
    build_data_docs()


if __name__ == "__main__":
    main()

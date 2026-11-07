"""Dagster assets for ingest, marts, MetricFlow export, and data docs."""

from dagster import AssetExecutionContext, Definitions, asset

from elective_wait.ingest import build_bronze
from elective_wait.metrics_export import export_metrics
from elective_wait.quality import build_data_docs
from elective_wait.transform import build_marts


@asset(group_name="elective")
def bronze_tables(context: AssetExecutionContext) -> dict[str, int]:
    counts = build_bronze()
    context.log.info("Bronze row counts: %s", counts)
    return counts


@asset(deps=[bronze_tables], group_name="elective")
def dbt_marts(context: AssetExecutionContext) -> None:
    context.log.info("Building dbt marts and validating MetricFlow configs")
    build_marts()


@asset(deps=[dbt_marts], group_name="elective")
def metric_exports(context: AssetExecutionContext) -> str:
    path = export_metrics()
    context.log.info("Dashboard JSON: %s", path)
    return path


@asset(deps=[bronze_tables], group_name="elective")
def expectation_docs(context: AssetExecutionContext) -> str:
    path = build_data_docs()
    context.log.info("Data docs: %s", path)
    return path


defs = Definitions(assets=[bronze_tables, dbt_marts, metric_exports, expectation_docs])

{{ config(materialized='table') }}

select cast(d as date) as date_day
from (
    select unnest(
        generate_series(date '2011-01-01', date '2026-12-31', interval 1 day)
    ) as d
)

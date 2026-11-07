{{ config(materialized='view') }}

select
    cast(hospital_name as varchar) as hospital_name,
    cast(reporting_unit_type as varchar) as reporting_unit_type,
    cast(reporting_level as varchar) as reporting_level,
    cast(state_code as varchar) as state_code,
    cast(state_name as varchar) as state_name,
    cast(peer_group as varchar) as peer_group,
    cast(financial_year as varchar) as financial_year,
    cast(report_date as date) as report_date,
    cast(urgency_code as varchar) as urgency_code,
    cast(urgency_label as varchar) as urgency_label,
    cast(recommended_days as integer) as recommended_days,
    cast(admissions as bigint) as admissions,
    cast(published_wait_days as bigint) as published_wait_days,
    cast(share_on_time as double) as share_on_time,
    cast(suppressed_fields as varchar) as suppressed_fields
from read_parquet('{{ env_var("ELECTIVE_BRONZE_DIR") }}/waiting.parquet')

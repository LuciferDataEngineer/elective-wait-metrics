{{ config(materialized='view') }}

select
    cast(reporting_unit as varchar) as reporting_unit,
    cast(reporting_unit_type as varchar) as reporting_unit_type,
    cast(reporting_level as varchar) as reporting_level,
    cast(state_code as varchar) as state_code,
    cast(state_name as varchar) as state_name,
    cast(financial_year as varchar) as financial_year,
    cast(report_date as date) as report_date,
    cast(intended_procedure as varchar) as intended_procedure,
    cast(admissions as bigint) as admissions,
    cast(published_wait_days as bigint) as published_wait_days,
    cast(share_waited_over_year as double) as share_waited_over_year
from read_parquet('{{ env_var("ELECTIVE_BRONZE_DIR") }}/procedure.parquet')

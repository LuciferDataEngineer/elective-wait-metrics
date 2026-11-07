{{ config(materialized='table') }}

-- Official State and National rows. Specialties partition admissions, so a
-- surgery-weighted share across specialties is the overall share.
select
    reporting_level || '|' || state_code || '|' || financial_year || '|' || surgical_specialty as slice_key,
    reporting_unit,
    reporting_level,
    state_code,
    state_name,
    financial_year,
    report_date,
    surgical_specialty,
    admissions,
    case
        when published_wait_days is not null then admissions else 0
    end as admissions_with_wait,
    case
        when published_wait_days is not null then published_wait_days * admissions else 0
    end as wait_days_times_admissions,
    case
        when share_waited_over_year is not null then admissions else 0
    end as admissions_with_over_year_share,
    case
        when share_waited_over_year is not null then admissions * share_waited_over_year else 0
    end as over_year_admissions,
    published_wait_days
from {{ ref('stg_specialty') }}
where reporting_level in ('State', 'National')
  and admissions is not null

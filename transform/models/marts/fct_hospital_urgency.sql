{{ config(materialized='table') }}

-- One row per public hospital, financial year, and urgency category.
-- Local hospital networks are excluded so state totals are not double counted.
-- Rows with no published admission count cannot be weighted and are dropped.
select
    hospital_name || '|' || financial_year || '|' || urgency_code as slice_key,
    hospital_name,
    state_code,
    state_name,
    coalesce(peer_group, 'Not available') as peer_group,
    financial_year,
    report_date,
    urgency_label,
    recommended_days,
    admissions,
    case
        when published_wait_days is not null then admissions else 0
    end as admissions_with_wait,
    case
        when published_wait_days is not null then published_wait_days * admissions else 0
    end as wait_days_times_admissions,
    case
        when share_on_time is not null then admissions else 0
    end as admissions_with_on_time_share,
    case
        when share_on_time is not null then admissions * share_on_time else 0
    end as on_time_admissions,
    case
        when share_on_time is not null then admissions * (1 - share_on_time) else 0
    end as outside_recommended_admissions,
    case
        when published_wait_days is not null
            and share_on_time is not null
            and recommended_days > 0
            then admissions
                * (1 - share_on_time)
                * greatest(published_wait_days - recommended_days, 0)
                / recommended_days
        else 0
    end as overdue_pressure,
    case
        when published_wait_days is not null and published_wait_days > recommended_days then 1
        else 0
    end as listings_past_recommended_wait,
    published_wait_days
from {{ ref('stg_waiting') }}
where reporting_unit_type = 'Hospital'
  and admissions is not null

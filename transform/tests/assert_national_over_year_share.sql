-- Lock the 2024–25 national share waiting more than a year.
-- 0.0593579 is the surgery-weighted share on the National specialty rows.
select share
from (
    select
        sum(over_year_admissions) / sum(admissions_with_over_year_share) as share
    from {{ ref('fct_specialty_report') }}
    where reporting_level = 'National'
      and financial_year = '2024-25'
) national
where abs(share - 0.0593579076) > 0.0000001

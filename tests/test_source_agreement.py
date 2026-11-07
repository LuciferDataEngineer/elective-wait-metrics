import json

import duckdb

from elective_wait.numbers import round_half_up
from elective_wait.runtime import SITE_DATA, SNAPSHOT_FILES


def test_dashboard_share_matches_specialty_snapshot():
    payload = json.loads(SITE_DATA.read_text(encoding="utf-8"))
    con = duckdb.connect()
    share, admissions = con.execute(
        f"""
        select
            sum(surgeries * share_waited_over_365_days) / sum(surgeries),
            sum(surgeries)
        from read_parquet('{SNAPSHOT_FILES["specialty"].as_posix()}')
        where reporting_unit_type = 'National'
          and year = '2024–25'
        """
    ).fetchone()
    assert int(admissions) == payload["audit"]["specialty_admissions_2024_25"] == 790528
    assert round_half_up(share * 100, 1) == payload["audit"]["share_waited_over_year_pct"] == 5.9
    assert abs(share - payload["audit"]["share_waited_over_year"]) < 1e-6

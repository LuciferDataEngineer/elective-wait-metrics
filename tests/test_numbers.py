from elective_wait.numbers import pct, round_half_up, year_label


def test_round_half_up_matches_published_rounding():
    assert round_half_up(0.0593579076 * 100, 1) == 5.9
    assert round_half_up(52.883116, 1) == 52.9
    assert round_half_up(3.45, 1) == 3.5


def test_year_label_uses_en_dash():
    assert year_label("2024-25") == "2024–25"
    assert pct(65.74) == "65.7%"
    assert pct(100) == "100%"

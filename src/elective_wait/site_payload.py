"""Turn MetricFlow query rows into the stakeholder page payload.

Python only filters, sorts, rounds, and writes plain-language sentences.
Shares and totals are the metric values, not a second aggregation.
"""

from __future__ import annotations

from elective_wait.numbers import pct, people, round_half_up, year_label

LATEST = "2024-25"
PREVIOUS = "2023-24"
URGENCY_ORDER = ["Urgent", "Semi-urgent", "Non-urgent"]
RECOMMENDED = {"Urgent": 30, "Semi-urgent": 90, "Non-urgent": 365}


def _year(row: dict) -> str:
    return str(row["financial_year"])


def _in_year(rows: list[dict], year: str) -> list[dict]:
    return [row for row in rows if _year(row) == year]


def _level(rows: list[dict], level: str) -> list[dict]:
    return [row for row in rows if row.get("reporting_level") == level]


def _f(row: dict, key: str) -> float:
    value = row[key]
    if value is None or value == "":
        raise KeyError(key)
    return float(value)


def _pct_points(row: dict, key: str) -> float:
    return round_half_up(_f(row, key) * 100, 1)


def _one(rows: list[dict], **match: str) -> dict:
    found = [
        row
        for row in rows
        if all(str(row.get(key)) == value for key, value in match.items())
    ]
    if len(found) != 1:
        raise RuntimeError(f"Expected one row for {match}, found {len(found)}")
    return found[0]


def _sorted_years(rows: list[dict]) -> list[str]:
    return sorted({_year(row) for row in rows})


def build_payload(frames: dict[str, list[dict]], published: dict, generated_at: str) -> dict:
    national_urgency = frames["hospital_urgency_national"]
    state_urgency = frames["hospital_urgency_state"]
    specialty_national = _level(frames["specialty_national"], "National")
    specialty_state = _level(frames["specialty_state"], "State")
    specialty_rows = _level(_in_year(frames["specialty_breakdown"], LATEST), "National")
    state_specialty = _level(_in_year(frames["specialty_breakdown"], LATEST), "State")
    procedures = _level(_in_year(frames["procedure_breakdown"], LATEST), "National")
    listings = _in_year(frames["hospital_listing"], LATEST)
    peers = _in_year(frames["hospital_peer"], LATEST)

    latest_national = _one(specialty_national, financial_year=LATEST)
    previous_national = _one(specialty_national, financial_year=PREVIOUS)
    over_year_now = _pct_points(latest_national, "share_waited_over_year")
    over_year_prev = _pct_points(previous_national, "share_waited_over_year")
    weighted_now = round_half_up(_f(latest_national, "specialty_weighted_wait_days"), 1)

    urgent_latest = {
        row["state_code"]: row
        for row in _in_year(state_urgency, LATEST)
        if row["urgency_label"] == "Urgent"
    }
    semi_latest = {
        row["state_code"]: row
        for row in _in_year(state_urgency, LATEST)
        if row["urgency_label"] == "Semi-urgent"
    }
    tas_urgent = _pct_points(urgent_latest["Tas"], "share_on_time")
    vic_urgent = _pct_points(urgent_latest["Vic"], "share_on_time")
    act_semi = _pct_points(semi_latest["ACT"], "share_on_time")
    tas_semi = _pct_points(semi_latest["Tas"], "share_on_time")

    hero_rows = []
    for row in _in_year(specialty_state, LATEST):
        hero_rows.append(
            {
                "label": row["state_name"],
                "short": row["state_code"],
                "value": _pct_points(row, "share_waited_over_year"),
                "admissions": int(_f(row, "specialty_admissions")),
            }
        )
    hero_rows.sort(key=lambda item: item["value"], reverse=True)

    change_rows = []
    for row in _in_year(specialty_state, LATEST):
        prior = _one(
            specialty_state,
            financial_year=PREVIOUS,
            state_code=row["state_code"],
        )
        change_rows.append(
            {
                "label": row["state_name"],
                "short": row["state_code"],
                "value": round_half_up(
                    (_f(row, "share_waited_over_year") - _f(prior, "share_waited_over_year"))
                    * 100,
                    1,
                ),
            }
        )
    change_rows.sort(key=lambda item: item["value"], reverse=True)

    volume_rows = [
        {
            "label": row["state_name"],
            "short": row["state_code"],
            "value": int(_f(row, "specialty_admissions")),
        }
        for row in sorted(
            _in_year(specialty_state, LATEST),
            key=lambda item: _f(item, "specialty_admissions"),
            reverse=True,
        )
    ]

    state_order = sorted(urgent_latest, key=lambda code: _pct_points(urgent_latest[code], "share_on_time"))
    on_time_rows = []
    for code in state_order:
        values = []
        for urgency in URGENCY_ORDER:
            match = _one(
                state_urgency,
                financial_year=LATEST,
                state_code=code,
                urgency_label=urgency,
            )
            values.append(_pct_points(match, "share_on_time"))
        on_time_rows.append(
            {
                "label": urgent_latest[code]["state_name"],
                "short": code,
                "values": values,
            }
        )

    trend_rows = []
    for year in _sorted_years(specialty_national):
        row = _one(specialty_national, financial_year=year)
        trend_rows.append(
            {
                "label": year_label(year),
                "value": _pct_points(row, "share_waited_over_year"),
            }
        )

    urgency_rows = []
    for urgency in URGENCY_ORDER:
        row = _one(national_urgency, financial_year=LATEST, urgency_label=urgency)
        urgency_rows.append(
            {
                "label": urgency,
                "on_time": _pct_points(row, "share_on_time"),
                "outside": int(round_half_up(_f(row, "outside_recommended_admissions"), 0)),
                "admissions": int(_f(row, "admissions")),
                "within_days": RECOMMENDED[urgency],
                "past_typical": int(_f(row, "listings_past_recommended_wait")),
            }
        )

    urgency_trend = []
    for year in _sorted_years(national_urgency):
        values = []
        for urgency in URGENCY_ORDER:
            row = _one(national_urgency, financial_year=year, urgency_label=urgency)
            values.append(_pct_points(row, "share_on_time"))
        urgency_trend.append({"label": year_label(year), "values": values})

    specialty_chart = sorted(
        [
            {
                "label": row["surgical_specialty"],
                "value": int(_f(row, "specialty_published_wait_days")),
                "admissions": int(_f(row, "specialty_admissions")),
                "over_year": _pct_points(row, "share_waited_over_year"),
            }
            for row in specialty_rows
        ],
        key=lambda item: item["value"],
        reverse=True,
    )

    procedure_chart = sorted(
        [
            {
                "label": row["intended_procedure"].split(" (")[0],
                "value": int(_f(row, "procedure_published_wait_days")),
                "admissions": int(_f(row, "procedure_admissions")),
                "over_year": _pct_points(row, "procedure_share_waited_over_year"),
            }
            for row in procedures
            if _f(row, "procedure_admissions") >= 4000
            and row.get("procedure_published_wait_days") not in (None, "")
        ],
        key=lambda item: item["value"],
        reverse=True,
    )[:8]

    priority = sorted(listings, key=lambda row: _f(row, "outside_recommended_admissions"), reverse=True)[:8]
    priority_rows = [
        {
            "label": f"{row['hospital_name']} · {row['urgency_label']}",
            "hospital": row["hospital_name"],
            "state": row["state_code"],
            "urgency": row["urgency_label"],
            "value": int(round_half_up(_f(row, "outside_recommended_admissions"), 0)),
            "on_time": _pct_points(row, "share_on_time"),
            "within_days": int(_f(row, "published_wait_days")),
        }
        for row in priority
    ]

    peer_rows = sorted(
        [
            {
                "label": row["peer_group"],
                "value": _pct_points(row, "share_on_time"),
                "admissions": int(_f(row, "admissions")),
            }
            for row in peers
        ],
        key=lambda item: item["value"],
    )

    breach_rows = [
        {"label": row["label"], "value": row["past_typical"], "within_days": row["within_days"]}
        for row in urgency_rows
    ]

    urgent_chart = sorted(
        [
            {
                "label": row["state_name"],
                "short": code,
                "value": _pct_points(row, "share_on_time"),
            }
            for code, row in urgent_latest.items()
        ],
        key=lambda item: item["value"],
    )
    semi_chart = sorted(
        [
            {
                "label": row["state_name"],
                "short": code,
                "value": _pct_points(row, "share_on_time"),
            }
            for code, row in semi_latest.items()
        ],
        key=lambda item: item["value"],
    )

    nsw_eyes = _one(
        state_specialty,
        state_code="NSW",
        surgical_specialty="Ophthalmology",
    )
    act_ent = _one(
        state_specialty,
        state_code="ACT",
        surgical_specialty="Ear, nose and throat surgery",
    )
    rah = _one(
        listings,
        hospital_name="Royal Adelaide Hospital",
        urgency_label="Urgent",
    )
    top = priority_rows[0]
    outside_semi = next(row["outside"] for row in urgency_rows if row["label"] == "Semi-urgent")
    semi_on_time = next(row["on_time"] for row in urgency_rows if row["label"] == "Semi-urgent")

    kpis = [
        {
            "value": f"{published['half_admitted_within_days']} days",
            "label": "Half of patients were admitted within this time",
            "detail": (
                f"Australia, {year_label(LATEST)}. "
                f"Down from {published['half_admitted_within_days_previous']} days the year before."
            ),
            "status": "watch",
        },
        {
            "value": f"{published['waited_over_year_pct']:.0f}%",
            "label": "Waited more than a year",
            "detail": (
                f"Down from {published['waited_over_year_pct_previous']:.1f}% the year before. "
                f"The hospital specialty tables come out at {pct(over_year_now)}."
            ),
            "status": "watch",
        },
        {
            "value": pct(tas_urgent),
            "label": "Of urgent surgery in Tasmania was done within 30 days",
            "detail": (
                f"The lowest of the states. Victoria's published hospital figures are at {pct(vic_urgent)}."
            ),
            "status": "poor",
        },
        {
            "value": pct(act_semi),
            "label": "Of semi-urgent surgery in the ACT was done within 90 days",
            "detail": f"Only about half. Tasmania is next, at {pct(tas_semi)}.",
            "status": "poor",
        },
        {
            "value": f"{published['admissions']:,}",
            "label": "People admitted from public waiting lists",
            "detail": (
                f"The specialty tables cover {int(_f(latest_national, 'specialty_admissions')):,} "
                f"operations in {year_label(LATEST)}."
            ),
            "status": "neutral",
        },
    ]

    banner = (
        f"Half of patients were admitted within {published['half_admitted_within_days']} days. "
        "About 1 in 17 waited more than a year. "
        f"Urgent surgery in Tasmania is the first place to look: {pct(tas_urgent)} were done within 30 days."
    )

    means = {
        "overview": (
            "These figures are about people who have already had their operation, not people still waiting. "
            f"The {published['half_admitted_within_days']}-day national figure counts every patient once. "
            "The state bars use each state total for waits longer than a year. "
            f"Nine in ten patients nationally were admitted within {published['nine_in_ten_admitted_within_days']} days."
        ),
        "states": (
            "A state can look reasonable overall and still miss the urgent clock. "
            f"New South Wales does well on urgent surgery and poorly on waits over a year, "
            f"driven by eye surgery: half of those patients waited longer than {int(_f(nsw_eyes, 'specialty_published_wait_days'))} days, "
            f"and {pct(_pct_points(nsw_eyes, 'share_waited_over_year'))} waited more than a year "
            f"({int(_f(nsw_eyes, 'specialty_admissions')):,} operations)."
        ),
        "hospitals": (
            f"{top['hospital']} has the largest single gap on this list: about {people(top['value'])} "
            f"{top['urgency'].lower()} patients were treated outside the recommended time. "
            f"At Royal Adelaide Hospital the typical urgent patient was admitted within "
            f"{int(_f(rah, 'published_wait_days'))} days, inside the 30-day mark, but only "
            f"{pct(_pct_points(rah, 'share_on_time'))} were. That is about "
            f"{people(_f(rah, 'outside_recommended_admissions'))} people."
        ),
        "urgency": (
            f"Semi-urgent surgery is the bulk of the missed clock: {pct(semi_on_time)} were done within 90 days, "
            f"about {people(outside_semi)} people were not. "
            "Ear, nose and throat, eye surgery, and orthopaedics have the longest typical waits. "
            "Knee replacement, septoplasty, tonsils, hip replacement, and cataract surgery are the high-volume operations to watch."
        ),
        "actions": (
            "Look first at urgent surgery where the 30-day mark is missed, then at semi-urgent services "
            "that miss the 90-day mark for a large number of people, then at the states and operations "
            "where more than a year is becoming common. Small hospitals with a handful of operations can post "
            "a very long typical wait; the list above weighs that by how many people are affected."
        ),
    }

    actions = [
        {
            "status": "poor",
            "title": "Start with urgent surgery in Tasmania",
            "body": (
                f"Only {pct(tas_urgent)} of urgent operations in Tasmanian public hospitals were done within 30 days. "
                f"The Northern Territory is at {pct(_pct_points(urgent_latest['NT'], 'share_on_time'))} and the ACT at "
                f"{pct(_pct_points(urgent_latest['ACT'], 'share_on_time'))}. "
                f"New South Wales is at {pct(_pct_points(urgent_latest['NSW'], 'share_on_time'))} and Victoria at {pct(vic_urgent)}."
            ),
        },
        {
            "status": "poor",
            "title": "Then the 90-day surgeries in the ACT, Tasmania, South Australia, and the NT",
            "body": (
                f"Nationally, {pct(semi_on_time)} of semi-urgent operations were done within 90 days. "
                f"The ACT is at {pct(act_semi)} and Tasmania at {pct(tas_semi)}. "
                "Canberra Hospital's typical semi-urgent wait is already past 90 days, with a large number of people affected."
            ),
        },
        {
            "status": "watch",
            "title": "Treat waits over a year as an ACT and New South Wales problem, not a flat national one",
            "body": (
                f"{hero_rows[0]['label']} is at {pct(hero_rows[0]['value'])} and "
                f"{hero_rows[1]['label']} at {pct(hero_rows[1]['value'])}. "
                f"Queensland is lowest, at {pct(hero_rows[-1]['value'])}. "
                f"NSW eye surgery and ACT ear, nose and throat surgery "
                f"({pct(_pct_points(act_ent, 'share_waited_over_year'))} waited more than a year) sit inside those state results."
            ),
        },
        {
            "status": "watch",
            "title": "Do not stop at the typical wait",
            "body": (
                "A hospital can admit the typical urgent patient inside 30 days and still miss hundreds or thousands of people. "
                f"Royal Adelaide's urgent list is the clearest example: typical wait "
                f"{int(_f(rah, 'published_wait_days'))} days, only {pct(_pct_points(rah, 'share_on_time'))} inside the limit."
            ),
        },
    ]

    return {
        "generated_at": generated_at,
        "timezone": "Australia/Melbourne",
        "latest_year": year_label(LATEST),
        "previous_year": year_label(PREVIOUS),
        "banner": {
            "kicker": "Public hospitals · Australia",
            "title": "Elective surgery waits",
            "dek": banner,
        },
        "kpis": kpis,
        "hero": {
            "title": "The ACT and New South Wales have the most people waiting longer than a year",
            "insight": "Share of operations in 2024–25. Queensland is the lowest.",
            "rows": hero_rows,
        },
        "overview": {
            "trend": {
                "title": "Long waits jumped in 2020 and have only partly come back down",
                "insight": f"Share waiting more than a year. The latest hospital-table figure is {pct(over_year_now)}.",
                "rows": trend_rows,
            },
            "urgency": {
                "title": "The 90-day surgeries are where most people miss the recommended time",
                "insight": "Share treated within 30, 90, or 365 days, 2024–25.",
                "rows": urgency_rows,
            },
        },
        "states": {
            "on_time": {
                "title": "Tasmania is last on urgent surgery, even where other states are close to the mark",
                "insight": "Share of hospital operations treated within the recommended time, 2024–25.",
                "categories": URGENCY_ORDER,
                "rows": on_time_rows,
            },
            "change": {
                "title": "Victoria improved the most since last year. New South Wales went the other way",
                "insight": "Change, in percentage points, in the share waiting more than a year.",
                "rows": change_rows,
            },
            "volume": {
                "title": "New South Wales and Victoria do most of the surgery",
                "insight": "Operations in the 2024–25 state specialty tables.",
                "rows": volume_rows,
            },
        },
        "hospitals": {
            "priority": {
                "title": "These hospitals account for the most people treated outside the recommended time",
                "insight": "Rebuilt from the published share and the number of operations. 2024–25.",
                "rows": priority_rows,
            },
            "peers": {
                "title": "Children’s hospitals and large regional hospitals are furthest from the recommended time",
                "insight": "Share treated on time, all urgencies, 2024–25.",
                "rows": peer_rows,
            },
            "breaches": {
                "title": "In a handful of hospitals, the typical wait is already past the recommended limit",
                "insight": "Hospitals where half of patients waited longer than 30, 90, or 365 days.",
                "rows": breach_rows,
            },
        },
        "urgency_tab": {
            "trend": {
                "title": "Urgent surgery is still mostly on time, but less so than before the pandemic",
                "insight": "Share treated within the recommended time, public hospitals.",
                "categories": URGENCY_ORDER,
                "rows": urgency_trend,
            },
            "specialties": {
                "title": "Ear, nose and throat, eyes, and orthopaedics have the longest typical waits",
                "insight": "Days by which half of national patients in that specialty were admitted, 2024–25.",
                "rows": specialty_chart,
            },
            "procedures": {
                "title": "Septoplasty and knee replacement leave people waiting the longest",
                "insight": "Common operations with at least 4,000 admissions. Days by which half of patients were admitted.",
                "rows": procedure_chart,
            },
        },
        "actions": {
            "urgent": {
                "title": "Urgent surgery within 30 days, by state",
                "insight": "Lowest shares need attention first. 2024–25.",
                "rows": urgent_chart,
            },
            "semi": {
                "title": "Semi-urgent surgery within 90 days, by state",
                "insight": "This is where the count of missed waits is largest.",
                "rows": semi_chart,
            },
            "cards": actions,
        },
        "means": means,
        "sources": [
            {
                "name": "Hospital, specialty, and procedure tables",
                "detail": (
                    "Australian Institute of Health and Welfare, MyHospitals elective surgery indicators, "
                    "redistributed by National Digital on publicdata.au under CC BY 4.0. "
                    "Urgency file version 2026-10-03. Procedure and specialty files version 2026-10-20. "
                    "Accessed 8 November 2026."
                ),
            },
            {
                "name": "National 45-day and 6% figures",
                "detail": (
                    "Australian Institute of Health and Welfare, Elective surgery waiting times 2024–25. "
                    f"{published['source_url']} . Accessed 8 November 2026. "
                    "These count each patient once and are not rebuilt by averaging hospital figures."
                ),
            },
        ],
        "audit": {
            "specialty_admissions_2024_25": int(_f(latest_national, "specialty_admissions")),
            "share_waited_over_year": round_half_up(_f(latest_national, "share_waited_over_year"), 6),
            "share_waited_over_year_pct": over_year_now,
            "previous_share_waited_over_year_pct": over_year_prev,
            "specialty_weighted_average_of_published_waits_days": weighted_now,
            "note": (
                "The weighted average of specialty waits is not the national 45-day figure. "
                "The page does not present it as one."
            ),
            "tas_urgent_on_time_pct": tas_urgent,
            "vic_urgent_on_time_pct": vic_urgent,
            "act_semi_on_time_pct": act_semi,
            "listings_past_recommended_wait": {
                row["label"]: row["past_typical"] for row in urgency_rows
            },
        },
    }

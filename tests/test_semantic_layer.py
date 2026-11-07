from elective_wait.runtime import TRANSFORM

SEMANTIC = (TRANSFORM / "models" / "marts" / "_semantic.yml").read_text(encoding="utf-8")


def test_semantic_layer_defines_the_headline_metrics():
    for name in [
        "semantic_models:",
        "name: hospital_urgency",
        "name: specialty_report",
        "name: procedure_report",
        "name: hospital",
        "name: state",
        "name: urgency",
        "name: report_year",
        "outside_recommended_admissions",
        "overdue_pressure",
        "share_on_time",
        "share_waited_over_year",
        "share_outside_recommended",
        "saved_queries:",
        "hospital_listing",
        "specialty_national",
        "procedure_breakdown",
    ]:
        assert name in SEMANTIC

from types import SimpleNamespace

from dashboard.app import compliance_status


def test_dashboard_status_is_unknown_without_complete_evidence() -> None:
    summary = SimpleNamespace(total_people=1, safe_workers=0, workers_with_violations=0)

    assert compliance_status(summary) == "UNKNOWN"


def test_dashboard_status_is_safe_only_for_fully_compliant_workers() -> None:
    summary = SimpleNamespace(total_people=1, safe_workers=1, workers_with_violations=0)

    assert compliance_status(summary) == "SAFE"
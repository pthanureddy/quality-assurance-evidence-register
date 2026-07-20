from qa_register.metrics import _percentage, calculate_kpis


def test_calculates_requirement_metrics(register):
    kpis = calculate_kpis(register)
    assert kpis["requirements_verified"] == 3
    assert kpis["requirement_verification_rate"] == 75.0


def test_calculates_complaint_metrics(register):
    kpis = calculate_kpis(register)
    assert kpis["complaints_total"] == 3
    assert kpis["complaints_open"] == 2
    assert kpis["average_closed_complaint_days"] == 15


def test_calculates_action_metrics(register):
    kpis = calculate_kpis(register)
    assert kpis["actions_total"] == 5
    assert kpis["actions_open"] == 3
    assert kpis["actions_overdue"] == 1
    assert kpis["closed_action_on_time_rate"] == 50.0


def test_calculates_audit_metrics(register):
    kpis = calculate_kpis(register)
    assert kpis["audits_total"] == 2
    assert kpis["audits_completed"] == 1
    assert kpis["audit_findings_open"] == 1


def test_calculates_active_risk_exposure(register):
    kpis = calculate_kpis(register)
    assert kpis["active_risks"] == 2
    assert kpis["gross_risk_exposure"] == 29
    assert kpis["residual_risk_exposure"] == 12


def test_percentage_handles_empty_denominator():
    assert _percentage(0, 0) is None


def test_percentage_rounds_to_one_decimal_place():
    assert _percentage(2, 3) == 66.7

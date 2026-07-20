from statistics import mean
from typing import Any

from .models import QualityRegister, Status


def calculate_kpis(register: QualityRegister) -> dict[str, Any]:
    open_complaints = [
        complaint for complaint in register.complaints if complaint.status != Status.CLOSED
    ]
    open_actions = [
        action for action in register.corrective_actions if action.status != Status.CLOSED
    ]
    overdue_actions = [
        action for action in open_actions if action.due_date < register.as_of
    ]
    closed_actions = [
        action for action in register.corrective_actions if action.status == Status.CLOSED
    ]
    on_time_actions = [
        action
        for action in closed_actions
        if action.closed_on is not None and action.closed_on <= action.due_date
    ]
    verified_requirements = [
        requirement
        for requirement in register.requirements
        if requirement.status.lower() == "verified"
    ]
    completed_audits = [
        audit for audit in register.audits if audit.status.lower() == "completed"
    ]
    open_findings = [
        finding
        for audit in register.audits
        for finding in audit.findings
        if finding.status != Status.CLOSED
    ]
    active_risks = [risk for risk in register.risks if risk.status != Status.CLOSED]
    closed_complaint_days = [
        (complaint.closed_on - complaint.opened_on).days
        for complaint in register.complaints
        if complaint.closed_on is not None
    ]

    return {
        "as_of": register.as_of.isoformat(),
        "projects_total": len(register.projects),
        "requirements_total": len(register.requirements),
        "requirements_verified": len(verified_requirements),
        "requirement_verification_rate": _percentage(
            len(verified_requirements), len(register.requirements)
        ),
        "complaints_total": len(register.complaints),
        "complaints_open": len(open_complaints),
        "average_closed_complaint_days": (
            round(mean(closed_complaint_days), 1) if closed_complaint_days else None
        ),
        "actions_total": len(register.corrective_actions),
        "actions_open": len(open_actions),
        "actions_overdue": len(overdue_actions),
        "closed_action_on_time_rate": _percentage(
            len(on_time_actions), len(closed_actions)
        ),
        "audits_total": len(register.audits),
        "audits_completed": len(completed_audits),
        "audit_findings_open": len(open_findings),
        "active_risks": len(active_risks),
        "gross_risk_exposure": sum(risk.gross_score for risk in active_risks),
        "residual_risk_exposure": sum(risk.residual_score for risk in active_risks),
    }


def _percentage(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator * 100, 1)


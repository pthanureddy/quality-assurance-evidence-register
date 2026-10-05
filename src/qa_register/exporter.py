import csv
import json
from collections.abc import Mapping
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .metrics import calculate_kpis
from .models import QualityRegister, Status


def export_register(register: QualityRegister, output_dir: str | Path) -> dict[str, int]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    kpis = calculate_kpis(register)

    files: dict[str, list[dict[str, Any]]] = {
        "dim_project.csv": _project_rows(register),
        "dim_date.csv": _date_rows(register),
        "fact_requirements.csv": _requirement_rows(register),
        "fact_complaints.csv": _complaint_rows(register),
        "fact_actions.csv": _action_rows(register),
        "fact_risks.csv": _risk_rows(register),
        "fact_audit_findings.csv": _audit_rows(register),
        "fact_kpis.csv": [kpis],
        "jira_action_handoff.csv": _jira_rows(register),
    }
    for filename, rows in files.items():
        _write_csv(output / filename, rows)

    (output / "quality_summary.json").write_text(
        json.dumps(kpis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "quality_assurance_plan.md").write_text(
        _quality_plan(register, kpis), encoding="utf-8"
    )
    (output / "confluence_quality_summary.md").write_text(
        _confluence_summary(register, kpis), encoding="utf-8"
    )
    return {filename: len(rows) for filename, rows in files.items()}


def _project_rows(register: QualityRegister) -> list[dict[str, Any]]:
    return [
        {
            "project_id": project.id,
            "project_name": project.name,
            "product_type": project.product_type,
            "customer": project.customer,
            "quality_plan_ref": project.quality_plan_ref,
        }
        for project in register.projects
    ]


def _date_rows(register: QualityRegister) -> list[dict[str, Any]]:
    dates = {register.as_of}
    for complaint in register.complaints:
        dates.add(complaint.opened_on)
        if complaint.closed_on:
            dates.add(complaint.closed_on)
    for action in register.corrective_actions:
        dates.add(action.due_date)
        if action.closed_on:
            dates.add(action.closed_on)
    for risk in register.risks:
        dates.add(risk.due_date)
    for audit in register.audits:
        dates.add(audit.planned_on)
        if audit.completed_on:
            dates.add(audit.completed_on)
    start, end = min(dates), max(dates)
    rows: list[dict[str, Any]] = []
    current = start
    while current <= end:
        rows.append(
            {
                "date": current.isoformat(),
                "year": current.year,
                "month_number": current.month,
                "month": current.strftime("%B"),
                "quarter": f"Q{((current.month - 1) // 3) + 1}",
                "iso_week": current.isocalendar().week,
            }
        )
        current += timedelta(days=1)
    return rows


def _requirement_rows(register: QualityRegister) -> list[dict[str, Any]]:
    return [
        {
            "requirement_id": item.id,
            "project_id": item.project_id,
            "source": item.source,
            "reference": item.reference,
            "description": item.description,
            "verification_method": item.verification_method,
            "status": item.status,
        }
        for item in register.requirements
    ]


def _complaint_rows(register: QualityRegister) -> list[dict[str, Any]]:
    records = {record.complaint_id: record for record in register.eight_d_records}
    return [
        {
            "complaint_id": item.id,
            "project_id": item.project_id,
            "customer_reference": item.customer_reference,
            "opened_on": item.opened_on,
            "closed_on": item.closed_on,
            "status": item.status,
            "severity": item.severity,
            "current_8d_stage": item.current_8d_stage,
            "jira_key": item.jira_key,
            "summary": item.summary,
            "root_cause_recorded": bool(
                records.get(item.id) and records[item.id].root_cause
            ),
            "requirement_ids": "|".join(item.requirement_ids),
        }
        for item in register.complaints
    ]


def _action_rows(register: QualityRegister) -> list[dict[str, Any]]:
    return [
        {
            "action_id": item.id,
            "project_id": item.project_id,
            "complaint_id": item.complaint_id,
            "source_type": item.source_type,
            "description": item.description,
            "owner": item.owner,
            "due_date": item.due_date,
            "status": item.status,
            "closed_on": item.closed_on,
            "verification_evidence": item.verification_evidence,
            "is_overdue": item.status != Status.CLOSED
            and item.due_date < register.as_of,
        }
        for item in register.corrective_actions
    ]


def _risk_rows(register: QualityRegister) -> list[dict[str, Any]]:
    return [
        {
            "risk_id": item.id,
            "project_id": item.project_id,
            "description": item.description,
            "likelihood": item.likelihood,
            "impact": item.impact,
            "gross_score": item.gross_score,
            "residual_likelihood": item.residual_likelihood,
            "residual_impact": item.residual_impact,
            "residual_score": item.residual_score,
            "owner": item.owner,
            "mitigation": item.mitigation,
            "due_date": item.due_date,
            "status": item.status,
        }
        for item in register.risks
    ]


def _audit_rows(register: QualityRegister) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for audit in register.audits:
        findings = audit.findings or [None]
        for finding in findings:
            rows.append(
                {
                    "audit_id": audit.id,
                    "project_id": audit.project_id,
                    "audit_type": audit.audit_type,
                    "planned_on": audit.planned_on,
                    "completed_on": audit.completed_on,
                    "audit_status": audit.status,
                    "scope": audit.scope,
                    "finding_id": finding.id if finding else None,
                    "finding_severity": finding.severity if finding else None,
                    "finding_status": finding.status if finding else None,
                    "finding_description": finding.description if finding else None,
                    "action_id": finding.action_id if finding else None,
                }
            )
    return rows


def _jira_rows(register: QualityRegister) -> list[dict[str, Any]]:
    complaint_by_id = {item.id: item for item in register.complaints}
    rows: list[dict[str, Any]] = []
    for action in register.corrective_actions:
        complaint = (
            complaint_by_id.get(action.complaint_id) if action.complaint_id else None
        )
        high_priority = (
            action.status != Status.CLOSED and action.due_date < register.as_of
        ) or (
            complaint is not None
            and complaint.severity.lower() in {"critical", "major"}
        )
        priority = "High" if high_priority else "Medium"
        rows.append(
            {
                "external_id": action.id,
                "summary": f"Quality action {action.id}: {action.description[:80]}",
                "issue_type": "Task",
                "priority": priority,
                "description": action.description,
                "due_date": action.due_date,
                "labels": f"quality,{action.source_type.replace(' ', '-').lower()}",
                "project_id": action.project_id,
                "source_reference": action.complaint_id or action.source_type,
                "owner": action.owner,
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"cannot export empty dataset: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _serialize(value) for key, value in row.items()})


def _serialize(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Status):
        return value.value
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def _quality_plan(register: QualityRegister, kpis: Mapping[str, Any]) -> str:
    lines = [
        "# Generated Quality Assurance Plan Summary",
        "",
        f"Evidence date: {register.as_of.isoformat()}",
        "",
        (
            "This generated summary supports review and planning. It does not assess or certify "
            "ISO 9001 or AS9100D compliance."
        ),
        "",
        "## Quality objectives and measurements",
        "",
        f"- Requirement verification rate: {kpis['requirement_verification_rate']}%",
        f"- Open customer complaints: {kpis['complaints_open']}",
        f"- Open / overdue corrective actions: {kpis['actions_open']} / {kpis['actions_overdue']}",
        f"- Open audit findings: {kpis['audit_findings_open']}",
        f"- Residual risk exposure: {kpis['residual_risk_exposure']}",
        "",
        "## Project quality setup",
        "",
    ]
    for project in register.projects:
        open_actions = sum(
            action.project_id == project.id and action.status != Status.CLOSED
            for action in register.corrective_actions
        )
        open_risks = sum(
            risk.project_id == project.id and risk.status != Status.CLOSED
            for risk in register.risks
        )
        lines.extend(
            [
                f"### {project.id} - {project.name}",
                "",
                f"- Product type: {project.product_type}",
                f"- Customer: {project.customer}",
                f"- Quality plan reference: {project.quality_plan_ref}",
                f"- Open actions: {open_actions}",
                f"- Open risks: {open_risks}",
                "",
            ]
        )
    lines.extend(
        [
            "## Required review decisions",
            "",
            "- Confirm stakeholder roles and approval authority.",
            "- Review customer-specific requirements and verification evidence.",
            "- Review overdue actions, complaint containment, root causes and effectiveness checks.",
            "- Review risk mitigations and residual exposure.",
            "- Confirm audit scope, evidence availability and finding follow-up.",
            "",
        ]
    )
    return "\n".join(lines)


def _confluence_summary(
    register: QualityRegister, kpis: Mapping[str, Any]
) -> str:
    return "\n".join(
        [
            "# Quality Status Summary",
            "",
            f"_Generated for review on {register.as_of.isoformat()}._",
            "",
            "| Measure | Value |",
            "| --- | ---: |",
            f"| Verified requirements | {kpis['requirements_verified']} / {kpis['requirements_total']} |",
            f"| Open complaints | {kpis['complaints_open']} |",
            f"| Open corrective actions | {kpis['actions_open']} |",
            f"| Overdue corrective actions | {kpis['actions_overdue']} |",
            f"| Open audit findings | {kpis['audit_findings_open']} |",
            f"| Residual risk exposure | {kpis['residual_risk_exposure']} |",
            "",
            "## Meeting focus",
            "",
            "1. Complaint containment and 8D progress.",
            "2. Overdue actions and verification evidence.",
            "3. Customer-requirement verification gaps.",
            "4. Risk mitigation status and residual exposure.",
            "5. Audit preparation and finding closure.",
            "",
            "This Markdown is a handoff artifact; publishing it to Confluence remains a controlled user action.",
            "",
        ]
    )

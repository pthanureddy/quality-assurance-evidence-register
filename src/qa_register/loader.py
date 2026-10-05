import json
from collections.abc import Iterable
from pathlib import Path

from .models import QualityRegister


def _require_unique(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise ValueError(f"duplicate {label} id(s): {joined}")


def load_register(path: str | Path) -> QualityRegister:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    register = QualityRegister.model_validate(payload)

    collections = {
        "project": register.projects,
        "requirement": register.requirements,
        "complaint": register.complaints,
        "8D record": register.eight_d_records,
        "corrective action": register.corrective_actions,
        "risk": register.risks,
        "audit": register.audits,
    }
    for label, records in collections.items():
        _require_unique((record.id for record in records), label)

    project_ids = {project.id for project in register.projects}
    requirement_ids = {requirement.id for requirement in register.requirements}
    complaint_ids = {complaint.id for complaint in register.complaints}
    action_ids = {action.id for action in register.corrective_actions}

    for requirement in register.requirements:
        _require_reference(requirement.project_id, project_ids, requirement.id, "project")
    for complaint in register.complaints:
        _require_reference(complaint.project_id, project_ids, complaint.id, "project")
        for requirement_id in complaint.requirement_ids:
            _require_reference(requirement_id, requirement_ids, complaint.id, "requirement")
    for record in register.eight_d_records:
        _require_reference(record.complaint_id, complaint_ids, record.id, "complaint")
        complaint = next(item for item in register.complaints if item.id == record.complaint_id)
        if record.completed_stage() != complaint.current_8d_stage:
            raise ValueError(
                f"{record.id} completed stage {record.completed_stage()} does not match "
                f"{complaint.id} stage {complaint.current_8d_stage}"
            )
    for action in register.corrective_actions:
        _require_reference(action.project_id, project_ids, action.id, "project")
        if action.complaint_id is not None:
            _require_reference(action.complaint_id, complaint_ids, action.id, "complaint")
    for risk in register.risks:
        _require_reference(risk.project_id, project_ids, risk.id, "project")
    for audit in register.audits:
        _require_reference(audit.project_id, project_ids, audit.id, "project")
        for finding in audit.findings:
            if finding.action_id is not None:
                _require_reference(finding.action_id, action_ids, finding.id, "corrective action")

    return register


def _require_reference(value: str, allowed: set[str], owner: str, label: str) -> None:
    if value not in allowed:
        raise ValueError(f"{owner} references unknown {label} {value}")


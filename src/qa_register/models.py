from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Status(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Project(StrictModel):
    id: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=3, max_length=160)
    product_type: str = Field(min_length=2, max_length=60)
    customer: str = Field(min_length=2, max_length=120)
    quality_plan_ref: str = Field(min_length=2, max_length=80)


class QualityRequirement(StrictModel):
    id: str
    project_id: str
    source: str
    reference: str
    description: str
    verification_method: str
    status: str


class Complaint(StrictModel):
    id: str
    project_id: str
    customer_reference: str
    opened_on: date
    closed_on: date | None = None
    status: Status
    summary: str
    severity: str
    current_8d_stage: str = Field(pattern=r"^D[1-8]$")
    jira_key: str | None = None
    requirement_ids: list[str] = Field(default_factory=list)

    @field_validator("closed_on")
    @classmethod
    def closure_must_not_precede_opening(
        cls, value: date | None, info: Any
    ) -> date | None:
        opened_on = info.data.get("opened_on")
        if value is not None and opened_on is not None and value < opened_on:
            raise ValueError("closed_on cannot precede opened_on")
        return value


class EightDRecord(StrictModel):
    id: str
    complaint_id: str
    team: str | None = None
    problem_statement: str | None = None
    containment_action: str | None = None
    root_cause: str | None = None
    corrective_action: str | None = None
    validation_evidence: str | None = None
    preventive_action: str | None = None
    closure_note: str | None = None

    def completed_stage(self) -> str:
        fields = (
            self.team,
            self.problem_statement,
            self.containment_action,
            self.root_cause,
            self.corrective_action,
            self.validation_evidence,
            self.preventive_action,
            self.closure_note,
        )
        completed = sum(value is not None and value.strip() != "" for value in fields)
        return f"D{max(1, completed)}"


class CorrectiveAction(StrictModel):
    id: str
    project_id: str
    complaint_id: str | None = None
    source_type: str
    description: str
    owner: str
    due_date: date
    status: Status
    closed_on: date | None = None
    verification_evidence: str | None = None

    @field_validator("closed_on")
    @classmethod
    def closed_date_requires_closed_status(
        cls, value: date | None, info: Any
    ) -> date | None:
        status = info.data.get("status")
        if value is not None and status != Status.CLOSED:
            raise ValueError("closed_on is allowed only when status is closed")
        return value


class Risk(StrictModel):
    id: str
    project_id: str
    description: str
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    residual_likelihood: int = Field(ge=1, le=5)
    residual_impact: int = Field(ge=1, le=5)
    owner: str
    mitigation: str
    due_date: date
    status: Status

    @property
    def gross_score(self) -> int:
        return self.likelihood * self.impact

    @property
    def residual_score(self) -> int:
        return self.residual_likelihood * self.residual_impact


class AuditFinding(StrictModel):
    id: str
    severity: str
    status: Status
    description: str
    action_id: str | None = None


class Audit(StrictModel):
    id: str
    project_id: str
    audit_type: str
    planned_on: date
    completed_on: date | None = None
    status: str
    scope: str
    findings: list[AuditFinding] = Field(default_factory=list)


class QualityRegister(StrictModel):
    as_of: date
    projects: list[Project]
    requirements: list[QualityRequirement]
    complaints: list[Complaint]
    eight_d_records: list[EightDRecord]
    corrective_actions: list[CorrectiveAction]
    risks: list[Risk]
    audits: list[Audit]


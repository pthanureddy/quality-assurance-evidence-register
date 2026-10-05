import csv
import json
from pathlib import Path

from qa_register.exporter import export_register

EXPECTED_FILES = {
    "dim_project.csv",
    "dim_date.csv",
    "fact_requirements.csv",
    "fact_complaints.csv",
    "fact_actions.csv",
    "fact_risks.csv",
    "fact_audit_findings.csv",
    "fact_kpis.csv",
    "jira_action_handoff.csv",
    "quality_summary.json",
    "quality_assurance_plan.md",
    "confluence_quality_summary.md",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_exports_expected_artifacts(register, tmp_path):
    export_register(register, tmp_path)
    assert {path.name for path in tmp_path.iterdir()} == EXPECTED_FILES


def test_manifest_reports_fact_row_counts(register, tmp_path):
    manifest = export_register(register, tmp_path)
    assert manifest["fact_requirements.csv"] == 4
    assert manifest["fact_complaints.csv"] == 3
    assert manifest["fact_actions.csv"] == 5
    assert manifest["fact_audit_findings.csv"] == 3


def test_action_export_marks_only_open_past_due_action(register, tmp_path):
    export_register(register, tmp_path)
    rows = read_csv(tmp_path / "fact_actions.csv")
    overdue = [row["action_id"] for row in rows if row["is_overdue"] == "true"]
    assert overdue == ["ACT-001"]


def test_jira_handoff_prioritizes_overdue_or_severe_complaints(register, tmp_path):
    export_register(register, tmp_path)
    rows = {row["external_id"]: row for row in read_csv(tmp_path / "jira_action_handoff.csv")}
    assert rows["ACT-001"]["priority"] == "High"
    assert rows["ACT-002"]["priority"] == "High"
    assert rows["ACT-003"]["priority"] == "High"
    assert rows["ACT-004"]["priority"] == "Medium"


def test_summary_json_matches_metrics(register, tmp_path):
    export_register(register, tmp_path)
    summary = json.loads((tmp_path / "quality_summary.json").read_text(encoding="utf-8"))
    assert summary["requirement_verification_rate"] == 75.0
    assert summary["residual_risk_exposure"] == 12


def test_date_dimension_is_contiguous(register, tmp_path):
    export_register(register, tmp_path)
    rows = read_csv(tmp_path / "dim_date.csv")
    assert rows[0]["date"] == "2026-05-01"
    assert rows[-1]["date"] == "2026-08-05"
    assert len(rows) == 97


def test_quality_plan_contains_boundary_and_review_topics(register, tmp_path):
    export_register(register, tmp_path)
    content = (tmp_path / "quality_assurance_plan.md").read_text(encoding="utf-8")
    assert "does not assess or certify ISO 9001 or AS9100D compliance" in content
    assert "Review risk mitigations and residual exposure" in content


def test_confluence_handoff_remains_controlled_user_action(register, tmp_path):
    export_register(register, tmp_path)
    content = (tmp_path / "confluence_quality_summary.md").read_text(encoding="utf-8")
    assert "publishing it to Confluence remains a controlled user action" in content

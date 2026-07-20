import pytest
from pydantic import ValidationError

from qa_register.loader import load_register


def test_loads_sample_and_preserves_counts(register):
    assert len(register.projects) == 2
    assert len(register.requirements) == 4
    assert len(register.complaints) == 3
    assert len(register.corrective_actions) == 5


def test_rejects_unknown_fields(sample_payload, write_payload):
    sample_payload["projects"][0]["uncontrolled_note"] = "not allowed"
    with pytest.raises(ValidationError, match="uncontrolled_note"):
        load_register(write_payload(sample_payload))


def test_rejects_duplicate_project_id(sample_payload, write_payload):
    sample_payload["projects"][1]["id"] = sample_payload["projects"][0]["id"]
    with pytest.raises(ValueError, match="duplicate project id"):
        load_register(write_payload(sample_payload))


def test_rejects_unknown_project_reference(sample_payload, write_payload):
    sample_payload["requirements"][0]["project_id"] = "MISSING"
    with pytest.raises(ValueError, match="REQ-001 references unknown project MISSING"):
        load_register(write_payload(sample_payload))


def test_rejects_unknown_requirement_reference(sample_payload, write_payload):
    sample_payload["complaints"][0]["requirement_ids"] = ["REQ-MISSING"]
    with pytest.raises(ValueError, match="COMP-001 references unknown requirement"):
        load_register(write_payload(sample_payload))


def test_rejects_unknown_complaint_reference(sample_payload, write_payload):
    sample_payload["eight_d_records"][0]["complaint_id"] = "COMP-MISSING"
    with pytest.raises(ValueError, match="8D-001 references unknown complaint"):
        load_register(write_payload(sample_payload))


def test_rejects_8d_stage_mismatch(sample_payload, write_payload):
    sample_payload["complaints"][0]["current_8d_stage"] = "D7"
    with pytest.raises(ValueError, match="completed stage D6.*stage D7"):
        load_register(write_payload(sample_payload))


def test_rejects_unknown_audit_action(sample_payload, write_payload):
    sample_payload["audits"][0]["findings"][0]["action_id"] = "ACT-MISSING"
    with pytest.raises(ValueError, match="FIND-001 references unknown corrective action"):
        load_register(write_payload(sample_payload))


def test_rejects_out_of_range_risk_score(sample_payload, write_payload):
    sample_payload["risks"][0]["likelihood"] = 6
    with pytest.raises(ValidationError, match="less than or equal to 5"):
        load_register(write_payload(sample_payload))


def test_rejects_closed_date_before_complaint_opened(sample_payload, write_payload):
    sample_payload["complaints"][2]["closed_on"] = "2026-04-30"
    with pytest.raises(ValidationError, match="closed_on cannot precede opened_on"):
        load_register(write_payload(sample_payload))

import copy
import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

from qa_register.cli import main
from qa_register.field_quality import (
    CostAssumptions,
    FieldSnapshot,
    build_field_cases,
    estimate_cost,
    export_field_cases,
    load_field_snapshot,
    wilson_interval,
)

FIELD_SAMPLE = Path(__file__).parents[1] / "data/sample_field_quality.json"


@pytest.fixture
def field_payload():
    return json.loads(FIELD_SAMPLE.read_text())


def test_distinct_units_are_not_repeat_event_counts(field_payload):
    report = build_field_cases(FieldSnapshot.model_validate(field_payload), "digest")
    case = next(c for c in report["cases"] if c["product"] == "SIM-A" and c["domain"] == "digital")
    assert case["current"]["eligible_units"] == 8
    assert case["current"]["affected_units"] == 2
    assert case["current"]["confirmed_events"] == 3
    assert case["current"]["pending_events"] == 1
    assert case["current"]["affected_fraction"] == 0.25
    assert case["baseline"]["affected_units"] == 1
    assert case["change_percentage_points"] == 12.5
    north = next(m for m in case["markets"] if m["market"] == "NORTH")
    west = next(m for m in case["markets"] if m["market"] == "WEST")
    assert north["current"]["affected_fraction"] == 0.5
    assert west["current"]["affected_fraction"] == 0.0
    component = next(c for c in report["cases"] if c["domain"] == "component")
    assert component["current"]["eligible_units"] == 6


def test_pending_safety_report_requires_review_without_counting_as_confirmed(field_payload):
    report = build_field_cases(FieldSnapshot.model_validate(field_payload), "digest")
    first = report["cases"][0]
    assert first["product"] == "SIM-B" and first["safety_report_present"]
    assert first["current"]["affected_units"] == 1
    assert first["current"]["pending_events"] == 1
    assert report["rejected_issue_ids"] == ["ISS-011"]
    assert report["outside_window_issue_ids"] == ["ISS-012"]
    assert all(
        not row["request_sent"]
        for c in report["cases"]
        for row in c["technical_material_checklist"]
    )


def test_wilson_known_values_and_boundary_counts():
    assert wilson_interval(4, 20) == pytest.approx([0.08065766, 0.41601743], abs=1e-8)
    assert wilson_interval(0, 10) == pytest.approx([0, 0.2775328], abs=1e-8)
    assert wilson_interval(1, 1) == pytest.approx([0.20654931, 1], abs=1e-8)
    assert wilson_interval(0, 0) is None


@pytest.mark.parametrize("affected,eligible", [(2, 1), (-1, 1), (0, -1), (True, 2), (1, 2.0)])
def test_invalid_statistical_denominators(affected, eligible):
    with pytest.raises(ValueError):
        wilson_interval(affected, eligible)


def test_cost_arithmetic_and_rounding(field_payload):
    assumptions = CostAssumptions.model_validate(field_payload["costs"])
    assert estimate_cost(2, assumptions) == {
        "units": 2,
        "gross_minor": 36000,
        "contribution_minor": 18000,
        "assumption_ref": "COST-001",
        "approved": False,
    }
    fractional = assumptions.model_copy(
        update={
            "parts_minor": 0,
            "logistics_minor": 0,
            "labor_minutes": 30,
            "labor_rate_minor_per_hour": 1,
        }
    )
    assert estimate_cost(3, fractional)["gross_minor"] == 2
    assert estimate_cost(0, assumptions)["gross_minor"] == 0
    with pytest.raises(ValueError):
        estimate_cost(-1, assumptions)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_asset",
        "duplicate_issue",
        "unknown_asset",
        "ineligible_domain",
        "overlap",
        "reverse_period",
        "future_report",
        "report_before_event",
        "late_cohort",
        "duplicate_domain",
        "return_without_part",
        "invalid_cost",
        "bool_money",
        "excess_share",
        "unknown_field",
        "real_scope",
    ],
)
def test_rejects_ambiguous_or_invalid_measurement_input(field_payload, mutation):
    p = copy.deepcopy(field_payload)
    if mutation == "duplicate_asset":
        p["assets"].append(p["assets"][0])
    elif mutation == "duplicate_issue":
        p["issues"].append(p["issues"][0])
    elif mutation == "unknown_asset":
        p["issues"][0]["asset_id"] = "MISSING"
    elif mutation == "ineligible_domain":
        p["issues"][8]["domain"] = "component"
    elif mutation == "overlap":
        p["baseline_end"] = p["current_start"]
    elif mutation == "reverse_period":
        p["current_end"] = "2026-07-01"
    elif mutation == "future_report":
        p["issues"][0]["reported_on"] = "2026-11-01"
    elif mutation == "report_before_event":
        p["issues"][0]["reported_on"] = "2026-01-01"
    elif mutation == "late_cohort":
        p["assets"][0]["enrolled_on"] = "2026-07-01"
    elif mutation == "duplicate_domain":
        p["assets"][0]["domains"].append("digital")
    elif mutation == "return_without_part":
        p["issues"][0]["return_status"] = "requested"
    elif mutation == "invalid_cost":
        p["costs"]["parts_minor"] = -1
    elif mutation == "bool_money":
        p["costs"]["parts_minor"] = True
    elif mutation == "excess_share":
        p["costs"]["contribution_bps"] = 10001
    elif mutation == "unknown_field":
        p["costs"]["approved"] = True
    elif mutation == "real_scope":
        p["data_scope"] = "production"
    with pytest.raises(ValueError):
        FieldSnapshot.model_validate(p)


def test_deterministic_bundle_and_pareto_scope(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    summary = export_field_cases(FIELD_SAMPLE, one)
    export_field_cases(FIELD_SAMPLE, two)
    assert summary["assets"] == 12 and summary["source_issues"] == 12 and summary["cases"] == 3
    assert summary["source_sha256"] == hashlib.sha256(FIELD_SAMPLE.read_bytes()).hexdigest()
    for path in one.iterdir():
        assert path.read_bytes() == (two / path.name).read_bytes()
    rows = list(csv.DictReader((one / "pareto.csv").open()))
    assert [int(r["confirmed_issue_unit_pairs"]) for r in rows] == [2, 2, 1]
    assert float(rows[-1]["cumulative_share"]) == 1.0
    costs = list(csv.DictReader((one / "cost_scenarios.csv").open()))
    assert len(costs) == 6 and all(row["approved"] == "False" for row in costs)
    assert "DRAFT - human review required" in (one / "review_pack.md").read_text()


def test_empty_current_period_is_a_valid_zero_case_export(field_payload, tmp_path):
    field_payload["issues"] = []
    path = tmp_path / "empty.json"
    path.write_text(json.dumps(field_payload))
    assert export_field_cases(path, tmp_path / "out")["cases"] == 0
    assert (tmp_path / "out" / "pareto.csv").read_text().count("\n") == 1


def test_bounded_source_and_duplicate_json_keys(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"x":1,"x":2}')
    with pytest.raises(ValueError, match="Duplicate JSON"):
        load_field_snapshot(path)
    path.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="5 MiB"):
        load_field_snapshot(path)


def test_field_case_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["qa-register", "field-cases", "--input", str(FIELD_SAMPLE), "--output", str(tmp_path)],
    )
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["cases"] == 3
    monkeypatch.setattr(sys, "argv", ["qa-register", "field-cases", "--input", str(FIELD_SAMPLE)])
    with pytest.raises(SystemExit, match="--output"):
        main()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "qa-register",
            "field-cases",
            "--input",
            "missing-private-source.json",
            "--output",
            str(tmp_path),
        ],
    )
    assert main() == 2
    output = capsys.readouterr().out
    assert "missing-private-source" not in output

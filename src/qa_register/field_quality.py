"""Static-cohort, synthetic field-quality measurements and human-review drafts."""

import csv
import hashlib
import json
import math
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .models import StrictModel

Code = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")]
Money = Annotated[int, Field(strict=True, ge=0, le=10**12)]


class Asset(StrictModel):
    id: Code
    product: Code
    market: Code
    domains: list[Code] = Field(min_length=1)
    enrolled_on: date


class FieldIssue(StrictModel):
    id: Code
    asset_id: Code
    domain: Code
    component: Code
    symptom: Code
    occurred_on: date
    reported_on: date
    status: Literal["confirmed", "pending", "rejected"]
    severity: Literal["safety", "major", "minor"]
    evidence_ref: Code
    part_ref: Code | None = None
    return_status: Literal["none", "requested", "received"] = "none"
    reported_cost_minor: Money = 0


class CostAssumptions(StrictModel):
    parts_minor: Money
    logistics_minor: Money
    labor_minutes: Annotated[int, Field(strict=True, ge=0, le=10000)]
    labor_rate_minor_per_hour: Money
    contribution_bps: Annotated[int, Field(strict=True, ge=0, le=10000)]
    assumption_ref: Code


class FieldSnapshot(StrictModel):
    data_scope: Literal["synthetic"]
    source_name: Code
    as_of: date
    baseline_start: date
    baseline_end: date
    current_start: date
    current_end: date
    currency: Literal["EUR", "SEK", "USD"]
    assets: list[Asset] = Field(min_length=1, max_length=50000)
    issues: list[FieldIssue] = Field(max_length=100000)
    costs: CostAssumptions

    @model_validator(mode="after")
    def consistent_snapshot(self):
        if not (
            self.baseline_start
            <= self.baseline_end
            < self.current_start
            <= self.current_end
            <= self.as_of
        ):
            raise ValueError("Periods must be ordered, nonoverlapping and not after cutoff")
        if len({a.id for a in self.assets}) != len(self.assets):
            raise ValueError("Duplicate asset ID")
        if len({i.id for i in self.issues}) != len(self.issues):
            raise ValueError("Duplicate issue ID")
        assets = {a.id: a for a in self.assets}
        for asset in self.assets:
            if asset.enrolled_on > self.baseline_start or len(set(asset.domains)) != len(
                asset.domains
            ):
                raise ValueError("Cohort must predate both periods and have unique domains")
        for issue in self.issues:
            asset = assets.get(issue.asset_id)
            if asset is None or issue.domain not in asset.domains:
                raise ValueError("Unknown asset or ineligible domain")
            if not issue.occurred_on <= issue.reported_on <= self.as_of:
                raise ValueError("Invalid occurrence/report/cutoff order")
            if issue.return_status != "none" and issue.part_ref is None:
                raise ValueError("A requested/received return needs a part reference")
        return self


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def load_field_snapshot(path: Path) -> tuple[FieldSnapshot, str]:
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("Input exceeds 5 MiB")
    raw = path.read_bytes()
    payload = json.loads(raw, object_pairs_hook=_unique_keys)
    return FieldSnapshot.model_validate(payload), hashlib.sha256(raw).hexdigest()


def wilson_interval(affected: int, eligible: int) -> list[float] | None:
    if type(affected) is not int or type(eligible) is not int or not 0 <= affected <= eligible:
        raise ValueError("Counts must be integers with 0 <= affected <= eligible")
    if eligible == 0:
        return None
    z = 1.959963984540054
    proportion = affected / eligible
    divisor = 1 + z * z / eligible
    center = (proportion + z * z / (2 * eligible)) / divisor
    half = (
        z
        * math.sqrt(proportion * (1 - proportion) / eligible + z * z / (4 * eligible**2))
        / divisor
    )
    return [max(0.0, center - half), min(1.0, center + half)]


def estimate_cost(units: int, assumptions: CostAssumptions) -> dict:
    if type(units) is not int or units < 0:
        raise ValueError("Units must be a nonnegative integer")
    labor = Decimal(assumptions.labor_minutes) * assumptions.labor_rate_minor_per_hour / 60
    gross = int(
        (units * (assumptions.parts_minor + assumptions.logistics_minor + labor)).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )
    funded = int(
        (Decimal(gross) * assumptions.contribution_bps / 10000).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )
    )
    return {
        "units": units,
        "gross_minor": gross,
        "contribution_minor": funded,
        "assumption_ref": assumptions.assumption_ref,
        "approved": False,
    }


def _measure(issues: list[FieldIssue], cohort: list[Asset], start: date, end: date) -> dict:
    ids = {a.id for a in cohort}
    selected = [i for i in issues if i.asset_id in ids and start <= i.occurred_on <= end]
    confirmed = [i for i in selected if i.status == "confirmed"]
    affected = len({i.asset_id for i in confirmed})
    eligible = len(cohort)
    return {
        "eligible_units": eligible,
        "affected_units": affected,
        "confirmed_events": len(confirmed),
        "pending_events": sum(i.status == "pending" for i in selected),
        "affected_fraction": affected / eligible if eligible else None,
        "wilson_95": wilson_interval(affected, eligible),
        "issue_ids": sorted(i.id for i in selected),
    }


def build_field_cases(snapshot: FieldSnapshot, source_sha256: str) -> dict:
    assets = {a.id: a for a in snapshot.assets}
    groups = {}
    for issue in snapshot.issues:
        if issue.status != "rejected":
            key = (assets[issue.asset_id].product, issue.domain, issue.component, issue.symptom)
            groups.setdefault(key, []).append(issue)
    cases = []
    for key, issues in sorted(groups.items()):
        current_issues = [
            i for i in issues if snapshot.current_start <= i.occurred_on <= snapshot.current_end
        ]
        if not current_issues:
            continue
        product, domain, component, symptom = key
        cohort = [a for a in snapshot.assets if a.product == product and domain in a.domains]
        current = _measure(issues, cohort, snapshot.current_start, snapshot.current_end)
        baseline = _measure(issues, cohort, snapshot.baseline_start, snapshot.baseline_end)
        markets = [
            {
                "market": market,
                "current": _measure(
                    issues,
                    [a for a in cohort if a.market == market],
                    snapshot.current_start,
                    snapshot.current_end,
                ),
                "baseline": _measure(
                    issues,
                    [a for a in cohort if a.market == market],
                    snapshot.baseline_start,
                    snapshot.baseline_end,
                ),
            }
            for market in sorted({a.market for a in cohort})
        ]
        part_requests = [
            {
                "issue_id": i.id,
                "evidence_ref": i.evidence_ref,
                "part_ref": i.part_ref,
                "return_status": i.return_status,
                "request_sent": False,
            }
            for i in sorted(current_issues, key=lambda i: i.id)
        ]
        cases.append(
            {
                "case_id": "QC-" + hashlib.sha256("|".join(key).encode()).hexdigest()[:12],
                "product": product,
                "domain": domain,
                "component": component,
                "symptom": symptom,
                "phase": "Draft Define/Measure - human review required",
                "safety_report_present": any(i.severity == "safety" for i in current_issues),
                "current": current,
                "baseline": baseline,
                "change_percentage_points": 100
                * (current["affected_fraction"] - baseline["affected_fraction"]),
                "reported_cost_minor_unverified": sum(
                    i.reported_cost_minor for i in current_issues
                ),
                "markets": markets,
                "technical_material_checklist": part_requests,
                "cost_scenarios": {
                    "confirmed_affected_units_only": estimate_cost(
                        current["affected_units"], snapshot.costs
                    ),
                    "entire_eligible_cohort": estimate_cost(
                        current["eligible_units"], snapshot.costs
                    ),
                },
            }
        )
    cases.sort(
        key=lambda c: (
            not c["safety_report_present"],
            -c["current"]["affected_units"],
            -c["reported_cost_minor_unverified"],
            c["case_id"],
        )
    )
    for priority, case in enumerate(cases, 1):
        case["review_priority"] = priority
    return {
        "data_scope": "synthetic",
        "as_of": snapshot.as_of.isoformat(),
        "source_name": snapshot.source_name,
        "source_sha256": source_sha256,
        "assets": len(snapshot.assets),
        "source_issues": len(snapshot.issues),
        "rejected_issue_ids": sorted(i.id for i in snapshot.issues if i.status == "rejected"),
        "outside_window_issue_ids": sorted(
            i.id
            for i in snapshot.issues
            if not (
                snapshot.baseline_start <= i.occurred_on <= snapshot.baseline_end
                or snapshot.current_start <= i.occurred_on <= snapshot.current_end
            )
        ),
        "currency": snapshot.currency,
        "periods": {
            "baseline": [str(snapshot.baseline_start), str(snapshot.baseline_end)],
            "current": [str(snapshot.current_start), str(snapshot.current_end)],
        },
        "priority_policy": "Safety reports first (including unconfirmed), then confirmed affected units, then unverified reported cost; human triage required",
        "measurement_boundary": "Same declared eligible cohort in both periods; proportions, not exposure-hour failure rates, causal findings or Volvo field results",
        "cost_boundary": "Hypothetical input assumptions, aggregate half-up minor-unit rounding; no Special Commitment approval or liability estimate",
        "cases": cases,
    }


def _csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def export_field_cases(path: Path, output: Path) -> dict:
    snapshot, digest = load_field_snapshot(path)
    report = build_field_cases(snapshot, digest)
    output.mkdir(parents=True, exist_ok=True)
    (output / "field_quality_cases.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    rows = []
    costs = []
    for case in report["cases"]:
        for market in case["markets"]:
            for period in ("baseline", "current"):
                measurement = market[period]
                rows.append(
                    {
                        "case_id": case["case_id"],
                        "market": market["market"],
                        "period": period,
                        **{
                            k: measurement[k]
                            for k in (
                                "eligible_units",
                                "affected_units",
                                "confirmed_events",
                                "pending_events",
                                "affected_fraction",
                            )
                        },
                    }
                )
        for name, scenario in case["cost_scenarios"].items():
            costs.append(
                {
                    "case_id": case["case_id"],
                    "scenario": name,
                    "currency": snapshot.currency,
                    **scenario,
                }
            )
    _csv(
        output / "market_measurements.csv",
        [
            "case_id",
            "market",
            "period",
            "eligible_units",
            "affected_units",
            "confirmed_events",
            "pending_events",
            "affected_fraction",
        ],
        rows,
    )
    _csv(
        output / "cost_scenarios.csv",
        [
            "case_id",
            "scenario",
            "currency",
            "units",
            "gross_minor",
            "contribution_minor",
            "assumption_ref",
            "approved",
        ],
        costs,
    )
    pareto = []
    total = sum(c["current"]["affected_units"] for c in report["cases"])
    cumulative = 0
    for case in sorted(
        report["cases"], key=lambda c: (-c["current"]["affected_units"], c["case_id"])
    ):
        cumulative += case["current"]["affected_units"]
        pareto.append(
            {
                "case_id": case["case_id"],
                "confirmed_issue_unit_pairs": case["current"]["affected_units"],
                "cumulative_share": cumulative / total if total else None,
            }
        )
    _csv(
        output / "pareto.csv", ["case_id", "confirmed_issue_unit_pairs", "cumulative_share"], pareto
    )
    lines = [
        "# Synthetic quality case review pack",
        "",
        "DRAFT - human review required.",
        "",
        f"Source SHA256: {digest}",
        report["measurement_boundary"],
        report["cost_boundary"],
        "",
    ]
    for case in report["cases"]:
        measurement = case["current"]
        lines.extend(
            [
                f"## {case['case_id']} - {case['product']}/{case['domain']}/{case['component']}/{case['symptom']}",
                f"Review priority: {case['review_priority']}; safety report: {case['safety_report_present']}",
                f"Current confirmed affected units: {measurement['affected_units']}/{measurement['eligible_units']}; events: {measurement['confirmed_events']}; pending: {measurement['pending_events']}",
                f"Wilson95%: {measurement['wilson_95']}; descriptive change: {case['change_percentage_points']:.4f} percentage points.",
                "Technical material checklist (no request sent): "
                + json.dumps(case["technical_material_checklist"]),
                "Cost scenarios (unapproved): " + json.dumps(case["cost_scenarios"]),
                "Review agenda: confirm problem/scope; check denominators/reporting lag; inspect evidence/parts needs; review cost assumptions; assign accountable follow-up.",
                "Bulletin-support metadata only: affected product/symptom and evidence references above. Root cause, remedy, approval and release remain unset; no service instruction issued.",
                "",
            ]
        )
    (output / "review_pack.md").write_text("\n".join(lines), encoding="utf-8")
    return {
        "assets": report["assets"],
        "source_issues": report["source_issues"],
        "cases": len(report["cases"]),
        "source_sha256": digest,
        "data_scope": "synthetic",
    }

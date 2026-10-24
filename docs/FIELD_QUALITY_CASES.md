# Synthetic Define and Measure case drafts

## Problem and architecture

Complaint counts alone cannot show how widespread a problem is. Repeated reports
from one unit, unequal market populations and pending triage can change the
interpretation. This extension keeps those quantities separate and produces a
reviewable case draft rather than an approved business decision.

`JSON -> strict snapshot/relationship validation -> product/domain/component/symptom
groups -> period/market measures -> review priority/cost scenarios -> JSON/CSV/Markdown`

Python/Pydantic are reused from the existing register. Standard-library math,
Decimal and CSV avoid an unnecessary analytics platform for deterministic small
case reports. The existing complaint/8D/action/risk/audit export is unchanged.

## Input contract

Use `data/sample_field_quality.json` as the executable contract. Unknown fields,
duplicate JSON keys, duplicate asset/report IDs, unknown assets, ineligible
domains, overlapping/reversed periods, late-enrolled cohort units, future
reports, reports before occurrence, missing part references for stated returns,
invalid currency/money and out-of-range contribution shares are rejected.
The input limit is5MiB. Money fields use strict nonnegative integer minor units;
booleans are not amounts. The CLI returns2 on input/output errors without
printing submitted values. A successful export returns0 and its source SHA256.

The input explicitly accepts `data_scope: synthetic`; this reference is not a
live field-data adapter. Assets declare product, market, eligible domains and
enrollment date. Every asset must predate both measurement windows. This is a
fixed eligible cohort assumed observed throughout both windows. There is no
installed-base import, utilization/exposure-hour model, censoring correction,
changing product applicability or geographic representativeness claim.

## Measures and uncertainty

Only confirmed reports form each period's numerator, counting distinct affected
units once per case. Confirmed event count and pending report count remain
separate. Denominators are eligible units of the same product/domain, restricted
to the market for market rows. Baseline/current comparisons use the same cohort.
Dates are inclusive and windows never overlap. Rejected and out-of-window IDs
are exported; they are not silently included in current affected-unit counts.
Reports after the declared analysis cutoff are invalid, not future information.

Wilson95% intervals use the binomial working formula documented in the
[NIST handbook](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).
Zero eligible units yields an undefined interval, not a zero rate. Intervals do
not account for under-reporting, correlated units, exposure differences or
selection bias. A difference in proportions is descriptive percentage points,
not a significance test, root-cause finding or proof of deterioration/improvement.
Even zero confirmed reports does not establish an absence of failures.

The frequency Pareto counts confirmed **issue-unit pairs**. One unit can occur
in different case categories, so the denominator is not the unique fleet and
its cumulative share is not fleet prevalence. Pareto order is distinct from
review priority: any current safety report, including pending reports, goes
first for human triage; then affected-unit count and unverified reported cost,
with stable case-ID tie breaking. This is an explicit example policy, not a
regulatory, safety or company scoring rule. No case is automatically approved.

## Cost and material review

Two hypothetical scopes are calculated per draft: confirmed affected units
only, and the whole declared eligible cohort. Each uses the input parts amount,
labor minutes/hourly rate, logistics amount and contribution basis points.
Decimal arithmetic rounds the aggregated gross amount half-up to integer minor
units; funding is calculated from rounded gross and rounded half-up again.
One currency applies to the snapshot. No FX, tax, warranty eligibility, repeat
repair policy, participation prediction or accounting-liability calculation.
`approved` is always false. These are generic commitment-review scenarios,
not actual Special Commitments or company policy implementation.

Technical-material checklists retain source report/evidence/part references
and declared return state. Reference presence does not verify an attachment or
physical receipt. `request_sent` is always false. The review pack contains an
agenda and affected-product/evidence metadata, not approved root cause, remedy,
repair instructions or a Service Bulletin. No messages or external actions occur.

## Reproduce and inspect

```text
python -m pip install -e ".[dev]"
ruff check .
pytest --cov=qa_register --cov-branch
python -m build
qa-register field-cases --input data/sample_field_quality.json --output build/field
```

Inspect all five files: `field_quality_cases.json`, `market_measurements.csv`,
`pareto.csv`, `cost_scenarios.csv`, `review_pack.md`. Repeating the command on
unchanged source yields byte-identical files in the tested environment. Case
IDs derive from the grouping key; the whole raw input has its own SHA256 so
data changes remain visible. Original report IDs survive the aggregation.
The demonstration has12units,12reports and3drafts; these are invented fixture
quantities, not measured employer/field outcomes. Power BI/Jira/Confluence outputs
elsewhere in the register are file handoffs, not verified live integrations.

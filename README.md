# Quality Assurance Evidence Register

A portfolio reference implementation for tracing quality-planning evidence across synthetic software and hardware projects. It connects customer requirements, complaints, 8D progress, corrective actions, risks, audits and review KPIs in one validated register.

The repository demonstrates a practical quality workflow; it does not claim ISO 9001 or AS9100D certification, compliance, professional aerospace experience or production use.

## What it produces

- A validated JSON source of quality records with cross-reference and stage checks.
- Complaint and generic D1-D8 evidence tracking with corrective-action follow-up.
- Gross and residual risk exposure for risk reviews.
- Audit findings linked to actions and customer requirements linked to complaints.
- A Power BI-ready star-schema export, a generic Jira CSV handoff and Confluence-ready Markdown.
- A generated quality-assurance-plan summary and machine-readable KPI snapshot.

All included people, organizations, projects, requirements and incidents are synthetic.

## Quick start

```text
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/qa-register validate --input data/sample_quality_records.json
.venv/Scripts/qa-register generate --input data/sample_quality_records.json --output build/powerbi
```

On Linux or macOS, use `.venv/bin/python` and `.venv/bin/qa-register`.

Run the quality gates:

```text
.venv/Scripts/ruff check .
.venv/Scripts/pytest
```

## Sample KPI result

The deterministic sample contains two projects, four requirements, three complaints, five corrective actions, three risks and two audits. As of 2026-07-20 it yields:

- 75.0% requirement verification.
- Two open complaints; the closed complaint took 15 days.
- Three open actions, including one overdue; 50.0% of closed actions completed on time.
- One open audit finding.
- Active gross risk exposure of 29 and residual exposure of 12.

These numbers describe the synthetic fixture, not an employer or live customer.

## Documentation

- [Requirements](docs/REQUIREMENTS.md)
- [Standards and claim boundary](docs/STANDARDS_BOUNDARY.md)
- [Quality assurance plan template](docs/QUALITY_ASSURANCE_PLAN_TEMPLATE.md)
- [Complaint and 8D process](docs/COMPLAINT_8D_PROCESS.md)
- [Risk review process](docs/RISK_REVIEW_PROCESS.md)
- [Internal audit preparation checklist](docs/INTERNAL_AUDIT_CHECKLIST.md)
- [Power BI model](docs/POWER_BI_MODEL.md)
- [Jira and Confluence handoff](docs/JIRA_CONFLUENCE_HANDOFF.md)

## Deliberate limitations

- No live Jira, Confluence or Power BI connection and no `.pbix` file.
- No identity, authorization, workflow approval or electronic-signature layer.
- No reproduction of proprietary standards text and no conformity assessment.
- The generated plan is a review aid; accountable stakeholders must approve the real plan and records.

## Container

```text
docker build -t quality-assurance-evidence-register .
docker run --rm quality-assurance-evidence-register
```

The container validates the sample, generates the export bundle and exits.

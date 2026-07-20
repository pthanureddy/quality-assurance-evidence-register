# Power BI Model

The generated CSV files form a simple star-schema handoff. `dim_project` filters requirements, complaints, actions, risks and audit findings by `project_id`. `dim_date` can relate to role-playing dates such as complaint opening, action due date and audit planned date. The model follows Microsoft's public [Power BI star-schema guidance](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema).

Suggested measures:

```text
Open Actions = CALCULATE(COUNTROWS(fact_actions), fact_actions[status] <> "closed")
Overdue Actions = CALCULATE(COUNTROWS(fact_actions), fact_actions[is_overdue] = TRUE())
Requirement Verification % = DIVIDE(CALCULATE(COUNTROWS(fact_requirements), fact_requirements[status] = "verified"), COUNTROWS(fact_requirements))
Open Findings = CALCULATE(COUNTROWS(fact_audit_findings), fact_audit_findings[finding_status] <> "closed", NOT(ISBLANK(fact_audit_findings[finding_id])))
Residual Risk Exposure = SUM(fact_risks[residual_score])
```

Validate relationship direction, date roles and measure behavior in the actual data model. This repository exports data only; it does not include or claim a `.pbix` dashboard.

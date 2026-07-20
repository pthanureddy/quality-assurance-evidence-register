# Demonstration Requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| QAR-01 | Reject records that do not match the typed schema. | Invalid-fixture tests |
| QAR-02 | Reject duplicate entity identifiers. | Loader test |
| QAR-03 | Reject missing project, requirement, complaint or action references. | Loader tests |
| QAR-04 | Reject complaint stage inconsistent with completed 8D evidence. | Loader test |
| QAR-05 | Calculate deterministic requirement, complaint, action, audit and risk KPIs. | Metric tests |
| QAR-06 | Export a project/date dimension and quality fact tables. | Export tests |
| QAR-07 | Mark open actions overdue relative to the register evidence date. | Metric/export tests |
| QAR-08 | Export a generic Jira action handoff and Confluence-ready summary. | Export tests |
| QAR-09 | Generate a quality-plan review summary with an explicit compliance disclaimer. | Export test |
| QAR-10 | Run lint, unit/integration tests and a container smoke test in CI. | GitHub Actions |

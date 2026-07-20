# Jira and Confluence Handoff

`jira_action_handoff.csv` is a generic, reviewable action export. Map its fields to an approved Jira project's schema before import. Priority is high when an open action is overdue or its linked complaint is major/critical; otherwise it is medium.

`confluence_quality_summary.md` is Markdown prepared for human review and controlled publication. It summarizes KPIs and meeting focus.

The tool does not call either service, administer projects or spaces, synchronize updates, handle credentials, or prove professional Jira/Confluence operating experience. A production integration would require authenticated APIs, field/configuration discovery, idempotency, permission checks, error recovery, audit logs and owner approval.

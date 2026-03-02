# architecture decision records: renewal radar sis dashboard

personal decision log for the renewal radar sis dashboard project.
format: adr (architecture decision records): retrospective, covering phase_01 through post-deployment security fixes (2026-03-01).

## how to add new entries

1. create a file `adr-000-title.md` in this folder
2. use the template below
3. add an entry to the index table

### template

```markdown
# adr-00: title

**date:** YYYY-MM-DD
**source:** [run/report where the decision was made or the problem was identified]

## problem

## decision

## alternatives considered

## consequences

## related
```

---

## index

| # | title | date | source run |
|---|-------|------|------------|
| [adr-001](adr-001-ddl-idempotency.md) | ddl idempotency | 2026-02-25 | phase_01_run_01 |
| [adr-002](adr-002-log-audit-event.md) | log_audit_event procedure | 2026-02-25 | phase_01_run_01 |
| [adr-003](adr-003-current-sis-user.md) | current_sis_user identity | 2026-03-01 | code_review_dashboard |
| [adr-004](adr-004-prompt-stop-gates.md) | prompt stop-gates | 2026-03-01 | phase_01_run_01 |
| [adr-005](adr-005-session-start-gate.md) | session start gate | 2026-03-01 | final_report_01 |
| [adr-006](adr-006-whitelist-filters.md) | whitelist filter validation | 2026-03-01 | phase_02_run_01 |
| [adr-007](adr-007-dml-procedures.md) | dml stored procedures | 2026-03-01 | code_review_dashboard |
| [adr-008](adr-008-secure-dml.md) | secure-dml skill | 2026-03-01 | session 2026-03-01 |
| [adr-009](adr-009-filter-change.md) | on_change= for filter_change | 2026-03-01 | final_report_01 |
| [adr-010](adr-010-altair-only.md) | altair-only charts | 2026-03-01 | phase_02_run_01 |
| [adr-011](adr-011-module-session.md) | module-level session | 2026-03-01 | code_review_dashboard |
| [adr-012](adr-012-prompt-vs-agents-enforcement.md) | prompt text as enforcement mechanism | 2026-03-02 | phase_02_run_04, phase_03_run_01 |
| [adr-013](adr-013-hooks-enforcement.md) | hooks-based gate enforcement | 2026-03-02 | phase_02_run_05, phase_03_run_02 |

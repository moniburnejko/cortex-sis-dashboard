# adr-003: current_sis_user identity

**date:** 2026-02-27
**source:** AGENTS.md sis critical constraints, code_review_dashboard.md issue 1.3

## problem

in streamlit in snowflake (sis), `CURRENT_USER()` (a sql function) returns the service account: the sis application owner, not the currently logged-in user. agents generating code defaulted to `CURRENT_USER()` or ignored this issue entirely. result: `AUDIT_LOG` with the wrong user_name, and `flagged_by` / `reviewed_by` fields populated with the service account instead of the real user.

## decision

`CURRENT_SIS_USER = st.user.user_name or "unknown"`: a python variable initialized once at the top of the module (or in an init function). available in streamlit 1.52.2. used everywhere user identity is needed: `flagged_by`, `reviewed_by`, `p_user_name` in every stored procedure call.

## alternatives considered

- `CURRENT_USER()` in sql: returns the service account. rejected: wrong identity.
- `st.experimental_user`: deprecated in streamlit 1.52. rejected: do not use deprecated apis.
- hardcoded fallback: e.g. `"system"` instead of `"unknown"`. rejected: masks configuration problems instead of surfacing them.

## consequences

- rule propagated to sis-patterns/SKILL.md and build-dashboard/SKILL.md as a required pattern
- `CURRENT_SIS_USER` must be passed as a parameter to every stored procedure call (`p_user_name`)
- `or "unknown"` as a fallback: signals a problem when `st.user` is unavailable (e.g. local development without a sis context) instead of crashing
- `st.user` may not be available outside the sis runtime. local testing requires mocking or a guard

## related

- [adr-002](adr-002-log-audit-event.md): `LOG_AUDIT_EVENT` accepts p_user_name
- [adr-007](adr-007-dml-procedures.md): INSERT/UPDATE procedures use p_user_name
- AGENTS.md: sis critical constraints
- `.cortex/skills/sis-streamlit/skills/sis-patterns/SKILL.md`

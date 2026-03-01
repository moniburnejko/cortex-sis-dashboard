# adr-002: log_audit_event procedure

**date:** 2026-03-01
**source:** AGENTS.md, phase_01_run_01.md

## problem

issuing an INSERT into `AUDIT_LOG` directly from sis (streamlit in snowflake) causes an identity problem. in sis, `CURRENT_USER()` returns the service account (the application owner), not the currently logged-in user, because sql executes in the service session context, not the user's session. an `AUDIT_LOG` with the wrong `user_name` loses its auditing value.

## decision

`LOG_AUDIT_EVENT` as a stored procedure with `EXECUTE AS OWNER`. the procedure accepts `p_user_name VARCHAR` as a parameter. sis passes the value of `st.user.user_name` (the identity of the logged-in user from the streamlit application layer). all calls go through `session.call('LOG_AUDIT_EVENT', ...)`.

## alternatives considered

- **Direct INSERT from sis**: simple, but `CURRENT_USER()` in the INSERT returns the service account instead of the user. rejected: loss of audit value.
- **Trigger on AUDIT_LOG**: not available in this form in snowflake for table INSERT triggers from the application side. rejected: not feasible.
- **INSERT with hardcoded CURRENT_SIS_USER in an f-string**: resolves the user_name issue but creates a sql injection vulnerability (see adr-008). rejected: security problem.

## consequences

- all `LOG_AUDIT_EVENT` calls go through `session.call()`: the same pattern as `INSERT_RENEWAL_FLAG` and `UPDATE_RENEWAL_FLAG` (adr-008)
- the procedure must be created in phase 1 alongside the ddl. included in phase 1 done criteria
- `p_user_name` must be passed to every call; `CURRENT_SIS_USER = st.user.user_name or "unknown"` is the canonical pattern (adr-003)

## related

- [adr-003](adr-003-current-sis-user.md): source of the user_name value
- [adr-008](adr-008-dml-stored-procedures.md): dml via stored procedures (`INSERT_RENEWAL_FLAG`, `UPDATE_RENEWAL_FLAG`)
- AGENTS.md: phase 1 done criteria (SHOW PROCEDURES check)
- `.cortex/skills/sis-streamlit/skills/secure-dml/SKILL.md`

# adr-007: dml stored procedures

**date:** 2026-03-01
**source:** code_review_dashboard.md issue 1.1, 1.2; final_report_01.md BUG-001, BUG-002

## problem

`flag_reason` (from `st.text_input`) and `review_notes` (from `st.text_area`) were interpolated directly into f-strings in INSERT and UPDATE statements:

```python
session.sql(f"INSERT INTO RENEWAL_FLAGS (flag_reason) VALUES ('{flag_reason}')")
session.sql(f"UPDATE ... SET review_notes = '{review_notes}'")
```

critical sql injection vulnerability: a user typing `'; DROP TABLE RENEWAL_FLAGS; --` can execute arbitrary sql. five pre-deploy scans missed this because the scans searched for `session.sql(f` but did not analyze whether the argument contained user input.

## decision

`INSERT_RENEWAL_FLAG` and `UPDATE_RENEWAL_FLAG` as stored procedures with `EXECUTE AS OWNER`. called via `session.call()` with values as bound parameters:

```python
session.call('INSERT_RENEWAL_FLAG', policy_id, flag_reason, CURRENT_SIS_USER, scope)
session.call('UPDATE_RENEWAL_FLAG', flag_id, review_notes, new_status, CURRENT_SIS_USER)
```

procedures created in phase 1 alongside `LOG_AUDIT_EVENT`. values passed as parameters, never interpolated into sql strings.

## alternatives considered

- **snowpark DataFrame api with `lit()`**: `session.table('RENEWAL_FLAGS').filter(...).update({'review_notes': lit(review_notes)})`. correct with respect to injection, but does not return flag_id (BUG-004 problem). rejected: loss of return value.
- **parameterized `session.sql()` with `?` placeholders**: `session.sql("INSERT ... VALUES (?)", [flag_reason])`. not supported by the snowpark python api in this form (no native bind parameters for session.sql). rejected: not available.
- **input sanitization before f-string**: `flag_reason.replace("'", "''")`. defence-in-depth but does not eliminate the threat; still an f-string. rejected: incomplete protection.

## consequences

- resolves BUG-001 (INSERT injection) and BUG-002 (UPDATE injection)
- resolves BUG-004: `INSERT_RENEWAL_FLAG` can return `flag_id` (RETURN statement in procedure)
- resolves BUG-007: `CURRENT_SIS_USER` in f-string replaced by `p_user_name` parameter
- 2 new objects in phase 1 ddl: `INSERT_RENEWAL_FLAG`, `UPDATE_RENEWAL_FLAG`
- phase 1 done criteria extended with 2 `SHOW PROCEDURES` checks
- build-dashboard/SKILL.md scan mode (step 2a) checks that dml with user text uses `session.call()`

## related

- [adr-002](adr-002-log-audit-event.md): `LOG_AUDIT_EVENT` (same pattern)
- [adr-003](adr-003-current-sis-user.md): `CURRENT_SIS_USER` as a parameter
- [adr-006](adr-006-whitelist-filters.md): injection for enum filters (different category)
- [adr-008](adr-008-secure-dml.md): secure-dml skill with ddl and call patterns
- `.cortex/skills/sis-streamlit/skills/secure-dml/SKILL.md`
- AGENTS.md: security rule 7

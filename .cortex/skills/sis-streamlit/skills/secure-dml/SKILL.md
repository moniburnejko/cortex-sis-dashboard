---
name: secure-dml
description: "stored procedure patterns for dml (INSERT/UPDATE) with user text input in streamlit in snowflake. load before writing the flag submission form (page 2) or the flag review update (page 3). use whenever any INSERT or UPDATE takes a value from st.text_input(), st.text_area(), or any user-writable widget. do NOT use f-string sql for dml with user text: use session.call() to stored procedures instead."
---

## why stored procedures for dml with user text

f-string sql with user-supplied text is sql injection risk regardless of whitelist validation.
whitelist validation is correct for IN-list filter values (enum sets like regions, segments).
it does NOT apply to free-text fields like `flag_reason` (st.text_input) or `review_notes`
(st.text_area): those values cannot be whitelisted and MUST go through stored procedures.

### the vulnerability (DO NOT write this)

```python
# WRONG — SQL injection: user entering '); DROP TABLE RENEWAL_FLAGS; -- in flag_reason
# executes arbitrary SQL
session.sql(f"""
    INSERT INTO {DATABASE}.{SCHEMA}.RENEWAL_FLAGS
    (flagged_by, scope, scope_region, scope_segment, scope_channel, flag_reason)
    VALUES ('{CURRENT_SIS_USER}', '{scope}', '{scope_region}',
            '{scope_segment}', '{scope_channel}', '{flag_reason}')
""").collect()
```

the stored procedure approach below eliminates this class of vulnerability entirely.
all values are passed as bound parameters, never interpolated into sql text.

---

## procedure 1: INSERT_RENEWAL_FLAG

creates one flag row and returns the generated `flag_id` uuid.

substitute `{database}` and `{schema}` with values from AGENTS.md environment table.

```sql
CREATE OR REPLACE PROCEDURE {database}.{schema}.INSERT_RENEWAL_FLAG(
    p_flagged_by    VARCHAR,
    p_scope         VARCHAR,
    p_scope_region  VARCHAR,
    p_scope_segment VARCHAR,
    p_scope_channel VARCHAR,
    p_flag_reason   VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
DECLARE
    v_flag_id VARCHAR;
BEGIN
    v_flag_id := UUID_STRING();
    INSERT INTO {database}.{schema}.RENEWAL_FLAGS
        (flag_id, flagged_by, scope, scope_region, scope_segment, scope_channel, flag_reason)
    VALUES
        (:v_flag_id, :p_flagged_by, :p_scope, :p_scope_region,
         :p_scope_segment, :p_scope_channel, :p_flag_reason);
    RETURN :v_flag_id;
END;
$$;
```

### python call pattern (page 2: flag for review)

```python
flag_id = session.call(
    f"{DATABASE}.{SCHEMA}.INSERT_RENEWAL_FLAG",
    CURRENT_SIS_USER,   # p_flagged_by
    scope,              # p_scope        e.g. "REGION_CHANNEL"
    scope_region,       # p_scope_region  e.g. "TX" or None
    scope_segment,      # p_scope_segment e.g. "SMALL_BUSINESS" or None
    scope_channel,      # p_scope_channel e.g. "AGENT" or None
    flag_reason         # p_flag_reason   from st.text_input() — user text, bound parameter
)
log_audit_event("FLAG_ADDED", "USER_INTERACTION", "page_2_premium_pressure",
                "flag_for_review", "flag_submitted")
st.success(f"Flag submitted: {flag_id}")
```

> `flag_id` is the uuid returned by the procedure. display it in `st.success()`.
> do NOT show `scope` in `st.success()`. that was a pre-secure-dml bug.

---

## procedure 2: UPDATE_RENEWAL_FLAG

marks one or more open flags as REVIEWED for the current user.
`p_flag_ids` is a comma-separated string of `flag_id` uuid values.
only flags owned by `p_reviewed_by` (`flagged_by = p_reviewed_by`) with `status = 'OPEN'` are updated.
row-level safety is enforced inside the procedure. the caller cannot review flags they did not create.

```sql
CREATE OR REPLACE PROCEDURE {database}.{schema}.UPDATE_RENEWAL_FLAG(
    p_reviewed_by VARCHAR,
    p_notes       VARCHAR,
    p_flag_ids    VARCHAR
)
RETURNS VARCHAR
LANGUAGE SQL
EXECUTE AS OWNER
AS
$$
BEGIN
    UPDATE {database}.{schema}.RENEWAL_FLAGS
    SET
        status      = 'REVIEWED',
        reviewed_by = :p_reviewed_by,
        reviewed_at = CURRENT_TIMESTAMP(),
        notes       = :p_notes
    WHERE flag_id IN (
        SELECT VALUE FROM TABLE(STRTOK_SPLIT_TO_TABLE(:p_flag_ids, ','))
    )
    AND flagged_by = :p_reviewed_by
    AND status = 'OPEN';
    RETURN 'OK';
END;
$$;
```

### python call pattern (page 3: mark reviewed)

```python
flag_ids_str = ",".join(selected_flag_ids)   # list of UUID strings from st.data_editor selection
session.call(
    f"{DATABASE}.{SCHEMA}.UPDATE_RENEWAL_FLAG",
    CURRENT_SIS_USER,   # p_reviewed_by
    review_notes,       # p_notes    from st.text_area() — user text, bound parameter
    flag_ids_str        # p_flag_ids  comma-separated UUIDs
)
log_audit_event("FLAG_REVIEWED", "USER_INTERACTION", "page_3_activity_log",
                "review_flags", "mark_reviewed")
```

---

## when to create these procedures

create in phase 1, together with `LOG_AUDIT_EVENT`. add to the phase 1 ddl sequence:

1. `LOG_AUDIT_EVENT`: already specified in AGENTS.md
2. `INSERT_RENEWAL_FLAG`: ddl above
3. `UPDATE_RENEWAL_FLAG`: ddl above

confirm after creation:
```sql
SHOW PROCEDURES LIKE 'INSERT_RENEWAL_FLAG' IN SCHEMA {database}.{schema};  -- expect: 1 row
SHOW PROCEDURES LIKE 'UPDATE_RENEWAL_FLAG' IN SCHEMA {database}.{schema};  -- expect: 1 row
```

---

## success criteria

- both procedures exist in `{database}.{schema}`
- `dashboard.py` uses `session.call()` for flag INSERT and review UPDATE. no f-string dml with user text
- `grep "session\.sql(f" dashboard.py | grep -iE "INSERT|UPDATE"` returns 0 matches
- `grep -c "session\.call(" dashboard.py` returns >= 2

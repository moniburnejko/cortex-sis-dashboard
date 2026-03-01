# code review: dashboard.py

**file:** dashboard.py (707 lines)
**date:** 2026-03-01
**context:** final version produced by cortex code cli after phase_02_run_05.
this is the deployed dashboard at CORTEX_DB.CORTEX_SCHEMA.RENEWAL_RADAR.
the agent declared the project complete. this review identifies issues that
were not caught by the agent's pre-deploy scans or final verification.

**companion report:** phase_02_run_05.md (conversation/session execution analysis)

---

## summary of findings

| # | category | severity | description |
|---|---|---|---|
| 1.1 | sql injection | critical | flag_reason (user text input) directly in INSERT f-string |
| 1.2 | sql injection | critical | review_notes (user text input) directly in UPDATE f-string |
| 1.3 | sql injection | low | CURRENT_SIS_USER (system value) in INSERT/UPDATE f-strings |
| 1.4 | sql injection | low | whitelist-validated filter values in SELECT f-strings via .join() |
| 1.5 | sql injection | minimal | date values from date_input in SELECT f-strings |
| 2 | missing feature | high | FILTER_CHANGE audit logging absent (required by AGENTS.md) |
| 3 | missing feature | medium | flag_id not returned/shown after INSERT (required by AGENTS.md) |
| 4 | filter gap | medium | heatmap ignores segment and channel filters |
| 5 | visual | low | LAPSED and NOT_TAKEN_UP share same color (#FFA726) |
| 6 | spec contradiction | info | module-level session vs sis-patterns "inside functions only" |

---

## 1. sql injection vulnerabilities

### 1.1 critical: flag_reason user input in INSERT (line 557-565)

```python
# dashboard.py lines 557-565
session.sql(f"""
    INSERT INTO {DATABASE}.{SCHEMA}.RENEWAL_FLAGS
    (flagged_by, scope, scope_region, scope_segment, scope_channel, flag_reason)
    VALUES ('{CURRENT_SIS_USER}', '{scope}',
            {'NULL' if scope_region is None else f"'{scope_region}'"},
            {'NULL' if scope_segment is None else f"'{scope_segment}'"},
            {'NULL' if scope_channel is None else f"'{scope_channel}'"},
            '{flag_reason}')
""").collect()
```

`flag_reason` comes from `st.text_input("Reason", ...)` on line 534. a user can type:

```
'); DROP TABLE RENEWAL_FLAGS; --
```

this would produce valid sql that drops the table. the scope_region, scope_segment,
scope_channel values are constrained by selectbox options (whitelist-safe), but flag_reason
is free-form text with no sanitization.

**fix:** use `session.call()` with a stored procedure, or use snowpark DataFrame api:

```python
from snowflake.snowpark.functions import lit, current_timestamp
session.table(f"{DATABASE}.{SCHEMA}.RENEWAL_FLAGS").insert([
    lit(CURRENT_SIS_USER), lit(scope), lit(scope_region),
    lit(scope_segment), lit(scope_channel), lit(flag_reason)
])
```

or create a dedicated INSERT procedure similar to `LOG_AUDIT_EVENT`:

```python
session.call(
    f"{DATABASE}.{SCHEMA}.INSERT_RENEWAL_FLAG",
    CURRENT_SIS_USER, scope, scope_region, scope_segment, scope_channel, flag_reason
)
```

### 1.2 critical: review_notes user input in UPDATE (line 660-669)

```python
# dashboard.py lines 660-669
session.sql(f"""
    UPDATE {DATABASE}.{SCHEMA}.RENEWAL_FLAGS
    SET status = 'REVIEWED',
        reviewed_by = '{CURRENT_SIS_USER}',
        reviewed_at = CURRENT_TIMESTAMP(),
        notes = '{review_notes}'
    WHERE flag_id IN ('{flag_ids_str}')
      AND flagged_by = '{CURRENT_SIS_USER}'
      AND status = 'OPEN'
""").collect()
```

`review_notes` comes from `st.text_area("Review notes", ...)` on line 651. same injection
risk as 1.1. additionally, `flag_ids_str` is built from `"','".join(flag_ids)` where
flag_ids come from the data_editor, but the values originate from the database - lower risk.

**fix:** same approach as 1.1 - use session.call() with a stored procedure for the UPDATE.

### 1.3 low: CURRENT_SIS_USER in sql (lines 560, 663, 667)

`CURRENT_SIS_USER` is `st.user.user_name or "unknown"`. this is a system-provided value
(not user-editable input), so injection risk is low. however, it is still interpolated
directly into f-string sql on multiple lines. for consistency with parameterized sql practices,
it should be passed as a procedure parameter.

### 1.4 low: whitelist-validated filter values in sql (lines 232-236, 418-422)

```python
# dashboard.py line 232-234
WHERE region IN ('{"','".join(regions)}')
  AND segment IN ('{"','".join(segments)}')
  AND channel IN ('{"','".join(channels)}')
```

the `regions`, `segments`, `channels` values are whitelist-validated:
```python
valid_sel_regions = [r for r in sel_regions if r in VALID_REGIONS]
```

this means only values that exist in the database can appear in the sql. practical injection
risk is negligible. however, this pattern violates AGENTS.md security rule 3 which specifies:

```python
selected = [r for r in user_selected if r in VALID_REGIONS]
df = session.table(...).filter(col("region").isin(selected))
```

the spec requires snowpark DataFrame api (`session.table().filter()`), not f-string sql.
the agent used f-string sql with whitelist validation instead.

**fix:** rewrite load_trend_data and load_outcome_premium_data to use snowpark DataFrame api
with DATE_TRUNC applied via snowpark functions, or keep the current approach and document
the exception in AGENTS.md (whitelist-validated f-string sql for aggregate queries with
DATE_TRUNC, which has no snowpark equivalent).

### 1.5 minimal: date values in sql (lines 235-236, 422)

```python
AND renewal_date >= '{date_from}'
AND renewal_date <= '{date_to}'
```

`date_from` and `date_to` come from `st.date_input()` which returns python `datetime.date`
objects. these are not user-typeable strings, so injection risk is minimal. the date_input
widget constrains values to valid dates within min/max bounds.

---

## 2. missing FILTER_CHANGE audit logging

**AGENTS.md requirement (line 634):**
```
audit: on filter change -> log_audit_event("FILTER_CHANGE", "USER_INTERACTION",
"page_1_kpi_overview", "sidebar_filters", "multiselect_change")
```

**AGENTS.md requirement (line 675):**
```
audit: on filter change -> log_audit_event("FILTER_CHANGE", "USER_INTERACTION",
"page_2_premium_pressure", "sidebar_filters", "multiselect_change")
```

**dashboard.py:** zero occurrences of `FILTER_CHANGE` in the code.

```
grep -c "FILTER_CHANGE" dashboard.py  ->  0
```

the dashboard only logs two event types:
- `FLAG_ADDED` (line 567)
- `FLAG_REVIEWED` (line 671)

**impact on verification:** phase 3 done criteria (AGENTS.md line 783) checks:
```sql
SELECT COUNT(*) FROM AUDIT_LOG WHERE action_type='FILTER_CHANGE';  -- >= 1
```

the agent's final verification reported 30 FILTER_CHANGE events. these exist from a prior
dashboard version that DID have filter logging (likely from run_03 or run_04). the current
dashboard.py does not produce them. if `AUDIT_LOG` were cleared, this check would fail.

**fix:** add `on_change` callbacks to the sidebar multiselect and date_input widgets:

```python
def on_filter_change():
    log_audit_event("FILTER_CHANGE", "USER_INTERACTION", page,
                    "sidebar_filters", "multiselect_change")

sel_regions = st.sidebar.multiselect(
    "Region", VALID_REGIONS, key="sel_regions",
    format_func=lambda x: REGION_LABELS.get(x, x),
    on_change=on_filter_change
)
```

note: `on_change` requires careful implementation in sis to avoid spurious logging on first
render. the session state initialization with actual defaults (lines 117-126) should prevent
this, but testing is required.

**AGENTS.md change:** add FILTER_CHANGE logging to the mandatory scan checklist in
build-dashboard SKILL.md (scan mode). add a pattern check:
```
grep -c "FILTER_CHANGE" <file>  -- must be >= 1
```

---

## 3. missing flag_id in st.success

**AGENTS.md requirement (line 673):**
```
show st.success() with the returned flag_id
```

**dashboard.py line 570:**
```python
st.success(f"Flag submitted successfully: {scope}")
```

the INSERT statement (lines 557-565) does not return the generated flag_id uuid.
st.success shows the scope (e.g. "REGION_SEGMENT") instead of the flag_id.

**fix option 1:** query the last inserted flag_id after INSERT:
```python
result = session.sql(f"""
    SELECT flag_id FROM {DATABASE}.{SCHEMA}.RENEWAL_FLAGS
    WHERE flagged_by = '{CURRENT_SIS_USER}'
    ORDER BY flagged_at DESC LIMIT 1
""").collect()
flag_id = result[0]['FLAG_ID']
st.success(f"Flag submitted: {flag_id}")
```

**fix option 2:** use a stored procedure that performs the INSERT and returns the flag_id:
```python
flag_id = session.call(f"{DATABASE}.{SCHEMA}.INSERT_RENEWAL_FLAG", ...)
st.success(f"Flag submitted: {flag_id}")
```

option 2 is preferred because it also resolves issue 1.1 (sql injection).

**AGENTS.md change:** clarify the flag_id return mechanism. currently the spec says "show
st.success() with the returned flag_id" but does not specify how to obtain it from the INSERT.

---

## 4. heatmap filter gap

**dashboard.py lines 455-476:**
```python
def load_heatmap_data(regions, segments, channels, date_from, date_to, final_only):
    # ...
    df = _session.sql(query).to_pandas()
    df = df.rename(columns=str.lower)
    df = df[df['region'].isin(regions)]  # <-- only region filtered
    return df
```

the function accepts `segments` and `channels` parameters but only applies region filtering
after the pandas conversion. segment and channel filters from the sidebar are ignored.

the sql query itself (lines 457-471) does not include segment or channel in its WHERE clause
either. this means the heatmap always shows data across all segments and all channels,
regardless of sidebar filter selections.

**fix:** add segment and channel filtering:
```python
df = df[
    (df['region'].isin(regions)) &
    (df['segment'].isin(segments)) &
    (df['channel'].isin(channels))
]
```

note: the heatmap sql query selects from `FACT_PREMIUM_EVENT` which has segment and channel
columns, so this filter will work correctly.

**AGENTS.md change:** add an explicit note to the page 2 heatmap spec that all sidebar
filters (region, segment, channel, date range) must apply to the heatmap query.

---

## 5. outcome color mapping

**dashboard.py line 293-295:**
```python
scale=alt.Scale(
    domain=OUTCOME_DISPLAY_ORDER,
    range=["#1565C0", "#FFA726", "#FFA726", "#E53935"]
)
```

domain order: ["Renewed", "Lapsed", "Not taken up", "Cancelled"]
color mapping:
- Renewed: #1565C0 (primary blue)
- Lapsed: #FFA726 (accent orange)
- Not taken up: #FFA726 (accent orange) - **same as Lapsed**
- Cancelled: #E53935 (error red)

two of four outcomes share the same color, making them visually indistinguishable in the
stacked bar chart (chart 3 on page 1).

**brand-identity SKILL.md** defines:
- primary: #1565C0
- accent: #FFA726
- status: SUCCESS #4CAF50, WARN #FFA726, ERROR #E53935

the current mapping treats Lapsed and Not taken up as the same category. if this is
intentional (both are "negative non-cancelled" outcomes), it should be documented. if not:

**fix:** differentiate the two orange outcomes:
```python
range=["#1565C0", "#FFA726", "#FB8C00", "#E53935"]
```
or use a 4-color qualitative palette from brand-identity.

**brand-identity change:** add an explicit outcome color mapping to the skill file:
```
renewal outcome colors:
- RENEWED: #1565C0 (primary)
- LAPSED: #FFA726 (accent)
- NOT_TAKEN_UP: #FB8C00 (darker accent)
- CANCELLED: #E53935 (error)
```

---

## 6. module-level session contradiction

**dashboard.py line 12:**
```python
session = get_active_session()
```

this module-level session object is used by:
- `log_audit_event()` (line 46)
- `flags_count_result` query (line 369)
- flag INSERT (line 557)
- flags query (line 612)
- flag UPDATE (line 660)
- agent operations query (line 682)

**build-dashboard SKILL.md scaffold template (line 89):**
```python
session = get_active_session()
```
the scaffold template explicitly places this at module level.

**sis-patterns SKILL.md section 1:**
```
call get_active_session() INSIDE the function, never at module level
```

these two skill files contradict each other. the scaffold template (which the agent follows
when generating code) says module level. the sis-patterns guidance (which the agent reads
before writing code) says inside functions only.

the practical impact in sis warehouse runtime is negligible - the session is valid for the
entire app lifecycle. however, the contradiction causes inconsistency: cached data loader
functions (load_filter_options, load_kpi_data, etc.) correctly call `get_active_session()`
inside the function, while non-cached functions use the module-level `session` variable.

**fix:** resolve the contradiction in one of two ways:

option A (keep module-level): update sis-patterns to clarify that module-level session is
acceptable for non-cached code, but cached functions (`@st.cache_data`) MUST call
`get_active_session()` inside the function because the module-level reference is not picklable.

option B (enforce inside-functions): update the scaffold template to remove module-level
session and add a helper function:
```python
def get_session():
    return get_active_session()
```

option A is recommended because it matches the actual sis behavior and the scaffold template.

---

## 7. recommendations for AGENTS.md

### 7.1 expand security rule 3: parameterized dml with user input

current rule 3 (line 752-758) covers IN-list filter validation only. it does not mention
INSERT or UPDATE statements with user-supplied text fields.

**add to security rule 3:**

```
all dml (INSERT, UPDATE, DELETE) with user-supplied text values (st.text_input, st.text_area,
st.data_editor) MUST use session.call() with a stored procedure. f-string interpolation of
user text into sql is a sql injection vulnerability.

allowed in f-string sql: DATABASE, SCHEMA, APP_NAME constants only.
allowed with whitelist validation: selectbox/multiselect values validated against VALID_* lists.
NOT allowed in f-string sql: text_input, text_area, data_editor free-text values.
```

### 7.2 add FILTER_CHANGE as mandatory feature

add to page 1 and page 2 specs:

```
mandatory: every sidebar filter widget (multiselect, date_input) must include on_change
callback that calls log_audit_event("FILTER_CHANGE", ...).
```

add to build-dashboard scan mode:

```
grep -c "FILTER_CHANGE" <file>  -- must be >= 1. if 0: FAIL - filter change logging missing.
```

### 7.3 clarify flag_id return

update the flag submission spec (line 671-673) to specify the mechanism:

```
after INSERT: query the inserted flag_id and show it in st.success().
preferred: create INSERT_RENEWAL_FLAG procedure that returns the uuid.
```

### 7.4 heatmap filter completeness

add to page 2 heatmap spec:

```
heatmap must respect all sidebar filters: region, segment, channel, date range.
```

### 7.5 clarify skill invocation syntax

add a note to the skills table:

```
notation: "$ sis-streamlit -> build-dashboard" means invoke $ sis-streamlit, then follow
its routing table to the build-dashboard sub-skill. this is NOT a compound command.
invoke $ sis-streamlit first, then the sub-skill according to the routing instructions.
```

---

## 8. recommendations for skills/

### 8.1 build-dashboard scan mode: user input in dml

add to scan mode step 3 (after the session.sql(f check):

```
check for user text input in dml statements:
- grep for st.text_input and st.text_area variable names
- trace each variable to see if it appears inside session.sql(f"...")
- violation: any user text variable interpolated into INSERT, UPDATE, or DELETE sql
- fix: use session.call() with stored procedure
```

### 8.2 build-dashboard scan mode: FILTER_CHANGE check

add to scan mode step 5 (style validation):

```
grep -c "FILTER_CHANGE" <file>  -- must be >= 1
if 0: FAIL - AGENTS.md requires FILTER_CHANGE audit logging on every page with filters
```

### 8.3 sis-patterns: resolve module-level session

update sis-patterns section 1 to clarify:

```
module-level session = get_active_session() is acceptable for non-cached code
(audit logging, flag operations, ad-hoc queries).

@st.cache_data functions MUST call get_active_session() inside the function body
because the module-level session reference is not serializable for caching.
```

### 8.4 brand-identity: outcome color mapping

add explicit outcome color mapping:

```
renewal outcome colors:
- RENEWED: #1565C0 (primary)
- LAPSED: #FFA726 (accent)
- NOT_TAKEN_UP: #FB8C00 (darker accent)
- CANCELLED: #E53935 (error)
```

---

## 9. recommendations for prompts.md

### 9.1 add code review prompt

current prompt 4 focuses on phase 3 sql acceptance checks (row counts, event counts).
it does not cover code quality, sql injection, or spec compliance of the deployed code.

consider adding a post-deployment code review prompt:

```
prompt 5 (code review):
run $ sis-streamlit -> build-dashboard dashboard.py (full scan mode).
then verify:
1. all sql injection patterns from scan mode step 3 return 0 violations
2. all audit logging events specified in AGENTS.md exist in the code
3. all sidebar filters apply to every query on every page
4. flag submission returns and displays flag_id
report any remaining issues.
```

this would ensure the scan is run comprehensively at least once after all edits are complete,
catching issues that may have been introduced during incremental refinement sessions like run_05.

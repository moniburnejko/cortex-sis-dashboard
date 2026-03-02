# code review: dashboard.py (728 lines)

**file:** dashboard.py (728 lines)
**date:** 2026-03-02
**context:** post-deploy state after phase_02_run_05 fixes. predecessor review:
code_review_dashboard.md (reviewed 707-line version after phase_02_run_04).
**model:** claude-sonnet-4-5 (session that produced this version)

**predecessor:** code_review_dashboard.md (prior 707-line version)

---

## 1. scope and methodology

| item | value |
|---|---|
| file reviewed | dashboard.py |
| line count | 728 |
| basis | current file state after phase_02_run_05 edits |
| predecessor | code_review_dashboard.md - reviewed 707-line version |
| checks run | sql injection, stored procedure usage, audit logging, spec compliance, visual correctness, sis api compliance |

this review checks whether the fixes described in code_review_dashboard.md were correctly
implemented, and identifies any remaining or new issues.

---

## 2. summary of findings

| # | issue | severity | status | location |
|---|---|---|---|---|
| 1.1 | f-string INSERT (flag_reason) via session.sql | critical | resolved | fixed via INSERT_RENEWAL_FLAG stored procedure |
| 1.2 | f-string UPDATE (review_notes) via session.sql | critical | resolved | fixed via UPDATE_RENEWAL_FLAG stored procedure |
| 2 | missing FILTER_CHANGE audit callbacks | high | resolved | log_filter_change_p1/p2 added at lines 129-138 |
| 3 | st.success shows scope not flag_id | medium | resolved | flag_id returned from INSERT_RENEWAL_FLAG, shown at line 595 |
| 4 | heatmap segment/channel filter gap | medium | open | load_heatmap_data lines 480-501 |
| 5 | outcome color duplication (#FFA726) | low | open | outcome_colors range at line 319 |
| 6 | module-level session vs sis-patterns conflict | informational | open | line 12 |
| 7 | f-string SELECT with constants (lower risk) | informational | accepted | lines 606-614, 631-637, 703-710 |

---

## 3. resolved issues

### 3.1 dml injection (critical - resolved)

prior state (707-line version):

```python
# lines 557-565 (INSERT with f-string user text)
session.sql(f"""
    INSERT INTO {DATABASE}.{SCHEMA}.RENEWAL_FLAGS
    ...
    '{flag_reason}'
""").collect()

# lines 660-669 (UPDATE with f-string user text)
session.sql(f"""
    UPDATE {DATABASE}.{SCHEMA}.RENEWAL_FLAGS
    SET notes = '{review_notes}'
    ...
""").collect()
```

`flag_reason` and `review_notes` were user-supplied text input (st.text_input, st.text_area)
interpolated directly into sql - a sql injection vulnerability.

fix applied in phase_02_run_05:

stored procedures INSERT_RENEWAL_FLAG and UPDATE_RENEWAL_FLAG created in snowflake.
dashboard.py updated to use session.call():

```python
# line 582 (INSERT via stored procedure)
flag_id = session.call(
    f"{DATABASE}.{SCHEMA}.INSERT_RENEWAL_FLAG",
    CURRENT_SIS_USER, scope, scope_region,
    scope_segment, scope_channel, flag_reason
)

# line 685 (UPDATE via stored procedure)
session.call(
    f"{DATABASE}.{SCHEMA}.UPDATE_RENEWAL_FLAG",
    CURRENT_SIS_USER, review_notes, flag_ids_str
)
```

verification:

```
grep -n "session\.sql(f" dashboard.py | grep -iE "INSERT|UPDATE"
```

result: 0 matches. no f-string DML remains.

status: resolved. all DML with user text now via session.call().

### 3.2 FILTER_CHANGE audit callbacks (high - resolved)

prior state (707-line version):

zero occurrences of FILTER_CHANGE in dashboard.py. the 30 FILTER_CHANGE events in
AUDIT_LOG at the time of code_review_dashboard.md were stale events from a prior
dashboard version.

fix applied in phase_02_run_05:

two callback functions added at lines 129-137:

```python
# lines 129-137
def log_filter_change_p1():
    """Callback for Page 1 filter changes"""
    log_audit_event("FILTER_CHANGE", "USER_INTERACTION",
                    "page_1_kpi_overview", "sidebar_filters", "multiselect_change")

def log_filter_change_p2():
    """Callback for Page 2 filter changes"""
    log_audit_event("FILTER_CHANGE", "USER_INTERACTION",
                    "page_2_premium_pressure", "sidebar_filters", "multiselect_change")
```

callbacks attached via on_change parameter:

| widget | line | callback |
|---|---|---|
| sel_regions multiselect | 153-157 | on_change=filter_callback (p1 or p2 based on current page) |
| sel_segments multiselect | 158-162 | on_change=filter_callback |
| sel_channels multiselect | 163-167 | on_change=filter_callback |
| date_from date_input | 168-175 | on_change=filter_callback |
| date_to date_input | 176-183 | on_change=filter_callback |
| final_offers_only toggle (page 2) | 338 | on_change=log_filter_change_p2 |

the page-routing logic (lines 146-151) sets `filter_callback` to the correct function
based on the active page, or None for the Activity Log page (no filter logging required).

verification:

```
grep -c "FILTER_CHANGE" dashboard.py  ->  2
```

phase_03_run_02 confirmed 6 genuine FILTER_CHANGE events logged during testing (scoped
to last hour).

status: resolved. FILTER_CHANGE logging present and functional.

### 3.3 flag_id return (medium - resolved)

prior state (707-line version):

```python
# line 570 (prior)
st.success(f"Flag submitted successfully: {scope}")
```

the INSERT did not return the flag_id. st.success showed the scope type string instead.

fix applied in phase_02_run_05:

INSERT_RENEWAL_FLAG stored procedure returns the generated uuid. session.call() captures
the return value:

```python
# lines 582-595
flag_id = session.call(
    f"{DATABASE}.{SCHEMA}.INSERT_RENEWAL_FLAG",
    ...
)
...
st.success(f"Flag submitted: {flag_id}")
```

status: resolved. flag_id displayed in confirmation message.

---

## 4. open issues

### 4.1 heatmap segment/channel filter gap (medium - open)

location: `load_heatmap_data` function, lines 480-501

issue: the function accepts `segments` and `channels` parameters but neither the
sql query nor the post-fetch pandas filter applies them. only `region` is filtered:

```python
# line 480
def load_heatmap_data(regions, segments, channels, date_from, date_to, final_only):
    _session = get_active_session()
    query = f"""
    SELECT region, ...
    FROM {DATABASE}.{SCHEMA}.FACT_PREMIUM_EVENT
    WHERE 1=1
    """
    if final_only:
        query += " AND is_final_offer = 1"
    # date_from, date_to not applied in SQL or pandas

    df = _session.sql(query).to_pandas()
    df = df.rename(columns=str.lower)
    df = df[df['region'].isin(regions)]  # line 500 - only region filtered
    return df
```

the sql WHERE clause has no segment or channel condition. the pandas filter at line 500
applies only region. date_from and date_to are also not applied.

AGENTS.md spec: page 2 heatmap should respect all sidebar filters (region, segment,
channel, date range).

impact: sidebar segment and channel selections (and date range) have no effect on
heatmap data. the heatmap always shows all segments, channels, and date ranges filtered
only by region and optionally by is_final_offer.

fix:

```python
# replace line 500 with:
df = df[
    (df['region'].isin(regions)) &
    (df['segment'].isin(segments)) &
    (df['channel'].isin(channels))
]
# add date filter in SQL or pandas:
# AND renewal_date >= '{date_from}' AND renewal_date <= '{date_to}'
```

note: FACT_PREMIUM_EVENT has segment and channel columns, so the pandas filter will work.
date filtering requires adding the date column to the select or applying it in the sql query.

status: open. not addressed in phase_02_run_05 (scope was security fixes only).

### 4.2 outcome color duplication (low - open)

location: alt.Scale range parameter, line 319

```python
# line 317-320
color=alt.Color('outcome_display:N',
    scale=alt.Scale(
        domain=OUTCOME_DISPLAY_ORDER,
        range=["#1565C0", "#FFA726", "#FFA726", "#E53935"]
    ),
```

domain order (line 94): `["Renewed", "Lapsed", "Not taken up", "Cancelled"]`

color mapping:
- Renewed: #1565C0 (primary blue)
- Lapsed: #FFA726 (accent orange)
- Not taken up: #FFA726 (accent orange) - same as Lapsed
- Cancelled: #E53935 (error red)

Lapsed and Not taken up are visually indistinguishable in the stacked bar chart
(chart 3 on page 1 "Renewal outcome distribution by segment").

impact: users cannot distinguish Lapsed from Not taken up in the outcome distribution
chart. both outcomes use the same orange color.

fix:

```python
range=["#1565C0", "#FFA726", "#FB8C00", "#E53935"]
```

or assign a distinct color from brand-identity to Not taken up.

status: open. not addressed in phase_02_run_05.

### 4.3 module-level session (informational)

location: line 12

```python
session = get_active_session()
```

sis-patterns skill specifies: "call get_active_session() INSIDE the function, never at
module level." the build-dashboard scaffold template places session at module level.
these two skill files contradict each other.

the module-level session is used by:
- `log_audit_event()` at line 46
- `flags_count_result` query (Activity Log page)
- flag INSERT session.call at line 582
- flags SELECT at line 637
- flag UPDATE session.call at line 685
- agent operations query at line 703

cached data loader functions (load_filter_options, load_kpi_data, etc.) correctly call
`get_active_session()` inside the function, consistent with sis-patterns.

impact: low. works in sis warehouse runtime (module re-executes on each user
interaction). inconsistency between cached and non-cached code - mixed pattern.

recommendation: resolve the sis-patterns vs build-dashboard contradiction. preferred
resolution: update sis-patterns to clarify that module-level session is acceptable for
non-cached code; cached functions must call get_active_session() inside the function
because the module-level reference is not picklable.

status: informational - same as code_review_dashboard.md issue 6. unchanged.

### 4.4 f-string SELECT with constants (informational - accepted)

location: lines 606-614, 631-637, 703-710

```python
# line 606
user_df = session.sql(f"""
    SELECT ... FROM {DATABASE}.{SCHEMA}.AUDIT_LOG
    WHERE streamlit_app_name = '{APP_NAME}'
    ...
""").to_pandas()
```

pattern: DATABASE, SCHEMA, APP_NAME (module-level constants) interpolated into SELECT
statements. no user input. `flags_query` at line 631 is an f-string variable that also
interpolates only DATABASE and SCHEMA constants.

the build-dashboard skill spec explicitly allows this pattern (constants-only f-string SQL).
the post-deployment scan (phase_03_run_02) confirmed all three as safe.

status: accepted per skill spec. not a vulnerability.

---

## 5. security posture change

| issue | code_review_dashboard.md (707 lines) | this review (728 lines) |
|---|---|---|
| dml injection (INSERT flag_reason) | critical - f-string INSERT with user text | resolved - session.call() |
| dml injection (UPDATE review_notes) | critical - f-string UPDATE with user text | resolved - session.call() |
| FILTER_CHANGE logging | missing - 0 occurrences in code | resolved - 2 occurrences, callbacks on 6 widgets |
| flag_id in st.success | missing - showed scope string | resolved - INSERT_RENEWAL_FLAG returns uuid |
| whitelist filter injection | low - valid whitelists applied | unchanged - same pattern |
| heatmap filter gap | medium | open - unchanged |
| outcome color duplication | low | open - unchanged |
| module-level session | informational | open - unchanged |
| f-string SELECT constants | informational | accepted per skill spec - unchanged |

---

## 6. spec compliance

checking key AGENTS.md dashboard requirements against dashboard.py:

| requirement | AGENTS.md ref | dashboard.py | status |
|---|---|---|---|
| FLAG_ADDED audit log | page 2 spec | line 592-593 | PASS |
| FLAG_REVIEWED audit log | page 3 spec | line 692-693 | PASS |
| FILTER_CHANGE audit log | page 1 and page 2 spec | lines 129-138, on_change callbacks | PASS |
| INSERT with stored procedure | security rule | line 582-590 | PASS |
| UPDATE with stored procedure | security rule | line 685-690 | PASS |
| flag_id returned in st.success | flag submission spec | line 595 | PASS |
| st.set_page_config first | sis api constraint | line 9 | PASS |
| no st.rerun(), st.fragment, .applymap | sis api constraints | 0 occurrences each | PASS |
| whitelist validation for filter values | security rule 3 | lines 190-192, 341-343 | PASS |
| heatmap respects all sidebar filters | page 2 spec | segment/channel ignored | FAIL - open issue 4.1 |
| distinct outcome colors | brand-identity | Lapsed/Not taken up both #FFA726 | FAIL - open issue 4.2 |
| python syntax valid | phase 2 done criteria | py_compile exit code 0 | PASS |

---

## 7. recommendations

### 7.1 fix heatmap filter gap (medium priority)

add segment and channel filtering to `load_heatmap_data` (line 480-501):
- add pandas filter for segment and channel after fetch
- add date range filter (sql or pandas)
- no sql query change needed for segment/channel (FACT_PREMIUM_EVENT has both columns)

### 7.2 fix outcome color duplication (low priority)

assign a distinct color to Not taken up in the alt.Scale range at line 319.
update brand-identity SKILL.md to include an explicit outcome color mapping.

### 7.3 resolve session scope contradiction

update sis-patterns SKILL.md to clarify that module-level session is acceptable for
non-cached code. cached functions with @st.cache_data must call get_active_session()
inside the function (current behavior is already correct for cached functions).

### 7.4 add gate instruction to prompt 5

update prompts.md to add the gate instruction to prompt 5, consistent with prompts 1-4.
the gate ran automatically for prompt 4 in phase_03_run_02 because the prompt included the
instruction. prompt 5 did not, and the gate was skipped.

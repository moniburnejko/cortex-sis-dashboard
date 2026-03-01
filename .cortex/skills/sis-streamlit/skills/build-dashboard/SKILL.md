---
name: build-dashboard
description: "scaffold, validate, and scan the streamlit in snowflake dashboard. three modes: (1) no args - load sis constraints; (2) scaffold - generate dashboard.py at project root; (3) with file arg - pre-deploy scan + style validation. trigger when loading sis constraints, scaffolding dashboard.py, running pre-deploy scan, or validating dashboard style. do NOT use for general python linting, local streamlit apps, or non-sis deployments."
---

-> Load `references/sis-api-constraints.md` on every invocation - full constraint detail, reasons, and error messages.
-> Load `references/sis-data-patterns.md` when generating streamlit code - session usage, caching, date casting, NULL handling.

## sis api constraint table

the following apis are forbidden or restricted in streamlit in snowflake warehouse runtime.
some exist in the runtime but are unsafe (cause crashes, infinite loops, or unreliable behavior).
some do not exist at all. both categories are forbidden in generated code.

### forbidden: exists but unsafe in sis warehouse runtime

| forbidden (exists but unsafe)     | use instead                                              | reason |
|-----------------------------------|----------------------------------------------------------|--------|
| `st.rerun()` | session_state flag + conditional re-render | causes infinite loops and connection resets in warehouse runtime |
| `st.fragment` / `@st.fragment` | manual refresh button + session_state flag | unreliable execution in warehouse runtime |

### forbidden: does not exist or causes errors

| forbidden                         | use instead                                              |
|-----------------------------------|----------------------------------------------------------|
| `st.experimental_rerun()` | session_state flag + conditional re-render |
| `st.bar_chart(horizontal=True)` | altair horizontal bar chart: `alt.Chart().mark_bar().encode(alt.Y(...), alt.X(...))` |
| `style.applymap()` | `style.map()` (applymap removed in pandas 2.2.0) |
| `PARSE_JSON()` in `VALUES (...)` | INSERT-SELECT: `INSERT INTO t SELECT ..., PARSE_JSON(...)` |
| `st.slider` with `datetime.date` min/max | `st.date_input` for all date range selection |
| `st.set_page_config(page_title=..., page_icon=..., menu_items=...)` | `st.set_page_config(layout="wide")` - only `layout` is supported in sis |
| any `st.*` call before `st.set_page_config()` | `st.set_page_config()` must be the first st call |

### safe patterns

| pattern | note |
|---------|------|
| date from `.collect()` | always cast: `datetime.date(raw.year, raw.month, raw.day)` |
| `SELECT DISTINCT` for filters | always add `WHERE col IS NOT NULL` |
| `session.call()` for procedures | never use `session.sql(f"CALL ... PARSE_JSON...")` |
| `st.toggle()` / `st.sidebar.toggle()` | available and safe in 1.52.2 |
| `st.scatter_chart()` | available and safe in 1.52.2 |
| `st.user.user_name` | available in 1.52.2 - use `st.user.user_name or "unknown"` |

---

## steps

### discovery mode (no file argument)

1. print the constraint table above. tell the agent: "sis constraints loaded - use the replacements above when generating streamlit code."
2. stop here. do not run scan or scaffold steps.

### scaffold mode (argument: scaffold)

-> Load `../brand-identity/SKILL.md` - visual identity, chart type rules, style defaults, language conventions.

1. create `dashboard.py` at project root using the scaffold template below.
   replace `{app_name}`, `{database}`, `{schema}` with values from AGENTS.md snowflake environment table.
2. create `environment.yml` at project root alongside `dashboard.py`:
   ```yaml
   name: renewal_radar_env
   channels:
   - snowflake
   dependencies:
   - streamlit=1.52.*
   - altair
   - pandas
   ```
3. confirm both files exist: `ls -lh dashboard.py environment.yml`.
4. run `python -m py_compile dashboard.py` - must return no errors.

### scaffold template

9 mandatory blocks. block order is mandatory - do NOT reorder.

```python
# --- imports ---
import streamlit as st
from snowflake.snowpark.context import get_active_session
import altair as alt
import pandas as pd
from datetime import date as py_date, timedelta

# --- page config - MUST be the first st.* call ---
st.set_page_config(layout="wide")

# --- session and user context ---
session = get_active_session()
CURRENT_SIS_USER = st.user.user_name or "unknown"
APP_NAME = "{app_name}"
DATABASE = "{database}"
SCHEMA = "{schema}"

# --- cached data loader ---
# call get_active_session() INSIDE the function, never capture module-level session
# MANDATORY: SELECT DISTINCT queries MUST include WHERE col IS NOT NULL
# MANDATORY: date values from .collect() MUST be cast to Python datetime.date
@st.cache_data(ttl=300)
def load_filter_options():
    _session = get_active_session()
    regions = [r[0] for r in _session.sql(
        f"SELECT DISTINCT region FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL WHERE region IS NOT NULL ORDER BY region"
    ).collect()]
    segments = [r[0] for r in _session.sql(
        f"SELECT DISTINCT segment FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL WHERE segment IS NOT NULL ORDER BY segment"
    ).collect()]
    channels = [r[0] for r in _session.sql(
        f"SELECT DISTINCT channel FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL WHERE channel IS NOT NULL ORDER BY channel"
    ).collect()]
    raw = _session.sql(
        f"SELECT MIN(renewal_date), MAX(renewal_date) FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL"
    ).collect()[0]
    if raw[0] is None or raw[1] is None:
        st.error("No data in source table.")
        st.stop()
    min_date = py_date(raw[0].year, raw[0].month, raw[0].day)
    max_date = py_date(raw[1].year, raw[1].month, raw[1].day)
    return {
        "regions": regions, "segments": segments, "channels": channels,
        "min_date": min_date, "max_date": max_date
    }

# --- audit logger ---
# use session.call() - NEVER build CALL strings with f-strings or PARSE_JSON
def log_audit_event(action_type, action_category, page, component, action):
    session.call(
        f"{DATABASE}.{SCHEMA}.LOG_AUDIT_EVENT",
        action_type, action_category, APP_NAME, page, component, action,
        None, None, None, None, None,
        CURRENT_SIS_USER
    )

# --- filter options and whitelist lists ---
FILTER_OPTIONS = load_filter_options()
VALID_REGIONS = FILTER_OPTIONS["regions"]
VALID_SEGMENTS = FILTER_OPTIONS["segments"]
VALID_CHANNELS = FILTER_OPTIONS["channels"]
MIN_DATE = FILTER_OPTIONS["min_date"]
MAX_DATE = FILTER_OPTIONS["max_date"]

# --- session state ---
# initialize with actual defaults so first-render does not fire spurious FILTER_CHANGE
if "sel_regions" not in st.session_state:
    st.session_state["sel_regions"] = list(VALID_REGIONS)
if "sel_segments" not in st.session_state:
    st.session_state["sel_segments"] = list(VALID_SEGMENTS)
if "sel_channels" not in st.session_state:
    st.session_state["sel_channels"] = list(VALID_CHANNELS)
if "date_from" not in st.session_state:
    st.session_state["date_from"] = MAX_DATE - timedelta(days=30)
if "date_to" not in st.session_state:
    st.session_state["date_to"] = MAX_DATE

# --- navigation ---
# navigation MUST come first in the sidebar - above the Filters header
page = st.sidebar.radio("Navigation", ["KPI Overview", "Premium Pressure", "Activity Log"])

# --- shared filters (sidebar) ---
# defined at module scope so values persist across all pages via session_state key=
# page-specific filters (e.g. "final offers only" toggle) are defined inside each page block
st.sidebar.header("Filters")
sel_regions  = st.sidebar.multiselect("Region",  VALID_REGIONS,  key="sel_regions")
sel_segments = st.sidebar.multiselect("Segment", VALID_SEGMENTS, key="sel_segments")
sel_channels = st.sidebar.multiselect("Channel", VALID_CHANNELS, key="sel_channels")
# use two separate date_input widgets (NOT a single tuple-value range picker - it is awkward in SiS sidebar)
# format="YYYY-MM-DD" ensures ISO date display (not locale-default YYYY/MM/DD)
date_from = st.sidebar.date_input(
    "Renewal date from",
    value=st.session_state["date_from"],
    min_value=MIN_DATE,
    max_value=MAX_DATE,
    format="YYYY-MM-DD",
)
date_to = st.sidebar.date_input(
    "Renewal date to",
    value=st.session_state["date_to"],
    min_value=MIN_DATE,
    max_value=MAX_DATE,
    format="YYYY-MM-DD",
)

# --- page routing ---
if page == "KPI Overview":
    ...
elif page == "Premium Pressure":
    ...
elif page == "Activity Log":
    ...
```

### scan mode (argument: file path)

> **MANDATORY SCAN. CANNOT BE SKIPPED OR SUMMARIZED.**
> every step below must be executed in full. report each pattern check individually
> with the exact count and every line number found. do NOT batch results or skip steps
> because the file "looks correct." failure to run a step is itself a scan failure.

1. confirm the file exists. if not found: stop and ask the user for the correct path.

2. run python syntax check: `python3 -m py_compile <file>` - must return exit code 0.
   if `python3` is not found, try `python -m py_compile <file>`.
   if it fails: show the full error and stop.

2a. **dml injection check (CRITICAL - run before any other pattern scan):**
    ```
    grep -n "session\.sql(f" <file> | grep -iE "INSERT|UPDATE"
    ```
    any match = **FAIL**. stop here if any matches found.
    message: "f-string dml with user text detected on line(s) [N]. load
    `$ sis-streamlit -> secure-dml` and rewrite using session.call() to stored procedure.
    do NOT proceed to deploy until this is fixed."

    also check for the inverse - dml via session.call() must be present:
    ```
    grep -c "session\.call(" <file>
    ```
    if count = 0: **FAIL** - no stored procedure calls found. INSERT and UPDATE must go
    through session.call(). load `$ sis-streamlit -> secure-dml`.

3. scan for each forbidden pattern. report the match count. all must be 0:
   - `st\.rerun\(\)` - 0 results required
   - `st\.experimental_rerun\(\)` - 0 results required
   - `\.applymap\(` - 0 results required
   - `horizontal=True` inside any bar_chart call - 0 results required
   - `PARSE_JSON\(` inside a `VALUES\s*\(` clause - 0 results required
   - `st\.fragment` - 0 results required
   - `PARSE_JSON` in `session.sql(` or `snow sql -q` strings - 0 results required
   - `st\.slider` with `min_value` or `max_value` set to a date variable - 0 results required
   - date values from `.collect()` passed to `st.date_input` without python cast - 0 violations required
   - `SELECT DISTINCT` for filter option loading without `IS NOT NULL` - 0 violations required
   - non-parameterized sql with filter variable interpolation - FAIL if found:
     grep -n `session\.sql(f` <file> then inspect each match for:
     (a) IN-clause filter variable interpolation: any `session.sql(f"... IN ({var}...")` or
         `session.sql(f"... WHERE ... {var} ...")` where `var` is a user-selected filter value.
         fix: `selected = [r for r in user_selected if r in VALID_LIST]`
         then: `session.table(...).filter(col("field").isin(selected))`
     (b) INSERT or UPDATE with ANY user-supplied text from st.text_input, st.text_area,
         st.selectbox, or any other widget - these are sql injection: FAIL.
         fix: load `$ sis-streamlit -> secure-dml` and rewrite using session.call().
     (c) CURRENT_SIS_USER or st.user.user_name interpolated in f-string sql - WARN
         (low practical risk as it's a system value, but violates parameterized sql practice)
     exception: `session.sql(f"SELECT ... FROM {DATABASE}.{SCHEMA}...")` is OK - only DATABASE,
     SCHEMA, and APP_NAME constants are allowed in f-string sql. user values are NEVER allowed.
   **grep limitations:** patterns 8-11 and the dml check require understanding data flow.
   grep catches obvious cases. for edge cases, manually inspect `load_filter_options()`,
   all page query functions, and every INSERT/UPDATE site.

3b. **audit event presence checks - all must be >= 1:**
    ```
    grep -c "FILTER_CHANGE" <file>
    grep -c "FLAG_ADDED" <file>
    grep -c "FLAG_REVIEWED" <file>
    ```
    any 0 count = **FAIL**. specific messages:
    - `FILTER_CHANGE` = 0: sidebar filter changes are not being logged to `AUDIT_LOG`.
      add `on_change=` callbacks to all sidebar multiselect and date_input widgets on pages
      1 and 2. see AGENTS.md page 1/2 sidebar spec for the required on_change pattern.
    - `FLAG_ADDED` = 0: flag submission is not being logged. add `log_audit_event("FLAG_ADDED", ...)`
      after the `session.call()` INSERT call on page 2.
    - `FLAG_REVIEWED` = 0: flag review is not being logged. add `log_audit_event("FLAG_REVIEWED", ...)`
      after the `session.call()` UPDATE call on page 3.

4. check `st.set_page_config` position:
   ```bash
   grep -n "st\." <file> | grep -v "^[0-9]*:.*#" | head -1
   ```
   the first match must be `st.set_page_config(`. if not: FAIL.

5. run style validation checks:
   - `legend=` on `alt.X(` or `alt.Y(`: FAIL - move to `alt.Color(legend=...)` or remove
   - `st.subheader(` with abbreviated words (Avg, Pct, Num, Cnt): WARN
   - `.applymap(`: FAIL - use `.map()`
   - mixed percentage format strings: WARN - standardize to `:.1%`
   - time-axis X encoding missing `title=None`: WARN
   - `alt\.X\(` or `alt\.Y\(` without `title=`: WARN - add human-readable sentence-case title
     (exception: time-series X encoding with `title=None` is correct - skip those)
   - `st.date_input(` with start date defaulting to min_date: WARN - use `max_date - timedelta(days=30)`
   - missing `labelAngle=0` on X axis with categorical data: WARN
   - `alt.Legend(` missing `orient="top"`: WARN
   - non-compliant color hex values: WARN

6. if any forbidden pattern count > 0 or FAIL results: fix all occurrences using replace_all,
   then re-run `python -m py_compile` and re-run the full scan.

7. confirm `snowflake.yml` exists in the project root. if missing: generate from AGENTS.md.

8. report: 'pre-deploy scan passed - all patterns 0 - style OK - snowflake.yml present'
   or list remaining issues with counts and line numbers.

## success criteria

discovery mode:
- constraint table is printed and agent confirms constraints loaded

scaffold mode:
- `dashboard.py` exists at project root with all mandatory blocks
- `environment.yml` exists at project root with `streamlit=1.52.*` and `channels: - snowflake`
- `python -m py_compile` returns exit code 0

scan mode:
- `python -m py_compile` returns exit code 0
- dml injection check passes: 0 `session.sql(f` matches with INSERT/UPDATE
- `session.call(` count >= 2 (INSERT_RENEWAL_FLAG + UPDATE_RENEWAL_FLAG)
- all forbidden pattern counts are 0
- audit event presence: FILTER_CHANGE, FLAG_ADDED, FLAG_REVIEWED each >= 1
- `st.set_page_config(` is the first `st.*` call
- style validation has 0 FAIL results
- `snowflake.yml` exists in project root with correct values

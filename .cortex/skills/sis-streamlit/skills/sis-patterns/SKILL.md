---
name: sis-patterns
description: "streamlit patterns for sis warehouse runtime (streamlit 1.52.*). covers: snowflake connection, caching, user context, available widgets, layout, session state, data display, page config. use before writing any streamlit code in this project. sub-skill of sis-streamlit."
---

-> Load `references/snowflake-sis-docs.md` on every invocation - sis runtime model, owner's rights, st.user, environment.yml package rules, caching behavior.

## 1. snowflake connection

always use `get_active_session()` from `snowflake.snowpark.context`.

**inside `@st.cache_data` functions:** MUST call `get_active_session()` inside the function.
the module-level session is not accessible in cached function context and will fail.

**module-level code (non-cached):** `session = get_active_session()` at module level is
acceptable for the audit logger, page routing, and other non-cached code in `dashboard.py`.
the project scaffold uses module-level session for these cases. this is intentional, not an error.

| context | pattern |
|---|---|
| `@st.cache_data` function | call `get_active_session()` inside the function |
| non-cached module-level code | module-level session is OK |

```python
from snowflake.snowpark.context import get_active_session

# correct inside @st.cache_data: call get_active_session() inside the function
@st.cache_data(ttl=300)
def load_data():
    _session = get_active_session()   # inside the cached function
    return _session.sql("SELECT ...").collect()

# acceptable at module level for non-cached code (audit logger, routing)
session = get_active_session()   # OK — not inside @st.cache_data
```

do NOT use `st.connection("snowflake")` - this is the spcs pattern. in sis, `get_active_session()`
is the correct method.

---

## 2. caching

use `@st.cache_data(ttl=300)`. call `get_active_session()` inside the cached function, not outside.
`ttl` controls how long (in seconds) results are cached before the query reruns.

```python
@st.cache_data(ttl=300)
def load_filter_options():
    _session = get_active_session()   # inside the cached function
    rows = _session.sql(
        "SELECT DISTINCT region FROM schema.TABLE WHERE region IS NOT NULL ORDER BY region"
    ).collect()
    return [r[0] for r in rows]
```

mandatory: every `SELECT DISTINCT` query used for filter options MUST include
`WHERE col IS NOT NULL`. if NULL rows are collected, `None` enters the options list
and crashes `st.multiselect` at runtime with a TypeError.

---

## 3. user context

in sis, `CURRENT_USER()` (sql) returns the app service account - the user who deployed the app,
not the person currently viewing it. to get the logged-in viewer's identity:

```python
CURRENT_SIS_USER = st.user.user_name or "unknown"
```

always use `CURRENT_SIS_USER` (not `CURRENT_USER()`) when:
- inserting `flagged_by` or `reviewed_by` into domain tables
- passing `p_user_name` to `LOG_AUDIT_EVENT`
- filtering rows to the current viewer in WHERE clauses

`st.user.user_name` is available and safe in streamlit 1.52.2.

---

## 4. available widgets (streamlit 1.52.*)

safe to use:
- `st.multiselect(label, options, default)` - multi-value selection
- `st.selectbox(label, options)` - single selection
- `st.radio(label, options)` - mutually exclusive selection
- `st.toggle(label)`, `st.sidebar.toggle(label)` - boolean toggle (available in 1.52.2)
- `st.date_input(label, value)` - date picker; use for ALL date range selection
- `st.data_editor(df)` - editable dataframe with inline checkbox column support
- `st.text_input(label)`, `st.text_area(label, max_chars=500)` - text input
- `st.button(label)`, `st.form(key)`, `st.form_submit_button(label)` - actions and forms

forbidden or broken in sis 1.52:
- `st.slider` with `datetime.date` as `min_value` or `max_value` - use `st.date_input` instead
- `st.container(horizontal=True)` - parameter does not exist in 1.52; use `st.columns()`
- `st.metric(..., chart_data=...)` sparklines - not available in 1.52
- `st.fragment` / `@st.fragment` - exists but unreliable in warehouse runtime; do NOT use
- `st.rerun()` - causes infinite loops in warehouse runtime; do NOT use

---

## 5. layout

```python
# KPI row: n equal-width columns
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Renewal Rate", "72.4%")

# tabs
tab1, tab2 = st.tabs(["User Activity", "Agent Operations"])
with tab1:
    ...

# sidebar navigation
page = st.sidebar.radio("Navigation", ["KPI Overview", "Premium Pressure", "Activity Log"])

# sidebar filters
selected = st.sidebar.multiselect("Region", VALID_REGIONS, default=VALID_REGIONS)

# collapsible section
with st.expander("Details"):
    st.write("...")
```

no `st.container(horizontal=True)` - that parameter does not exist in streamlit 1.52.

---

## 6. session state

init pattern: always initialize with the ACTUAL default values, not empty lists or None.
if initialized with an empty list but the widget defaults to "all selected", the first
render fires a spurious change event before the user interacts, writing a false audit entry.

```python
# correct: match the widget's actual default
if "selected_regions" not in st.session_state:
    st.session_state.selected_regions = list(VALID_REGIONS)   # matches multiselect default

# detect change on each render
current = st.sidebar.multiselect(
    "Region", VALID_REGIONS, default=st.session_state.selected_regions
)
if current != st.session_state.selected_regions:
    st.session_state.selected_regions = current
    log_audit_event(...)   # only fires on actual user interaction
```

---

## 7. data display

- `st.dataframe(df)` - read-only table display
- `st.data_editor(df)` - editable table with checkbox column support
- `st.metric(label, value, delta)` - kpi card; no `chart_data` parameter in 1.52

**snowflake column names are UPPERCASE:** `session.sql(...).to_pandas()` and
`session.table(...).to_pandas()` return DataFrames with UPPERCASE column names (e.g.
`PRICE_SHOCK_BAND`, `REGION`, `IS_RENEWED`). always use uppercase column names in `groupby`,
`pivot_table`, and column access, OR call `.rename(columns=str.lower)` immediately after
`.to_pandas()` to normalize to lowercase before any pandas operations.

```python
# correct: normalize column names right after to_pandas()
df = session.sql("SELECT price_shock_band, region, ...").to_pandas()
df = df.rename(columns=str.lower)   # PRICE_SHOCK_BAND -> price_shock_band
df.groupby(["price_shock_band", "region"])...

# wrong: lowercase column name not found
df.groupby(["price_shock_band", "region"])...   # KeyError if column is PRICE_SHOCK_BAND
```

charts: use altair only. do NOT use `st.bar_chart`, `st.line_chart`, or `st.scatter_chart`
for dashboard charts - native streamlit charts cannot format percentage axes or support
advanced axis labeling. see `brand-identity` for altair chart rules and color palette.

date values from `.collect()` MUST be cast to python `datetime.date` before use in widgets
or comparisons:

```python
raw = session.sql("SELECT MIN(date_col), MAX(date_col) FROM t").collect()[0]
if raw[0] is None or raw[1] is None:
    st.error("no data in source table.")
    st.stop()
min_date = datetime.date(raw[0].year, raw[0].month, raw[0].day)
max_date = datetime.date(raw[1].year, raw[1].month, raw[1].day)
```

pandas styling: `.applymap()` was removed in pandas 2.2. always use `.map()` for
cell-level styling functions. see `brand-identity` for styling examples.

---

## 8. page config

`st.set_page_config(layout="wide")` MUST be the first `st.*` call in the file - before any
other streamlit call, including `st.title`, `st.sidebar`, or any widget.

only the `layout` parameter is supported in sis. do NOT pass `page_title`, `page_icon`,
or `menu_items` - they are ignored in warehouse runtime and may cause warnings.

```python
import streamlit as st
from snowflake.snowpark.context import get_active_session
import altair as alt
import pandas as pd

st.set_page_config(layout="wide")   # FIRST st.* call - before everything else

session = get_active_session()
...
```

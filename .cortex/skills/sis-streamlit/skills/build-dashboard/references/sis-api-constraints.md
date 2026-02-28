# SiS API constraints - full reference

source: [limitations and library changes | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/limitations)
source: [troubleshooting Streamlit in Snowflake | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/troubleshooting)

---

this file documents every API restriction enforced by `build-dashboard` scan mode. each entry includes:
- the forbidden pattern
- the required replacement
- the reason for the restriction
- the error raised if violated

---

## constraint table

### 1. `st.rerun()` / `st.experimental_rerun()`

| | |
|---|---|
| **forbidden** | `st.rerun()`, `st.experimental_rerun()` |
| **replacement** | `session_state` flag + conditional re-render |
| **reason** | `st.rerun()` triggers a full script re-execution. in SiS warehouse runtime, this causes infinite loops or connection resets. `st.experimental_rerun` does not exist in the runtime. |
| **error** | app may hang or raise `StreamlitAPIException` |

**replacement pattern:**
```python
# instead of st.rerun(), use a session_state flag:
if st.button("Refresh"):
    st.session_state["trigger_refresh"] = True

if st.session_state.get("trigger_refresh"):
    st.session_state["trigger_refresh"] = False
    # re-render by re-calling your data-loading function
```

---

### 2. `st.bar_chart(horizontal=True)`

| | |
|---|---|
| **forbidden** | `st.bar_chart(horizontal=True)` |
| **replacement** | Altair horizontal bar chart: `alt.Chart().mark_bar().encode(alt.Y(...), alt.X(...))` |
| **reason** | the `horizontal` parameter does not exist in the SiS runtime. |
| **error** | `TypeError: bar_chart() got an unexpected keyword argument 'horizontal'` |

---

### 3. `@st.fragment` decorator

| | |
|---|---|
| **forbidden** | `@st.fragment`, `st.fragment` |
| **replacement** | manual refresh button + `session_state` flag |
| **reason** | `st.fragment` exists in Streamlit 1.52.2 but causes unreliable behavior in SiS warehouse runtime (partial re-execution conflicts with the managed executor). |
| **error** | unpredictable: partial renders, stale state, or silent data corruption |

---

### 4. `style.applymap()`

| | |
|---|---|
| **forbidden** | `df.style.applymap()` |
| **replacement** | `df.style.map()` |
| **reason** | `applymap()` was deprecated in pandas 2.1.0 and removed in pandas 2.2.0. SiS uses pandas 2.x. |
| **error** | `AttributeError: 'Styler' object has no attribute 'applymap'` |

---

### 5. `PARSE_JSON()` inside `VALUES (...)`

| | |
|---|---|
| **forbidden** | `INSERT INTO t VALUES (..., PARSE_JSON(...), ...)` |
| **replacement** | `INSERT INTO t SELECT ..., PARSE_JSON(...)` |
| **reason** | Snowflake does not support function calls inside a `VALUES` clause. |
| **error** | `SQL compilation error: syntax error ... unexpected 'PARSE_JSON'` |

---

### 6. `st.slider` with `datetime.date` min/max values

| | |
|---|---|
| **forbidden** | `st.slider(min_value=some_date_obj, max_value=some_date_obj)` |
| **replacement** | `st.date_input` for all date range selection |
| **reason** | `st.slider` raises an internal Protobuf serialization error when Python `datetime.date` objects are passed. |
| **error** | `TypeError: bad argument type for built-in operation` on app load |

---

### 7. date values from `.collect()` passed directly to widgets

| | |
|---|---|
| **forbidden** | passing `.collect()` date results directly to `st.date_input` |
| **replacement** | cast explicitly: `datetime.date(raw.year, raw.month, raw.day)` |
| **reason** | Snowflake `.collect()` returns internal date types, not Python `datetime.date`. Streamlit's Protobuf serializer cannot handle these. |
| **error** | `TypeError: bad argument type for built-in operation` on app load |

**replacement pattern:**
```python
row = session.sql("SELECT MIN(date_col), MAX(date_col) FROM t").collect()[0]
min_date = datetime.date(row[0].year, row[0].month, row[0].day)
max_date = datetime.date(row[1].year, row[1].month, row[1].day)
```

---

### 8. `SELECT DISTINCT col` without `IS NOT NULL`

| | |
|---|---|
| **forbidden** | `SELECT DISTINCT col FROM t ORDER BY col` (when `col` may contain NULLs) |
| **replacement** | `SELECT DISTINCT col FROM t WHERE col IS NOT NULL ORDER BY col` |
| **reason** | NULL rows become Python `None` in the list. `st.multiselect(options=[..., None, ...])` raises TypeError during Protobuf serialization. |
| **error** | `TypeError: bad argument type for built-in operation` on app load |

---

### 9. `session.sql(f"CALL ... PARSE_JSON ...")`

| | |
|---|---|
| **forbidden** | `session.sql(f"CALL LOG_AUDIT_EVENT(... PARSE_JSON('{json_str}') ...)")` |
| **replacement** | `session.call("LOG_AUDIT_EVENT", arg1, ..., None, None)` |
| **reason** | building CALL statements with PARSE_JSON in f-strings creates double-escaping issues and SQL injection risk. `session.call()` maps Python `None` to SQL `NULL` correctly. |
| **error** | `SQL compilation error` or silent data corruption |

---

### 10. any `st.*` call before `st.set_page_config()`

| | |
|---|---|
| **forbidden** | any `st.*` call (including `st.user`, `st.sidebar`, `@st.cache_data`) before `st.set_page_config()` |
| **replacement** | `st.set_page_config()` must be the very first `st.*` call after the import block |
| **error** | `TypeError: set_page_config() can only be called once per app, and must be called as the first Streamlit command` |

---

### 11. unsupported parameters in `st.set_page_config()`

| | |
|---|---|
| **forbidden** | `st.set_page_config(page_title=..., page_icon=..., menu_items=...)` |
| **replacement** | `st.set_page_config(layout="wide")` - only `layout` is supported in SiS |
| **reason** | SiS does not support `page_title`, `page_icon`, or `menu_items`. |
| **error** | runtime error on app load |

---

## scan patterns reference

the following regex patterns are checked during scan mode. all must return 0 matches:

| # | pattern | covers |
|---|---|---|
| 1 | `st\.rerun\(\)` | constraint 1 |
| 2 | `st\.experimental_rerun\(\)` | constraint 1 |
| 3 | `\.applymap\(` | constraint 4 |
| 4 | `horizontal=True` in `bar_chart` call | constraint 2 |
| 5 | `PARSE_JSON\(` inside `VALUES\s*\(` | constraint 5 |
| 6 | `st\.fragment` | constraint 3 |
| 7 | `PARSE_JSON` in `session.sql(` strings | constraint 9 |
| 8 | `st\.slider` with date variable min/max | constraint 6 |
| 9 | date from `.collect()` without Python cast | constraint 7 |
| 10 | `SELECT DISTINCT` without `IS NOT NULL` | constraint 8 |

**grep limitations for patterns 8-10:** these checks require understanding data flow and multi-line context, which grep cannot fully verify. grep catches the obvious cases. for edge cases, manually inspect `load_filter_options()` and any code that passes `.collect()` results to widgets. if deploy fails with `TypeError: bad argument type for built-in operation`, one of these patterns is likely the cause.

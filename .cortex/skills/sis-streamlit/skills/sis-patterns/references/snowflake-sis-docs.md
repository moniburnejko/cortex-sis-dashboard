# Snowflake Streamlit in Snowflake (SiS) - runtime model and features

source: [Streamlit in Snowflake overview | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
source: [owner's rights and caller's rights | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/stored-procedure/owner-caller-rights)
source: [additional Streamlit in Snowflake features | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/additional-features)
source: [Streamlit in Snowflake packages | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/packages)
source: [accessing Snowflake data from Streamlit | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/example-access-snowflake)

---

## SiS runtime model

Streamlit in Snowflake (SiS) runs in two distinct runtime environments. this project uses **warehouse runtime** exclusively.

| property | warehouse runtime | SPCS (container runtime) |
|---|---|---|
| execution host | Snowflake virtual warehouse | Snowpark Container Services pod |
| snowflake connection | `get_active_session()` | `st.connection("snowflake")` |
| `st.rerun()` | crashes / infinite loop - FORBIDDEN | supported |
| `@st.fragment` | unreliable - FORBIDDEN | supported |
| `st.connection()` | not needed - FORBIDDEN | required |
| session auth | pre-authenticated, owner's rights | explicit credentials |

**always use `get_active_session()` from `snowflake.snowpark.context` in this project.** never use `st.connection("snowflake")` - that is the SPCS pattern.

---

## owner's rights execution model

SiS apps run with **owner's rights** by default. all SQL queries execute as the role that owns the Streamlit object, regardless of who is viewing the app.

consequences:
- all viewers see the same data (filtered only by app logic, not their Snowflake roles)
- `SELECT CURRENT_ROLE()` inside the app returns the OWNER role, not the viewer's role
- `CURRENT_USER()` (SQL) returns the app service account (the deployer), not the viewer

to identify the current viewer inside the app, always use:

```python
CURRENT_SIS_USER = st.user.user_name or "unknown"
```

---

## st.user properties

`st.user` is the SiS-specific user identity object. available properties in Streamlit 1.52.2:

| property | type | description |
|---|---|---|
| `st.user.user_name` | str or None | Snowflake login name of the current viewer |
| `st.user.email` | str or None | email address from the Snowflake user profile |

usage pattern:

```python
# safe: fallback to "unknown" if user_name is None
CURRENT_SIS_USER = st.user.user_name or "unknown"

# use CURRENT_SIS_USER (not CURRENT_USER()) for:
# - inserting flagged_by / reviewed_by into domain tables
# - passing p_user_name to LOG_AUDIT_EVENT procedure
# - filtering rows to the current viewer in WHERE clauses
```

**do NOT call `SELECT CURRENT_USER()` via SQL** to get the viewer identity. it returns the app owner role's service account.

---

## environment.yml - package rules

`environment.yml` must be placed in the **same directory as the main `.py` file**.
for this project, both `dashboard.py` and `environment.yml` are at the project root.
the key rule is co-location - `environment.yml` must be at the same level as `main_file`.

SiS uses the **Snowflake Anaconda channel** only. do NOT use `defaults`, `conda-forge`, or `pip` channels.

```yaml
name: renewal_radar_env
channels:
- snowflake
dependencies:
- streamlit=1.52.*
- altair
- pandas
```

available packages in the Snowflake Anaconda channel (partial list of packages used in this project):

| package | channel | notes |
|---|---|---|
| `streamlit` | snowflake | pin to `1.52.*` for this project |
| `altair` | snowflake | Vega-Altair 5.x |
| `pandas` | snowflake | 2.x - note: `.applymap()` removed in 2.2, use `.map()` |
| `snowflake-snowpark-python` | snowflake | pre-installed, do NOT add to environment.yml |

**do NOT add** `snowflake-snowpark-python` or `snowflake-connector-python` to `environment.yml`. they are pre-installed in the SiS runtime and re-adding them causes version conflict errors.

---

## caching behavior in SiS

`@st.cache_data` is supported in warehouse runtime with important limitations:

| property | behavior |
|---|---|
| scope | single-session only - cached values are NOT shared between different user sessions |
| TTL | works as expected - cache expires after `ttl` seconds |
| arguments | cache key includes function arguments - different filter values = different cache entries |
| session object | do NOT pass `session` as a function argument - it is not serializable |

```python
# correct: get session inside the cached function
@st.cache_data(ttl=300)
def load_data(start_date: str, end_date: str) -> pd.DataFrame:
    session = get_active_session()   # inside the function, not passed as arg
    return session.sql(
        f"SELECT * FROM FACT_RENEWAL WHERE renewal_date BETWEEN '{start_date}' AND '{end_date}'"
    ).to_pandas()

# wrong: session is not serializable for cache key
@st.cache_data
def load_data(session, start_date):   # DO NOT PASS session
    ...
```

---

## session.sql() vs session.table() vs session.call()

| method | returns | use when |
|---|---|---|
| `session.sql("SELECT ...")` | Snowpark DataFrame (lazy) | ad-hoc queries, filter options, KPI queries |
| `.collect()` | `list[Row]` | scalar values, small result sets, single-row lookups |
| `.to_pandas()` | `pandas.DataFrame` | displaying in `st.dataframe` or Altair charts |
| `session.table("schema.TABLE")` | Snowpark DataFrame (lazy) | full table access with Snowpark transforms |
| `session.call("schema.PROC", arg1, ...)` | result value | stored procedures - handles None->NULL, VARIANT types |

**always use `session.call()` for stored procedures.** never build `CALL` SQL strings with f-strings - `PARSE_JSON()` inside `VALUES (...)` is broken in SiS.

```python
# correct: session.call() handles None -> NULL automatically
session.call("SCHEMA.LOG_AUDIT_EVENT", app_name, "FLAG_ADDED", policy_id, None)

# wrong: PARSE_JSON in VALUES clause crashes in SiS
session.sql(f"CALL SCHEMA.LOG_AUDIT_EVENT('{app_name}', PARSE_JSON(NULL))").collect()
```

---

## date type casting

Snowflake `.collect()` returns Snowflake-internal date types, not Python `datetime.date`. passing them directly to Streamlit widgets causes `TypeError: bad argument type for built-in operation`.

always cast explicitly:

```python
import datetime

row = session.sql("SELECT MIN(renewal_date), MAX(renewal_date) FROM FACT_RENEWAL").collect()[0]

# wrong - Snowflake internal type, crashes in st.date_input:
min_date = row[0]

# correct - Python datetime.date, works in all widgets:
min_date = datetime.date(row[0].year, row[0].month, row[0].day)
max_date = datetime.date(row[1].year, row[1].month, row[1].day)
```

---

## NULL handling for filter options

filter option lists must exclude NULLs before passing to `st.multiselect`:

```python
# correct - IS NOT NULL guard prevents None in options list:
rows = session.sql(
    "SELECT DISTINCT region FROM FACT_RENEWAL WHERE region IS NOT NULL ORDER BY region"
).collect()
regions = [r[0] for r in rows]

# wrong - None in list causes TypeError in st.multiselect:
rows = session.sql("SELECT DISTINCT region FROM FACT_RENEWAL ORDER BY region").collect()
regions = [r[0] for r in rows]   # may contain None -> crashes on app load
```

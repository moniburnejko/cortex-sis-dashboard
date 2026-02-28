# SiS data access patterns

source: [accessing Snowflake data from Streamlit | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/example-access-snowflake)
source: [additional Streamlit in Snowflake features | Snowflake documentation](https://docs.snowflake.com/en/developer-guide/streamlit/additional-features)

---

## getting the active session

every SiS app has an active Snowflake session available. always get it this way:

```python
from snowflake.snowpark.context import get_active_session

session = get_active_session()
```

**do NOT** create a new Snowflake connection manually - the active session already has the correct role, warehouse, database, and schema configured in `snowflake.yml`.

---

## querying data

### session.sql() - for ad-hoc queries

```python
# returns a Snowpark DataFrame (lazy - not yet executed)
df = session.sql("SELECT * FROM MY_TABLE WHERE status = 'ACTIVE'")

# execute and get results as a list of Row objects
rows = df.collect()
value = rows[0]["COLUMN_NAME"]

# execute and get a pandas DataFrame (for Streamlit display)
pdf = df.to_pandas()
st.dataframe(pdf)
```

### session.table() - for full table access

```python
df = session.table("MY_SCHEMA.MY_TABLE")
pdf = df.select("col1", "col2").filter(col("status") == "ACTIVE").to_pandas()
```

### session.call() - for stored procedures

```python
result = session.call("MY_SCHEMA.MY_PROC", arg1, arg2)

# pass None for VARIANT/NULL parameters
result = session.call("LOG_AUDIT_EVENT", app_name, action, None, None)
```

**use `session.call()` instead of building f-string CALL SQL statements** - it handles escaping, `None` -> `NULL` mapping, and VARIANT parameters correctly.

---

## `.collect()` vs `.to_pandas()` - when to use each

| method | returns | use when |
|---|---|---|
| `.collect()` | `list[Row]` | scalar values, small result sets, single-row lookups |
| `.to_pandas()` | `pandas.DataFrame` | displaying in `st.dataframe`, `st.bar_chart`, or Altair charts |
| `.to_pandas()` with column selection | `pandas.DataFrame` | large tables - always select only needed columns |

```python
# CORRECT - select only needed columns for performance:
pdf = session.sql("SELECT col1, col2 FROM big_table").to_pandas()

# AVOID - loads all columns unnecessarily:
pdf = session.sql("SELECT * FROM big_table").to_pandas()
```

---

## date/timestamp type casting

Snowflake `.collect()` returns **Snowflake-internal date types**, not Python `datetime.date`. passing them directly to Streamlit widgets causes `TypeError: bad argument type for built-in operation`.

**always cast explicitly:**

```python
import datetime

row = session.sql("SELECT MIN(date_col), MAX(date_col) FROM my_table").collect()[0]

# WRONG - Snowflake internal type, crashes in st.date_input:
min_date = row[0]

# CORRECT - Python datetime.date, works in all widgets:
min_date = datetime.date(row[0].year, row[0].month, row[0].day)
max_date = datetime.date(row[1].year, row[1].month, row[1].day)
```

---

## caching in SiS

`@st.cache_data` is supported in SiS warehouse runtime but with important limitations:

| property | behavior |
|---|---|
| scope | **single-session only** - cached values are NOT shared between different user sessions |
| TTL | works as expected - cache expires after `ttl` seconds |
| arguments | cache key includes function arguments - different filter values = different cache entries |
| session object | do NOT pass the `session` object as an argument to a cached function - it is not serializable |

```python
# CORRECT - get session inside the cached function:
@st.cache_data(ttl=300)
def load_renewal_data(start_date: str, end_date: str) -> pd.DataFrame:
    session = get_active_session()
    return session.sql(
        f"SELECT * FROM FACT_RENEWAL WHERE renewal_date BETWEEN '{start_date}' AND '{end_date}'"
    ).to_pandas()

# WRONG - session is not serializable for cache key:
@st.cache_data
def load_data(session, start_date):  # DO NOT PASS session
    ...
```

---

## NULL handling

filter option lists must exclude NULLs before passing to `st.multiselect`:

```python
# CORRECT - IS NOT NULL guard prevents None in options list:
rows = session.sql(
    "SELECT DISTINCT region FROM fact_renewal WHERE region IS NOT NULL ORDER BY region"
).collect()
regions = [r[0] for r in rows]

# WRONG - None in list causes TypeError in st.multiselect:
rows = session.sql("SELECT DISTINCT region FROM fact_renewal ORDER BY region").collect()
regions = [r[0] for r in rows]  # may contain None -> crashes on app load
```

---

## owner's rights vs. caller's rights

by default, SiS apps run with **owner's rights** - all queries execute as the role that owns the Streamlit object, regardless of which user is viewing the app. this means:

- all users see the same data (filtered only by the app's logic, not their Snowflake permissions)
- `SELECT CURRENT_ROLE()` inside the app returns the owner role, not the viewer's role
- use `st.user.user_name` to identify the current viewer for logging/audit

---

## accessing the current user

```python
CURRENT_SIS_USER = st.user.user_name or "unknown"
```

in SiS, `CURRENT_USER()` (SQL) returns the app service account, not the logged-in viewer. always use `st.user.user_name` for user identity in dashboard code.

---

## writing back to Snowflake

use `session.sql().collect()` for INSERT/UPDATE/DELETE:

```python
# insert a row
session.sql(
    f"INSERT INTO my_table (col1, col2) VALUES ('{val1}', '{val2}')"
).collect()

# call a procedure for write-back (preferred for audit logging)
session.call("LOG_AUDIT_EVENT", app_name, "FLAG_ADDED", policy_id, None)
```

---

## complete data loading template

```python
import streamlit as st
import pandas as pd
from datetime import date as py_date
from snowflake.snowpark.context import get_active_session

# st.set_page_config() MUST be first st.* call - page_title/page_icon/menu_items not supported in SiS
st.set_page_config(layout="wide")

@st.cache_data(ttl=300)
def load_filter_options():
    session = get_active_session()
    # dates - cast from Snowflake internal type
    row = session.sql("SELECT MIN(date_col), MAX(date_col) FROM my_table").collect()[0]
    min_d = py_date(row[0].year, row[0].month, row[0].day)
    max_d = py_date(row[1].year, row[1].month, row[1].day)
    # categorical options - exclude NULLs
    regions = [
        r[0] for r in session.sql(
            "SELECT DISTINCT region FROM my_table WHERE region IS NOT NULL ORDER BY region"
        ).collect()
    ]
    return min_d, max_d, regions
```

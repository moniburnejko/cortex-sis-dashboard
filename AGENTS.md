# AGENTS.md

## what this is

this file gives cortex code cli the full context it needs to autonomously:
1. create logging infrastructure (AUDIT_LOG, APP_EVENTS, V_APP_EVENTS, LOG_AUDIT_EVENT procedure), RENEWAL_FLAGS table, and a stage in {database}.{schema}
2. load 3 local csv files into source tables via internal stage
3. build and deploy a 3-page streamlit in snowflake dashboard ({app_name})
4. log user interactions and agent operations via LOG_AUDIT_EVENT procedure

this is a scoped demo against {database}.{schema}. do not touch any other database or schema.

## sections

- [SECTION 1 - ENVIRONMENT & INFRASTRUCTURE](#section-1): environment, skills, schemas, DDL, data loading, done criteria phase 1
- [SECTION 2 - DASHBOARD BUILD](#section-2): file edit protocol, page specification, done criteria phase 2
- [SECTION 3 - GOVERNANCE & VERIFICATION](#section-3): security rules, memory validation, done criteria phase 3

---

# SECTION 1 - ENVIRONMENT & INFRASTRUCTURE
<!-- phase 1: everything needed before writing any code -->

## snowflake environment

| setting   | value          |
|-----------|----------------|
| database  | CORTEX_DB   |
| schema    | CORTEX_SCHEMA |
| warehouse | CORTEX_WH   |
| role      | CORTEX_ADMIN |
| stage     | STAGE_RAW_CSV  |
| app_name  | renewal_radar  |

> **SINGLE SOURCE OF TRUTH** - database, schema, warehouse, role, stage, and app_name are defined here only.
> all DDL, YAML templates, and code in this file use the values above.
> to change the project environment, update this table - nowhere else.
>
> **placeholder notation:** SQL and YAML blocks in this file use `{setting}` syntax (e.g. `{database}.{schema}.TABLE`) as templates. substitute values from this table before running.

---

## skills

invoke with `$ skill-name`. do NOT replicate skill steps manually - manual execution bypasses skill governance and is not allowed.

| skill | when (mandatory) |
|---|---|
| `$ check-local-environment` | session start, 1st |
| `$ check-snowflake-context` | session start, 2nd |
| `$ prepare-data` | data loading |
| `$ sis-streamlit` -> `sis-patterns` | before writing any Streamlit code |
| `$ sis-streamlit` -> `build-dashboard` | before scaffolding dashboard or running pre-deploy scan |
| `$ sis-streamlit` -> `brand-identity` | before generating any chart, color, or label code |
| `$ sis-streamlit` -> `deploy-and-verify` | deploy + all acceptance checks |

> **skill constraints - bypassing any of these is not allowed:**
>
> - `$ check-local-environment` completed: do NOT run `snow` CLI commands or environment checks manually afterward
> - `$ check-snowflake-context` completed: do NOT run context queries via `snow sql` or `SNOWFLAKE_SQL_EXECUTE` afterward
> - `$ prepare-data` required: do NOT run PUT, COPY INTO, gzip, or csv validation manually - the skill handles all of this
> - `$ sis-streamlit sis-patterns` and `build-dashboard` required: do NOT write any Streamlit code before loading both
> - `$ sis-streamlit brand-identity` required: do NOT generate charts, colors, or UI labels before loading
> - `$ sis-streamlit deploy-and-verify` required: do NOT run `snow streamlit deploy` or acceptance SQL manually

---

## session start gate

before executing any DDL, data loading, or code generation in this session:

- [ ] `$ check-local-environment` passed - snow CLI connected, credentials valid
- [ ] `$ check-snowflake-context` passed - role, warehouse, database, schema confirmed

do NOT proceed to source files, DDL, or code until both checks pass.

---

## source files (local)

| csv path (relative to repo root)              | target table                          | delimiter | rows  |
|-----------------------------------------------|---------------------------------------|-----------|-------|
| `data/fact_renewal.csv`                       | {schema}.FACT_RENEWAL           | `,`       | ~50k  |
| `data/fact_premium_event.csv`                 | {schema}.FACT_PREMIUM_EVENT     | `,`       | ~94k  |
| `data/dim_policy.csv`                         | {schema}.DIM_POLICY             | `,`       | ~36k  |

stage: `{database}.{schema}.{stage}`

---

## source table schemas

### {schema}.FACT_RENEWAL
```
policy_id        VARCHAR(10)   -- PK grain (policy_id, renewal_date)
client_id        VARCHAR(10)
renewal_date     DATE
region           VARCHAR(2)    -- TX MO LA TN OK KS AR
segment          VARCHAR(30)
product_variant  VARCHAR(20)
channel          VARCHAR(20)   -- AGENT BROKER DIRECT
agent_id         VARCHAR(10)   -- NULL for DIRECT channel
renewal_outcome  VARCHAR(20)   -- RENEWED LAPSED NOT_TAKEN_UP CANCELLED
is_quoted        NUMBER(1)
is_bound         NUMBER(1)
is_renewed       NUMBER(1)
quote_tta        FLOAT
target_tta_hours FLOAT
```

### {schema}.FACT_PREMIUM_EVENT
```
pricing_event_id VARCHAR(30)   -- PK
policy_id        VARCHAR(10)
client_id        VARCHAR(10)
renewal_date     DATE
event_ts         TIMESTAMP_NTZ
event_seq        NUMBER(2)
event_type       VARCHAR(20)   -- INITIAL_QUOTE REVISED_QUOTE FINAL_OFFER
is_final_offer   NUMBER(1)
source_system    VARCHAR(30)
region           VARCHAR(2)
segment          VARCHAR(30)
channel          VARCHAR(20)
agent_id         VARCHAR(10)
expiring_premium FLOAT
offered_premium  FLOAT
discount_amt     FLOAT
discount_pct     FLOAT
discount_reason  VARCHAR(100)
renewal_outcome  VARCHAR(20)
```

key metric: `(offered_premium - expiring_premium) / expiring_premium` = premium_change_pct

### {schema}.DIM_POLICY
```
policy_id              VARCHAR(10)  -- PK
client_id              VARCHAR(10)
segment                VARCHAR(30)
region                 VARCHAR(2)
product_variant        VARCHAR(20)
date_inception         DATE
date_last_renewal      DATE
date_next_renewal      DATE
sum_insured_band       VARCHAR(10)  -- LOW MEDIUM HIGH
risk_tier              VARCHAR(15)  -- PREFERRED STANDARD HIGH_RISK
payment_frequency      VARCHAR(15)
auto_renewal_flag      NUMBER(1)
annual_aggregate_limit FLOAT
per_occurrence_limit   FLOAT
policy_excess          FLOAT
```

### source table DDL

> **DDL rule - no exceptions:** use `CREATE OR ALTER TABLE` for all tables.
> never `CREATE OR REPLACE TABLE` - that drops and recreates, destroying existing data.
> copy the DDL blocks below verbatim (substitute `{database}` and `{schema}` only).

idempotent - safe to re-run. `CREATE OR ALTER TABLE` creates the table if it does not exist or alters it to match the definition if it does.

```sql
CREATE OR ALTER TABLE {database}.{schema}.FACT_RENEWAL (
    policy_id        VARCHAR(10),
    client_id        VARCHAR(10),
    renewal_date     DATE,
    region           VARCHAR(2),
    segment          VARCHAR(30),
    product_variant  VARCHAR(20),
    channel          VARCHAR(20),
    agent_id         VARCHAR(10),
    renewal_outcome  VARCHAR(20),
    is_quoted        NUMBER(1),
    is_bound         NUMBER(1),
    is_renewed       NUMBER(1),
    quote_tta        FLOAT,
    target_tta_hours FLOAT
);

CREATE OR ALTER TABLE {database}.{schema}.FACT_PREMIUM_EVENT (
    pricing_event_id VARCHAR(30),
    policy_id        VARCHAR(10),
    client_id        VARCHAR(10),
    renewal_date     DATE,
    event_ts         TIMESTAMP_NTZ,
    event_seq        NUMBER(2),
    event_type       VARCHAR(20),
    is_final_offer   NUMBER(1),
    source_system    VARCHAR(30),
    region           VARCHAR(2),
    segment          VARCHAR(30),
    channel          VARCHAR(20),
    agent_id         VARCHAR(10),
    expiring_premium FLOAT,
    offered_premium  FLOAT,
    discount_amt     FLOAT,
    discount_pct     FLOAT,
    discount_reason  VARCHAR(100),
    renewal_outcome  VARCHAR(20)
);

CREATE OR ALTER TABLE {database}.{schema}.DIM_POLICY (
    policy_id              VARCHAR(10),
    client_id              VARCHAR(10),
    segment                VARCHAR(30),
    region                 VARCHAR(2),
    product_variant        VARCHAR(20),
    date_inception         DATE,
    date_last_renewal      DATE,
    date_next_renewal      DATE,
    sum_insured_band       VARCHAR(10),
    risk_tier              VARCHAR(15),
    payment_frequency      VARCHAR(15),
    auto_renewal_flag      NUMBER(1),
    annual_aggregate_limit FLOAT,
    per_occurrence_limit   FLOAT,
    policy_excess          FLOAT
);
```

---

## domain table: RENEWAL_FLAGS

create in phase 1. this is the only domain table to create - logging infrastructure (AUDIT_LOG, APP_EVENTS, V_APP_EVENTS, LOG_AUDIT_EVENT) is created separately below.

```sql
CREATE OR ALTER TABLE {database}.{schema}.RENEWAL_FLAGS (
    flag_id        VARCHAR(40)   DEFAULT UUID_STRING(),
    flagged_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    flagged_by     VARCHAR(100),          -- populated explicitly by app; do NOT rely on DEFAULT CURRENT_USER() in SiS
    scope          VARCHAR(50),          -- any combination of REGION/SEGMENT/CHANNEL joined by '_'
    scope_region   VARCHAR(50),          -- NULL when not scoped to a region
    scope_segment  VARCHAR(50),          -- NULL when not scoped to a segment
    scope_channel  VARCHAR(50),          -- NULL when not scoped to a channel
    flag_reason    VARCHAR(200),
    status         VARCHAR(20)   DEFAULT 'OPEN',
    reviewed_by    VARCHAR(100),
    reviewed_at    TIMESTAMP_NTZ,
    notes          VARCHAR(500),
    PRIMARY KEY (flag_id)
);
```

---

## stage (create in phase 1)

create before data loading. `CREATE STAGE IF NOT EXISTS` is idempotent - safe to re-run.

```sql
CREATE STAGE IF NOT EXISTS {database}.{schema}.{stage};
```

confirm after creation:
```sql
SHOW STAGES IN SCHEMA {database}.{schema};
-- expect: 1 row with name STAGE_RAW_CSV
```

---

## logging infrastructure (create or ensure in phase 1)

> **DDL rule - no exceptions:** use `CREATE OR ALTER TABLE` for all tables.
> never `CREATE OR REPLACE TABLE` - that drops and recreates, destroying existing data.
> copy the DDL blocks below verbatim (substitute `{database}` and `{schema}` only).
>
> `CREATE OR ALTER VIEW` does not exist in Snowflake. views always use `CREATE OR REPLACE VIEW` (safe: views hold no data).
>
> `LOG_AUDIT_EVENT` procedure uses `CREATE OR REPLACE PROCEDURE` - that is intentional and correct.

create or ensure these objects exist in phase 1 using idempotent DDL (CREATE OR ALTER / CREATE IF NOT EXISTS). all statements are safe to re-run - if AUDIT_LOG already exists, re-running is safe.
exception: ADD SEARCH OPTIMIZATION - if those return 'column already has search optimization', skip them (optimization is already in place).

### APP_EVENTS event table

```sql
CREATE EVENT TABLE IF NOT EXISTS {database}.{schema}.APP_EVENTS
    DATA_RETENTION_TIME_IN_DAYS = 7
    MAX_DATA_EXTENSION_TIME_IN_DAYS = 7
    CHANGE_TRACKING = TRUE;
```

### AUDIT_LOG table

```sql
CREATE OR ALTER TABLE {database}.{schema}.AUDIT_LOG (
    audit_id              NUMBER AUTOINCREMENT PRIMARY KEY,
    event_timestamp       TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP() NOT NULL,
    user_name             VARCHAR(256),
    role_name             VARCHAR(256),
    session_id            NUMBER,
    client_session_id     VARCHAR(256),
    client_ip             VARCHAR(45),
    client_application_id VARCHAR(256),
    client_environment    VARIANT,
    action_type           VARCHAR(100) NOT NULL,
    action_category       VARCHAR(50),
    object_type           VARCHAR(100),
    object_name           VARCHAR(512),
    object_database       VARCHAR(256),
    object_schema         VARCHAR(256),
    query_id              VARCHAR(256),
    query_text            TEXT,
    query_tag             VARCHAR(2000),
    execution_status      VARCHAR(50),
    error_code            NUMBER,
    error_message         TEXT,
    rows_affected         NUMBER,
    bytes_scanned         NUMBER,
    execution_time_ms     NUMBER,
    streamlit_app_name    VARCHAR(256),
    streamlit_page        VARCHAR(256),
    streamlit_component   VARCHAR(256),
    streamlit_action      VARCHAR(256),
    request_payload       VARIANT,
    response_payload      VARIANT,
    correlation_id        VARCHAR(256),
    parent_correlation_id VARCHAR(256),
    tags                  VARIANT,
    metadata              VARIANT,
    created_at            TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP(),
    source_system         VARCHAR(100) DEFAULT 'STREAMLIT_APP'
);
```

run once - skip if 'already exists' error returned:
```sql
ALTER TABLE {database}.{schema}.AUDIT_LOG
    ADD SEARCH OPTIMIZATION ON EQUALITY(
        user_name, role_name, action_type, action_category,
        object_name, query_id, correlation_id, streamlit_app_name, execution_status
    );

ALTER TABLE {database}.{schema}.AUDIT_LOG
    ADD SEARCH OPTIMIZATION ON SUBSTRING(query_text, error_message, object_name);

ALTER TABLE {database}.{schema}.AUDIT_LOG
    CLUSTER BY (event_timestamp, action_type);
```

### V_APP_EVENTS view

```sql
CREATE OR REPLACE VIEW {database}.{schema}.V_APP_EVENTS AS
SELECT
    TIMESTAMP,
    RESOURCE_ATTRIBUTES,
    RECORD_TYPE,
    RECORD,
    RECORD_ATTRIBUTES,
    SCOPE,
    VALUE
FROM {database}.{schema}.APP_EVENTS
WHERE SCOPE['name']::STRING LIKE '%{schema}%'
   OR RESOURCE_ATTRIBUTES['snow.database.name']::STRING = '{database}';
```

### LOG_AUDIT_EVENT procedure

> **SiS user context warning:** In Streamlit in Snowflake, `CURRENT_USER()` returns the app
> service account (app owner), NOT the logged-in user. SiS callers MUST pass the logged-in
> user as `p_user_name` using `st.user.user_name`. SQL CALL sites (agent operations) may
> omit `p_user_name` - `CURRENT_USER()` is correct there (agent runs as the actual user).

```sql
CREATE OR REPLACE PROCEDURE {database}.{schema}.LOG_AUDIT_EVENT(
    p_action_type         VARCHAR,
    p_action_category     VARCHAR,
    p_streamlit_app_name  VARCHAR,
    p_streamlit_page      VARCHAR,
    p_streamlit_component VARCHAR,
    p_streamlit_action    VARCHAR,
    p_request_payload     VARIANT,
    p_response_payload    VARIANT,
    p_correlation_id      VARCHAR,
    p_tags                VARIANT,
    p_metadata            VARIANT,
    p_user_name           VARCHAR DEFAULT NULL
)
RETURNS VARCHAR
LANGUAGE SQL
AS
$$
BEGIN
    INSERT INTO {database}.{schema}.AUDIT_LOG (
        user_name, role_name, session_id, action_type, action_category, query_id,
        streamlit_app_name, streamlit_page, streamlit_component, streamlit_action,
        request_payload, response_payload, correlation_id, tags, metadata, execution_status
    )
    SELECT
        COALESCE(:p_user_name, CURRENT_USER()), CURRENT_ROLE(), CURRENT_SESSION(),
        :p_action_type, :p_action_category, LAST_QUERY_ID(),
        :p_streamlit_app_name, :p_streamlit_page, :p_streamlit_component, :p_streamlit_action,
        :p_request_payload, :p_response_payload, :p_correlation_id, :p_tags, :p_metadata,
        'SUCCESS';
    RETURN 'Audit event logged successfully';
END;
$$;
```

---

## LOG_AUDIT_EVENT usage pattern

two calling conventions - use the correct one for each context:

**cortex code cli agent** (SQL CALL, during phase 1 setup and agent trace events):
```sql
CALL {database}.{schema}.LOG_AUDIT_EVENT(
    'DATA_LOAD',          -- p_action_type
    'AGENT_OPERATION',    -- p_action_category
    '{app_name}',         -- p_streamlit_app_name
    'phase_1_infra',      -- p_streamlit_page
    'csv_ingestion',      -- p_streamlit_component
    'copy_into_complete', -- p_streamlit_action
    NULL,                 -- p_request_payload
    NULL,                 -- p_response_payload
    NULL,                 -- p_correlation_id
    NULL,                 -- p_tags
    NULL                  -- p_metadata
    -- p_user_name omitted (DEFAULT NULL) - CURRENT_USER() is correct for agent context
);
```

**streamlit app** (Snowpark `session.call()`, in dashboard.py - never build CALL strings with f-strings):
```python
session.call(
    "{database}.{schema}.LOG_AUDIT_EVENT",
    "FILTER_CHANGE",       # p_action_type
    "USER_INTERACTION",    # p_action_category
    "{app_name}",          # p_streamlit_app_name  <- constant
    "page_1_kpi_overview", # p_streamlit_page      <- constant per page
    "sidebar_filters",     # p_streamlit_component <- constant
    "multiselect_change",  # p_streamlit_action    <- constant
    None,                  # p_request_payload     <- dict or None
    None,                  # p_response_payload
    None,                  # p_correlation_id
    None,                  # p_tags
    None,                  # p_metadata
    CURRENT_SIS_USER       # p_user_name <- SiS viewer, NOT CURRENT_USER()
)
```

> **first render guard:** initialize session state to the actual default values, not empty lists.
> Otherwise the filter comparison fires a spurious FILTER_CHANGE on first page load.
> ```python
> if "kpi_filters" not in st.session_state:
>     st.session_state.kpi_filters = {
>         "regions": list(VALID_REGIONS),    # match multiselect default
>         "segments": list(VALID_SEGMENTS),
>         "channels": list(VALID_CHANNELS)
>     }
> ```

action_type values: `FILTER_CHANGE` | `FLAG_ADDED` | `FLAG_REVIEWED` | `PAGE_VIEW` | `DATA_LOAD`
action_category: `USER_INTERACTION` (from Streamlit) | `AGENT_OPERATION` (from CLI)

---

## key business metrics

```
renewal_rate = SUM(is_renewed) / COUNT(*)
leakage_rate = 1 - renewal_rate
quote_to_bind = SUM(is_bound) / NULLIF(SUM(is_quoted), 0)
service_delay_idx = AVG(quote_tta / target_tta_hours)
premium_change_pct = (offered_premium - expiring_premium) / expiring_premium
                     -- use WHERE is_final_offer = 1
price_shock_band = CASE
    WHEN premium_change_pct <= 0.05 THEN '0_TO_5'
    WHEN premium_change_pct <= 0.10 THEN '5_TO_10'
    WHEN premium_change_pct <= 0.15 THEN '10_TO_15'
    ELSE 'GT_15' END
```

---

## data loading instructions

1. run `$ check-local-environment` to confirm snow CLI and connection.
2. confirm stage: `SHOW STAGES IN SCHEMA {database}.{schema}` - if {stage} missing: `CREATE STAGE IF NOT EXISTS {database}.{schema}.{stage}`.
3. run `$ prepare-data` to validate csv files, PUT + COPY INTO, and verify row counts.
   do NOT run these steps manually - the skill handles compression, encoding checks, and error handling.
4. log phase completion via SQL CALL (agent context, not Snowpark):
   `snow sql -q "CALL {database}.{schema}.LOG_AUDIT_EVENT('DATA_LOAD', 'AGENT_OPERATION', '{app_name}', 'phase_1_infra', 'csv_ingestion', 'copy_into_complete', NULL, NULL, NULL, NULL, NULL)"`

---

## done criteria - phase 1

run `$ sis-dashboard` -> `deploy-and-verify phase-1` to verify. do NOT run these SQL checks manually. do NOT proceed to SECTION 2 until all checks pass.

```sql
-- source tables loaded
SELECT COUNT(*) FROM {database}.{schema}.FACT_RENEWAL;              -- expect: ~50K
SELECT COUNT(*) FROM {database}.{schema}.FACT_PREMIUM_EVENT;        -- expect: ~94K
SELECT COUNT(*) FROM {database}.{schema}.DIM_POLICY;                -- expect: ~36K

-- domain table created (empty)
SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA='{schema}' AND TABLE_NAME='RENEWAL_FLAGS';          -- expect: 1

-- logging infrastructure created
SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA='{schema}' AND TABLE_NAME IN ('APP_EVENTS','AUDIT_LOG'); -- expect: 2

SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS
WHERE TABLE_SCHEMA='{schema}' AND TABLE_NAME='V_APP_EVENTS';           -- expect: 1

SHOW PROCEDURES LIKE 'LOG_AUDIT_EVENT' IN SCHEMA {database}.{schema}; -- expect: 1 row

-- agent trace logged (at least 1 CALL after each major phase step)
SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG
WHERE streamlit_app_name='{app_name}' AND action_category='AGENT_OPERATION'; -- expect: >= 1
```

after completing phase 1, generate a report:
- what was done (objects created, files generated)
- results (pass/fail for each check, row counts)
- issues encountered and how they were resolved
- recommendations for next steps

---

# SECTION 2 - DASHBOARD BUILD
<!-- phase 2: page specification, done criteria -->

## pre-flight: phase 1 complete?

confirm all phase 1 done criteria (above) passed before starting SECTION 2.
do NOT proceed if any check failed.

---

## SiS critical constraints

these apply regardless of skill invocation. violating any of these causes crashes, loops, or deploy failures.

> **forbidden in SiS - these cause infinite loops, crashes, or silent failures at runtime:**
>
> - `st.rerun()` - causes infinite loops in warehouse runtime; do NOT use under any circumstance
> - `@st.fragment` - unreliable in warehouse runtime; do NOT use
> - `applymap()` - removed in pandas 2.2; use `.map()` instead
> - `horizontal=True` on radio/checkbox - does not exist in streamlit 1.52; use `st.columns()` instead
> - `st.slider` with date values - use `st.date_input` instead
> - `st.bar_chart`, `st.line_chart`, `st.scatter_chart` - use Altair only
> - `st.connection("snowflake")` - use `get_active_session()` inside functions instead
> - `CURRENT_USER()` in Streamlit code - returns service account, not the viewer; use `st.user.user_name or "unknown"` instead

> **YAML files:**
>
> - `snowflake.yml`: do NOT include `artifacts`, `runtime_name`, or `compute_pool` fields
> - `environment.yml`: MUST be created at project root alongside `dashboard.py`. required to pin Streamlit to 1.52.* and load altair + pandas from the Snowflake Anaconda channel. must have `name: renewal_radar_env` and `channels: - snowflake`. do NOT delete this file.

---

## mandatory skill usage for scan and deploy

**these steps MUST go through skills. running the commands directly is NOT allowed:**

- pre-deploy scan: `$ sis-streamlit` -> `build-dashboard dashboard.py`
  do NOT run `python -m py_compile` or manual grep scans as a substitute.
- deployment: `$ sis-streamlit` -> `deploy-and-verify deploy`
  do NOT run `snow streamlit deploy --replace` directly.

both constraints are also in SECTION 1 skill table. they apply here too.
the skills perform additional checks (snowflake.yml validation, forbidden pattern scan,
post-deploy audit log check) that direct commands bypass.

---

## file edit protocol

after every EDIT:
1. immediately GREP for the changed line - confirm it is present in the file
2. only after confirmation: proceed to the next EDIT
3. for global replacements (deprecated API calls): use replace_all, not sequential EDIT

pattern: EDIT -> GREP(verify) -> EDIT -> GREP(verify) -> deploy
NOT: EDIT x N -> deploy

---

## streamlit dashboard specification

framework: SiS - connection: `get_active_session()` - file: `dashboard.py` (project root)
app name for AUDIT_LOG: `{app_name}`
SQL: parameterized only - use whitelist validation for all IN-list filters (see security rules)

chart types, colors, axis formatting, language conventions, and label rules are in `brand-identity`. load it before generating code (via `$ sis-streamlit`).

### page 1 - renewal KPI overview

sidebar: navigation radio MUST appear first (above the Filters header); filters below: region, segment, channel multiselect + two separate date_input widgets: "Renewal date from" and "Renewal date to" (both with `format="YYYY-MM-DD"` and default: last 30 days). do NOT use a single date_input with tuple value - use two separate calls. all `SELECT DISTINCT` filter queries MUST include `WHERE col IS NOT NULL`.

4 KPI metrics (from FACT_RENEWAL, respecting active filters):
- renewal_rate = SUM(is_renewed) / COUNT(*)
- leakage_rate = 1 - renewal_rate
- quote_to_bind = SUM(is_bound) / NULLIF(SUM(is_quoted), 0)
- service_delay_idx = AVG(quote_tta / target_tta_hours)

3 charts (all Altair - native st.bar_chart / st.line_chart are forbidden):
- renewal rate trend over time (line with points, adaptive granularity: day/week/month)
  MANDATORY: aggregate dates in SQL using DATE_TRUNC - do NOT plot raw renewal_date values (one point per policy = jagged broken line)
  determine granularity from the active date range: day (<=30 days), week (31-180 days), month (>180 days)
  query pattern: `SELECT DATE_TRUNC('month', renewal_date) AS period, SUM(is_renewed)*1.0/COUNT(*) AS renewal_rate FROM FACT_RENEWAL [+ filters] GROUP BY period ORDER BY period`
  Altair: `mark_line(color="#1565C0", point=True)` + `alt.X("period:T", title=None)` + `alt.Y("renewal_rate:Q", axis=alt.Axis(format=".1%"), title="Renewal rate")`
- renewal rate by region (vertical bar chart, sorted descending)
  X = region code (short 2-letter codes - use vertical/column orientation)
  Altair: `mark_bar(color="#1565C0")` + `alt.X("region:N", sort="-y", axis=alt.Axis(labelAngle=0), title="Region")` + `alt.Y("renewal_rate:Q", axis=alt.Axis(format=".1%"), title="Renewal rate")`
- renewal_outcome distribution by segment (proportional 100% stacked horizontal bar - shows % share of each outcome per segment;
  query: SELECT segment, renewal_outcome, COUNT(*) AS n FROM FACT_RENEWAL GROUP BY segment, renewal_outcome;
  do NOT normalize in Python - use Altair stack="normalize" to guarantee exact 100% fill with no floating-point gaps;
  compute pct in Python ONLY for the tooltip: df["pct"] = df["n"] / df.groupby("segment")["n"].transform("sum");
  Altair encoding:
    alt.X("n:Q", stack="normalize", axis=alt.Axis(format=".0%"), title="share of policies"),
    alt.Y("segment:N", sort=alt.EncodingSortField("n", op="sum", order="descending")),
    alt.Color("renewal_outcome:N", scale=alt.Scale(domain=["RENEWED","LAPSED","NOT_TAKEN_UP","CANCELLED"],
      range=["#1565C0","#FFA726","#FFA726","#E53935"]), legend=alt.Legend(orient="top")),
    alt.Order("renewal_outcome:N", sort="descending"),  <- REQUIRED: puts RENEWED at 0% left edge
    tooltip=[alt.Tooltip("renewal_outcome:N", title="outcome"),
             alt.Tooltip("pct:Q", format=".1%", title="share"),
             alt.Tooltip("n:Q", title="policies")];
  do NOT plot RENEWED as the only series - all 4 outcomes must appear as separate stacked segments)

audit: on filter change -> `log_audit_event("FILTER_CHANGE", "USER_INTERACTION", "page_1_kpi_overview", "sidebar_filters", "multiselect_change")`

### page 2 - premium pressure analysis

sidebar filters: region, segment, channel multiselect + date range (default: last 30 days) + "Final Offers Only" toggle (default on, `st.sidebar.toggle()`) - filters `is_final_offer = 1`. all queries on this page respect all sidebar filters.

3 KPI metrics (render at top of page, before charts):
- Policies price-shocked (>10%): COUNT(premium_change_pct > 0.10) / COUNT(*) from FACT_PREMIUM_EVENT
- Avg premium change: AVG(premium_change_pct) from FACT_PREMIUM_EVENT
- Flags for review: COUNT(*) from RENEWAL_FLAGS WHERE status = 'OPEN'

3 charts (all Altair):
- average premium_change_pct by price_shock_band (vertical bar, sorted by band order: 0_TO_5, 5_TO_10, 10_TO_15, GT_15)
  applies: all active sidebar filters including is_final_offer toggle
- average premium_change_pct by renewal_outcome (vertical bar: all 4 outcomes - RENEWED / LAPSED / NOT_TAKEN_UP / CANCELLED)
  IMPORTANT: do NOT apply `is_final_offer = 1` to this chart. LAPSED/NOT_TAKEN_UP/CANCELLED policies often have no final offer event,
  so filtering to is_final_offer=1 removes all non-RENEWED outcomes and produces a single-bar chart.
  applies: region, segment, channel, and date filters only. ignore the "Final Offers Only" toggle for this chart.
  IMPORTANT: FACT_PREMIUM_EVENT.renewal_outcome may be NULL for non-renewed events. to guarantee all 4 outcomes appear,
  join to FACT_RENEWAL to get renewal_outcome from the authoritative source (FACT_RENEWAL always has all outcomes populated).
  query: `SELECT r.renewal_outcome, AVG((e.offered_premium - e.expiring_premium) / NULLIF(e.expiring_premium, 0)) AS avg_change FROM {database}.{schema}.FACT_PREMIUM_EVENT e JOIN {database}.{schema}.FACT_RENEWAL r ON e.policy_id = r.policy_id WHERE e.region IN (...) AND e.segment IN (...) AND e.channel IN (...) AND e.renewal_date >= '{date_from}' AND e.renewal_date <= '{date_to}' GROUP BY r.renewal_outcome ORDER BY r.renewal_outcome`
  Altair: `mark_bar(color="#1565C0")` + `alt.X("renewal_outcome:N", axis=alt.Axis(labelAngle=0), title="Renewal outcome")` + `alt.Y("avg_change:Q", axis=alt.Axis(format=".1%"), title="Average premium change")`
- price_shock_band x region -> renewal_rate (heatmap via pandas pivot + st.dataframe styled - see brand-identity for color function;
  IMPORTANT: `session.sql(...).to_pandas()` returns UPPERCASE column names: `PRICE_SHOCK_BAND`, `REGION`, `IS_RENEWED`.
  call `.rename(columns=str.lower)` on the DataFrame immediately after `.to_pandas()` before any groupby or pivot operations)

flag for review section:
- selectbox: Region (blank first option), Segment (blank first option), Channel (blank first option)
- text_input: Reason (required)
- submit button disabled unless at least one dimension is non-blank AND reason is non-empty
- derive scope: join selected dimension names with `_` (e.g. `REGION_CHANNEL`, `SEGMENT`)
- on submit: `INSERT INTO {database}.{schema}.RENEWAL_FLAGS (flagged_by, scope, scope_region, scope_segment, scope_channel, flag_reason)` with `CURRENT_SIS_USER` for flagged_by
- then: `log_audit_event("FLAG_ADDED", "USER_INTERACTION", "page_2_premium_pressure", "flag_for_review", "flag_submitted")`
- show `st.success()` with the returned flag_id

audit: on filter change -> `log_audit_event("FILTER_CHANGE", "USER_INTERACTION", "page_2_premium_pressure", "sidebar_filters", "multiselect_change")`

### page 3 - activity log

tab 1 - user interactions:
```sql
SELECT event_timestamp, user_name, streamlit_page, action_type, streamlit_action, execution_status
FROM {database}.{schema}.AUDIT_LOG
WHERE streamlit_app_name = '{app_name}'
  AND action_category = 'USER_INTERACTION'
ORDER BY event_timestamp DESC
LIMIT 200
```
review flags section (below the table):
```sql
SELECT flag_id, status, scope, scope_region, scope_segment, scope_channel,
       flag_reason, flagged_by, flagged_at
FROM {database}.{schema}.RENEWAL_FLAGS
ORDER BY flagged_at DESC
```
- use `st.data_editor` with inline checkbox column for selection
- filter controls (widgets ABOVE the table - NOT columns in the SELECT or the rendered table): `st.selectbox` Show (Open / All), `st.selectbox` Scope (All / REGION / SEGMENT / CHANNEL), `st.text_input` reason search - filters rows client-side on FLAG_REASON string match
- `st.text_area` for review notes (optional, max 500 chars)
- "mark reviewed" button:
```sql
UPDATE {database}.{schema}.RENEWAL_FLAGS
SET status='REVIEWED', reviewed_by=:sis_user, reviewed_at=CURRENT_TIMESTAMP(), notes=:review_notes
WHERE flag_id IN (...) AND flagged_by=:sis_user AND status = 'OPEN'
```
  (`:sis_user` = `st.user.user_name`, NOT `CURRENT_USER()`)
- then: `log_audit_event("FLAG_REVIEWED", "USER_INTERACTION", "page_3_activity_log", "review_flags", "mark_reviewed")`

tab 2 - agent operations:
```sql
SELECT event_timestamp, user_name, action_type, execution_status, error_message
FROM {database}.{schema}.AUDIT_LOG
WHERE streamlit_app_name = '{app_name}'
  AND action_category = 'AGENT_OPERATION'
ORDER BY event_timestamp DESC
LIMIT 100
```
status color coding: see brand-identity for the `.map()` color function (do NOT use `.applymap()`).

---

## done criteria - phase 2

run `$ sis-dashboard` -> `deploy-and-verify phase-2` to verify. do NOT run these SQL checks manually. do NOT proceed to SECTION 3 until confirmed.

```
snow streamlit list -> {app_name} must appear
python3 -m py_compile dashboard.py -> exit code 0
app URL opens, all 3 pages render with data (manual verification)
```

after completing phase 2, generate a report:
- what was done (files created, deploy output)
- results (pre-deploy scan pass/fail, app URL, pages verified)
- issues encountered and how they were resolved
- recommendations for next steps

---

# SECTION 3 - GOVERNANCE & VERIFICATION
<!-- phase 3: security rules, memory validation, done criteria -->

## pre-flight: phase 2 complete?

confirm all phase 2 done criteria (above) passed before starting SECTION 3.
do NOT proceed if any check failed.

---

## security and governance rules

1. isolation: all DDL/DML in {database}.{schema} only. never touch other databases.
2. no DROP: never DROP SCHEMA, DROP DATABASE, or DROP TABLE on any existing object.
3. parameterized SQL - whitelist validation for IN-list filters:
```python
# WHERE col IS NOT NULL is MANDATORY - NULL rows become None in the list and crash st.multiselect
VALID_REGIONS = [r[0] for r in session.sql(
    "SELECT DISTINCT region FROM {database}.{schema}.FACT_RENEWAL WHERE region IS NOT NULL").collect()]
selected = [r for r in user_selected if r in VALID_REGIONS]
df = session.table("{database}.{schema}.FACT_RENEWAL").filter(col("region").isin(selected))
```
4. audit trail: every RENEWAL_FLAGS INSERT/UPDATE must be followed by a LOG_AUDIT_EVENT call.
5. advisory posture: dashboard displays insights only - no policy approvals or campaign sends.
6. row-level safety: RENEWAL_FLAGS UPDATE must include `AND flagged_by=:sis_user` in WHERE clause, where sis_user is the SiS logged-in user (`st.user.user_name`). in SiS, `CURRENT_USER()` returns the app service account and must NOT be used for row-level safety.

---

## memory validation protocol

if prior session memory is found:
1. check the memory file's last modified date.
2. run `SELECT CURRENT_ACCOUNT(), CURRENT_ROLE()` and compare with the memory file's account/role.
3. ask the user: "found prior progress from [date] on account [account]. resume or start fresh?"
4. do NOT resume automatically if memory is older than 7 days or from a different account.

---

## done criteria - phase 3

run `$ sis-dashboard` -> `deploy-and-verify phase-3` to verify. do NOT run these SQL checks manually.

### phase 3 - write-back
```sql
SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG
WHERE streamlit_app_name='{app_name}' AND action_type='FILTER_CHANGE';  -- >= 1

SELECT COUNT(*) FROM {database}.{schema}.RENEWAL_FLAGS
WHERE status='OPEN';                                                           -- >= 1

SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG
WHERE streamlit_app_name='{app_name}' AND action_type='FLAG_ADDED';     -- >= 1

SELECT COUNT(*) FROM {database}.{schema}.RENEWAL_FLAGS
WHERE status='REVIEWED' AND reviewed_by IS NOT NULL;                           -- >= 1

SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG
WHERE streamlit_app_name='{app_name}' AND action_type='FLAG_REVIEWED';  -- >= 1
```

after completing this phase, generate a final report:
- full pass/fail summary across all phases
- issues encountered across the entire session
- recommendations for production readiness

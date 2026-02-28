---
name: deploy-and-verify
description: "deploy the Streamlit in Snowflake app and run SQL acceptance checks per phase. two modes: (1) deploy - pre-deploy scan + snow streamlit deploy; (2) verify - run done criteria SQL checks for phase-1, phase-2, phase-3, or all. trigger when the user asks to deploy, redeploy, run acceptance checks, or verify done criteria. do NOT use for local Streamlit apps. do NOT use before the dashboard Python file exists."
---

-> Load `references/sis-file-structure.md` for directory layout and common mistakes.
-> Load `references/snow-streamlit-cli.md` for deploy syntax and common error reference.
-> Load `references/snowflake-yml-reference.md` for snowflake.yml field reference.

read the expected environment from AGENTS.md:
- `{database}` - target database
- `{schema}` - target schema
- `{warehouse}` - query warehouse
- `{role}` - expected active role
- `{app_name}` - streamlit app name

---

## deploy mode

1. confirm the Python file exists (`dashboard.py`) at project root.
   if missing: stop and tell the user the file must be created first.

2. run `$ build-dashboard dashboard.py` (scan mode).
   wait for it to complete. if any check fails: stop here. do NOT proceed to deploy.

3. verify `snowflake.yml` exists with correct values from AGENTS.md:
   - definition_version: 2
   - entities.{app_name}.type: streamlit
   - entities.{app_name}.identifier.name: matches app name
   - entities.{app_name}.query_warehouse: `{warehouse}`
   - entities.{app_name}.main_file: `dashboard.py`
   - do NOT add an `artifacts` section
   if any value is wrong or file is missing: create / fix before proceeding.

4. confirm the correct role is active:
   `snow sql -q "SELECT CURRENT_ROLE()"` - must return `{role}`.
   if wrong: `snow sql -q "USE ROLE {role}"`.

5. run: `snow streamlit deploy --replace`
   capture the full output including the app URL.

6. if deploy fails:
   a. show the full error text.
   b. if Python syntax error: re-run `python -m py_compile dashboard.py`.
   c. if missing object error: verify the table/procedure exists in `{database}.{schema}`.
      common: RENEWAL_FLAGS, AUDIT_LOG, LOG_AUDIT_EVENT not created yet (run phase 1 first).
   d. if permission error: check the role has CREATE STREAMLIT and USAGE on warehouse and schema.
   e. if "Multiple file or directories were mapped to one output destination":
      remove the `artifacts` key from snowflake.yml.
   f. do NOT make file edits without first scanning the entire file for all occurrences of the same error class.

7. if deploy succeeds but the app crashes on load:
   a. if `TypeError: bad argument type for built-in operation`: likely a date casting issue,
      NULL in filter list, or `st.slider` with dates. manually inspect `load_filter_options()`.
   b. if `SchemaValidationError` from Altair: check for `legend=` on `alt.X()` or `alt.Y()`.

8. if deploy succeeds and app loads: show the app URL.
   verify environment.yml was uploaded: run `snow streamlit list` and check the `user_packages`
   column for the app row. if `user_packages` is empty, environment.yml was NOT uploaded -
   STOP and report to the user: "environment.yml is missing from the SiS stage. the default
   Streamlit version will be used instead of 1.52.*. ensure environment.yml exists at project
   root and re-deploy."
   ask the user to open it and confirm all 3 pages render with data.

9. after user confirms: run `snow sql -q "SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG LIMIT 1"`
   to confirm logging infrastructure is accessible.

---

## verify mode

if called with a phase argument (`phase-1`, `phase-2`, `phase-3`): run only that phase's criteria.
if called without arguments or `all`: run all three phases in order.

### phase 1 - infrastructure

1. RENEWAL_FLAGS table exists:
   `SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='{schema}' AND TABLE_NAME='RENEWAL_FLAGS'`
   pass: 1

2. FACT_RENEWAL row count:
   `SELECT COUNT(*) FROM {database}.{schema}.FACT_RENEWAL`
   pass: within +/-5% of ~50,000

3. FACT_PREMIUM_EVENT row count:
   `SELECT COUNT(*) FROM {database}.{schema}.FACT_PREMIUM_EVENT`
   pass: within +/-5% of ~94,000

4. DIM_POLICY row count:
   `SELECT COUNT(*) FROM {database}.{schema}.DIM_POLICY`
   pass: within +/-5% of ~36,000

5. APP_EVENTS and AUDIT_LOG exist:
   `SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='{schema}' AND TABLE_NAME IN ('APP_EVENTS','AUDIT_LOG')`
   pass: 2

6. V_APP_EVENTS view exists:
   `SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA='{schema}' AND TABLE_NAME='V_APP_EVENTS'`
   pass: 1

7. LOG_AUDIT_EVENT procedure exists:
   `SHOW PROCEDURES LIKE 'LOG_AUDIT_EVENT' IN SCHEMA {database}.{schema}`
   pass: 1 row returned

8. agent logged at least one event:
   `SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG WHERE streamlit_app_name='{app_name}' AND action_category='AGENT_OPERATION'`
   pass: >= 1

### phase 2 - dashboard

9. app is deployed:
   `snow streamlit list` - `{app_name}` must appear

10. no syntax errors:
    `python -m py_compile dashboard.py` - exit code 0

11. app renders with data (manual):
    ask the user: "please confirm all 3 pages of the dashboard load with data (yes/no)."
    if no: note as fail and ask the user to describe the issue.

### phase 3 - write-back

12. FILTER_CHANGE logged:
    `SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG WHERE streamlit_app_name='{app_name}' AND action_type='FILTER_CHANGE'`
    pass: >= 1

13. flag exists in RENEWAL_FLAGS:
    `SELECT COUNT(*) FROM {database}.{schema}.RENEWAL_FLAGS`
    pass: >= 1

14. FLAG_ADDED logged:
    `SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG WHERE streamlit_app_name='{app_name}' AND action_type='FLAG_ADDED'`
    pass: >= 1

15. flag marked REVIEWED:
    `SELECT COUNT(*) FROM {database}.{schema}.RENEWAL_FLAGS WHERE status='REVIEWED' AND reviewed_by IS NOT NULL`
    pass: >= 1

16. FLAG_REVIEWED logged:
    `SELECT COUNT(*) FROM {database}.{schema}.AUDIT_LOG WHERE streamlit_app_name='{app_name}' AND action_type='FLAG_REVIEWED'`
    pass: >= 1

### report

produce a results table after each verify run:

| # | phase | criterion | result | actual |
|---|-------|-----------|--------|--------|
| 1 | infra | RENEWAL_FLAGS exists | PASS/FAIL | ... |
| ... | ... | ... | ... | ... |

total: X/16 passed (criterion 11 is manual, target: 15/15 auto + 1 manual confirmed).

if any criterion fails: diagnose the root cause and report.
do NOT attempt to fix failures automatically - describe the issue and stop.

generate a phase report:
- what was done (queries run, objects verified)
- results (pass/fail for each criterion)
- issues encountered and how they were resolved
- recommendations for next steps

## success criteria

deploy mode:
- pre-deploy scan passes (all forbidden patterns 0, style OK)
- `snowflake.yml` exists with correct values
- `snow streamlit deploy --replace` completes without error
- app URL is accessible and all 3 pages render with data
- AUDIT_LOG query runs without error

verify mode:
- all SQL queries execute without error
- all numeric thresholds met (within +/-5% for row counts)
- user confirms manual criterion 11
- final report produced with pass/fail for each criterion

# phase 1 execution report: renewal radar sis dashboard (run 1.5)

**date:** 2026-02-28
**session:** cortex code cli, prompt 1 only - partial run, interrupted
**environment:** CORTEX_DB.CORTEX_SCHEMA, role CORTEX_ADMIN, warehouse CORTEX_WH
**final outcome:** interrupted mid-ddl - `AUDIT_LOG` created with wrong ddl syntax; remaining objects not created

---

## 1. prompt used

```
set up phase 1 infrastructure: logging objects, domain table, stage,
and source tables.
do not load csv data yet.
stop and show what was created.
```

---

## 2. execution trace

### skills
both session-start skills were invoked in the correct order:

- `$ check-local-environment` - invoked correctly
- `$ check-snowflake-context` - invoked correctly

however, after each skill the agent ran additional manual commands anyway:
- after check-local-environment: `snow --version`, `snow connection list` (failed), `snow connection test` (failed), `snow connection test -c pl_agents_team` (succeeded)
- after check-snowflake-context: `snow sql -q "SELECT CURRENT_ACCOUNT()..."` and `SHOW SCHEMAS` queries

these manual commands are explicitly prohibited by the skill constraints.

### ddl executed

| object | type | result |
|---|---|---|
| `APP_EVENTS` | event table | already existed |
| `AUDIT_LOG` | table | created - but with `CREATE OR REPLACE TABLE` (violation) |
| `AUDIT_LOG` search optimization | ALTER | applied |
| `AUDIT_LOG` clustering | ALTER | applied |
| `V_APP_EVENTS` | view | cancelled |
| `LOG_AUDIT_EVENT` | procedure | cancelled |

remaining objects (`RENEWAL_FLAGS`, stage, source tables) were not reached.

### interruption

the session was interrupted after noticing `CREATE OR REPLACE TABLE` on `AUDIT_LOG`.
AGENTS.md specifies `CREATE OR ALTER TABLE` for all tables. the agent acknowledged
the error and confirmed the correct rule. session ended.

---

## 3. deviations

### deviation 1: CREATE OR REPLACE TABLE used for AUDIT_LOG

**what happened:** agent used `CREATE OR REPLACE TABLE` instead of `CREATE OR ALTER TABLE`.

**root cause:** `CREATE OR REPLACE` is the dominant pattern in snowflake training data.
the rule was present in AGENTS.md but not visually prominent - it appeared as prose in a section header,
not as a dedicated callout block near the ddl.

**consequence:** the `AUDIT_LOG` table was dropped and recreated. since it was empty (new session),
no data was lost in this run. in a resumed session this would destroy existing audit rows.

**status:** addressed - see section 4.

---

### deviation 2: manual commands after skill completion

**what happened:** after both session-start skills completed, the agent ran manual `snow` cli
and `snow sql` context queries that the skills had already covered.

**root cause:** the skill constraints were in a table column ("constraint") which has lower
visual weight than a callout block.

**consequence:** no data corruption, but skill governance was bypassed. the session-start
gate in AGENTS.md is intended to prevent exactly this pattern.

**status:** addressed - see section 4.

---

## 4. AGENTS.md changes made after session

five changes were applied in a follow-up repository maintenance session (outside cortex code cli).

**change 1: ddl callout blocks added**

two `> **DDL rule - no exceptions:**` callout blocks added - one before source table ddl,
one before logging infrastructure ddl. each block states the rule explicitly and explains
why it matters (data destruction). the second callout also clarifies:
- `CREATE OR ALTER VIEW` does not exist in snowflake - views use `CREATE OR REPLACE VIEW` (safe, no data)
- `LOG_AUDIT_EVENT` procedure uses `CREATE OR REPLACE PROCEDURE` - intentional and correct

**change 2: V_APP_EVENTS ddl corrected**

`CREATE OR ALTER VIEW` changed to `CREATE OR REPLACE VIEW`. this was the direct cause of the
"malformed view" error seen in previous sessions - `CREATE OR ALTER VIEW` is not a valid
snowflake syntax. views do not store data, so replacing them is always safe.

**change 3: page 1 kpi column names corrected**

the dashboard spec for page 1 referenced two columns that do not exist in `FACT_RENEWAL`:
- `quote_status` - does not exist; correct columns are `is_quoted` and `is_bound`
- `service_delay_days` - does not exist; correct expression is `quote_tta / target_tta_hours`

formulas corrected to match both the source table schema and the "key business metrics" section.

**change 4: stage ddl section added**

`CREATE STAGE IF NOT EXISTS {database}.{schema}.{stage}` was only mentioned conditionally in the
data loading instructions. a dedicated `## stage (create in phase 1)` section added between
`RENEWAL_FLAGS` and logging infrastructure, with confirmation query.

**change 5: skills constraints and sis forbidden patterns restructured**

both sections were converted from table columns (low visual weight) to dedicated `> **...:**`
callout blocks placed immediately after the relevant reference table. each constraint is now
a clearly separated bullet point with explicit "do NOT" language.

---

## 4b. skill changes made after session

one change was applied to the skill library in a follow-up repository maintenance session (outside cortex code cli).

**change 1: connections.toml renamed to config.toml in all skill files**

**what happened:** `snow connection list` failed with `'String' object has no attribute 'items'`
during the `check-local-environment` run. the error was caused by `default_connection_name`
being present in `~/.snowflake/connections.toml` - snow cli 3.x only supports this key in
`~/.snowflake/config.toml`. the file had to be renamed to fix the issue.

**files updated:**
- `skills/check-local-environment/SKILL.md` - all references (stat path, chmod path, error guidance, success criteria)
- `skills/check-snowflake-context/SKILL.md` - description
- `skills/sis-dashboard/SKILL.md` - routing table + workflow sequence
- `skills/README.md` - check-local-environment description
- `skills/developing-with-streamlit/skills/deploy-and-verify/references/snow-streamlit-cli.md` - `--connection` flag description and notes section

**root cause:** snow cli 3.x expects `config.toml` as the main config file. `connections.toml`
is a legacy name that does not support top-level keys like `default_connection_name`.
when snow cli reads `connections.toml` and finds that key as a string, calling `.items()` on it fails.

---

## 5. lessons learned

- callout blocks (`> **rule:**`) outperform table columns for constraints that must not be missed. tables are good for reference; callouts are good for enforcement.
- `CREATE OR ALTER VIEW` does not exist in snowflake - this is a hard syntax error, not a policy preference. views always use `CREATE OR REPLACE VIEW`.
- even when skills are invoked correctly, agents may run equivalent manual commands in parallel. constraints need to say "do NOT run X afterward", not just "invoke the skill".
- snow cli 3.x requires `~/.snowflake/config.toml` as the main config file. `connections.toml` does not support `default_connection_name` - renaming the file is the fix.

# phase 1 execution report: renewal radar sis dashboard

**date:** 2026-02-28
**session:** cortex code cli, single session covering prompt 1 and prompt 2
**environment:** CORTEX_DB.CORTEX_SCHEMA, role CORTEX_ADMIN, warehouse CORTEX_WH
**final outcome:** phase 1 complete - all 7 acceptance criteria passed

---

## 1. what phase 1 covers

phase 1 establishes everything needed before any dashboard code is written:

- prompt 1 (infrastructure):
   - create logging objects: `APP_EVENTS`, `AUDIT_LOG`, `V_APP_EVENTS`, `LOG_AUDIT_EVENT`
   - create domain table: `RENEWAL_FLAGS`
   - create stage: `STAGE_RAW_CSV`
   - create 3 source tables: `FACT_RENEWAL`, `FACT_PREMIUM_EVENT`, `DIM_POLICY`
   - no data loaded yet
- prompt 2 (data load):
   - validate 3 local csv files
   - load them into the source tables via PUT and COPY INTO
   - log the operation
   - run acceptance checks
   - stop and wait for confirmation

---

## 2. prompts used

### prompt 1

```
set up phase 1 infrastructure: logging objects, domain table, stage,
and source tables.
do not load csv data yet.
stop and show what was created.
```

### prompt 2

```
validate and load all 3 csv files into the source tables.
log the data load operation.
run phase 1 acceptance checks and show the full results.
stop and wait for my confirmation.
```

### prompt 2b (after first attempt failed due to skill bypass)

```
you should have used the prepare-data skill. please use skills as defined.
```

---

## 3. what AGENTS.md specifies for phase 1

### mandatory skills (from the skills section)

| skill | when | note |
|---|---|---|
| `$ check-local-environment` | session start | verify snow cli, connections.toml, python |
| `$ check-snowflake-context` | session start, after check-local-environment | verify role, warehouse, database, schema objects |
| `$ prepare-data` | data loading | validate csv + PUT + COPY INTO + row count verify |
| `$ deploy-and-verify phase-1` | after phase 1 | run sql acceptance checks per phase |

constraint added after session (see section 10):
"when a task matches a skill listed above, you MUST invoke it using `$ skill-name`.
do NOT replicate the skill's steps manually."

### data loading instructions (AGENTS.md section)

1. run `$ check-local-environment` to confirm snow cli and connection.
2. confirm stage - if missing: `CREATE STAGE IF NOT EXISTS`.
3. run `$ prepare-data` to validate csv files, PUT + COPY INTO, and verify row counts.
4. log phase completion via `snow sql -q "CALL ... LOG_AUDIT_EVENT(...)"`.

### phase 1 done criteria (7 checks)

```sql
SELECT COUNT(*) FROM FACT_RENEWAL;              -- expect ~50k
SELECT COUNT(*) FROM FACT_PREMIUM_EVENT;        -- expect ~94k
SELECT COUNT(*) FROM DIM_POLICY;                -- expect ~36k
SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME='RENEWAL_FLAGS';               -- expect 1
SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('APP_EVENTS','AUDIT_LOG'); -- expect 2
SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS
WHERE TABLE_NAME='V_APP_EVENTS';                -- expect 1
SHOW PROCEDURES LIKE 'LOG_AUDIT_EVENT';         -- expect 1 row
SELECT COUNT(*) FROM AUDIT_LOG
WHERE action_category='AGENT_OPERATION';        -- expect >= 1
```

---

## 4. execution trace: prompt 1 (infrastructure)

### skills supposed to run
- `$ check-local-environment` (session start)
- `$ check-snowflake-context` (session start)

### skills actually used
none.

### what the agent did instead

the agent skipped both session-start skills and ran a single sql query directly:

```sql
SELECT CURRENT_ACCOUNT(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()
```

result:

| ACCOUNT  | ROLE           | WAREHOUSE    | DATABASE     | SCHEMA         |
|----------|----------------|--------------|--------------|----------------|
| CORTEX_ACCOUNT | CORTEX_ADMIN | CORTEX_WH | CORTEX_DB | CORTEX_SCHEMA |

all values matched AGENTS.md environment. the agent proceeded without verifying connections.toml
permissions, snow cli version, or python availability (those are covered by check-local-environment).
it also did not verify the stage or schema existence explicitly via the check-snowflake-context steps.

### ddl execution

the agent executed all ddl from AGENTS.md in the correct order:

| object | type | result |
|---|---|---|
| `APP_EVENTS` | event table | already existed |
| `AUDIT_LOG` | table | created with search optimization and clustering |
| `V_APP_EVENTS` | view | created |
| `LOG_AUDIT_EVENT` | procedure | created |
| `RENEWAL_FLAGS` | domain table | created |
| `STAGE_RAW_CSV` | internal stage | already existed |
| `FACT_RENEWAL` | source table | created |
| `FACT_PREMIUM_EVENT` | source table | created |
| `DIM_POLICY` | source table | created |

all ddl was idempotent as specified (CREATE OR ALTER, CREATE IF NOT EXISTS). the "already existed"
results for `APP_EVENTS` and `STAGE_RAW_CSV` are expected and correct.

### outcome

all 10 objects were created and verified. the agent stopped and produced a phase report listing all objects with status, exactly as instructed by prompt 1.

---

## 5. execution trace: prompt 2 - first attempt (skill bypassed)

### skill supposed to run
`$ prepare-data`

### skill actually used
none.

### what the agent did

the agent ran the prepare-data workflow manually using bash commands:

1. validation: `head -3 <file>`, `ls -la`, `wc -l` for each csv file.
2. no compression step: the agent skipped `gzip -k` entirely.
3. PUT (uncompressed): ran PUT directly on `.csv` files without `AUTO_COMPRESS=FALSE`:
   ```
   snow sql -q "PUT file:///...data/dim_policy.csv @STAGE_RAW_CSV ..."
   snow sql -q "PUT file:///...data/fact_renewal.csv @STAGE_RAW_CSV ..."
   snow sql -q "PUT file:///...data/fact_premium_event.csv @STAGE_RAW_CSV ..."
   ```
   because `AUTO_COMPRESS` defaults to `TRUE`, snowflake compressed the files during upload.
   the data reached the stage in a valid state, so COPY INTO succeeded.
4. COPY INTO: all 3 tables loaded with 0 errors:
   - `DIM_POLICY`: 36,298 rows loaded
   - `FACT_RENEWAL`: 50,000 rows loaded
   - `FACT_PREMIUM_EVENT`: 94,642 rows loaded

### why the skill was bypassed

at the time of this session, `prepare-data` was NOT listed in the mandatory block of AGENTS.md.
it appeared only in the skills table under the column "when to invoke", which the agent interpreted
as guidance rather than a hard requirement. the agent chose the most direct path to the outcome.

additionally, because the agent never invoked the skill, it never read step 5 of the skill
("check if already compressed - if not, run `gzip -k`"). the compression requirement was
completely invisible to the agent.

### session error

after the 3 COPY INTO operations completed successfully, a connectivity error ended the session:

```
Error: Error processing response: Unable to connect. Is the computer able to access the url?
```

this error is unrelated to data loading. it appears to be a transient network issue between
the cortex code cli client and the response processing layer. as a result, the agent could not:
- call `LOG_AUDIT_EVENT` to log the data load
- run the phase 1 acceptance checks
- stop and wait for confirmation

the data in snowflake was correct at this point (50k / 94k / 36k rows), but the session ended
mid-workflow.

---

## 6. corrections

after the failed first attempt, i prompted a new session with prompt 2 again and sent a correction:

```
you should have used the prepare-data skill. use skills as defined.
```

the agent acknowledged the correction and invoked `$ prepare-data`.

---

## 7. execution trace: prompt 2 - second attempt (skill invoked correctly)

### skill used
`$ prepare-data` - correctly invoked.

### what the skill did

validation phase (prepare-data step 1-4):

the skill checked all 3 files in sequence:

| file | encoding | columns | rows | oversized rows | status |
|---|---|---|---|---|---|
| fact_renewal.csv | ASCII | 14 | 50,000 | 0 | OK |
| fact_premium_event.csv | ASCII | 19 | 94,642 | 0 | OK |
| dim_policy.csv | ASCII | 15 | 36,298 | 0 | OK |

no ERROR or WARN conditions. validation passed for all 3 files.

agent autonomous decision: TRUNCATE before reload

before proceeding to load, the agent queried current row counts and found:

| TABLE_NAME | ROW_COUNT |
|---|---|
| FACT_RENEWAL | 100,000 |
| FACT_PREMIUM_EVENT | 189,284 |
| DIM_POLICY | 72,596 |

the tables had been loaded twice from the first attempt (50k + 50k = 100k, etc.).
the agent decided to TRUNCATE all 3 tables and reload.

the prepare-data SKILL.md states: "to force reload: add `FORCE=TRUE`, or `TRUNCATE TABLE` first.
ask the user before force-reloading." the agent did ask before truncating.

compression phase (prepare-data step 5):

```bash
rm -f *.gz && gzip -k fact_renewal.csv && gzip -k dim_policy.csv && gzip -k fact_premium_event.csv
```

result:
- dim_policy.csv.gz: 851K
- fact_premium_event.csv.gz: 2.0M
- fact_renewal.csv.gz: (created)

this step was correctly executed this time, unlike the first attempt.

PUT phase (prepare-data step 6):

all 3 files uploaded with `AUTO_COMPRESS=FALSE` (correct, since files were already compressed):

```
PUT file:///...data/fact_renewal.csv.gz @STAGE_RAW_CSV AUTO_COMPRESS=FALSE OVERWRITE=TRUE
PUT file:///...data/dim_policy.csv.gz @STAGE_RAW_CSV AUTO_COMPRESS=FALSE OVERWRITE=TRUE
PUT file:///...data/fact_premium_event.csv.gz @STAGE_RAW_CSV AUTO_COMPRESS=FALSE OVERWRITE=TRUE
```

all returned status `UPLOADED`.

COPY INTO phase (prepare-data step 7):

| file | rows_parsed | rows_loaded | errors_seen | status |
|---|---|---|---|---|
| fact_renewal.csv.gz | 50,000 | 50,000 | 0 | LOADED |
| dim_policy.csv.gz | 36,298 | 36,298 | 0 | LOADED |
| fact_premium_event.csv.gz | 94,642 | 94,642 | 0 | LOADED |

row count verification (prepare-data step 8):

| TABLE_NAME | ROW_COUNT | EXPECTED | WITHIN TOLERANCE |
|---|---|---|---|
| FACT_RENEWAL | 50,000 | ~50k | yes |
| FACT_PREMIUM_EVENT | 94,642 | ~94k | yes |
| DIM_POLICY | 36,298 | ~36k | yes |

logging (AGENTS.md data loading instructions step 4):

```
CALL CORTEX_DB.CORTEX_SCHEMA.LOG_AUDIT_EVENT(
  'DATA_LOAD', 'AGENT_OPERATION', 'renewal_radar', 'phase_1_infra',
  'csv_ingestion', 'copy_into_complete', NULL, NULL, NULL, NULL, NULL
)
```

executed via `snow sql`. `LOG_AUDIT_EVENT` returned: "Audit event logged successfully".

### acceptance checks

the agent ran 7 sql checks. note: these were run manually, not via `$ deploy-and-verify phase-1`.
see skill compliance section below.

| check | actual | expected | status |
|---|---|---|---|
| `FACT_RENEWAL` row count | 50,000 | ~50k | PASS |
| `FACT_PREMIUM_EVENT` row count | 94,642 | ~94k | PASS |
| `DIM_POLICY` row count | 36,298 | ~36k | PASS |
| `RENEWAL_FLAGS` exists | 1 | 1 | PASS |
| `APP_EVENTS` + `AUDIT_LOG` tables | 2 | 2 | PASS |
| `V_APP_EVENTS` view | 1 | 1 | PASS |
| `LOG_AUDIT_EVENT` procedure | 1 | 1 | PASS |
| agent operations logged | 6 | >= 1 | PASS |

all 7 (8 with agent logging check) criteria passed. phase 1 complete.

---

## 8. skill compliance summary

| skill | supposed to run | actually invoked | result |
|---|---|---|---|
| `$ check-local-environment` | yes (session start) | no | agent ran one sql query directly; snow cli version, connections.toml, python not verified |
| `$ check-snowflake-context` | yes (session start) | no | agent ran one sql query directly; schema and stage existence not checked per skill protocol |
| `$ prepare-data` | yes (data loading) | no on 1st attempt, yes on 2nd after my correction | first attempt loaded data correctly but skipped compression and logging |
| `$ deploy-and-verify phase-1` | yes (after phase) | no | agent ran acceptance sql checks manually |

skills invoked: 1 out of 4 required (prepare-data, on second attempt only).

---

## 9. deviations and root causes

### deviation 1: check-local-environment and check-snowflake-context skipped

what happened: agent ran a single `SNOWFLAKE_SQL_EXECUTE` instead of invoking the two
session-start skills.

root cause: these skills were in the mandatory block, but no explicit prohibition existed
against running equivalent commands manually. the agent saw that context values matched AGENTS.md
and considered the check complete.

consequence: snow cli version, connections.toml permissions (0600 check), python availability,
and explicit schema/stage verification were not performed. in this session, all prerequisites
were already in place so no failure resulted.

assessment (post-session): these two skills are non-negotiable. they must always run at
session start, with no exceptions. a single context sql query is not a substitute:
- it does not verify connections.toml permissions (a misconfigured 0600 triggers confusing errors later)
- it does not normalize the session (USE ROLE, USE WAREHOUSE, USE DATABASE) if there is a mismatch
- it does not explicitly confirm the target schema and stage exist before any ddl runs
- it does not verify python availability, which is required for pre-deploy scan in phase 2
skipping them in a known-good environment appears harmless, but creates silent risk in any
other environment. the session start gate added to AGENTS.md (see section 10, change 6)
enforces this as a hard stop before any ddl, data loading, or code generation.

status: addressed - see section 10, changes 4, 5, and 6.

---

### deviation 2: prepare-data bypassed on first attempt

what happened: agent ran bash commands (head, ls, wc -l) and snow sql PUT commands manually,
skipping the `$ prepare-data` skill entirely.

root cause: `prepare-data` was not listed in the mandatory block. the skills table column
"when to invoke" was treated as a suggestion. because the agent never read the skill file,
it did not know about the required gzip compression step.

consequence: files were uploaded uncompressed. snowflake's default `AUTO_COMPRESS=TRUE`
compressed them during upload, so data loaded correctly. no data corruption occurred.

assessment (post-session): while compression itself is not required for correctness (small
files, snowflake handles both), the skill bypass had real consequences beyond compression:
validation (encoding, column count, oversized rows) was skipped entirely, and the logging
step (`LOG_AUDIT_EVENT` after load) did not run before the session hit a network error.
the skill is mandatory because it is the only guaranteed path
through validation, loading, and logging as a single atomic workflow.

corrective action: intervention (prompt 2b) redirected the agent to use the skill.

---

### deviation 3: deploy-and-verify phase-1 skipped

what happened: the agent ran acceptance sql queries directly instead of invoking
`$ deploy-and-verify phase-1`.

root cause: no explicit prohibition against running acceptance checks manually. the mandatory
block listed deploy-and-verify but did not prohibit manual sql.

consequence: the acceptance checks performed matched the phase 1 done criteria in AGENTS.md,
so the outcome was correct. however, any extended checks or reporting logic inside the skill
were bypassed.

status: addressed - see section 10, changes 4 and 5.

---

## 10. file changes made after session

### AGENTS.md

three changes were applied to close the governance gaps identified during this session.

change 1: added prepare-data to mandatory block

before:
```
mandatory:
- session start: run `$ check-local-environment` then `$ check-snowflake-context`
- before generating streamlit code: ...
```

after:
```
mandatory:
- session start: run `$ check-local-environment` then `$ check-snowflake-context`
- data loading: run `$ prepare-data` - do NOT run PUT, COPY INTO, gzip, or csv validation commands manually
- before generating streamlit code: ...
```

change 2: added general constraint after mandatory block

```
constraint: when a task matches a skill listed above, you MUST invoke it using `$ skill-name`.
do NOT replicate the skill's steps manually. manual replication bypasses skill governance and is not allowed.
```

change 3: strengthened data loading instructions step 3

before:
```
3. run `$ prepare-data` to validate csv files, PUT + COPY INTO, and verify row counts.
```

after:
```
3. run `$ prepare-data` to validate csv files, PUT + COPY INTO, and verify row counts.
   do NOT run these steps manually - the skill handles compression, encoding checks, and error handling.
```

change 4: added explicit "do NOT" prohibition to all remaining mandatory skill entries

the pattern established for `prepare-data` was applied to every other mandatory skill:

| skill entry | do NOT added |
|---|---|
| session start | "do NOT run context or environment checks manually via snow sql or SNOWFLAKE_SQL_EXECUTE" |
| before streamlit code | "do NOT write any streamlit code without loading sis constraints and visual identity first" |
| before every deploy | "do NOT run snow streamlit deploy without completing this scan first" |
| after each phase | "do NOT run acceptance sql queries manually" |

this closed the remaining gaps identified in this session for deviations 1 and 4.

change 5: restructured skills section - merged skills table, mandatory block, and constraint into a single table

the previous format duplicated information across two structures:
- skills table: `when to invoke` column (treated as suggestion by the agent)
- mandatory block: same skills repeated with enforcement language

the new format is a single table with columns: skill, scope, when (mandatory), do NOT.
enforcement is now co-located with the skill description - no separate mandatory block needed.
the general constraint was compressed to one sentence above the table.

before (22 lines, 3 separate blocks):
```
| skill | scope | when to invoke |    <- description only, no enforcement
...

mandatory:
- session start: run ...              <- enforcement separate from description
...

constraint: ...                       <- general rule separate from both
```

after (12 lines, 1 block):
```
invoke with $ skill-name. do NOT replicate skill steps manually ...

| skill | scope | when (mandatory) | constraint |    <- description + enforcement together
...
```

change 6: added session start gate to AGENTS.md

a new `session start gate` section was added immediately after the skills table. it is a
hard stop before any ddl, data loading, or code generation:

```
before executing any DDL, data loading, or code generation in this session:

- [ ] $ check-local-environment passed - snow cli connected, credentials valid
- [ ] $ check-snowflake-context passed - role, warehouse, database, schema confirmed

do NOT proceed to source files, DDL, or code until both checks pass.
```

this directly addresses deviation 1. the checklist format makes the gate explicit and
leaves no room for interpretation - both items must be checked before any work begins.

change 7: added phase gates between SECTION 1, 2, and 3

each done criteria section now begins with `run $ deploy-and-verify phase-X to verify`
and each section transition has an explicit pre-flight check:

- done criteria phase 1: "run `$ deploy-and-verify phase-1` to verify. do NOT proceed to
  SECTION 2 until all checks pass."
- SECTION 2 opens with: "confirm all phase 1 done criteria passed before starting SECTION 2.
  do NOT proceed if any check failed."
- done criteria phase 2: "run `$ deploy-and-verify phase-2` to verify. do NOT proceed to
  SECTION 3 until confirmed."
- SECTION 3 opens with: "confirm all phase 2 done criteria passed before starting SECTION 3."
- done criteria phase 3: "run `$ deploy-and-verify phase-3` to verify."

this addresses deviation 4 (deploy-and-verify skipped) by embedding the skill call directly
into the done criteria instructions rather than relying on the agent to remember it from the
skills table.

change 8: added sis critical constraints table to SECTION 2

a compact reference table of forbidden sis patterns was added at the top of SECTION 2,
before any code generation work begins. this consolidates the most critical constraints
(st.rerun, @st.fragment, applymap, horizontal=True, st.slider with dates, etc.) in a single
visible block, reducing reliance on the agent loading build-dashboard skill before consulting
the constraint list.

---

## 11. lessons learned

- guidance without an explicit prohibition is not enforcement. "when to invoke" is not a mandate. every mandatory skill needs a "do NOT replicate manually" constraint co-located with it.
- skills alone do not enforce sequence. phase gates and checklists in AGENTS.md are what enforce ordering - an earlier version of this project had them before skills were introduced, they were dropped, and this session confirmed they are needed.
- the prompts.md stop-and-wait design is the recovery protocol for transient errors: re-run the same prompt from a new session. prepare-data detects existing data and asks before reloading.

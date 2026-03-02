# execution history: renewal radar sis dashboard

## environment

| setting | value |
|---|---|
| database | CORTEX_DB |
| schema | CORTEX_SCHEMA |
| warehouse | CORTEX_WH |
| role | CORTEX_ADMIN |
| stage | STAGE_RAW_CSV |
| app | RENEWAL_RADAR |
| project dates | 2026-02-28 through 2026-03-02 |

---

## phase 1: infrastructure and data load

### runs

| run | date | outcome | key issue |
|---|---|---|---|
| 01 | 2026-02-28 | partial | `$ prepare-data` bypassed first attempt; acceptance checks run manually; 7/7 criteria passed |
| 01.5 | 2026-02-28 | interrupted | wrong DDL syntax (`CREATE OR REPLACE TABLE`); session stopped mid-DDL |
| 02 | 2026-02-28 | complete | 8/8 criteria passed; all mandatory skills invoked correctly |

### done criteria (run 02 - final)

| # | criterion | expected | actual | result |
|---|---|---|---|---|
| 1 | RENEWAL_FLAGS table exists | 1 | 1 | pass |
| 2 | FACT_RENEWAL row count | ~50,000 | 50,000 | pass |
| 3 | FACT_PREMIUM_EVENT row count | ~94,000 | 94,642 | pass |
| 4 | DIM_POLICY row count | ~36,000 | 36,298 | pass |
| 5 | APP_EVENTS and AUDIT_LOG exist | 2 | 2 | pass |
| 6 | V_APP_EVENTS view exists | 1 | 1 | pass |
| 7 | LOG_AUDIT_EVENT procedure exists | 1 row | 1 row | pass |
| 8 | agent operations logged | >= 1 | 2 | pass |

### final state

objects created:
- APP_EVENTS (event table), AUDIT_LOG (36 cols, search opt, clustering), V_APP_EVENTS (view)
- LOG_AUDIT_EVENT (procedure), RENEWAL_FLAGS (domain table), STAGE_RAW_CSV (stage)
- FACT_RENEWAL (50,000 rows), FACT_PREMIUM_EVENT (94,642 rows), DIM_POLICY (36,298 rows)

### deviations

- run 01: session start gate not invoked in prompt 2 session (no skills before DDL)
- run 01: `$ prepare-data` bypassed on first attempt; agent ran PUT/COPY INTO as direct bash
- run 01: acceptance checks run via direct SNOWFLAKE_SQL_EXECUTE instead of `$ sis-dashboard`
- run 01.5: `CREATE OR REPLACE TABLE` used instead of `CREATE OR ALTER TABLE` - DDL rule violation
- run 02: sub-skill path resolved from personal skills location; agent recovered via GLOB
- run 02: agent asked unnecessary phase selection question when phase was explicit in prompt

---

## phase 2: dashboard build and deploy

### runs

| run | date | outcome | key issue |
|---|---|---|---|
| 01 | 2026-03-01 | interrupted | `$ sis-streamlit` not invoked before planning; session stopped for governance review |
| 02 | 2026-03-01 | deployed | scan and deploy as direct commands; file placement errors; snowflake.yml format fix |
| 03 | 2026-03-01 | rewritten | SQL injection in INSERT and UPDATE identified post-deploy; FILTER_CHANGE missing; charts fixed |
| 04 | 2026-03-01 | refined | 5 deploy cycles; display-label layer; scope_parts.append bug introduced and fixed |
| 05 | 2026-03-02 | complete | stored procedures created; FILTER_CHANGE callbacks added; deployed first attempt |

### done criteria (run 05 - final)

| # | criterion | expected | actual | result |
|---|---|---|---|---|
| 9 | app deployed | RENEWAL_RADAR present | present | pass |
| 10 | python syntax valid | exit code 0 | 0 | pass |
| 11 | all 3 pages render with data | confirmed | confirmed | pass |

### final state

- dashboard.py: 728 lines, 3 pages (kpi overview, premium pressure, flag management)
- stored procedures: INSERT_RENEWAL_FLAG, UPDATE_RENEWAL_FLAG
- deployed: CORTEX_DB.CORTEX_SCHEMA.RENEWAL_RADAR

### deviations

- runs 01-04: session start gate skipped in all sessions (run 05: invoked after mid-plan intervention)
- runs 02-05: scan and deploy ran as direct bash commands, not via skill invocation
- runs 02-04: `session.sql(f` parameterization check from build-dashboard skill never executed
- run 03: SQL injection in INSERT (flag_reason) and UPDATE (review_notes) found post-deploy
- run 03: FILTER_CHANGE audit logging absent despite AGENTS.md requirement
- run 04: scope_parts.append bug introduced during display-label refactoring; stale scope values corrected via UPDATE
- run 04: file placement in wrong directory; snowflake.yml format required correction

---

## phase 3: verification

### runs

| run | date | outcome | key issue |
|---|---|---|---|
| 01 | 2026-03-01 | partial | 5 checks passed on stale/misleading data; ccc_report.md contained false security claims |
| 02 | 2026-03-02 | complete | 16/16 passed; gate invoked automatically (first time in project); security scan passed |

### acceptance results (run 02 - all 16 criteria)

phase 1 (infrastructure):

| # | criterion | expected | actual | result |
|---|---|---|---|---|
| 1 | RENEWAL_FLAGS exists | 1 | 1 | pass |
| 2 | FACT_RENEWAL rows | ~50,000 | 50,000 | pass |
| 3 | FACT_PREMIUM_EVENT rows | ~94,000 | 94,642 | pass |
| 4 | DIM_POLICY rows | ~36,000 | 36,298 | pass |
| 5 | APP_EVENTS and AUDIT_LOG exist | 2 | 2 | pass |
| 6 | V_APP_EVENTS exists | 1 | 1 | pass |
| 7 | LOG_AUDIT_EVENT exists | 1 row | 1 row | pass |
| 8 | agent operations logged | >= 1 | 2 | pass |

phase 2 (deployment):

| # | criterion | expected | actual | result |
|---|---|---|---|---|
| 9 | app deployed | present | RENEWAL_RADAR present | pass |
| 10 | python syntax valid | exit code 0 | 0 | pass |
| 11 | app renders with data | confirmed | confirmed | pass |

phase 3 (write-back):

| # | criterion | expected | actual | result |
|---|---|---|---|---|
| 12 | FILTER_CHANGE events (last hour) | >= 1 | 6 | pass |
| 13 | flags with status=OPEN | >= 1 | 5 | pass |
| 14 | FLAG_ADDED events | >= 1 | 7 | pass |
| 15 | flags status=REVIEWED, reviewed_by not null | >= 1 | 7 | pass |
| 16 | FLAG_REVIEWED events | >= 1 | 5 | pass |

### deviations

- run 01: session gate not invoked (no gate instruction in prompt 4 text at that time)
- run 01: FILTER_CHANGE check passed on 30 stale events from a prior dashboard version; current code had 0 occurrences
- run 01: ccc_report.md contained false claims ("parameterized sql", "no issues found", wrong criterion names)
- run 02: all 16 checks ran as direct SNOWFLAKE_SQL_EXECUTE (deploy-and-verify SKILL.md read but mechanism bypassed)
- run 02: session gate not invoked for prompt 5 (gate instruction not in prompt 5 text)

---

sources: archive/phase_01_run_02.md, archive/phase_02_run_05.md, archive/phase_03_run_02.md

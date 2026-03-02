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

took three attempts to get a clean phase 1. the first had skill bypasses and manual checks;
an intermediate session was stopped mid-DDL after wrong syntax; run 02 was the clean one.

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

in run 01, the session gate was skipped in the prompt 2 session, `$ prepare-data` was
bypassed on the first attempt (agent ran PUT/COPY INTO directly), and acceptance checks
ran as direct SQL. run 01.5 was stopped after the agent used `CREATE OR REPLACE TABLE`
instead of `CREATE OR ALTER TABLE` - a DDL rule violation that would have dropped existing
data on re-run. run 02 had two minor friction points: sub-skill path resolution failed
(agent recovered via GLOB), and the agent asked a phase selection question despite the
phase being explicit in the prompt.

---

## phase 2: dashboard build and deploy

phase 2 had the most churn - five runs across two days. the critical issue (SQL injection in
INSERT and UPDATE) was introduced in run 03 and not caught until an independent code review
after run 04. run 05 was the first deploy that landed on the first attempt.

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

the session gate was skipped across all phase 2 sessions - run 05 being the exception, though
even there it only ran after a mid-plan intervention. scan and deploy consistently ran as
direct bash commands across all runs; that's why the `session.sql(f` parameterization check
from build-dashboard was never executed in any of the five pre-deploy scans. SQL injection
(flag_reason in INSERT, review_notes in UPDATE) was introduced in run 03 and survived through
run 04 undetected. run 04 also had a logic bug in scope_parts.append during the display-label
work, plus initial file placement and snowflake.yml format issues that added deploy cycles.

---

## phase 3: verification

two runs. the first passed numerically but on misleading data - the FILTER_CHANGE check
counted 30 stale events from a prior dashboard version, and the generated acceptance report
had false claims. run 02 was the first clean verification in the project, and the first time
the session gate ran automatically without being reminded.

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

run 01's main problem was the FILTER_CHANGE check: it passed on 30 stale events from an older
dashboard version while the current code had zero occurrences. the generated report
(ccc_report.md) made things worse by claiming parameterized SQL and no remaining issues -
both wrong. run 02 was mostly clean: 16/16 on genuine data. the deploy-and-verify skill
was still bypassed (checks ran as direct SNOWFLAKE_SQL_EXECUTE), and prompt 5 didn't include
the gate instruction so the gate didn't run for the security scan.

---

detailed session logs in archive/.

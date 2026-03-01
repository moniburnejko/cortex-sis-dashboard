# adr-001: ddl idempotency

**date:** 2026-03-01
**source:** phase_01_run_01.md, AGENTS.md DDL rule

## problem

the default agent instruction used `CREATE OR REPLACE TABLE`: this syntax drops and recreates the table from scratch on every re-run. if phase 1 needs to be re-executed (e.g. after a ddl fix), all existing data would be destroyed. the project requires the ability to safely re-run phase 1 without data loss.

## decision

use `CREATE OR ALTER TABLE`: an idempotent snowflake syntax that modifies the schema of an existing table without dropping it. safe for re-runs of phase 1. exception: views use `CREATE OR REPLACE VIEW` (safe, views store no data).

## alternatives considered

- **CREATE TABLE IF NOT EXISTS**: idempotent with respect to existence, but does not modify the schema if the table already exists with different columns. rejected: does not cover schema changes.
- **CREATE OR REPLACE TABLE**: drops and recreates the table. rejected: data loss on every re-run.
- **ALTER TABLE + IF NOT EXISTS guard**: possible, but requires separate logic per column. rejected: too verbose.

## consequences

- safe ddl when phase 1 is executed multiple times
- `CREATE OR ALTER` is snowflake-specific syntax. does not work in other databases (PostgreSQL, MySQL, etc.)
- views require an exception: `CREATE OR REPLACE VIEW` remains correct and safe
- rule encoded in AGENTS.md as a ddl rule; build-dashboard/SKILL.md scans for `OR REPLACE TABLE` as a bug pattern

## related

- AGENTS.md: DDL rules section
- `.cortex/skills/sis-streamlit/skills/build-dashboard/SKILL.md`: scan mode step 2

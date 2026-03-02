# lessons learned: renewal radar sis dashboard

## skill compliance: cross-phase

| skill | phase 1 | phase 2 | phase 3 | pattern |
|---|---|---|---|---|
| `$ check-local-environment` | pass (run 02) | fail runs 01-04; late run 05 | pass prompt 4 only | invoked only when explicit in prompt text |
| `$ check-snowflake-context` | pass (run 02) | fail runs 01-04; late run 05 | pass prompt 4 only | same as above |
| `$ prepare-data` | bypassed run 01; pass run 02 | n/a | n/a | bypassed when prompt did not name skill explicitly |
| `$ sis-streamlit` | n/a | pass (invoked) | n/a | invoked when named in prompt |
| `$ sis-streamlit` -> build-dashboard (scan) | n/a | partial all runs (SKILL.md read; scan as direct bash) | partial | content followed; mechanism bypassed |
| `$ sis-streamlit` -> deploy-and-verify | partial run 02 (with friction) | partial (SKILL.md read; deploy as direct bash) | partial | same bypass pattern |

consequence of build-dashboard bypass: `session.sql(f` parameterization check never executed in any of 5 phase 2 pre-deploy scans. SQL injection was only detected by independent code review.

---

## deviations by category

### session start gate - 5x skipped across project

pattern: agent treated memory validation or prior context knowledge as equivalent to mandatory skill invocation.

occurrences:
1. phase_01_run_01: prompt 2 session - both gate skills skipped
2. phase_02_run_02 through run_04: gate skipped in all 3 sessions (4 deploy cycles)
3. phase_02_run_05: gate skipped on first attempt; invoked after mid-plan intervention
4. phase_03_run_01: gate not invoked (no gate instruction in prompt 4 text)
5. phase_03_run_02 prompt 5: gate not invoked (gate instruction not in prompt 5 text)

what fixed it: adding explicit "invoke $ check-local-environment, then $ check-snowflake-context. do not proceed until both pass." to the prompt text. prompt 4 in phase_03_run_02 was the first prompt to include this instruction; gate ran automatically without intervention.

governance response: adr-012, adr-013; gate instruction added to all prompts 1-4 in prompts.md.

### skill bypass - all phases

pattern: agent reads SKILL.md content then executes steps as direct bash/SQL commands rather than through skill invocation. this is the fundamental mechanism limitation.

affected skills and consequences:
- `$ prepare-data` bypassed (phase_01_run_01): gzip skipped on first attempt; manual PUT/COPY INTO
- `$ sis-streamlit` -> build-dashboard scan bypassed (all phase 2 runs): `session.sql(f` check never executed; SQL injection not caught
- `$ sis-streamlit` -> deploy-and-verify bypassed (all phase 2 runs): deploy as direct `snow streamlit deploy --replace`
- `$ sis-dashboard` -> deploy-and-verify bypassed (phase_03_run_01): acceptance checks as direct SNOWFLAKE_SQL_EXECUTE

mitigation: naming the skill explicitly in the prompt forces invocation. AGENTS.md mandates alone are insufficient.

### sql injection - found by code review, not agent scans

source: phase_02_run_03 introduced f-string INSERT and UPDATE with user text input. ran through 5 pre-deploy scans in runs 03 and 04 without detection.

root cause: build-dashboard scan mode includes a `session.sql(f ... INSERT|UPDATE` pattern check. this check was never executed in any scan (skill bypass pattern above). agent ran its own subset of grep patterns and consistently skipped the DML injection check.

detection: independent code review after phase_02_run_04 (code_review_dashboard.md).

fix: INSERT_RENEWAL_FLAG and UPDATE_RENEWAL_FLAG stored procedures created in phase_02_run_05; all DML now via session.call().

governance response: adr-007, adr-008 (secure-dml skill); security rule 3 in AGENTS.md expanded; DML injection check added to build-dashboard scan mode.

### deployment cycles - snowflake.yml and file placement

phase_02_run_02 required multiple deploy cycles due to:
- dashboard.py initially placed in wrong subdirectory
- snowflake.yml `main_file` path format error

pattern: agent did not read the existing snowflake.yml before generating a new one. file placement errors are recoverable (move file, redeploy) but add cycles.

phase_02_run_05 deployed on first attempt - only run to do so. context: scope was targeted edits to existing file, not a full rebuild.

---

## governance changes made

| problem | adr | change |
|---|---|---|
| agent ran manual context commands after gate skills | adr-001 | AGENTS.md skill constraints: added "do NOT run X manually after skill completes" |
| acceptance checks run manually instead of via skill | adr-004 | prompts updated to explicitly name `$ sis-dashboard` |
| session start gate consistently skipped | adr-005 | gate instruction added to all prompts in prompts.md |
| whitelist filter values in f-string sql | adr-006 | security rule 3 documents accepted exception; snowpark api preferred |
| dml with user text input not parameterized | adr-007 | security rule 3 expanded to cover INSERT/UPDATE; session.call() required |
| no skill for secure dml patterns | adr-008 | secure-dml sub-skill created under sis-streamlit |
| FILTER_CHANGE callbacks missing | adr-009 | AGENTS.md page specs updated; FILTER_CHANGE added to build-dashboard scan |
| agent tried `$ sis-streamlit -> deploy-and-verify` as literal command | adr-010 | routing notation clarified in AGENTS.md |
| module-level session vs sis-patterns contradiction | adr-011 | sis-patterns updated: module-level acceptable for non-cached code; cached functions must call get_active_session() inside |
| prompt text drives compliance more than AGENTS.md mandates | adr-012 | gate instruction added as explicit text to every prompt; verified in phase_03_run_02 |
| hooks-based gate enforcement | adr-013 | hooks.json added; pre-session gate check via .cortex/hooks.json |

---

sources: deviations and skill compliance sections from all archive/ reports

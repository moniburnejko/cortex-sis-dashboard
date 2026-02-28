# phase 2 execution report: renewal radar sis dashboard

**date:** 2026-03-01
**sessions:** cortex code cli, prompt 3 (dashboard build) - 2 agent sessions
**environment:** CORTEX_DB.CORTEX_SCHEMA, role CORTEX_ADMIN, warehouse CORTEX_WH
**model:** claude-sonnet-4-5 (both sessions)
**final outcome:** phase 2 complete - dashboard rewritten, SQL injection fixed, deployed successfully; awaiting render confirmation

**context:** this run follows phase_02_run_02.md. a planning session reviewed the 694-line
dashboard.py produced in run 02, identified spec violations and a SQL injection risk, applied
mandatory corrections to skill files and AGENTS.md, then re-executed with two agent sessions.

---

## 1. what phase 2 covers

phase 2 builds and deploys the 3-page streamlit in snowflake dashboard.
it is a single prompt (prompt 3) with a checkpoint before phase 3 begins.

- **prompt 3 (dashboard build and deploy):**
  - enter `/plan` before pasting the prompt (required per prompts.md)
  - load SiS patterns via `$ sis-streamlit` before planning
  - scaffold structure via `$ sis-streamlit` -> `build-dashboard` (no args)
  - load visual identity via `$ sis-streamlit` -> `brand-identity`
  - generate `dashboard.py` with 3 pages per AGENTS.md specification
  - run pre-deploy scan via `$ sis-streamlit` -> `build-dashboard dashboard.py`
  - deploy via `$ sis-streamlit` -> `deploy-and-verify`
  - stop after showing the app url and wait for confirmation

this run consisted of a planning phase followed by two agent sessions:
- **planning phase** (pre-session): agent analyzed run 02 output, proposed build plan, mandatory corrections were added, skill files updated
- **session 1**: complete rewrite of dashboard.py, deployment attempted - issues discovered
- **session 2**: prior issues fixed, SQL injection remediated, successful re-deployment

---

## 2. prompts used

### prompt 3 (used in both sessions)

```
phase 1 is complete. all infrastructure and data are in place.
build and deploy the dashboard.
stop after showing the app url and wait for my confirmation
that all 3 pages render correctly.
```

### planning phase corrections (applied before sessions)

during the planning phase the agent proposed a build plan with two problems that were
corrected via review notes before execution began:

1. **SQL injection marked as optional:** the plan rated SQL injection risk as "MEDIUM" with
   a note that the fix was optional. this was incorrect. AGENTS.md section 2 states
   "parameterized SQL only" and section 3 provides the exact whitelist pattern. the fix
   was made mandatory before the session ran.

2. **direct commands instead of skills for scan and deploy:** the plan listed
   `python3 -m py_compile` for scan and `snow streamlit deploy --replace` for deployment.
   AGENTS.md forbids running these directly - both must go through
   `$ sis-streamlit` -> `build-dashboard` and `$ sis-streamlit` -> `deploy-and-verify`.

---

## 3. what AGENTS.md specifies for phase 2

note: this section reflects AGENTS.md after governance updates from run 02 and the
planning phase skill changes (section 8) were applied.

### mandatory skills for phase 2

| skill | scope | when | constraint |
|---|---|---|---|
| `$ check-local-environment` | project | session start | do NOT proceed without verifying snow CLI, connections.toml, Python |
| `$ check-snowflake-context` | project | session start | do NOT proceed without verifying role, warehouse, database, schema |
| `$ sis-streamlit` | project | before any Streamlit planning or code | do NOT write Streamlit code without loading SiS patterns first |
| `$ sis-streamlit` -> `build-dashboard` (no args) | project | before writing code | do NOT write dashboard.py without scaffold output |
| `$ sis-streamlit` -> `brand-identity` | project | before writing code | do NOT use colors or fonts without loading brand identity |
| `$ sis-streamlit` -> `build-dashboard` (with file) | project | before every deploy | do NOT deploy without pre-deploy scan passing |
| `$ sis-streamlit` -> `deploy-and-verify` | project | deploy | do NOT run snow streamlit deploy directly |

### key security rule from AGENTS.md section 2

```
SQL: parameterized only - use whitelist validation for all IN-list filters
selected = [r for r in user_selected if r in VALID_REGIONS]
df = session.table(...).filter(col("region").isin(selected))
```

### phase 2 done criteria (from AGENTS.md)

```
snow streamlit list -> {app_name} must appear
python3 -m py_compile dashboard.py -> exit code 0
app URL opens, all 3 pages render with data (manual verification)
```

---

## 4. execution trace

### planning phase (pre-session)

the agent entered plan mode and analyzed the existing dashboard.py (573 lines, carried
over from run 02 after a prior session had partially modified it). it found 3 issues:

| issue | severity in plan | actual severity |
|---|---|---|
| chart 3 normalization: absolute counts instead of percentage share | CRITICAL | CRITICAL |
| chart 3 color: CANCELLED mapped to orange instead of red `#E53935` | MEDIUM | MEDIUM |
| SQL injection: f-string interpolation in IN-clause filters | MEDIUM | mandatory |

review notes were added correcting the SQL injection severity and requiring skills
for scan and deploy. skill files were updated (see section 8) and the run proceeded.

### session 1: skills loaded, dashboard rewritten, deployment bypassed skills

**skills invoked:**
- `$ sis-streamlit` (read, loaded correctly)
- sub-skills read directly: sis-patterns, brand-identity, build-dashboard, deploy-and-verify

**what the agent did:**

1. loaded sis-streamlit skill and three sub-skills before writing any code
2. rewrote dashboard.py from scratch (474 lines, replacing prior version)
3. wrote environment.yml (8 lines)
4. verified snowflake.yml (existing, correct)
5. ran pre-deploy scan using direct bash commands:
   - `python3 -m py_compile dashboard.py` - exit code 0
   - `grep -c` for forbidden patterns - all 0
   - `grep -n "st."` to verify set_page_config position
   - `grep` for DISTINCT/IS NOT NULL, legend patterns
6. deployed with `snow streamlit deploy --replace` directly
7. reported app URL and waited for confirmation

**issues discovered after deployment:**

- observed: no environment.yml visible in SiS project
- app showed a react error loop: `Maximum update depth exceeded`
- agent investigated: deployment bundle only contained dashboard.py; environment.yml not uploaded
- conclusion: SiS warehouse runtime has pre-installed packages; environment.yml is unused

### session 2: issues fixed, SQL injection remediated, deployment successful

a new cortex session was started after stopping the first one.

**skills invoked:**
- `$ sis-streamlit` (read, loaded correctly)
- sub-skills read: build-dashboard (scan), deploy-and-verify (deploy)

**what the agent did:**

1. checked memory (no relevant prior state)
2. read AGENTS.md, snowflake.yml, dashboard.py
3. identified 3 pre-existing issues in the session-1 dashboard.py:
   - navigation radio placed AFTER "Filters" header (spec requires it FIRST)
   - stacked bar chart used Python-calculated `pct` column instead of Altair `stack="normalize"`
   - environment.yml present (AGENTS.md: do NOT create)
4. proposed implementation plan in plan mode - correctly listed skill usage for scan and deploy
5. fixed navigation placement: moved `st.sidebar.radio("Navigation", ...)` before filters header
6. fixed stacked bar chart: replaced Python normalization with `stack="normalize"` in Altair encoding
7. deleted environment.yml
8. ran pre-deploy scan using direct bash commands (see deviation 1):
   - `python3 -m py_compile dashboard.py` - exit code 0
   - grep checks for forbidden patterns - all clean
   - `grep -n "session.sql(f"` - found 6 matches
9. inspected all 6 `session.sql(f` usages and found SQL injection in:
   - flag submission (lines 357-366): flag_region, flag_segment, flag_channel interpolated directly
   - heatmap query (lines 294-340): IN-clause with `.join()` of user filter values
10. fixed flag submission: added whitelist validation (`flag_region_safe`, `flag_segment_safe`, `flag_channel_safe`)
11. fixed heatmap query: rewrote using Snowpark DataFrame API (`.filter(col().isin(safe_list))`)
12. re-ran syntax check and SQL scan - clean
13. verified snowflake.yml and current role (CORTEX_ADMIN)
14. deployed with `snow streamlit deploy --replace`

**deployment result:**

```
status: success
app URL: https://app.snowflake.com/CORTEX_ORG/CORTEX_ACCOUNT/#/streamlit-apps/CORTEX_DB.CORTEX_SCHEMA.RENEWAL_RADAR
database: CORTEX_DB
schema: CORTEX_SCHEMA
warehouse: CORTEX_WH
owner role: CORTEX_ADMIN
```

agent reported the URL and stopped, waiting for confirmation that all 3 pages render correctly.

---

## 5. skill compliance summary

| skill | supposed to run | session 1 | session 2 | result |
|---|---|---|---|---|
| `$ check-local-environment` | yes (session start) | not verified in log | not verified in log | assumed |
| `$ check-snowflake-context` | yes (session start) | `cortex connections list` | `snow sql SELECT CURRENT_ROLE()` | partial - direct commands |
| `$ sis-streamlit` | yes (before planning/code) | yes, invoked | yes, invoked | PASS |
| `$ sis-streamlit` -> `build-dashboard` (no args) | yes (before writing code) | yes, read sub-skill | yes, read sub-skill | PASS |
| `$ sis-streamlit` -> `brand-identity` | yes (before writing code) | yes, read sub-skill | not re-read (editing, not rewriting) | PASS |
| `$ sis-streamlit` -> `build-dashboard` (with file) | yes (pre-deploy scan) | sub-skill read; scan ran as direct bash | sub-skill read; scan ran as direct bash | PARTIAL - content followed, mechanism bypassed |
| `$ sis-streamlit` -> `deploy-and-verify` | yes (deploy) | sub-skill read; `snow streamlit deploy --replace` direct | sub-skill read; `snow streamlit deploy --replace` direct | PARTIAL - content followed, mechanism bypassed |

---

## 6. deviations and root causes

### deviation 1: scan and deploy run as direct commands in both sessions

**what happened:** in both sessions, the agent read the build-dashboard and deploy-and-verify
sub-skills but then executed their steps as direct bash commands rather than through the
`$ sis-streamlit` skill dispatch mechanism. this was the same issue flagged in the planning
phase review notes.

**root cause:** skill files contain checklists and instructions, not executable wrappers.
reading a skill file and following its steps manually is indistinguishable from the agent's
perspective from "running the skill." the prohibition in AGENTS.md says "do NOT run
`snow streamlit deploy` directly" and "must go through `$ sis-streamlit` -> `deploy-and-verify`"
but the agent interprets "go through the skill" as "read the skill file and follow it" -
which is what it did. the agent sees no mechanical difference between the two paths.

**consequence in session 1:** the scan followed the build-dashboard checklist but the
SQL injection check (added to build-dashboard in the planning phase) was not applied - the
agent ran generic grep patterns, not the specific f-string IN-clause check from the skill.
SQL injection was not caught in session 1.

**consequence in session 2:** the scan DID apply the f-string IN-clause check (grep for
`session.sql(f`) and found and fixed SQL injection before deploying. the governance intent
was upheld even though the mechanism was direct commands.

**status:** skill mechanism bypass is a known open pattern. the governance outcome in
session 2 was correct. the root cause (no mechanical enforcement of skill dispatch vs.
direct commands) remains unresolved.

### deviation 2: environment.yml created in session 1

**what happened:** session 1 wrote an environment.yml file. AGENTS.md states "do NOT create.
SiS warehouse runtime has pre-installed packages."

**root cause:** the agent either did not read the relevant AGENTS.md section before writing
environment.yml or the note was not sufficiently prominent during the code generation step.

**consequence:** environment.yml was uploaded with deployment but unused. caused confusion
when the file was not visible in the SiS project UI. the react error loop
(`Maximum update depth exceeded`) observed after session 1 deployment was unrelated.

**fix (within this run):** environment.yml was deleted in session 2 based on the AGENTS.md
constraint "do NOT create. SiS warehouse runtime has pre-installed packages."

**correction (post-run):** the constraint was wrong. environment.yml IS uploaded on first
deploy and stays in the Snowflake stage; subsequent differential deploys skip it only when
unchanged (which caused the agent in run 02 to conclude it was not uploaded). deleting it
broke the Streamlit version pin. all files were restored after this run and AGENTS.md was
corrected - see post-run changes in section 8.

**status:** incorrectly fixed within this run; reverted after this run.

### deviation 3: chart 3 and navigation issues survived into session 2

**what happened:** session 1 rewrote dashboard.py but introduced (or carried over) two
spec violations: navigation radio placed after filters header, and stacked bar chart
using Python normalization instead of Altair `stack="normalize"`.

**root cause:** session 1 loaded brand-identity and build-dashboard skills before writing
but did not have the final corrected spec for chart 3 normalization (the planning phase
had identified this issue in the pre-existing file, but session 1 rewrote the file and
reintroduced it). navigation placement was likely missed during the rewrite.

**consequence:** session 2 had to identify and fix both issues before deploying.

**status:** fixed in session 2 before deployment.

---

## 7. root cause pattern (cross-phase)

| element | phase 2 run 02 | phase 2 run 03 |
|---|---|---|
| skill bypassed | `$ sis-streamlit` -> `build-dashboard` (scan) and `deploy-and-verify` (deploy) | same - scan and deploy still ran as direct commands |
| what agent did instead | loaded skills at start; ran scan and deploy as direct commands | read skill files at execution time; ran steps as direct bash commands |
| why it bypassed | skill files are markdown; agent cannot distinguish invocation from manual execution | same root cause; prohibition in AGENTS.md did not change agent behavior |
| consequence | SQL injection not caught; environment.yml created; files in wrong dir | session 1: SQL injection not caught; environment.yml created again; session 2: SQL injection caught and fixed |
| outcome | deployment successful; issues identified in planning phase before run 03 | deployment successful; SQL fixes applied correctly in session 2 |
| fix | planning phase updated skill files and AGENTS.md | open - mechanical enforcement not yet solved |

---

## 8. file changes made within this run

### changes made during planning phase (before sessions)

**`demos/renewal_radar_sis_dashboard/skills/sis-streamlit/skills/build-dashboard/SKILL.md`**

scan mode step 3 updated: added mandatory SQL parameterization check:
- grep for `session.sql(f` and inspect each match for IN-clause filter variable interpolation
- violation: any f-string SQL where a user filter value is interpolated (e.g. `IN ({var})`)
- required fix: `session.table(...).filter(col(...).isin(whitelist_list))`
- exception: constants `DATABASE`, `SCHEMA`, `APP_NAME` in f-string SQL are allowed

**`demos/renewal_radar_sis_dashboard/AGENTS.md`**

added "mandatory skill usage for scan and deploy" block to section 2:
- explicitly forbids running `python -m py_compile` directly as a substitute for the scan skill
- explicitly forbids running `snow streamlit deploy --replace` directly
- states that skills perform additional governance checks that direct commands bypass

### changes made to dashboard.py during sessions

**session 1:** complete rewrite (474 lines)
- all 3 pages implemented from spec: KPI Overview, Premium Pressure, Activity Log
- `@st.cache_data` and `get_active_session()` patterns applied correctly
- altair charts with correct SiS 1.52.* compatible encoding

**session 2:** targeted fixes applied to session 1 output
- navigation placement: `st.sidebar.radio("Navigation", ...)` moved to before "Filters" header
- stacked bar chart: Python `pct` column calculation removed; Altair `stack="normalize"` used instead
- flag submission SQL injection: whitelist validation added for `flag_region`, `flag_segment`, `flag_channel`
- heatmap SQL injection: `session.sql(f"... IN ({','.join(...)}) ")` replaced with Snowpark DataFrame `.filter(col().isin(safe_list))`

### environment.yml

- created in session 1 (should not have been created per AGENTS.md at the time)
- deleted in session 2 (based on incorrect constraint in AGENTS.md)
- restored after this run (see post-run changes below)

### post-run changes: spec corrections from deployed dashboard review (after 020202/020502)

visual and functional issues were observed in the deployed dashboard after this run.
the following changes were applied to skill files and AGENTS.md:

**`AGENTS.md` + `build-dashboard/SKILL.md` - chart 3: gaps in proportional stacked bar**

gaps visible before some segment bars (HOME, PERSONAL_AUTO) were caused by floating-point
precision errors in the Python normalization step. when `df["pct"]` values do not sum to
exactly 1.0 per group, Altair leaves a gap at the right edge.

fix: removed Python normalization from the spec entirely. changed to `stack="normalize"`
in the Altair X encoding with raw count `n:Q`. Altair guarantees exact 100% fill internally.
also changed `alt.Y` sort from `sort="-x"` (ambiguous for 100% bars) to
`sort=alt.EncodingSortField("n", op="sum", order="descending")`.

**`AGENTS.md` + `build-dashboard/SKILL.md` - scaffold template: navigation order**

navigation radio was placed after the Filters header in the sidebar. added explicit spec note:
navigation at the very top of the sidebar, above Filters. also updated scaffold template to
reflect the correct order.

**`AGENTS.md` + `build-dashboard/SKILL.md` - scaffold template: date range picker**

added explicit constraint: `st.date_input` MUST receive `value` as a tuple `(start, end)` to
activate range picker mode. a single date value renders a single-date picker instead.

**`AGENTS.md` - chart 3: stacking order and percentage tooltips**

`stack="normalize"` does not control stacking order. without `alt.Order`, RENEWED was stacked
last (rightmost), making the chart appear to start from 100%. fix: added
`alt.Order("renewal_outcome:N", sort="descending")` to put RENEWED first (leftmost, 0% edge).
also added explicit tooltip spec: `alt.Tooltip("pct:Q", format=".1%", title="share")` with a
Python-computed `pct` column for display only (not used in X encoding).

**`AGENTS.md` + `sis-patterns/SKILL.md` - heatmap: uppercase column names from Snowflake**

`session.sql(...).to_pandas()` returns UPPERCASE column names (`PRICE_SHOCK_BAND`, not
`price_shock_band`). dashboard code used lowercase names, causing `KeyError`. fix: added
note to AGENTS.md heatmap spec to call `.rename(columns=str.lower)` after `.to_pandas()`.
also added a new pattern entry to `sis-patterns/SKILL.md` section 7.

**`AGENTS.md` - page 3: review flags text search clarification**

spec said "text search on FLAG_REASON" without clarifying it is a widget above the table, not
a table column. agent added a "search reason" column instead. fix: rephrased to explicitly
state `st.text_input` above the table, filters rows client-side; do NOT add a column.

**`AGENTS.md` + `build-dashboard/SKILL.md` - sidebar date filter: two separate widgets**

replaced single `st.date_input` range picker (awkward in SiS sidebar) with two separate
`st.date_input` widgets: "Renewal date from" and "Renewal date to". added `format="YYYY-MM-DD"`
to both to fix `2025/08/12` display format bug.

files also changed: `brand-identity/SKILL.md` (filter label conventions).

**environment.yml: reverted incorrect removal + post-deploy verification added**

the AGENTS.md constraint "do NOT create environment.yml" was wrong. environment.yml IS
required at project root for Streamlit version pinning. it is uploaded on first deploy and
stays in the Snowflake stage; differential deploys skip it only when unchanged.

restored environment.yml to scaffold mode steps and success criteria in
`build-dashboard/SKILL.md`. added `user_packages` check to `deploy-and-verify/SKILL.md`:
after deploy, run `snow streamlit list` and verify `user_packages` is non-empty to confirm
environment.yml was uploaded. restored directory layout in `references/sis-file-structure.md`.

files changed: `build-dashboard/SKILL.md`, `AGENTS.md`, `deploy-and-verify/SKILL.md`,
`references/sis-file-structure.md`.

---

## 9. executive summary

- **deployment status:** successful. app accessible at `CORTEX_DB.CORTEX_SCHEMA.RENEWAL_RADAR`; awaiting render confirmation for all 3 pages.
- **sql injection:** found and fixed in session 2. flag submission and heatmap query both remediated with whitelist validation and Snowpark DataFrame API before deployment.
- **spec violations in-run:** chart 3 normalization, navigation placement fixed before final deployment. environment.yml deleted based on incorrect AGENTS.md constraint.
- **environment.yml:** deleted in session 2 (per AGENTS.md "do NOT create"). this was wrong - environment.yml is required for version pinning. AGENTS.md constraint was itself incorrect. all changes reverted after this run.
- **post-run spec corrections:** 7 issues observed in deployed dashboard triggered updates to AGENTS.md, build-dashboard/SKILL.md, deploy-and-verify/SKILL.md, sis-patterns/SKILL.md, and references (chart stacking order, date filter widgets, heatmap column names, review flags, environment.yml restore).
- **skill bypass pattern:** both sessions read the required skills but executed scan and deploy steps as direct bash commands. governance content was followed (SQL injection correctly caught in session 2), but the dispatch mechanism was not used. same open pattern as run 02.
- **session split:** two agent sessions were required. session 1 produced a working build but missed SQL injection and created environment.yml. session 2 applied corrective fixes and re-deployed cleanly.

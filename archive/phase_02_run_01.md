# phase 2 execution report: renewal radar sis dashboard

**date:** 2026-02-28
**session:** cortex code cli, prompt 3 (dashboard build)
**environment:** CORTEX_DB.CORTEX_SCHEMA, role CORTEX_ADMIN, warehouse CORTEX_WH
**final outcome:** phase 2 interrupted - developing-with-streamlit skill skipped at planning stage; session redirected to governance improvements

---

## 1. what phase 2 covers

phase 2 builds and deploys the 3-page streamlit in snowflake dashboard.
it is a single prompt (prompt 3) with a checkpoint before phase 3 begins.

- prompt 3 (dashboard build and deploy):
  - enter `/plan` before pasting the prompt (required per prompts.md)
  - load sis patterns via `$ developing-with-streamlit` before planning
  - scaffold structure via `$ build-dashboard` (no args)
  - load visual identity via `$ brand-identity`
  - generate `streamlit/dashboard.py` with 3 pages per AGENTS.md specification
  - run pre-deploy scan via `$ build-dashboard streamlit/dashboard.py`
  - deploy via `$ deploy-and-verify phase-2`
  - stop after showing the app url and wait for confirmation

---

## 2. prompts used

### prompt 3

```
phase 1 is complete. all infrastructure and data are in place.
build and deploy the dashboard.
stop after showing the app url and wait for my confirmation
that all 3 pages render correctly.
```

### correction (after skill bypass detected)

i asked the agent whether it had checked the global skills as written in agents.md and the project skills, noting that the plan did not include the expected guidelines. the agent acknowledged it had not invoked the skill but had seen the reference to it in agents.md.

---

## 3. what AGENTS.md specifies for phase 2

note: this section reflects AGENTS.md as it existed at the start of phase 2 (after phase 1 changes
were applied). changes made in response to phase 2 are documented in section 8.

### mandatory skills for phase 2

| skill | when | note |
|---|---|---|
| `$ check-local-environment` | session start | verify snow cli, connections.toml, python |
| `$ check-snowflake-context` | session start | verify role, warehouse, database, schema |
| `$ developing-with-streamlit` | before any streamlit code (1st) | global skill; load sis warehouse runtime constraints before planning |
| `$ build-dashboard` (no args) | before writing code | scaffold: discover pages, return constraints |
| `$ brand-identity` | before any streamlit code (after build-dashboard) | load visual identity |
| `$ build-dashboard` (with file) | before every deploy | pre-deploy scan: forbidden apis, import errors |
| `$ deploy-and-verify phase-2` | after phase 2 | acceptance checks + app url |

### phase 2 done criteria (from AGENTS.md)

```
snow streamlit list -> {app_name} must appear
python3 -m py_compile streamlit/dashboard.py -> exit code 0
app URL opens, all 3 pages render with data (manual verification)
```

---

## 4. execution trace: prompt 3

### skills supposed to run (in order)

see section 3, mandatory skills table. skill sequence matches the table row order.

### skills actually used

1. `$ build-dashboard` (no args) - invoked to read constraints
2. `$ brand-identity` - invoked to read brand colors and styling

### what the agent did

the agent entered `/plan` mode per prompts.md and began planning the dashboard build.
it read AGENTS.md, build-dashboard, and brand-identity skills directly but did NOT invoke the global `$ developing-with-streamlit` skill before creating the plan.

the agent did read the build-dashboard and deploy-and-verify skills. it created a detailed plan that included:
- 9-block scaffold structure for streamlit/dashboard.py
- 3-page layout: kpi overview, premium pressure, activity log
- correct use of `@st.cache_data`, `get_active_session()`, and altair charts for sis 1.52.*
- appropriate pre-deploy and deploy steps

after reviewing the plan, i asked whether the agent had checked the global developing-with-streamlit skill as well.

the agent acknowledged the error, explaining that it had seen the reference in AGENTS.md but did not proactively read the global developing-with-streamlit skill to understand what patterns it provides by default. this was a process error: the agent should have read the global skill first to understand the defaults, then applied project-specific overrides.

the session was interrupted when the skill bypass was detected. phase 2 was not completed and governance improvements were prioritized instead.

---

## 5. skill compliance summary

| skill | supposed to run | actually invoked | result |
|---|---|---|---|
| `$ check-local-environment` | yes (session start) | yes (assumed) | assumed passed - not verified in session log |
| `$ check-snowflake-context` | yes (session start) | yes (assumed) | assumed passed - not verified in session log |
| `$ developing-with-streamlit` | yes (before planning) | no | agent planned without proactively reading global sis patterns |
| `$ build-dashboard` (no args) | yes (before writing code) | yes | read for scaffold and constraints |
| `$ brand-identity` | yes (before writing code) | yes | read for colors and styling |
| `$ build-dashboard` (with file) | yes (pre-deploy) | no (phase not reached) | phase interrupted before deploy |
| `$ deploy-and-verify phase-2` | yes (after phase) | no (phase interrupted) | not reached |

---

## 6. deviations and root causes

### deviation 1: developing-with-streamlit skipped before planning

what happened: the agent entered `/plan` mode and created a plan for the dashboard build
without invoking `$ developing-with-streamlit` first. the plan proceeded from the dashboard
specification in AGENTS.md directly, without loading sis warehouse runtime constraints.

root cause: the mandatory skills block at the time of phase 2 told the agent what skills
to run, but the `developing-with-streamlit` entry was located in the global skills section
(described as an override), not in a procedural gate before planning begins. the agent
saw "before any streamlit code" as a trigger tied to code generation, not to the planning step.
additionally, the global skill description was not co-located with a prohibition - there was
nothing saying "do NOT plan streamlit code without loading this skill first."

see section 7 for cross-phase comparison.

consequence: despite the agent eventually reading build-dashboard and brand-identity skills,
it did not proactively read the global developing-with-streamlit skill to understand the baseline
sis warehouse runtime patterns. this is different from missing constraints - the plan itself was
correct. the issue is methodological: the agent should have started with the global skill to understand
what patterns the project overrides, rather than jumping directly to project skills.

assessment (post-session): the global developing-with-streamlit skill is never needed if
a local demo-level skill is present with the correct frontmatter description. the fix is
not to force the agent to read the global skill, but to create a local skill that supersedes
it and add it to the skills table with a constraint that prohibits writing streamlit code
without loading it first. this also reduces token cost: the agent reads the skill description
only, not the full global skill body.

status: addressed - see section 8.

---

## 7. root cause pattern (cross-phase)

phases 1 and 2 both produced skill bypass incidents with the same underlying structure:

| element | phase 1 (prepare-data) | phase 2 (developing-with-streamlit) |
|---|---|---|
| skill bypassed | `$ prepare-data` | `$ developing-with-streamlit` |
| what agent did instead | ran bash + snow sql manually | planned without constraints loaded |
| why it bypassed | skill was not in mandatory block; no prohibition against manual steps | no gate before planning; global skill section was descriptive, not procedural |
| consequence | gzip step skipped; validation skipped | plan missed sis warehouse constraints |
| outcome | data loaded correctly (by luck) | plan generated without sis constraints; phase not completed |
| fix | added to mandatory block + do NOT prohibition | created local skill + added to skills table + pre-planning gate |

the pattern: describing a skill (what it does, when to invoke) is not the same as
enforcing it (hard stop if not invoked). skills must be paired with co-located
prohibitions to be reliable.

---

## 8. file changes made after session

changes made in response to the phase 2 incident, in addition to changes already
documented in report_phase_1.md.

### new files: demo-level developing-with-streamlit skill

three new skill files were created at demo level so the agent never needs to reach
for the global developing-with-streamlit skill:

`demos/renewal_radar_sis_dashboard/skills/developing-with-streamlit/SKILL.md`

main skill, supersedes the global developing-with-streamlit for this project.
frontmatter description explicitly states "sis warehouse runtime (streamlit 1.52.*) -
supersedes the global developing-with-streamlit skill." routes to two sub-skills.
contains a critical differences table (sis vs spcs): connection, dependencies,
streamlit version, forbidden apis, deployment config.

`demos/renewal_radar_sis_dashboard/skills/developing-with-streamlit/skills/general-streamlit/SKILL.md`

8 sections covering sis-specific patterns:
- snowflake connection: `get_active_session()` inside functions, never module-level
- caching: `@st.cache_data`, not `@st.cache_resource`
- user context: `CURRENT_SIS_USER = st.user.user_name or "unknown"`
- available widgets (streamlit 1.52): full list of supported components
- layout: `st.set_page_config(layout="wide")` must be first `st.*` call
- session state, data display, page config

`demos/renewal_radar_sis_dashboard/skills/developing-with-streamlit/skills/sis-dashboard/SKILL.md`

routes to existing project skills (`$ build-dashboard`, `$ brand-identity`, `$ deploy-and-verify`).
contains mandatory sequence before generating dashboard.py.
contains sis warehouse runtime constraints summary table.
contains yaml file templates (snowflake.yml with no artifacts/runtime_name; environment.yml).

### AGENTS.md changes

change 1: added developing-with-streamlit to skills table

the skill was added to the mandatory skills table with its constraint:

```
| `$ developing-with-streamlit` | project | before any streamlit code (1st) | do NOT write streamlit code without loading sis patterns first |
```

this ensures the agent sees the skill co-located with its prohibition, not buried in a
separate override section.

change 2: skills table constraint column format

before: column header was "do NOT"; cell values were positive statements.

```
| when (mandatory) | do NOT                         |
| data loading     | PUT/COPY INTO/gzip/csv manually |
```

agent had to mentally combine "do NOT" + "PUT/COPY..." to derive the prohibition.

after: column renamed to "constraint"; each cell is a complete negation starting with "do NOT":

```
| when (mandatory) | constraint                                              |
| data loading     | do NOT run PUT, COPY INTO, gzip, or csv validation manually |
```

prohibition is now self-contained per row - no mental combination required.

change 3: removed redundant sis content from SECTION 2

approximately 90 lines removed that were now covered by the developing-with-streamlit skill:
- sis api constraints introduction paragraph
- sis user context explanation
- dashboard.py scaffold pointer
- snowflake.yml template (moved to sis-dashboard sub-skill)
- environment.yml template (moved to sis-dashboard sub-skill)
- pre-deploy checklist

this reduced AGENTS.md by ~90 lines without losing any information - the agent now reads
it from the skill instead.

change 4: moved done criteria to be adjacent to their phases

before: done criteria for phases 1 and 2 were at the end of the file in SECTION 3.
the agent had to scroll the entire document to find them.

after:
- done criteria phase 1: end of SECTION 1 (adjacent to the phase 1 work)
- done criteria phase 2: end of SECTION 2 (adjacent to the phase 2 work)
- done criteria phase 3: remains in SECTION 3

criteria are now co-located with the work they verify - the agent does not need to
cross-reference sections.

change 5: moved data loading instructions from SECTION 3 to SECTION 1

data loading was documented in SECTION 3 (governance) but belongs logically in SECTION 1
(infrastructure). moved to end of SECTION 1, before done criteria phase 1.

---

### build-dashboard SKILL.md fix

the scaffold mode output in build-dashboard had an outdated environment.yml template -
it was missing `name: renewal_radar_env` and `channels: - snowflake`. this was corrected
to match the current AGENTS.md template.

---

## 9. executive summary

this section summarizes the key findings from sections 6, 7, and 8 for reference.

- trigger scope: "before any streamlit code" is not a gate before planning. the agent treats planning and code generation as separate triggers. constraints must explicitly cover both: "before planning OR writing any streamlit code." (see section 6, deviation 1 root cause.)
- local supersedes global: a local skill with frontmatter stating "supersedes global X for this project" is chosen automatically over the global skill. this also reduces token cost: the agent reads local content instead of the full global skill body. (see section 6, assessment.)
- bypass pattern: the root cause pattern is stable across phases - missing mandatory entry + no co-located prohibition = agent takes the direct path. the fix is always the same: skill in mandatory table + prohibition + concrete gate. apply this pattern when adding any new skill. (see section 7.)

# phase 2 execution report: renewal radar sis dashboard

**date:** 2026-02-28
**session:** cortex code cli, prompt 3 (dashboard build) - 1 agent session
**environment:** CORTEX_DB.CORTEX_SCHEMA, role CORTEX_ADMIN, warehouse CORTEX_WH
**model:** claude-sonnet-4-5
**final outcome:** phase 2 complete - dashboard deployed; files relocated to root; redeployed; awaiting render confirmation

---

## 1. what phase 2 covers

phase 2 builds and deploys the 3-page streamlit in snowflake dashboard.
it is a single prompt (prompt 3) with a checkpoint before phase 3 begins.

- prompt 3 (dashboard build and deploy):
  - enter `/plan` before pasting the prompt (required per prompts.md)
  - load sis patterns via `$ sis-streamlit` before planning
  - scaffold structure via `$ sis-streamlit` -> `build-dashboard` (no args)
  - load visual identity via `$ sis-streamlit` -> `brand-identity`
  - generate `dashboard.py` with 3 pages per AGENTS.md specification
  - run pre-deploy scan via `$ sis-streamlit` -> `build-dashboard dashboard.py`
  - deploy via `$ sis-streamlit` -> `deploy-and-verify`
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

### correction (after deployment)

environment.yml was not visible in the sis project, so dashboard.py and environment.yml
were moved from `streamlit/` to the project root, snowflake.yml was updated accordingly,
and a redeploy was triggered.

---

## 3. what AGENTS.md specifies for phase 2

note: this section reflects AGENTS.md as it existed at the start of this run
(after phase_02_run_01 governance updates were applied).

### mandatory skills for phase 2

| skill | scope | when | constraint |
|---|---|---|---|
| `$ check-local-environment` | project | session start | do NOT proceed without verifying snow cli, connections.toml, python |
| `$ check-snowflake-context` | project | session start | do NOT proceed without verifying role, warehouse, database, schema |
| `$ sis-streamlit` | project | before any streamlit planning or code | do NOT write streamlit code without loading sis patterns first |
| `$ sis-streamlit` -> `build-dashboard` (no args) | project | before writing code | do NOT write dashboard.py without scaffold output |
| `$ sis-streamlit` -> `brand-identity` | project | before writing code | do NOT use colors or fonts without loading brand identity |
| `$ sis-streamlit` -> `build-dashboard` (with file) | project | before every deploy | do NOT deploy without pre-deploy scan passing |
| `$ sis-streamlit` -> `deploy-and-verify` | project | deploy | do NOT run snow streamlit deploy directly |

### phase 2 done criteria (from AGENTS.md)

```
snow streamlit list -> {app_name} must appear
python3 -m py_compile dashboard.py -> exit code 0
app URL opens, all 3 pages render with data (manual verification)
```

---

## 4. execution trace

### plan mode

the agent entered plan mode correctly and proposed the following build plan:

1. load sis-streamlit, build-dashboard, brand-identity skills
2. create `streamlit/` directory structure with dashboard.py and environment.yml
3. build dashboard.py with 3 pages per AGENTS.md specification
4. implement audit logging via `LOG_AUDIT_EVENT`
5. run pre-deploy scan via `$ sis-streamlit build-dashboard`
6. deploy via `$ sis-streamlit deploy-and-verify phase-2`

the plan correctly listed skill-based scan and deploy commands (steps 5 and 6).
execution did not follow these steps - see deviation 1 and 2.

### execution

skills loaded:
- `$ sis-streamlit` - invoked correctly
- sub-skills read directly: sis-patterns (186 lines), build-dashboard (220 lines), brand-identity (165 lines)

build:

1. created `streamlit/` directory
2. wrote `streamlit/environment.yml` (8 lines, sis dependencies)
3. wrote `streamlit/dashboard.py` (694 lines, all 3 pages)
4. verified python syntax: `python3 -m py_compile streamlit/dashboard.py` - exit code 0

pre-deploy scan (direct bash commands):

- `grep -c "st.rerun()"` - 0
- `grep -c ".applymap("` - grep syntax error on first attempt, re-run without escaping - 0
- `grep -c "@st.fragment"` - 0
- `grep -c "st.experimental_rerun()"` - 0
- `grep -n "st."` - confirmed `st.set_page_config()` at line 9 (first st.* call)
- `grep -c "horizontal=True"` - 0
- `grep -c "PARSE_JSON"` - 0

read deploy-and-verify sub-skill before deploying.

snowflake.yml creation and fix cycle:

| attempt | result | issue |
|---|---|---|
| create snowflake.yml v1 | FAIL | definition_version 2 requires `entities:` structure |
| fix: added entities structure | FAIL | `env_file:` field not supported in DefinitionV20 |
| fix: removed `env_file` field | SUCCESS | deployed at 13:57:10 PST |

first deployment:
- command: `snow streamlit deploy --replace`
- result: success after two snowflake.yml fix cycles
- verified: `snow streamlit list` - RENEWAL_RADAR present

file relocation:

environment.yml was not visible in the sis project; files were moved to root. agent:

1. `mv streamlit/dashboard.py dashboard.py && mv streamlit/environment.yml environment.yml`
2. updated snowflake.yml: `main_file: streamlit/dashboard.py` -> `main_file: dashboard.py`
3. verified python syntax - exit code 0
4. redeployed: `snow streamlit deploy --replace` - success at 14:01:46 PST

final state:

```
app URL: https://app.snowflake.com/CORTEX_ORG/CORTEX_ACCOUNT/#/streamlit-apps/CORTEX_DB.CORTEX_SCHEMA.RENEWAL_RADAR
status: deployed
file layout: dashboard.py (root), environment.yml (root), snowflake.yml (root), streamlit/ (empty)
```

agent stopped and waited for confirmation that all 3 pages render correctly.

---

## 5. skill compliance summary

| skill | supposed to run | actually invoked | result |
|---|---|---|---|
| `$ check-local-environment` | yes (session start) | not verified in log | assumed |
| `$ check-snowflake-context` | yes (session start) | yes - `cortex connections list` + `snow sql SELECT CURRENT_ROLE()` | partial - direct commands |
| `$ sis-streamlit` | yes (before planning/code) | yes, invoked | PASS |
| `$ sis-streamlit` -> `build-dashboard` (no args) | yes (before writing code) | yes, read sub-skill | PASS |
| `$ sis-streamlit` -> `brand-identity` | yes (before writing code) | yes, read sub-skill | PASS |
| `$ sis-streamlit` -> `build-dashboard` (with file) | yes (pre-deploy scan) | sub-skill not read; scan ran as direct bash commands | FAIL - mechanism bypassed |
| `$ sis-streamlit` -> `deploy-and-verify` | yes (deploy) | deploy-and-verify sub-skill read; `snow streamlit deploy --replace` run directly | PARTIAL - content referenced, mechanism bypassed |

---

## 6. deviations and root causes

### deviation 1: scan run as direct bash commands

what happened: the agent read the deploy-and-verify sub-skill before deploying but ran all
pre-deploy scan checks as direct bash grep/compile commands rather than through the
`$ sis-streamlit` -> `build-dashboard` skill. build-dashboard sub-skill was not re-read
at scan time.

root cause: skill files are markdown checklists. after loading sub-skills at the start,
the agent had their content in context and executed the steps directly. it did not distinguish
between "running a skill" and "reading a skill and following it manually."

consequence: the scan did not apply the full build-dashboard checklist - notably missing
the sql parameterization check. no sql injection issue was caught in this run.

status: open pattern (no mechanical enforcement). sql injection was found and fixed
in the next run (phase_02_run_03.md) based on planning phase analysis.

### deviation 2: deploy run as direct command

what happened: deployment used `snow streamlit deploy --replace` directly in both
the initial deploy and the post-relocation redeploy. this bypassed the deploy-and-verify
skill governance (file structure check, post-deploy audit log verification).

root cause: same as deviation 1. the plan correctly specified skill-based deployment,
but execution defaulted to the direct command.

status: open pattern. deployment succeeded and app is accessible.

### deviation 3: files initially created in streamlit/ subdirectory

what happened: the agent created `streamlit/dashboard.py` and `streamlit/environment.yml`
instead of placing them in the project root.

root cause: the agent's build plan step 2 specified creating a `streamlit/` directory.
AGENTS.md did not have an explicit constraint against this at the time. the issue was
corrected after deployment.

consequence: initial deploy uploaded files from the wrong path. environment.yml was not
visible in sis (warehouse runtime does not surface it). files were relocated and redeployed
within the same session, after i requested the change.

status: fixed within this run. AGENTS.md updated after the run (see section 8).

### deviation 4: snowflake.yml required two fix cycles before deploy succeeded

what happened: the initial snowflake.yml was created with the wrong structure for
definition_version 2. first fix added the `entities:` wrapper but left an unsupported
`env_file:` field. second fix removed `env_file`.

root cause: the build-dashboard sub-skill scaffold output provided a template, but the
agent reconstructed snowflake.yml from memory rather than copying the exact template.

status: fixed within this run. three deploy attempts were needed.

---

## 7. root cause pattern (cross-phase)

| element | phase 2 run 01 | phase 2 run 02 |
|---|---|---|
| skill bypassed | `$ developing-with-streamlit` (planning gate) | `$ sis-streamlit` -> `build-dashboard` (scan) and `deploy-and-verify` (deploy) |
| what agent did instead | planned without loading sis patterns | loaded skills at start; ran scan and deploy as direct commands |
| why it bypassed | no gate before planning; global skill section was descriptive, not procedural | skill files are markdown; agent cannot mechanically distinguish invocation from manual execution |
| consequence | plan missed sis warehouse constraints; session interrupted | sql injection not caught; environment.yml created; files in wrong directory |
| outcome | governance improvements made; run did not complete | deployment successful; issues identified and corrected in follow-up session (run 03) |

---

## 8. file changes made after this run

analysis of this run's output was performed in the planning phase before run 03.
the planning session identified the following issues in the 694-line dashboard.py
produced here:

- chart 3 (renewal outcome distribution): showed absolute counts instead of percentage share
- chart 3 color: CANCELLED mapped to orange (`#FFA726`) instead of red (`#E53935`)
- sql injection: f-string interpolation in IN-clause filters (lines 516-526, 597-598, 634-644)

### skill file changes (applied before run 03)

`demos/renewal_radar_sis_dashboard/skills/sis-streamlit/skills/build-dashboard/SKILL.md`

scan mode step 3 updated: added mandatory sql parameterization check:
- grep for `session.sql(f` and inspect each match for IN-clause filter variable interpolation
- violation: any f-string sql where a user filter value is interpolated (e.g. `IN ({var})`)
- required fix: `session.table(...).filter(col(...).isin(whitelist_list))`
- exception: constants `DATABASE`, `SCHEMA`, `APP_NAME` in f-string sql are allowed

`demos/renewal_radar_sis_dashboard/AGENTS.md`

added "mandatory skill usage for scan and deploy" block to section 2:
- explicitly forbids running `python -m py_compile` directly
- explicitly forbids running `snow streamlit deploy --replace` directly
- states that skills perform additional governance checks that direct commands bypass

### file location: path references updated across 11 files

the `mv` of dashboard.py and environment.yml from `streamlit/` to root during the run
required updating all hardcoded path references. files changed:
`build-dashboard/SKILL.md`, `deploy-and-verify/SKILL.md`, `sis-streamlit/SKILL.md`,
`AGENTS.md`, `references/sis-file-structure.md`,
`references/snowflake-yml-reference.md`, `references/snow-streamlit-cli.md`,
`references/snowflake-sis-docs.md`, `skills/README.md`, `sis-dashboard/SKILL.md`

### `build-dashboard/SKILL.md` - scaffold template: global filters

blocks 7-8 in the scaffold template now include session state initialization and shared
sidebar filter widgets at module scope (before navigation). uses `key=` on each multiselect
so values persist via `st.session_state` when navigating between pages. page-specific
filters (e.g. "final offers only" toggle on page 2) remain inside their respective page blocks.

### `AGENTS.md` - chart 3 spec: renewal outcome distribution changed to 100% stacked bar

changed spec from a plain stacked bar to a proportional 100% stacked bar. includes
explicit normalization query, pandas transform, and altair encoding with all 4 outcomes
(RENEWED, LAPSED, NOT_TAKEN_UP, CANCELLED) as required series.

---

## 9. executive summary

- deployment status: successful. app deployed twice within the session (initial + post-relocation). app accessible at `CORTEX_DB.CORTEX_SCHEMA.RENEWAL_RADAR`; awaiting render confirmation.
- sql injection: not caught during this run. scan ran as direct bash commands and missed the f-string IN-clause check. identified and fixed in run 03.
- file placement: files initially created in `streamlit/` subdirectory; relocated to root and redeployed cleanly.
- snowflake.yml: required two fix cycles before deploy succeeded (definition_version 2 format, unsupported env_file field).
- skill bypass pattern: sis-streamlit loaded correctly; sub-skills read at session start; scan and deploy steps executed as direct bash commands. plan correctly specified skill-based commands but execution did not follow. same bypass pattern as run 01, different skill.

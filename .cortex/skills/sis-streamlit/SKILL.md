---
name: sis-streamlit
description: "use for ALL streamlit tasks in this project: building, editing, debugging, styling, deploying, or running acceptance checks. sis warehouse runtime (streamlit 1.52.*) - supersedes the global developing-with-streamlit skill. routes to: sis-patterns, build-dashboard, brand-identity, secure-dml, deploy-and-verify."
---

## runtime context

this project uses streamlit in snowflake (sis) warehouse runtime, pinned to streamlit 1.52.*.
this is NOT local streamlit, NOT spcs container runtime.

the global `developing-with-streamlit` skill targets spcs container runtime. its patterns for
connection, dependencies, deployment, and streamlit apis are wrong for this project.
use the sub-skills below instead.

## routing table

| task | load |
|---|---|
| check local tooling (snow cli, config.toml, python) | `$ check-local-environment` (personal skill) |
| verify snowflake role, warehouse, schema objects | `.cortex/skills/check-snowflake-context/SKILL.md` |
| validate and load csv files | `.cortex/skills/prepare-data/SKILL.md` |
| writing any streamlit code: connection, caching, widgets, layout, session state | `.cortex/skills/sis-streamlit/skills/sis-patterns/SKILL.md` |
| load sis api constraints before writing code / scaffold dashboard.py / pre-deploy scan | `.cortex/skills/sis-streamlit/skills/build-dashboard/SKILL.md` |
| load visual identity: colors, chart type rules, language conventions | `.cortex/skills/sis-streamlit/skills/brand-identity/SKILL.md` |
| writing INSERT or UPDATE with user text (flag form, review form) | `.cortex/skills/sis-streamlit/skills/secure-dml/SKILL.md` |
| deploy the sis app or run phase acceptance checks | `.cortex/skills/sis-streamlit/skills/deploy-and-verify/SKILL.md` |

## standard workflow sequence

```
phase 0 - session start
  1. $ check-local-environment      (snow cli, config.toml, python)
  2. check-snowflake-context        (role, warehouse, database, schema objects)

before writing any streamlit code
  3. build-dashboard                (discovery mode - loads sis api constraints)
  4. brand-identity                 (visual identity, chart type rules, colors)

phase 1 - data loading
  5. prepare-data                   (validate csv files + PUT + COPY INTO)
  6. deploy-and-verify phase-1      (infrastructure acceptance checks)

phase 2 - dashboard build and deploy
  7. build-dashboard scaffold       (generate dashboard.py at project root)
  8. secure-dml                     (stored procedure ddl for flag INSERT and review UPDATE)
     [implement page content per AGENTS.md page specifications]
  9. build-dashboard <file>         (scan mode - forbidden patterns + dml injection + audit presence)
 10. deploy-and-verify deploy       (snow streamlit deploy --replace)
 11. deploy-and-verify phase-2      (dashboard acceptance checks)

phase 3 - write-back acceptance
 12. deploy-and-verify phase-3      (flag write-back + audit log checks)
```

## stopping points

- if phase is not specified in the user prompt: confirm which phase to run before proceeding
- if phase is specified (e.g. "phase 1 acceptance checks", "deploy-and-verify phase-1"): route directly, do NOT ask

## sis vs spcs: critical differences

| topic | global skill (spcs) | this project (sis) |
|---|---|---|
| snowflake connection | `st.connection("snowflake")` | `get_active_session()` inside functions |
| dependencies file | `pyproject.toml` + pip | `environment.yml` (project root) + anaconda channel |
| streamlit version | `streamlit>=1.53.0` | `streamlit=1.52.*` (pinned) |
| `snowflake.yml` | `runtime_name`, `compute_pool`, `artifacts` required | none of these - omit entirely |
| `@st.fragment` | recommended for partial reruns | forbidden - unreliable in warehouse runtime |
| `st.rerun()` | valid pattern | forbidden - causes infinite loops in warehouse runtime |
| kpi row layout | `st.container(horizontal=True)` | `st.columns()` - horizontal not in 1.52 |

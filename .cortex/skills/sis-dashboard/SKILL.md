---
name: sis-dashboard
description: "master routing skill for the renewal radar streamlit in snowflake dashboard project. trigger when the user asks to start a session, set up the environment, check prerequisites, load csv data, build the dashboard, validate style, deploy the sis app, or run acceptance checks. do NOT use for general snowflake queries unrelated to this project."
---

# renewal radar sis dashboard

route to the correct sub-skill based on user intent.

## routing table

| user intent | route |
|---|---|
| start session / check local tooling (snow cli, config.toml, python) | Load `../check-local-environment/SKILL.md` |
| verify snowflake role, warehouse, database, schema objects | Load `../check-snowflake-context/SKILL.md` |
| load sis api constraints before writing streamlit code | Load `../sis-streamlit/skills/build-dashboard/SKILL.md` (discovery mode, no args) |
| load visual identity, chart type rules, colors, language conventions | Load `../sis-streamlit/skills/brand-identity/SKILL.md` |
| scaffold / generate dashboard.py from template | Load `../sis-streamlit/skills/build-dashboard/SKILL.md` (scaffold mode) |
| writing flag INSERT (page 2) or review UPDATE (page 3) with user text | Load `../sis-streamlit/skills/secure-dml/SKILL.md` |
| scan python file for forbidden patterns + style before deploy | Load `../sis-streamlit/skills/build-dashboard/SKILL.md` (scan mode, with file arg) |
| validate and load csv files into snowflake | Load `../prepare-data/SKILL.md` |
| deploy or redeploy the sis dashboard app | Load `../sis-streamlit/skills/deploy-and-verify/SKILL.md` (deploy mode) |
| run acceptance criteria / done checks / sql verification | Load `../sis-streamlit/skills/deploy-and-verify/SKILL.md` (verify mode) |

## standard workflow sequence

```
phase 0 - session start
  1. check-local-environment      (snow cli, config.toml, python)
  2. check-snowflake-context      (role, warehouse, database, schema objects)

before writing any streamlit code
  3. build-dashboard              (discovery mode - loads sis api constraints)
  4. brand-identity               (loads visual identity, chart type rules, colors, language)

phase 1 - data loading
  5. prepare-data                 (validate csv files + PUT + COPY INTO)
  6. deploy-and-verify phase-1    (infrastructure acceptance checks)

phase 2 - dashboard build and deploy
  7. build-dashboard scaffold     (generate dashboard.py at project root)
  8. secure-dml                   (stored procedure ddl for flag INSERT and review UPDATE)
     [implement page content per AGENTS.md page specifications]
  9. build-dashboard <file>       (scan mode - forbidden patterns + dml injection + audit presence)
 10. deploy-and-verify deploy     (snow streamlit deploy --replace)
 11. deploy-and-verify phase-2    (dashboard acceptance checks)

phase 3 - write-back acceptance
 12. deploy-and-verify phase-3    (flag write-back + audit log checks)
```

## stopping points

- if phase is not specified in the user prompt: confirm which phase to run before proceeding
- if phase is specified (e.g. "phase 1 acceptance checks", "deploy-and-verify phase-1"): route directly, do NOT ask

## notes

- skills depend on AGENTS.md for environment values (`{role}`, `{warehouse}`, `{database}`, `{schema}`, `{app_name}`)
- `build-dashboard` operates in three modes: discovery (no args), scaffold, and scan (with file arg)
- `deploy-and-verify` calls `build-dashboard` scan mode internally before deploy - do not run it separately
- sub-skills (build-dashboard, brand-identity, deploy-and-verify, sis-patterns) are in the project directory.
  do NOT invoke `$ sis-streamlit` directly - its personal skills installation does not include
  sub-skills. always route through this skill (`$ sis-dashboard`) which uses project-relative paths.
- see [README.md](../README.md) for full project workflow and skill documentation

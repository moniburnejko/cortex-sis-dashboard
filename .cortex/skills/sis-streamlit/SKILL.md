---
name: sis-streamlit
description: "use for ALL streamlit tasks in this project: building, editing, debugging, styling, or deploying. SiS warehouse runtime (streamlit 1.52.*) - supersedes the global developing-with-streamlit skill. routes to: sis-patterns (connection, caching, widgets, layout, session state), build-dashboard (constraints, scaffold, scan), brand-identity (visual identity, chart rules), deploy-and-verify (deploy + acceptance checks)."
---

## runtime context

this project uses streamlit in snowflake (SiS) warehouse runtime, pinned to streamlit 1.52.*.
this is NOT local streamlit, NOT SPCS container runtime.

the global `developing-with-streamlit` skill targets SPCS container runtime. its patterns for
connection, dependencies, deployment, and streamlit APIs are wrong for this project.
use the sub-skills below instead.

## sub-skill routing

| task | load |
|------|------|
| writing any streamlit code: connection, caching, widgets, layout, session state, user context | `-> Load skills/sis-patterns/SKILL.md` |
| load SiS API constraints before writing code / scaffold dashboard.py / pre-deploy scan | `-> Load skills/build-dashboard/SKILL.md` |
| load visual identity: colors, chart type rules, language conventions | `-> Load skills/brand-identity/SKILL.md` |
| deploy the SiS app or run phase acceptance checks | `-> Load skills/deploy-and-verify/SKILL.md` |

when writing dashboard code, load in this order:
1. `sis-patterns` - SiS runtime patterns (connection, caching, widgets, layout)
2. `build-dashboard` - SiS API constraints and forbidden patterns
3. `brand-identity` - visual identity, chart type rules, colors

## SiS vs SPCS: critical differences

| topic | global skill (SPCS) | this project (SiS) |
|-------|---------------------|--------------------|
| snowflake connection | `st.connection("snowflake")` | `get_active_session()` inside functions |
| dependencies file | `pyproject.toml` + pip | `environment.yml` (project root) + Anaconda channel |
| streamlit version | `streamlit>=1.53.0` | `streamlit=1.52.*` (pinned) |
| `snowflake.yml` | `runtime_name`, `compute_pool`, `artifacts` required | none of these - omit entirely |
| `@st.fragment` | recommended for partial reruns | forbidden - unreliable in warehouse runtime |
| `st.rerun()` | valid pattern | forbidden - causes infinite loops in warehouse runtime |
| KPI row layout | `st.container(horizontal=True)` | `st.columns()` - horizontal not in 1.52 |

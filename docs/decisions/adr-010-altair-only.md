# adr-010: altair-only charts

**date:** 2026-03-01
**source:** AGENTS.md sis critical constraints, brand-identity/SKILL.md

## problem

streamlit's native chart functions (`st.bar_chart`, `st.line_chart`, `st.scatter_chart`) do not support percentage axis formatting, horizontal bar layout, or fine-grained legend placement. the renewal radar dashboard requires stacked bar charts with percentage labels, horizontal outcome bars, and consistent color encoding across chart types. none of which are achievable with native streamlit charts.

## decision

altair for all charts without exception. native streamlit chart functions (`st.bar_chart`, `st.line_chart`, `st.scatter_chart`) are on the forbidden list. all chart examples in brand-identity/SKILL.md and AGENTS.md use the altair api with `st.altair_chart()`.

## alternatives considered

- native streamlit charts with custom css: custom css injection is not available in sis. rejected: not feasible.
- plotly: feature-rich, but not available via the anaconda channel in the version of the environment used by the project. rejected: dependency not available.
- matplotlib / seaborn: static image output; poor interactivity in sis. rejected: inferior ux.

## consequences

- `environment.yml` must include `- altair` in dependencies
- all chart code examples in brand-identity and AGENTS.md use altair api
- encoding conventions are standardized: `alt.X("period:T")`, `alt.Color("outcome:N", scale=alt.Scale(...))`, etc.
- color domain/range must be passed explicitly via `alt.Scale(domain=..., range=...)` to enforce consistent outcome colors

## related

- `.cortex/skills/sis-streamlit/skills/brand-identity/SKILL.md`
- AGENTS.md: sis critical constraints (forbidden chart functions)

# adr-015: module-level session

**date:** 2026-03-01
**source:** code_review_dashboard.md issue 6, sis-patterns/SKILL.md (contradiction)

## problem

the build-dashboard scaffold placed `session = get_active_session()` at module level. the sis-patterns skill said "never capture session at module level, always inside functions". these two instructions directly contradicted each other. the agent, facing both, produced inconsistent code: module-level session in some files, inside-function session in others, and crashes when module-level session was referenced inside `@st.cache_data` functions (where the session is not accessible).

## decision

clear rule with two cases:
- **module-level session is OK** for non-cached code: the main module, routing logic, audit logger initialization. the scaffold template is correct.
- **inside `@st.cache_data` functions: MANDATORY `get_active_session()` inside the function body.** a module-level session is not accessible in the cached execution context and will raise a `SnowflakeConnectionError`.

sis-patterns/SKILL.md updated with an explicit table documenting both cases and the reason for the distinction.

## alternatives considered

- **always inside functions**: the safest approach and eliminates the contradiction, but verbose; the scaffold template would need to change. rejected: unnecessary churn; scaffold is correct for its use case.
- **always module-level**: simpler, but crashes inside `@st.cache_data`. rejected: breaks caching.
- **remove `@st.cache_data` from data-fetching functions**: eliminates the problem but at the cost of performance (no caching). rejected: caching is important for sis performance.

## consequences

- contradiction in sis-patterns removed; scaffold template remains valid
- rule documents why the scaffold looks different from the sis-patterns "inside functions" guidance
- build-dashboard/SKILL.md scan checks for `get_active_session()` inside `@st.cache_data` functions
- any new `@st.cache_data` function must always call `get_active_session()` locally

## related

- AGENTS.md: sis critical constraints
- `.cortex/skills/sis-streamlit/skills/sis-patterns/SKILL.md`: updated with the two-case table
- `.cortex/skills/sis-streamlit/skills/build-dashboard/SKILL.md`: scan for session inside cache_data

# adr-006: whitelist filter validation

**date:** 2026-03-01
**source:** AGENTS.md security rule 3, build-dashboard/SKILL.md scan mode

## problem

filters (regions, segments, channels) from `st.multiselect` are interpolated into sql `IN (...)`. if the list is not validated before interpolation, a malicious value (injected e.g. by modifying the client) could contain sql injection. these filters are not free-text (they have a finite set of values from the db), but the code-generating agent used a simple `.join()` + f-string approach.

## decision

two-layer protection:
1. **whitelist validation**: `selected = [r for r in user_selected if r in VALID_LIST]`. filters out values outside the allowed set
2. **snowpark api**: `session.table(...).filter(col('region').isin(selected))` instead of f-string sql. parameterization via snowpark, not string concatenation

`VALID_LIST` is fetched from the db at startup (or via `@st.cache_data`): a dynamic whitelist that stays current.

## alternatives considered

- **f-string with `.join()` after validation**: `f"IN ({','.join(selected)})"`. still an f-string sql construction, non-compliant with security rule 3. rejected even with validation.
- **snowpark for everything including DATE_TRUNC**: technically correct, but the snowpark api for `DATE_TRUNC('month', col(...))` is verbose; mixing snowpark and session.sql is fine for different queries. rejected as over-engineering.
- **no validation + snowpark isin()**: snowpark `isin()` with parameterization is technically sufficient, but the whitelist adds defence in depth. both layers are retained.

## consequences

- whitelist validation applies ONLY to enums (regions, segments, channels): a finite set of values
- does NOT apply to free-text (flag_reason, review_notes). that is covered by adr-007 (stored procedures)
- `VALID_LIST` must be refreshed when db data changes; `@st.cache_data` with a TTL is the recommended pattern
- build-dashboard/SKILL.md scan mode checks for f-string IN-list construction without a whitelist

## related

- [adr-007](adr-007-dml-procedures.md): dml with free-text user input (different threat category)
- AGENTS.md: security rule 3
- `.cortex/skills/sis-streamlit/skills/build-dashboard/SKILL.md`: scan step 2a

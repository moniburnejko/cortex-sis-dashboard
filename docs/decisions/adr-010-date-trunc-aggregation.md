# adr-010: date_trunc aggregation

**date:** 2026-03-01
**source:** AGENTS.md page 1 spec, phase_02_run_01.md (jagged line bug)

## problem

plotting raw `renewal_date` values in altair produced one data point per policy: a jagged, unreadable line chart. each unique date value appeared as a separate point, making trends invisible. the chart needed aggregation to show meaningful trends over time.

## decision

`SELECT DATE_TRUNC('month'/'week'/'day', renewal_date) AS period, ... GROUP BY period`: aggregation in sql. altair receives pre-aggregated data and draws a smooth line. adaptive granularity based on the selected date range:
- `'day'` for ranges <= 30 days
- `'week'` for 31-180 days
- `'month'` for > 180 days

## alternatives considered

- **aggregation in pandas after fetching**: `df.groupby(pd.Grouper(freq='M'))`. correct result but transfers all raw rows to the app before aggregating; unnecessary data transfer at scale. rejected: inefficient.
- **altair `timeUnit` transform**: `alt.X('renewal_date:T').timeUnit('month')`. insufficient for large date ranges and does not support adaptive granularity. rejected: limited control.
- **fixed monthly granularity**: simpler, but monthly buckets are too coarse for a 7-day filter selection. rejected: poor ux for short ranges.

## consequences

- aggregation pattern mandatory in brand-identity/SKILL.md for all time-series charts
- altair encoding uses `alt.X("period:T", title=None)`. the `T` type flag tells altair to treat the field as temporal
- the sql query must include the granularity logic (CASE WHEN on date range length), making queries slightly more complex
- granularity switch must be recalculated whenever the date filter changes

## related

- [adr-013](adr-013-altair-only.md): altair as the exclusive charting library
- [adr-014](adr-014-two-date-inputs.md): date range inputs that drive granularity selection
- AGENTS.md: page 1 chart spec
- `.cortex/skills/sis-streamlit/skills/brand-identity/SKILL.md`

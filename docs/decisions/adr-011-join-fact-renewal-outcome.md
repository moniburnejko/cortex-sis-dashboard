# adr-011: fact_renewal join for renewal_outcome

**date:** 2026-03-01
**source:** phase_02_run_04.md (outcome chart single bar bug), AGENTS.md page 2 spec

## problem

`FACT_PREMIUM_EVENT.renewal_outcome` is NULL for non-renewed events. the "Final Offers Only" toggle (filter `is_final_offer = 1`) removes all non-renewed records from `FACT_PREMIUM_EVENT`, leaving only `RENEWED` rows. result: the outcome distribution chart showed a single bar (RENEWED), making it useless as a kpi.

## decision

JOIN `FACT_PREMIUM_EVENT e JOIN FACT_RENEWAL r ON e.policy_id = r.policy_id`. `FACT_RENEWAL` always has `renewal_outcome` for all 4 outcome values (RENEWED, LAPSED, CANCELLED, NOT_TAKEN_UP). the "Final Offers Only" toggle applies to the premium trend chart but NOT to the outcome distribution chart. two charts on the same page use different filter scopes.

## alternatives considered

- **GROUP BY with COALESCE**: `COALESCE(e.renewal_outcome, 'UNKNOWN')`. does not solve the underlying problem; non-renewed events simply have no outcome value in `FACT_PREMIUM_EVENT` regardless of COALESCE. rejected: does not address root cause.
- **separate queries per outcome**: one query per outcome value. rejected: 4 round trips instead of 1; harder to maintain.
- **remove the "Final Offers Only" toggle from the page**: simplifies the query but removes a required feature. rejected: feature is in the spec.

## consequences

- principle: "two different filters for two charts on the same page": a non-obvious pattern, worth documenting
- the JOIN requirement is explicit in AGENTS.md page 2 spec and in build-dashboard/SKILL.md
- the "Final Offers Only" toggle must only be wired to the premium trend chart query, not to the outcome distribution query
- query complexity increases slightly (explicit JOIN instead of single-table scan)

## related

- [adr-010](adr-010-date-trunc-aggregation.md): sql aggregation patterns for charts
- [adr-013](adr-013-altair-only.md): altair rendering of the outcome distribution chart
- AGENTS.md: page 2 chart spec
- `.cortex/skills/sis-streamlit/skills/build-dashboard/SKILL.md`

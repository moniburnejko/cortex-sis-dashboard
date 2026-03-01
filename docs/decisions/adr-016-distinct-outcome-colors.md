# adr-016: distinct outcome colors

**date:** 2026-03-01
**source:** code_review_dashboard.md issue 5, final_report_01.md BUG-006

## problem

LAPSED and NOT_TAKEN_UP were assigned the same color (`#FFA726`, Material amber). on a stacked bar chart the two outcomes were visually indistinguishable: a user could not tell them apart without hovering over each segment. the dashboard's main purpose is to show outcome distribution, so color distinctiveness is critical.

## decision

explicit color assignment for each of the four outcomes:

| outcome | color | hex |
|---------|-------|-----|
| RENEWED | primary blue | `#1565C0` |
| LAPSED | amber | `#FFA726` |
| NOT_TAKEN_UP | darker orange | `#FB8C00` |
| CANCELLED | red | `#E53935` |

this table is the single source of truth in brand-identity/SKILL.md. enforced in altair via `alt.Scale(domain=[...], range=[...])`.

## alternatives considered

- **grayscale for non-renewed outcomes**: visually distinct from RENEWED (blue) but poor contrast between grayscale values. rejected: accessibility concern and poor readability.
- **different saturations of a single hue**: e.g. four shades of orange. not sufficiently distinct at the saturation levels available. rejected: too similar in practice.
- **letting altair pick colors automatically**: altair's default scheme does not guarantee the required semantic meaning (red = cancelled, blue = positive). rejected: inconsistent meaning across renders.

## consequences

- color change propagated to brand-identity/SKILL.md and AGENTS.md page 1 chart spec
- every generated dashboard must use this exact color table. no deviations
- altair encoding: `alt.Color("outcome:N", scale=alt.Scale(domain=OUTCOME_DOMAIN, range=OUTCOME_COLORS))`
- `OUTCOME_DOMAIN` and `OUTCOME_COLORS` defined as module-level constants in dashboard.py

## related

- [adr-013](adr-013-altair-only.md): altair as the charting library (scale parameter usage)
- `.cortex/skills/sis-streamlit/skills/brand-identity/SKILL.md`: color spec table
- AGENTS.md: page 1 chart spec with explicit color values

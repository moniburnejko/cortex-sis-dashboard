# renewal radar sis dashboard

cortex code cli demo: autonomous end-to-end build — infra, data load, streamlit in snowflake app, audit loop. zero manual code.

## what this is

cortex code cli takes `AGENTS.md` as input and autonomously:
1. creates logging infrastructure (AUDIT_LOG, APP_EVENTS, V_APP_EVENTS, LOG_AUDIT_EVENT), domain table, and stage
2. loads 3 csv files into source tables via internal stage
3. builds and deploys a 3-page streamlit in snowflake dashboard
4. logs user interactions and agent operations via LOG_AUDIT_EVENT procedure

## repo contents

| file/dir | description |
|---|---|
| `AGENTS.md` | cortex code cli project spec - single source of truth |
| `dashboard.py` | streamlit in snowflake app |
| `snowflake.yml` | sis deployment config |
| `environment.yml` | conda env - streamlit 1.52.*, altair, pandas |
| `.cortex/skills/` | project skills invoked by the agent |
| `docs/prompts.md` | 4-phase session prompts with checkpoints |
| `docs/reports/` | session reports from cortex code cli runs |
| `.githooks/` | pre-commit hook for credential sanitization |

## dashboard pages

1. **kpi overview** - renewal rate, leakage rate, quote-to-bind, service delay index + trend and regional breakdown charts
2. **premium pressure** - price shock analysis, premium change by outcome, heatmap + flag-for-review write-back to RENEWAL_FLAGS
3. **activity log** - user interaction audit trail, inline flag review with mark-reviewed write-back

## running a session

see `docs/prompts.md` for the full 4-phase workflow (infrastructure, data load, dashboard build, verification).

```bash
# install personal skills to ~/.snowflake/cortex/skills/
# (check-local-environment, sis-streamlit)

cd dashboard-sis
cortex
```

## credential sanitization

real snowflake object names are replaced with placeholders by the pre-commit hook before every commit.

one-time setup:
```bash
git config core.hooksPath .githooks
cp .githooks/sanitize-map.example .githooks/.sanitize-map
# fill in real values
```

```bash
.githooks/sanitize.sh --check    # verify no credentials exposed
.githooks/sanitize.sh --reverse  # restore real names locally after pull
```

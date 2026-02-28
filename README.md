# renewal radar sis dashboard

Insurance renewal analytics dashboard built autonomously by Cortex Code CLI.

End-to-end demonstration of agent-driven development: infrastructure setup, Streamlit app, and governance audit loop — all executed by an AI agent following structured specifications.

## what's in here

- [`AGENTS.md`](AGENTS.md) — project specification for Cortex Code CLI (single source of truth)
- [`dashboard.py`](dashboard.py) — Streamlit in Snowflake app
- [`snowflake.yml`](snowflake.yml) — SiS deployment config
- [`environment.yml`](environment.yml) — Conda environment (streamlit 1.52.*, altair, pandas)
- [`.cortex/skills/`](.cortex/skills/) — project skills invoked by the agent
- [`docs/prompts.md`](docs/prompts.md) — 4-phase session prompts with checkpoints
- [`docs/reports/`](docs/reports/) — session reports from Cortex Code CLI runs

## dashboard

3-page Streamlit in Snowflake app:

1. **KPI Overview** — renewal rate, leakage rate, quote-to-bind, service delay index; trend and regional breakdown charts
2. **Premium Pressure** — price shock analysis, premium change by outcome, heatmap; flag-for-review write-back
3. **Activity Log** — user interaction audit trail; inline flag review with mark-reviewed write-back

## running a session

See [`docs/prompts.md`](docs/prompts.md) for the full 4-phase workflow.

Quick start:
```bash
# 1. install personal skills to ~/.snowflake/cortex/skills/
#    (check-local-environment, sis-streamlit)

# 2. cd to this directory and start cortex code cli
cd dashboard-sis
cortex
```

## credential sanitization

This repo uses a pre-commit hook to replace real Snowflake object names with placeholders before committing. Real values stay local only.

Setup (one-time):
```bash
git config core.hooksPath .githooks
cp .githooks/sanitize-map.example .githooks/.sanitize-map
# fill in real values in .sanitize-map
```

To check for exposed credentials: `.githooks/sanitize.sh --check`
To restore real names locally after a pull: `.githooks/sanitize.sh --reverse`

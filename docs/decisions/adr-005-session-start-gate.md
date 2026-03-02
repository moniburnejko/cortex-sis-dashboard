# adr-005: session start gate

**date:** 2026-03-01
**source:** final_report_01.md section 4.2 pattern #1, phase_02_run_04.md

## problem

in phase 2+, the agent treated a manual `SELECT CURRENT_ROLE()` or reading a memory file as equivalent to invoking the `check-local-environment` skill. the session start gate was consistently skipped. skills perform additional validation steps (checking role, warehouse, schema access) that manual sql commands do not cover. result: the agent started phase 2 without confirmation that the environment was ready.

## decision

AGENTS.md session start gate reinforced with an explicit STOP and a note: "manual sql is not equivalent to skill invocation. running `SELECT CURRENT_ROLE()` does NOT substitute for calling the check-local-environment skill". the skill must be invoked via the cortex code cli, not through manual sql commands. the pattern from phase_01 where the prompt explicitly said `use $ sis-streamlit` (an explicit cli invocation): that pattern works.

## alternatives considered

- **remove the gate**: agent skips environment checks before starting. rejected: loss of governance; environment errors are only discovered mid-phase (harder to fix).
- **change gate to an optional WARN**: agent logs a warning but does not stop. rejected: too weak; the pattern showed the agent ignores warnings.
- **inline sql check instead of a skill**: `SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE()` in the prompt. rejected: this is exactly the problem, partial validation instead of the full check.

## consequences

- requires education in every prompt: explicit skill naming or cli command
- `use $ sis-streamlit` as the preferred pattern in prompts.md
- AGENTS.md contains an explicit note that manual sql does not substitute for skill invocation
- `->` notation in AGENTS.md (e.g. `check-local-environment -> phase 1`) is a conceptual routing hint, not a literal cli command. this interpretation is reinforced in AGENTS.md

## related

- [adr-004](adr-004-prompt-stop-gates.md): stop-gate pattern for prompts
- AGENTS.md: session start gate section
- `docs/prompts.md`: prompt 1 with explicit skill call

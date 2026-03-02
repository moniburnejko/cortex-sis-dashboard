# adr-012: prompt text as enforcement mechanism for mandatory steps

**date:** 2026-03-02
**source:** phase_02_run_04.md, phase_03_run_01.md, secure_dml_test_260302.md

## problem

adr-005 added an explicit STOP constraint to AGENTS.md for the session start gate. the constraint was ignored in every subsequent run (phase_02_run_04 sessions 1 and 2, phase_03_run_01, secure_dml_test_260302 - 5 sessions total). the same pattern applies to other AGENTS.md constraints: skill invocation rules, scan-before-deploy requirements, and do-not-run-sql-manually rules are documented but consistently bypassed.

root cause: the agent processes instructions in priority order:
1. explicit instruction in the active prompt (highest)
2. recent context - memory files, prior conversation turns
3. AGENTS.md background constraints (lowest)

when the active prompt says "build and deploy the dashboard", the agent optimizes for that task. AGENTS.md constraints are background context - the agent reads them but does not treat them as blocking when the prompt gives no indication they apply to this specific interaction.

this is not a bug in the agent. it is a property of how llm agents process competing instructions. markdown files used as background context are documentation, not enforcement.

## decision

mandatory first steps belong in the prompt text, not only in AGENTS.md.

`docs/prompts.md` updated: every prompt (1-4) now opens with:
```
invoke $ check-local-environment, then $ check-snowflake-context. do not proceed until both pass.
```

this makes the gate an explicit task in the active prompt - same priority as "build the dashboard". the agent cannot treat it as optional background context because it is the first instruction it receives.

## alternatives considered

- stronger constraint language in AGENTS.md: already tried (adr-005 - added STOP and bold warnings). not effective. the agent reads the constraint and understands it but does not self-enforce when the prompt does not reference it.
- session hooks in cortex code cli: would allow pre-session validation at the runtime level, not instruction level. not available in current cortex code cli.
- rely on user to catch and remind: current fallback. requires the user to monitor every session start. fragile - increases cognitive load and defeats the purpose of automation.
- remove the gate entirely: rejected. the gate catches environment drift (wrong role, wrong warehouse, missing permissions) that would cause errors later in the session.

## consequences

- every prompt in `docs/prompts.md` now starts with the gate instruction
- the gate will still be skipped if the user does not paste the prompt exactly (e.g. ad-hoc prompts)
- this pattern generalizes: any step that must happen before the main task should appear as the first line of the prompt, not only in AGENTS.md
- AGENTS.md constraints remain as documentation and secondary reinforcement - they are not removed, but they are not relied on as the primary enforcement mechanism

## related

- [adr-005](adr-005-session-start-gate.md): original session start gate decision (enforcement via AGENTS.md - insufficient)
- [adr-004](adr-004-prompt-stop-gates.md): stop-gate pattern for prompts
- `docs/prompts.md`: prompts 1-4 with gate instruction added

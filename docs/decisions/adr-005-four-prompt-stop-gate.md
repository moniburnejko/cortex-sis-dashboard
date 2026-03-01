# adr-005: prompt stop-gates

**date:** 2026-03-01
**source:** docs/prompts.md, phase_01_run_01.md (deviation: agent did not stop)

## problem

without explicit stop conditions, the agent proceeded through phases without waiting for user confirmation. a bug identified in phase 1 (incorrect ddl) propagated through phases 2-4 because the agent did not pause for review. by the time of the code review (phase_03_run_01), the code contained 5+ issues, several of them critical (sql injection).

## decision

4 prompts, each ending with an explicit stop condition + waiting for user confirmation. structure:
- prompt 1: phase 1 (ddl + stored procedures): STOP, review output
- prompt 2: phase 2 (dashboard pages 1-3): STOP, review output
- prompt 3: phase 3 (deploy + verify): STOP, review output
- prompt 4: pre-deploy security scan: STOP, review output
- prompt 5 (added 2026-03-01): post-deployment security scan. verifies BUG-001/002/003 fixes

## alternatives considered

- **single large prompt**: agent proceeds through all phases autonomously. rejected: no control; an early-phase bug propagates to the end.
- **8+ prompts**: one per task. rejected: too granular; context is lost between prompts; management overhead.
- **prompts without stop conditions**: relying on default agent behavior. rejected: agent does not know when to stop (identified pattern in phase_01_run_01).

## consequences

- longer session time (4 separate interactions instead of 1)
- full user control at each checkpoint
- `docs/prompts.md` becomes a required artifact. must be up to date before each session
- stop conditions must be explicit in the prompt: "STOP. do not proceed to phase 2 until confirmed."
- prompt 5 as an optional post-deployment scan, triggered when a code review identifies security issues

## related

- [adr-006](adr-006-session-start-gate.md): session start gate (related control pattern)
- `docs/prompts.md`: current prompt set with stop conditions

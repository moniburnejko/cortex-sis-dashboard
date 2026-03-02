# adr-013: hooks-based enforcement for session start gate

**date:** 2026-03-02
**source:** phase_02_run_05.md, phase_03_run_02.md, docs/coco_cli_features/hooks.md

## problem

adr-012 identified session hooks as the ideal enforcement mechanism for the session start gate but recorded them as "not available in current cortex code cli." that assessment was wrong - the user subsequently found `docs/coco_cli_features/hooks.md`, which documents a full hooks system including `SessionStart`, `PreCompact`, and `type: "prompt"` hooks.

prompt-text enforcement (adr-012) works when the user pastes the exact prompt. it fails for:
- ad-hoc prompts that do not include the gate instruction
- prompt 5, which was missing the gate instruction until this change
- any session where the user forgets to paste or modifies the prompt

## decision

implement a `type: "prompt"` `SessionStart` hook in `.cortex/hooks.json`.

add a second `PreCompact` hook to reinject key project context before context compaction in long sessions.

retain the gate instruction in `docs/prompts.md` prompt texts (belt-and-suspenders).

## alternatives considered

- `type: "command"` hook with a shell script: requires an absolute path. project-level hooks committed to git must work across machines with different home directories. rejected for portability.
- `PreToolUse` blocking hook for deploy: would block any bash call matching the deploy command, including legitimate ones. requires `type: "command"` (same portability issue). rejected - fragile, low value vs risk of false blocks.
- remove gate from prompt texts now that hooks exist: rejected. belt-and-suspenders is safer. prompt text also documents intent for readers of the prompts file.
- `type: "prompt"` hook with `source` filtering: the hooks documentation shows `source` ("startup" | "resume" | "clear" | "compact") is available in hook input stdin for command hooks, not in prompt hooks. the gate prompt text handles resume cases with inline instruction: "if this is a resumed session and both gate skills passed earlier in this conversation, you may skip."

## consequences

- gate is enforced at runtime level for all sessions, including ad-hoc ones not using `docs/prompts.md`
- prompt 5 gate gap closed (previously missing)
- `PreCompact` hook prevents environment drift in long sessions (phase_02_run_05 + phase_03_run_02 ran as a single session that spanned compaction)
- `.cortex/hooks.json` is committed to git - hooks apply to anyone running cortex in this project directory
- hooks config is snapshotted at session start per hooks documentation

## related

- [adr-012](adr-012-prompt-vs-agents-enforcement.md): prompt-text enforcement - superseded for ad-hoc prompts; retained as secondary reinforcement
- [adr-005](adr-005-session-start-gate.md): original session start gate decision
- `.cortex/hooks.json`: implementation
- `docs/hooks.md`: setup and reference

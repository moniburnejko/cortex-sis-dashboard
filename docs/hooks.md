# hooks

## what hooks are

cortex code cli hooks inject instructions or run scripts at specific points in a session.
this project uses `type: "prompt"` hooks, which inject text into the agent.
no shell scripts or absolute paths required - the json config is the entire implementation.

## hook file location

cortex code cli loads hooks exclusively from `~/.snowflake/cortex/hooks.json`.
the project-level `.cortex/hooks.json` is not auto-loaded.

verify the file is in place and valid json before running cortex:

```bash
cat ~/.snowflake/cortex/hooks.json
python3 -m json.tool ~/.snowflake/cortex/hooks.json
```

## active hooks

- `SessionStart`: injects the session start gate - agent must invoke `$ check-local-environment` and `$ check-snowflake-context` before any work
- `PreCompact`: reinjects key project context (re-reads AGENTS.md) before context compaction
- `PreToolUse` (matcher: `snowflake_.*`): soft warning before any direct snowflake tool call - reminds agent to prefer skill invocations over raw SQL

## enforcement model

in practice, `type: "prompt"` hooks are soft: the agent receives the injected text
but may prioritize an explicit user task over the gate instruction.

observed behavior:
- `SessionStart` hook fires and injects the gate prompt - but agent can still skip the gate if the user's first message is an explicit task
- `~/.snowflake/cortex/memory/operational-protocol.md` is what reliably enforces the gate - the agent reads `/memories` automatically and treats it as authoritative
- `PreCompact` is effective - reinjects context before compaction when the agent has no competing task to prioritize
- `PreToolUse` is effective as a soft reminder before direct snowflake tool calls

primary enforcement: `~/.snowflake/cortex/memory/operational-protocol.md`
secondary enforcement: `SessionStart` hook (belt-and-suspenders, may be strengthened in future cli versions)

### why sessionstart hook is kept

even if it does not reliably block, it adds another injection point for the gate instruction.
if cortex code cli strengthens how `type: "prompt"` hooks interact with user tasks in a future
version, the hook will become a first-class enforcement mechanism without any config change.

### why precompact

long sessions (phase_02_run_05 + phase_03_run_02 ran as one session) trigger compaction. the hook reinjects environment values and mandatory skill requirements into the compressed context, preventing drift.

### why pretooluse

skill invocations are preferable to raw SQL for context and validation. the hook provides a checkpoint before each `snowflake_.*` tool call without blocking legitimate calls.

## testing

1. verify the hook file exists in the correct location:

```bash
ls ~/.snowflake/cortex/hooks.json
```

2. start a new cortex session in the project directory:

```
cd /path/to/dashboard-sis
cortex
```

3. the agent's first message should include gate invocation (`$ check-local-environment`, then `$ check-snowflake-context`) without any prompt instruction from you.

4. enable debug logging to see hook execution:

```bash
SNOVA_DEBUG=true cortex
```

## disabling a hook temporarily

add `"enabled": false` to the hook entry in `~/.snowflake/cortex/hooks.json`:

```json
{
  "type": "prompt",
  "prompt": "...",
  "timeout": 10,
  "enabled": false
}
```

remove the field (or set to `true`) to re-enable.

## related

- `.cortex/hooks.json`: template - copy to `~/.snowflake/cortex/hooks.json` to activate
- `docs/decisions/adr-013-hooks-enforcement.md`: decision record

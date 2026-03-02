# hooks

## what hooks are

cortex code cli hooks inject instructions or run scripts at specific points in a session.
this project uses `type: "prompt"` hooks, which inject text into the agent.
no shell scripts or absolute paths required - the json config is the entire implementation.

config file: `.cortex/hooks.json` (committed to git, auto-loaded when running `cortex` in the project directory).

## active hooks

| event | purpose |
|---|---|
| `SessionStart` | injects the session start gate instruction - agent must run `$ check-local-environment` and `$ check-snowflake-context` before any work |
| `PreCompact` | reinjects key project facts (environment, mandatory skills, security rule) before context compaction |

### why sessionstart

the gate was documented in `AGENTS.md` (adr-005) and in prompt texts (adr-012) but bypassed in ad-hoc sessions and when prompts were modified. the hook fires regardless of what the user types.

### why precompact

long sessions (phase_02_run_05 + phase_03_run_02 ran as one session) trigger compaction. the hook reinjects environment values and mandatory skill requirements into the compressed context, preventing drift.

## testing

start a new cortex session in the project directory:

```
cd /path/to/dashboard-sis
cortex
```

the agent's first message should include gate invocation (`$ check-local-environment`, then `$ check-snowflake-context`) without any prompt instruction from you.

validate the json before committing:

```bash
python3 -m json.tool .cortex/hooks.json
```

enable debug logging to see hook execution:

```bash
SNOVA_DEBUG=true cortex
```

## disabling a hook temporarily

add `"enabled": false` to the hook entry:

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

- `.cortex/hooks.json`: hook configuration
- `docs/decisions/adr-013-hooks-enforcement.md`: decision record

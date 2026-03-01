# adr-004: project vs personal skills

**date:** 2026-03-01
**source:** phase_01_run_01_5.md, phase_01_run_02.md (deviation: skill path resolution)

## problem

cortex code cli resolves skill paths from two locations: `~/.snowflake/cortex/skills/` (personal) and `.cortex/skills/` (project). in phase_01_run_01_5, the agent resolved sub-skill paths (`build-dashboard`, `brand-identity`, etc.) from personal skills instead of the project. sub-skills were unavailable or stale. projects cloned to a new machine lost all personal skills.

## decision

split by responsibility:
- **project skills** (`.cortex/skills/`, committed to git): `sis-dashboard`, `sis-streamlit`, and all sub-skills (`build-dashboard`, `brand-identity`, `sis-patterns`, `deploy-and-verify`, `secure-dml`). project-specific, should travel with the repository
- **personal skills** (`~/.snowflake/cortex/skills/`, not committed): `sis-streamlit` entry point and `check-local-environment`. depend on the local snowflake environment configuration

## alternatives considered

- **everything in personal skills**: portable across projects but not across machines and not versioned with code. rejected: no reproducibility.
- **everything in project skills**: possible, but the entry-point skill depends on local snowflake config. rejected: violates separation of concerns (local config vs project spec).
- **symlinks**: between personal and project. rejected: brittle, breaks after cloning to a new machine.

## consequences

- the project requires only 2 personal skills installed on a new machine (`sis-streamlit` entry point + `check-local-environment`)
- sis-dashboard routing always uses paths relative to the project (`.cortex/skills/...`)
- new sub-skills (e.g. `secure-dml`) are added exclusively to `.cortex/skills/sis-streamlit/skills/` and committed

## related

- [adr-009](adr-009-secure-dml-standalone-skill.md): new sub-skill added to project skills
- `.cortex/skills/sis-dashboard/SKILL.md`: routing table
- `.cortex/skills/sis-streamlit/SKILL.md`: standard workflow sequence

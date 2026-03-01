# adr-009: secure-dml skill

**date:** 2026-03-01
**source:** session 2026-03-01

## problem

the stored procedure patterns for dml needed to be documented somewhere accessible to the agent before it writes page 2 and page 3 code. options were: inline in AGENTS.md, inline in build-dashboard, or a separate skill. the choice affects how the agent loads the material and how maintainable it is.

## decision

a separate sub-skill `secure-dml/SKILL.md`: one file, one responsibility. ddl definitions and `session.call()` patterns for `INSERT_RENEWAL_FLAG` and `UPDATE_RENEWAL_FLAG`. the agent loads this skill before writing the flag form on page 2 and the review form on page 3.

## alternatives considered

- **inline in AGENTS.md**: easy to find, but the section would become very long; AGENTS.md is a spec, not an implementation reference. rejected: wrong file for ddl content.
- **inline in build-dashboard**: build-dashboard is a validator/scanner, not a pattern library. mixing scan instructions with ddl creates a confusing single file. rejected: wrong responsibility.
- **note only in AGENTS.md security rule 7 (no ddl)**: without the ddl the agent must guess the procedure signatures. rejected: guessing leads to mismatched call signatures.

## consequences

- skill visible in the routing table in `sis-dashboard/SKILL.md` and `sis-streamlit/SKILL.md`
- new step 8 in the standard workflow sequence: "load secure-dml before writing flag form"
- agent MUST load it before the flag form code. enforced by an AGENTS.md constraint
- follows adr-004: placed in `.cortex/skills/sis-streamlit/skills/secure-dml/` and committed to git

## related

- [adr-004](adr-004-project-vs-personal-skills.md): project skills location
- [adr-008](adr-008-dml-stored-procedures.md): the dml patterns this skill documents
- `.cortex/skills/sis-streamlit/skills/secure-dml/SKILL.md`
- `.cortex/skills/sis-dashboard/SKILL.md`: routing table
- AGENTS.md: constraint referencing secure-dml

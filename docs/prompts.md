# prompts: renewal radar sis dashboard

## before you start

complete these steps before launching cortex code cli:

1. install skills
   - project skills in `.cortex/skills/` (shared via git):
     check-snowflake-context, prepare-data,
     sis-streamlit sub-skills:
     sis-patterns, build-dashboard, brand-identity, deploy-and-verify, secure-dml
   - personal skills in `~/.snowflake/cortex/skills/` (do not commit):
     check-local-environment, sis-streamlit
     NOTE: sis-streamlit sub-skills live in `.cortex/skills/sis-streamlit/skills/`.
     invoke `$ sis-streamlit` which routes to sub-skills via project-relative paths.

2. copy AGENTS.md to the project root.
   cortex code cli loads it automatically from the working directory.

3. place the 3 csv files under `data/` as defined in AGENTS.md.

4. start the session:
   ```
   cd /path/to/your/project
   cortex
   ```

---

## session guidance

### when to use /plan mode

- **prompt 3** (dashboard build): the agent will generate a large Python file.
  enter `/plan` before pasting the prompt so you can review the approach
  before code is written.
- **any time the agent does something unexpected**: enter `/plan` and ask
  what it intends.
- do NOT use `/plan` for prompts 1, 2, or 4. those are deterministic
  sequences where planning adds no value.

### what to watch during execution

- the agent should use idempotent DDL. watch that it does not DROP
  existing objects.
- the agent must stay within the schema defined in AGENTS.md.
- if the agent writes INSERT or UPDATE using f-strings with values from
  `st.text_input`, `st.text_area`, or any user widget: **stop it immediately.**
  require `$ sis-streamlit -> secure-dml` before any DML code is written.
  the fix requires a stored procedure, not whitelist validation.
- if the agent builds SQL with f-strings using user-selected filter values
  (regions, segments, channels in IN-clauses): stop and ask for whitelist
  validation per security rule 3 in AGENTS.md.
- if the agent skips `$ check-local-environment` or `$ check-snowflake-context`
  at session start and proceeds directly to SQL or code: remind it to use the
  skills. direct SQL checks or memory file checks are not equivalent.
- if the agent runs pre-deploy scan as manual grep/bash commands instead of
  `$ sis-streamlit -> build-dashboard dashboard.py`: remind it to use the skill.
  the skill includes DML injection checks and audit event presence checks that
  manual grep sequences miss.
- ADD SEARCH OPTIMIZATION may return "already exists." this is expected.

### error reporting template

if a runtime error appears at any phase, paste this to the agent:

```
runtime error after [phase/deploy]:
- error: [full error text from Snowflake or Streamlit]
- page: [page 1/2/3, if applicable]
- what i did: [what i clicked or changed before the error]

scan the entire file for all occurrences of the same error class
before fixing. fix all occurrences at once, then redeploy.
```

the "scan the entire file" instruction is critical. without it the agent
fixes one occurrence and the same error class surfaces on the next
interaction.

---

## prompt 1: infrastructure

```
invoke $ check-local-environment, then $ check-snowflake-context. do not proceed until both pass.

set up phase 1 infrastructure: logging objects, domain table, stage,
and source tables.
do not load csv data yet.
stop and report what was created. do not run the phase 1 acceptance checks - those run in prompt 2.
```

### checkpoint 1

the agent should produce a phase report covering:
- objects created (event table, audit log, view, procedure, domain table, stage, source tables)
- pass/fail for each object verification check
- any issues encountered and how they were resolved

if all correct, proceed to prompt 2.
if anything is missing, tell the agent what is missing.

---

## prompt 2: data load

```
invoke $ check-local-environment, then $ check-snowflake-context. do not proceed until both pass.

validate and load all 3 csv files into the source tables.
log the data load operation.
use $ sis-streamlit to run the phase 1 acceptance checks and show the full results.
stop and wait for my confirmation.
```

### checkpoint 2

the agent should produce a phase report covering:
- files validated and loaded (row counts per table)
- pass/fail for each phase 1 acceptance criterion
- any issues encountered and how they were resolved

all phase 1 criteria should pass. key things to check:
- row counts are in the expected range
- agent operation is logged in the audit log

if all pass:
```
phase 1 verified. proceed to phase 2.
```

if anything fails, tell the agent exactly what failed (use template from session guidance).

---

## prompt 3: dashboard build and deploy

enter `/plan` before pasting this prompt.

```
invoke $ check-local-environment, then $ check-snowflake-context. do not proceed until both pass.

phase 1 is complete. all infrastructure and data are in place.
build and deploy the dashboard.
stop after showing the app url and wait for my confirmation
that all 3 pages render correctly.
```

### checkpoint 3

open the app url and interact with all 3 pages:

**page 1 (renewal KPI overview):**
- 4 kpi cards show values (not None or NaN)
- 3 charts display data
- sidebar filters work (region, segment, channel, date range)
- change a filter, then go to page 3 tab 1: a FILTER_CHANGE row must appear
  with your username and a timestamp within the last 5 minutes.
  if no new row appears: FILTER_CHANGE logging is missing from the code.

**page 2 (premium pressure analysis):**
- 3 kpi cards at top
- bar charts and heatmap display data
- sidebar has region, segment, channel, date range + "Final Offers Only" toggle
- "flag for review" section works: submit a flag, see st.success with a flag_id
  (st.success MUST show a UUID like "Flag submitted: 3f9a1c42-...", NOT the scope string)

**page 3 (activity log):**
- tab 1: user interactions table with your username in USER_NAME (not NULL or a service account)
- tab 1: review flags section with "mark reviewed" button. FLAGGED_BY shows your username.
- tab 2: agent operations table
- select a flag, add a review comment, click "mark reviewed"

if everything works:
```
checkpoint 3 verified. all 3 pages render correctly.
i have tested filter changes on page 1, flag submission on page 2,
and flag review on page 3. my username appears in USER_NAME and FLAGGED_BY.
```

if an error appears, use the error reporting template from the session
guidance section.

**after checkpoint 3 passes:** commit dashboard.py to git.
this enables git diff verification for any subsequent changes and allows
the agent to verify what changed between deploys.

---

## prompt 4: final verification

```
invoke $ check-local-environment, then $ check-snowflake-context. do not proceed until both pass.

use $ sis-streamlit to run the full acceptance check across all phases.
for the manual app-renders criterion, mark it as confirmed,
i have already verified it.
if any criterion fails, report the root cause but do not
attempt fixes. wait for my decision.
```

### checkpoint 4

the agent should produce a final report covering:
- pass/fail table for all 16 criteria (15 automated + 1 manual)
- any issues found and root cause analysis
- recommendations

target: 15/15 automated checks pass + 1 manual confirmed.

if all pass, the project is complete.
if anything fails, decide whether to fix and re-run or accept.

---

## prompt 5: post-deployment code review (run after checkpoint 3)

this is a security and completeness scan of the deployed dashboard.py.
run it after checkpoint 3 passes and after committing to git.

```
use $ sis-streamlit -> build-dashboard dashboard.py to run a full
post-deployment security scan of the file.
report every issue found including:
- any session.sql(f matches containing INSERT or UPDATE
- FILTER_CHANGE, FLAG_ADDED, FLAG_REVIEWED presence (each must be >= 1)
- session.call( count (must be >= 2)
- any other forbidden patterns

do not attempt fixes. wait for my decision.
```

### checkpoint 5

the scan report should show:
- DML injection: 0 `session.sql(f` matches with INSERT/UPDATE
- `session.call(` count >= 2
- FILTER_CHANGE, FLAG_ADDED, FLAG_REVIEWED: each >= 1
- forbidden API patterns: all 0
- style: 0 FAIL results (WARNs are acceptable)

if any security issue is found: do not proceed until it is fixed and
the scan is re-run clean.

this prompt catches issues introduced during incremental editing after
the initial deploy. the pre-deploy scan before deployment 1 does not
cover changes made in subsequent edit cycles.

---

## why 5 prompts

each prompt ends with a stop condition and waits for user confirmation:

- **prompt 1** ensures infrastructure exists before data is loaded.
  catching DDL or permission failures here prevents cascading errors
  in data load.
- **prompt 2** ensures data is in Snowflake before any code is written.
  row count mismatches caught here prevent dashboard bugs.
- **prompt 3** ensures the dashboard is deployed and working before
  verification queries check for user interaction records.
- **prompt 4** runs the full acceptance sweep after the user has
  interacted with all features.
- **prompt 5** runs a post-deployment security scan: checks for DML injection,
  audit event presence, and forbidden patterns introduced during incremental editing.

without stopping after each phase, a misunderstanding in phase 1
compounds through subsequent phases, making it harder to debug.

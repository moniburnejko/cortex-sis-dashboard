# final report: renewal radar sis dashboard

**date:** 2026-03-01
**scope:** phase 1 (run 02), phase 2 (run 04), phase 3 (run 01), code review
**environment:** CORTEX_DB.CORTEX_SCHEMA, role CORTEX_ADMIN, warehouse CORTEX_WH
**model:** claude-sonnet-4-5
**dashboard:** RENEWAL_RADAR (707 lines, 3 pages, deployed at CORTEX_DB.CORTEX_SCHEMA)

---

## 1. executive summary

the renewal radar sis dashboard was built and deployed across 3 phases using cortex code cli
with an AGENTS.md-driven skill orchestration framework. the project tested whether an ai agent
can follow a structured spec (AGENTS.md), invoke skills in the correct order, and produce a
production-quality streamlit in snowflake dashboard.

**key outcomes:**
- dashboard is functional: 3 pages render with data, flag submission and review work, display labels applied
- all numerical acceptance checks pass (8 phase 1 + 3 phase 2 + 5 phase 3 = 16 total)
- 2 critical sql injection vulnerabilities remain in the deployed code
- 1 required feature (FILTER_CHANGE logging) is missing from the current code
- skill compliance was partial across all phases: session start gate consistently skipped, scans and deploys executed as direct commands instead of through skills
- the agent-generated final report (ccc_report.md) contains false claims about security and completeness

---

## 2. phase summaries

### phase 1: infrastructure and data load (phase_01_run_02.md)

**status:** complete, all 8/8 acceptance checks passed

phase 1 established the snowflake infrastructure and loaded source data. executed across 2 prompts
in 2 separate sessions.

| deliverable | result |
|---|---|
| logging objects (`APP_EVENTS`, `AUDIT_LOG`, `V_APP_EVENTS`, `LOG_AUDIT_EVENT`) | created, all functional |
| domain table (`RENEWAL_FLAGS`) | created |
| stage (`STAGE_RAW_CSV`) | created |
| source tables (`FACT_RENEWAL`, `FACT_PREMIUM_EVENT`, `DIM_POLICY`) | created, loaded |
| `FACT_RENEWAL` rows | 50,000 |
| `FACT_PREMIUM_EVENT` rows | 94,642 |
| `DIM_POLICY` rows | 36,298 |
| audit log entry for data load | present (2 events) |

**skill compliance:** all 4 mandatory skills invoked correctly in prompt 2. session start gate
passed in both sessions. `$ prepare-data` executed all 8 steps including gzip compression,
PUT, COPY INTO, and row count verification.

**deviations found:** 4 total, 2 addressed post-session (stopping point rule tightened,
skill path resolution fixed via renaming sis-streamlit). 2 non-critical (step order variation,
post-ddl verification queries).

---

### phase 2: dashboard build and deploy (phase_02_run_04.md)

**status:** dashboard deployed after 5 deploy cycles across 2 sessions

phase 2 built the 3-page dashboard from scratch (574 lines), then refined it through bug fixes,
display-label additions, and scope corrections (final: 707 lines).

| deliverable | result |
|---|---|
| dashboard.py | 707 lines, 3 pages, deployed |
| environment.yml | correct (streamlit 1.52.*, pandas, altair) |
| snowflake.yml | correct format |
| page 1: kpi overview | renewal rate, trends, outcomes by region |
| page 2: premium pressure | heatmap, premium change charts, band analysis |
| page 3: flag management | flag submission, review, audit log |
| display-label layer | 6 mapping dictionaries, all charts/filters/tables use human-readable labels |
| deploy cycles | 5 total (1 runtime error fix, 1 bug fix, 1 display-label, 1 scope fix, 1 db correction) |

**skill compliance:** partial. `$ sis-streamlit` loaded in both sessions. sub-skills (build-dashboard,
brand-identity, sis-patterns) read correctly. however:
- session start gate not invoked in either session
- pre-deploy scan ran as direct bash commands (not via skill invocation) in all 5 cycles
- `session.sql(f` parameterization check never executed in any scan
- brand-identity not loaded before display-label work

**deviations found:** 7 total. 1 fixed in-session (scope_parts.append bug). 6 remain as open patterns.

---

### phase 3: write-back verification (phase_03_run_01.md)

**status:** all 5 sql checks pass numerically, but with caveats

phase 3 verified flag submission, flag review, and audit logging via 5 sql threshold checks.

| check | expected | actual | status |
|---|---|---|---|
| FILTER_CHANGE events in `AUDIT_LOG` | >= 1 | 30 | PASS (misleading, see bugs section) |
| open flags in `RENEWAL_FLAGS` | >= 1 | 5 | PASS |
| FLAG_ADDED events in `AUDIT_LOG` | >= 1 | 6 | PASS |
| reviewed flags with reviewed_by | >= 1 | 6 | PASS |
| FLAG_REVIEWED events in `AUDIT_LOG` | >= 1 | 2 | PASS |

**skill compliance:** `$ sis-dashboard` not invoked. all checks ran manually via SNOWFLAKE_SQL_EXECUTE.
same bypass pattern as all prior runs.

**ccc_report.md accuracy:** the agent-generated final report contains multiple errors:
- criterion #13 reports wrong name and value (11 total flags instead of 5 open)
- claims "parameterized sql with whitelist validation" (false)
- claims "no issues found, no fixes required" (false)
- does not identify any of the remaining issues documented in the code review

---

### code review: dashboard.py (code_review_dashboard.md)

**status:** 6 issues identified, 0 fixed

independent code review of the final 707-line dashboard.py, performed after the agent declared
the project complete.

| # | issue | severity | status |
|---|---|---|---|
| 1.1 | sql injection in INSERT (flag_reason) | critical | open |
| 1.2 | sql injection in UPDATE (review_notes) | critical | open |
| 1.3 | CURRENT_SIS_USER in f-string sql | low | open |
| 1.4 | whitelist-validated filters in f-string sql | low | open |
| 1.5 | date values in f-string sql | minimal | open |
| 2 | missing FILTER_CHANGE audit logging | high | open |
| 3 | missing flag_id in st.success | medium | open |
| 4 | heatmap ignores segment/channel filters | medium | open |
| 5 | LAPSED and NOT_TAKEN_UP share same color | low | open |
| 6 | module-level session vs sis-patterns contradiction | info | open |

---

## 3. comprehensive bug and issue registry

### 3.1 critical issues (require immediate fix before any production use)

#### BUG-001: sql injection in INSERT via flag_reason
- **source:** code_review_dashboard.md issue 1.1
- **location:** dashboard.py lines 557-565
- **description:** `flag_reason` from `st.text_input()` is interpolated directly into an INSERT
  f-string sql statement. a user can type `'); DROP TABLE RENEWAL_FLAGS; --` to execute
  arbitrary sql.
- **status:** OPEN, not fixed
- **detected by:** manual code review (not caught by any agent scan)
- **why it was missed:** the `session.sql(f` parameterization check in build-dashboard SKILL.md
  was never executed during any of the 5 pre-deploy scans. the agent ran its own subset of
  pattern checks but consistently skipped this one.
- **proposed fix (option A, preferred):** create an `INSERT_RENEWAL_FLAG` stored procedure that
  accepts all values as parameters and performs the INSERT internally. call it via
  `session.call()`:
  ```python
  flag_id = session.call(
      f"{DATABASE}.{SCHEMA}.INSERT_RENEWAL_FLAG",
      CURRENT_SIS_USER, scope, scope_region, scope_segment, scope_channel, flag_reason
  )
  st.success(f"Flag submitted: {flag_id}")
  ```
  this also resolves BUG-004 (missing flag_id return).
- **proposed fix (option B):** use snowpark DataFrame api with `lit()` for all values:
  ```python
  from snowflake.snowpark.functions import lit
  session.table(f"{DATABASE}.{SCHEMA}.RENEWAL_FLAGS").insert([
      lit(CURRENT_SIS_USER), lit(scope), lit(scope_region),
      lit(scope_segment), lit(scope_channel), lit(flag_reason)
  ])
  ```
- **AGENTS.md change needed:** expand security rule 3 to cover INSERT/UPDATE with user text input.
  current rule only covers IN-list filter validation.

#### BUG-002: sql injection in UPDATE via review_notes
- **source:** code_review_dashboard.md issue 1.2
- **location:** dashboard.py lines 660-669
- **description:** `review_notes` from `st.text_area()` is interpolated directly into an UPDATE
  f-string sql statement. same injection risk as BUG-001.
- **status:** OPEN, not fixed
- **detected by:** manual code review
- **why it was missed:** same root cause as BUG-001
- **proposed fix (option A, preferred):** create an `UPDATE_RENEWAL_FLAG` stored procedure.
  call via `session.call()`:
  ```python
  session.call(
      f"{DATABASE}.{SCHEMA}.UPDATE_RENEWAL_FLAG",
      CURRENT_SIS_USER, review_notes, flag_ids_str
  )
  ```
- **proposed fix (option B):** use parameterized sql via snowpark.
- **AGENTS.md change needed:** same as BUG-001.

---

### 3.2 high severity issues (significant functional gap)

#### BUG-003: missing FILTER_CHANGE audit logging
- **source:** code_review_dashboard.md issue 2, phase_03_run_01.md issue 1
- **location:** dashboard.py (entire file, 0 occurrences of FILTER_CHANGE)
- **description:** AGENTS.md requires `log_audit_event("FILTER_CHANGE", ...)` on every sidebar
  filter change on pages 1 and 2. the current dashboard.py contains zero FILTER_CHANGE logging
  code. the 30 FILTER_CHANGE events in `AUDIT_LOG` exist from a prior dashboard version.
- **status:** OPEN, not fixed
- **detected by:** code review + phase 3 analysis
- **consequence:** if `AUDIT_LOG` were cleared and the current dashboard tested from scratch, the
  phase 3 check #1 (FILTER_CHANGE >= 1) would FAIL. the numerical pass is based on stale data.
- **proposed fix:** add `on_change` callbacks to all sidebar multiselect and date_input widgets:
  ```python
  def on_filter_change():
      log_audit_event("FILTER_CHANGE", "USER_INTERACTION", current_page,
                      "sidebar_filters", "multiselect_change")

  sel_regions = st.sidebar.multiselect(
      "Region", VALID_REGIONS, key="sel_regions",
      format_func=lambda x: REGION_LABELS.get(x, x),
      on_change=on_filter_change
  )
  ```
- **note:** `on_change` in sis requires careful testing to avoid spurious logging on first render.
- **AGENTS.md change needed:** add FILTER_CHANGE as a mandatory pattern check in build-dashboard
  scan mode: `grep -c "FILTER_CHANGE" <file>` must be >= 1.

---

### 3.3 medium severity issues (functional gaps, not security-critical)

#### BUG-004: missing flag_id in st.success after flag submission
- **source:** code_review_dashboard.md issue 3
- **location:** dashboard.py line 570
- **description:** AGENTS.md line 673 requires "show st.success() with the returned flag_id."
  the current code shows scope instead: `st.success(f"Flag submitted successfully: {scope}")`.
  the INSERT does not return the generated uuid.
- **status:** OPEN, not fixed
- **detected by:** manual code review
- **proposed fix:** resolved together with BUG-001 if using stored procedure approach (option A).
  the procedure returns the flag_id which is then displayed in st.success.
- **AGENTS.md change needed:** clarify the flag_id return mechanism (currently spec says "returned
  flag_id" but does not specify how to obtain it from INSERT).

#### BUG-005: heatmap ignores segment and channel filters
- **source:** code_review_dashboard.md issue 4
- **location:** dashboard.py lines 455-476 (load_heatmap_data function)
- **description:** the heatmap data loader accepts `segments` and `channels` parameters but only
  applies region filtering after pandas conversion. segment and channel sidebar selections are
  ignored for the heatmap visualization.
- **status:** OPEN, not fixed
- **detected by:** manual code review
- **proposed fix:** add pandas filtering for segment and channel:
  ```python
  df = df[
      (df['region'].isin(regions)) &
      (df['segment'].isin(segments)) &
      (df['channel'].isin(channels))
  ]
  ```
- **AGENTS.md change needed:** add explicit note to page 2 heatmap spec that all sidebar filters
  must apply.

---

### 3.4 low severity issues (visual, style, minor inconsistencies)

#### BUG-006: LAPSED and NOT_TAKEN_UP share same color
- **source:** code_review_dashboard.md issue 5
- **location:** dashboard.py lines 293-295
- **description:** the outcome color scale maps both LAPSED and NOT_TAKEN_UP to #FFA726 (accent
  orange), making them visually indistinguishable in stacked bar charts.
- **status:** OPEN, not fixed
- **detected by:** manual code review
- **proposed fix:** differentiate with a darker accent shade:
  ```python
  range=["#1565C0", "#FFA726", "#FB8C00", "#E53935"]
  ```
- **brand-identity change needed:** add explicit outcome color mapping to skill file.

#### BUG-007: CURRENT_SIS_USER in f-string sql
- **source:** code_review_dashboard.md issue 1.3
- **location:** dashboard.py lines 560, 663, 667
- **description:** `CURRENT_SIS_USER` (from `st.user.user_name`) is interpolated directly into
  f-string sql. this is a system value (not user-editable), so practical injection risk is low.
  however, it violates parameterized sql best practices.
- **status:** OPEN
- **proposed fix:** resolved together with BUG-001/BUG-002 if using stored procedure approach.

#### BUG-008: whitelist-validated filter values in f-string sql
- **source:** code_review_dashboard.md issue 1.4
- **location:** dashboard.py lines 232-236, 418-422
- **description:** filter values (regions, segments, channels) are whitelist-validated but still
  interpolated via f-string `.join()` into sql. AGENTS.md security rule 3 specifies snowpark
  DataFrame api (`session.table().filter(col().isin())`), not f-string sql.
- **status:** OPEN
- **proposed fix:** rewrite to snowpark DataFrame api, or document as accepted exception for
  aggregate queries with DATE_TRUNC.

#### BUG-009: module-level session vs sis-patterns contradiction
- **source:** code_review_dashboard.md issue 6
- **location:** dashboard.py line 12, sis-patterns SKILL.md section 1, build-dashboard scaffold
- **description:** build-dashboard scaffold places `session = get_active_session()` at module level.
  sis-patterns says "inside functions only." both are loaded before code generation, creating
  a contradiction.
- **status:** OPEN (informational)
- **proposed fix (recommended):** update sis-patterns to clarify: module-level is acceptable for
  non-cached code; `@st.cache_data` functions must call `get_active_session()` inside the function.

---

### 3.5 issues found and fixed during development

these issues were detected and resolved during the phase 1-3 execution sessions.

| issue | phase | severity | description | how detected | resolution |
|---|---|---|---|---|---|
| skill bypass gap | 1 (run 01) | high | agent did not invoke `$ sis-dashboard` for acceptance checks | manual review of run 01 | prompt 2 updated to explicitly say "use $ sis-dashboard" |
| stopping point ambiguity | 1 (run 02) | medium | agent asked phase selection despite clear prompt | session observation | sis-dashboard SKILL.md stopping points rewritten with explicit conditions |
| skill path resolution | 1 (run 02) | medium | sub-skill path resolved from personal skills location instead of project | session observation | project skill renamed to sis-streamlit, routing paths corrected |
| TypeError: pandas.Series in snowpark filter | 2 (run 04) | high | `pd.Series().isin()` passed to snowpark `.filter()` | runtime error after deploy | removed snowpark filter, kept pandas filtering |
| outcome chart single bar | 2 (run 04) | medium | chart showed only RENEWED bar, missing 3 other outcomes | user testing | added JOIN to `FACT_RENEWAL` for authoritative renewal_outcome |
| raw field names in axis titles | 2 (run 04) | low | axis titles showed "renewal_outcome", "avg_change" etc. | user testing | added `title=` parameters to altair encodings |
| scope_parts.append bug | 2 (run 04) | medium | agent wrote `append(flag_region)` instead of `append("REGION")` during display-label refactoring | user testing | fixed all 3 occurrences, db records corrected via UPDATE |
| stale TX/TN values in `RENEWAL_FLAGS.scope` | 2 (run 04) | low | old flags had TX/TN instead of REGION in scope column | user testing | UPDATE statements to correct 3 rows |
| compound skill syntax error | 2 (run 04) | low | agent tried `$ sis-streamlit -> deploy-and-verify` as literal command | runtime error | agent fell back to reading SKILL.md directly |

---

## 4. skill compliance and agent behavior patterns

### 4.1 cross-phase skill compliance

| skill | phase 1 | phase 2 session 1 | phase 2 session 2 | phase 3 |
|---|---|---|---|---|
| `$ check-local-environment` | PASS | FAIL (not invoked) | FAIL (not invoked) | FAIL (not invoked) |
| `$ check-snowflake-context` | PASS | FAIL (not invoked) | FAIL (not invoked) | FAIL (not invoked) |
| `$ sis-streamlit` | n/a | PASS | PASS (prompt 1 only) | n/a |
| `$ sis-streamlit` -> sub-skills | n/a | PASS (read) / PARTIAL (execution) | PARTIAL | n/a |
| `$ sis-dashboard` -> `deploy-and-verify` | PASS (with friction) | PARTIAL | PARTIAL | FAIL (not invoked) |
| `$ prepare-data` | PASS | n/a | n/a | n/a |

### 4.2 recurring patterns across all runs

1. **session start gate consistently skipped in phase 2+:** the agent treated memory validation
   or direct sql context checks as equivalent to the mandatory skill invocation. the gate was
   only reliably followed in phase 1 after explicit prompt engineering.

2. **scan and deploy as direct commands:** the agent reads skill SKILL.md files but executes
   steps as direct bash commands rather than through skill orchestration. this causes selective
   step execution, with `session.sql(f` check consistently missed.

3. **prompt wording drives compliance more than AGENTS.md mandates:** when the prompt explicitly
   names a skill (e.g. "use $ sis-dashboard"), the agent invokes it. when the prompt does not
   name the skill, the agent bypasses it even when AGENTS.md mandates it.

4. **agent self-verification is insufficient:** the agent's own pre-deploy scans missed sql
   injection, and the final report (ccc_report.md) contained false claims. the agent does not
   reliably detect its own errors.

5. **agent introduces bugs during refactoring:** the scope_parts.append error was introduced by
   the agent during the display-label implementation. pattern-based scans do not catch logic errors.

---

## 5. ccc_report.md assessment

the agent-generated final report (ccc_report.md) has the following accuracy issues:

| claim in ccc_report.md | reality | severity |
|---|---|---|
| "Parameterized sql with whitelist validation" | sql injection exists in INSERT and UPDATE with user text input | critical misrepresentation |
| "No issues found. No fixes required." | 5+ issues exist including 2 critical sql injections | critical misrepresentation |
| criterion #13: "Flag exists in RENEWAL_FLAGS: 11 flags" | should be "Open flags: 5" per AGENTS.md | factual error |
| FILTER_CHANGE: 30 events, PASS | events are stale from prior version; current code has 0 FILTER_CHANGE logging | misleading |
| "Zero forbidden patterns" | session.sql(f check was never run | incomplete assessment |

**conclusion:** ccc_report.md should NOT be used as a production readiness assessment. it reflects
numerical threshold checks only, not code quality or security posture.

---

## 6. next steps

### 6.1 critical: fix sql injection vulnerabilities (BUG-001, BUG-002)

**priority:** immediate, before any further use of the dashboard

1. create `INSERT_RENEWAL_FLAG` stored procedure in snowflake that accepts all flag fields as
   parameters and returns the generated flag_id uuid
2. create `UPDATE_RENEWAL_FLAG` stored procedure that accepts review_notes, flag_ids, and
   reviewer as parameters
3. replace f-string INSERT (lines 557-565) with `session.call()` to the INSERT procedure
4. replace f-string UPDATE (lines 660-669) with `session.call()` to the UPDATE procedure
5. this also resolves BUG-004 (missing flag_id) and BUG-007 (CURRENT_SIS_USER in f-string)
6. update AGENTS.md security rule 3 to cover dml with user text input
7. add user-input-in-dml check to build-dashboard scan mode

### 6.2 high: implement FILTER_CHANGE logging (BUG-003)

1. add `on_change` callbacks to all sidebar filter widgets (multiselect, date_input) on pages 1 and 2
2. each callback calls `log_audit_event("FILTER_CHANGE", "USER_INTERACTION", page, "sidebar_filters", "multiselect_change")`
3. test carefully in sis to avoid spurious logging on initial render
4. verify by clearing test events and confirming new FILTER_CHANGE events appear after filter interactions
5. add `grep -c "FILTER_CHANGE"` check to build-dashboard scan mode

### 6.3 medium: fix remaining functional issues (BUG-004, BUG-005)

1. **flag_id return** - resolved by 6.1 if using stored procedure approach
2. **heatmap filter gap** - add segment and channel pandas filtering in load_heatmap_data
3. redeploy and verify all 3 pages still render correctly

### 6.4 low: visual and style fixes (BUG-006, BUG-008, BUG-009)

1. differentiate LAPSED/NOT_TAKEN_UP colors in outcome charts
2. consider rewriting filter sql to snowpark DataFrame api (or document exception)
3. resolve sis-patterns vs build-dashboard scaffold contradiction for module-level session

### 6.5 test agents-md-semantic-model branch

the agents-md-semantic-model branch contains updates to the AGENTS.md specification and
potentially the semantic model layer. next steps:

1. review the branch diff against current main to understand scope of changes
2. check if any of the AGENTS.md changes address the issues found in this report (security
   rule 3 expansion, FILTER_CHANGE mandate, flag_id clarification, heatmap filter spec)
3. test a fresh phase 2 build using the updated AGENTS.md to see if skill compliance improves
4. specifically verify whether the `session.sql(f` check is now reliably executed
5. compare agent behavior (session start gate, skill invocation, scan completeness) against
   the baseline established in this report

### 6.6 governance and process improvements

1. **commit dashboard.py after each successful deploy** - enables git diff verification for
   subsequent changes. the agent's inability to verify changes (phase_02_run_04.md deviation 5)
   was caused by the file being untracked.
2. **add post-deployment code review prompt** (prompts.md prompt 5) - runs full build-dashboard
   scan after all edits are complete, catching issues introduced during incremental refinement.
3. **update AGENTS.md memory validation protocol** - change from binary "resume or start fresh"
   to the 3-option pattern (resume / re-run checks / reload) that the agent naturally produced
   in phase 1.
4. **clarify skill invocation syntax** - add note to AGENTS.md that `->` is conceptual routing
   notation, not a compound command. the agent confused this in phase 2 session 2.
5. **regenerate ccc_report.md** - the current version contains false claims and should be
   replaced with an accurate report after all critical fixes are applied.

### 6.7 suggested execution order

```
1. [critical]  fix sql injection (BUG-001, BUG-002) + flag_id return (BUG-004)
2. [critical]  redeploy and verify
3. [high]      implement FILTER_CHANGE logging (BUG-003)
4. [high]      redeploy and verify phase 3 check passes with fresh events
5. [medium]    fix heatmap filter gap (BUG-005)
6. [medium]    redeploy and full regression test
7. [low]       visual/style fixes (BUG-006, BUG-008, BUG-009)
8. [process]   commit dashboard.py to git
9. [process]   update AGENTS.md (security rule 3, FILTER_CHANGE, flag_id, heatmap)
10. [process]  update skills (build-dashboard scan, sis-patterns, brand-identity)
11. [test]     review and test agents-md-semantic-model branch
12. [test]     run fresh phase 2 build with updated AGENTS.md, compare agent behavior
13. [process]  regenerate ccc_report.md with accurate findings
```

---

## 7. appendix: source reports

| report | file | covers |
|---|---|---|
| phase 1 final | phase_01_run_02.md | infrastructure ddl, data load, 8 acceptance checks |
| phase 2 final | phase_02_run_04.md | dashboard build, 5 deploy cycles, display-label layer |
| phase 3 final | phase_03_run_01.md | write-back verification, 5 sql checks, ccc_report.md analysis |
| code review | code_review_dashboard.md | 6 issues in final dashboard.py (707 lines) |

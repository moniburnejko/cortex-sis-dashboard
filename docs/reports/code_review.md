# code review: dashboard.py

the first review happened the day after phase_02_run_04, when the agent had declared the project complete. it found two critical SQL injection issues the pre-deploy scans had never caught. the second review, a day later, confirmed the fixes from run_05 landed correctly.

## review 1: dashboard.py (2026-03-01)

post-deploy state after phase_02_run_04. review performed after agent declared project complete.

| # | severity | category | finding | status |
|---|---|---|---|---|
| 1.1 | critical | sql injection | flag_reason (st.text_input) in INSERT f-string | open |
| 1.2 | critical | sql injection | review_notes (st.text_area) in UPDATE f-string | open |
| 1.3 | low | sql injection | CURRENT_SIS_USER in INSERT/UPDATE f-strings | open |
| 1.4 | low | sql injection | whitelist-validated filter values in SELECT via .join() | open |
| 2 | high | missing feature | FILTER_CHANGE audit logging absent (0 occurrences; 30 in AUDIT_LOG are stale) | open |
| 3 | medium | missing feature | flag_id not returned or shown after INSERT | open |
| 4 | medium | filter gap | load_heatmap_data ignores segment and channel filters | open |
| 5 | low | visual | LAPSED and NOT_TAKEN_UP share same color (#FFA726) | open |
| 6 | info | spec contradiction | module-level session vs sis-patterns "inside functions only" | open |

---

## review 2: dashboard.py (2026-03-02)

post-deploy state after phase_02_run_05 security fixes. the security-critical issues were all
addressed - what remains is lower-priority functional and visual work.

resolved since review 1:
- issues 1.1 and 1.2: INSERT_RENEWAL_FLAG and UPDATE_RENEWAL_FLAG stored procedures created; all DML now via session.call()
- issue 2: log_filter_change_p1() and log_filter_change_p2() added with on_change callbacks on 5 shared sidebar widgets and page 2 toggle
- issue 3: INSERT_RENEWAL_FLAG returns uuid; shown in st.success("Flag submitted: {flag_id}")

still open:
- issue 4: heatmap segment/channel (and date range) filter gap unchanged in load_heatmap_data lines 480-501
- issue 5: outcome color duplication unchanged; LAPSED and NOT_TAKEN_UP both #FFA726 at line 319
- issue 6: module-level session contradiction unchanged; low practical impact in sis runtime

additional accepted pattern:
- f-string SELECT at lines 606-614, 631-637, 703-710 interpolates DATABASE, SCHEMA, APP_NAME constants only; confirmed safe by post-deployment security scan (phase_03_run_02 prompt 5)

### tracking across both reviews

| issue | review 1 status | review 2 status |
|---|---|---|
| 1.1 critical: INSERT flag_reason injection | open | resolved - session.call(INSERT_RENEWAL_FLAG) |
| 1.2 critical: UPDATE review_notes injection | open | resolved - session.call(UPDATE_RENEWAL_FLAG) |
| 1.3 low: CURRENT_SIS_USER in f-string | open | resolved as part of 1.1/1.2 fix |
| 1.4 low: whitelist filter in f-string SELECT | open | accepted - whitelist validation reduces risk; no user text |
| 2 high: FILTER_CHANGE missing | open | resolved - 2 callbacks, on_change on 6 widgets |
| 3 medium: flag_id not shown | open | resolved - INSERT_RENEWAL_FLAG returns uuid |
| 4 medium: heatmap filter gap | open | open |
| 5 low: outcome color duplication | open | open |
| 6 info: module-level session | open | open (informational) |

---

full findings and code examples in archive/code_review_dashboard_01.md and archive/code_review_dashboard_02.md.

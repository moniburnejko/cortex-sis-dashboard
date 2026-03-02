# adr-009: on_change= for filter_change

**date:** 2026-03-01
**source:** final_report_01.md BUG-003, code_review_dashboard.md issue 2

## problem

the agent implemented FILTER_CHANGE logging via session_state comparison: `if current_value != st.session_state.get('prev_value'): log_audit_event(...)`. the code was structurally present but the comparison ran after widget rendering. the change had already been applied to session_state, so `current == previous` always. result: 0 FILTER_CHANGE events were logged in the live application. the 30 events visible in `AUDIT_LOG` were stale data from a previous version.

## decision

`on_change=` callback on every `st.multiselect` and `st.date_input` in the sidebar on pages 1 and 2. the callback fires before the new value is committed to session_state, making the before/after comparison accurate. first-render guard: initialize session_state keys to match widget default values (not empty lists) to prevent a spurious FILTER_CHANGE event on first load.

## alternatives considered

- **session_state comparison**: agent chose this approach; it does not work as described above. rejected: produces 0 audit events.
- **`st.form` with on_submit**: captures all filter changes as a batch on form submit. does not match the sidebar interaction model (changes should be applied immediately). rejected: wrong ux pattern for sidebar filters.

## consequences

- deploy-and-verify criterion 12 changed to a timestamp filter (last hour). excludes stale data from earlier runs; prevents false positives
- build-dashboard/SKILL.md scan checks `grep -c "FILTER_CHANGE"` >= 1 to confirm presence
- `on_change=` callbacks must reference `LOG_AUDIT_EVENT`, not just update session_state
- each date_input gets its own callback (two separate `on_change=` parameters for `date_from` and `date_to`)

## related

- `.cortex/skills/sis-streamlit/skills/deploy-and-verify/SKILL.md`: criterion 12
- `.cortex/skills/sis-streamlit/skills/build-dashboard/SKILL.md`: FILTER_CHANGE presence check
- AGENTS.md: FILTER_CHANGE on_change requirement

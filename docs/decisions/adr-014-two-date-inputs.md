# adr-014: two st.date_input widgets

**date:** 2026-03-01
**source:** AGENTS.md page 1 sidebar spec, phase_02_run_01.md

## problem

`st.date_input` can accept a tuple value to act as a range picker, returning `(start_date, end_date)`. in the sis sidebar this produces a compact but confusing ui. the two dates share a single label and the date format defaults to the locale setting (e.g. `YYYY/MM/DD` in some locales), inconsistent with the rest of the dashboard. additionally, `st.slider` with date values does not exist in streamlit 1.52.

## decision

two separate `st.date_input` widgets: "Renewal date from" and "Renewal date to", each with `format="YYYY-MM-DD"`. the explicit format prevents locale-dependent display. each widget has its own session_state key (`date_from`, `date_to`) and its own `on_change=` callback for FILTER_CHANGE logging.

## alternatives considered

- **single tuple date_input**: compact but visually confusing in the sidebar; format control limited. rejected: poor ux.
- **`st.slider` with dates**: does not exist in streamlit 1.52. rejected: not available.
- **`st.text_input` with date string parsing**: flexible but requires validation and error handling for invalid date strings. rejected: unnecessary complexity when date_input suffices.

## consequences

- two separate session_state keys: `date_from` and `date_to`
- both values need `on_change=` callbacks for FILTER_CHANGE (adr-012)
- `format="YYYY-MM-DD"` must be explicitly set on both widgets
- granularity logic in adr-010 uses `(date_to - date_from).days` to determine `DATE_TRUNC` interval

## related

- [adr-010](adr-010-date-trunc-aggregation.md): date range drives DATE_TRUNC granularity
- [adr-012](adr-012-filter-change-on-change.md): on_change callbacks on each date input
- AGENTS.md: page 1 sidebar spec

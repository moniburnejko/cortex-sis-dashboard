---
name: brand-identity
description: "load the visual identity, chart type rules, style defaults, and language conventions for the renewal radar dashboard. trigger before generating any streamlit code - after build-dashboard (no args). do NOT use for sis api constraints (those are in build-dashboard) or for snowflake environment checks."
---

-> Load `references/altair-docs.md` on every invocation - altair mark types, encoding shorthands, axis formatting, legend placement, complete chart examples.

## colors

load these values into context and use them consistently across all pages.

### primary palette

| token            | hex     | usage                                          |
|------------------|---------|------------------------------------------------|
| primary          | #1565C0 | trend lines, primary bars, "RENEWED" state, heatmap high end |
| accent-lapsed    | #FFA726 | LAPSED state, warnings                         |
| accent-ntu       | #FB8C00 | NOT_TAKEN_UP state (darker orange, visually distinct from LAPSED) |
| accent-cancelled | #E53935 | CANCELLED state                                |

> **LAPSED and NOT_TAKEN_UP must have distinct colors.** never assign the same hex to
> two different outcome values. `#FFA726` is reserved for LAPSED only.

---

## outcome color mapping

use this exact domain/range in every chart that encodes `renewal_outcome` as color.

| outcome      | hex     | token            |
|--------------|---------|------------------|
| RENEWED      | #1565C0 | primary          |
| LAPSED       | #FFA726 | accent-lapsed    |
| NOT_TAKEN_UP | #FB8C00 | accent-ntu       |
| CANCELLED    | #E53935 | accent-cancelled |

```python
alt.Scale(
    domain=["RENEWED", "LAPSED", "NOT_TAKEN_UP", "CANCELLED"],
    range=["#1565C0", "#FFA726", "#FB8C00", "#E53935"]
)
```

### status palette (for tabular data)

| status | background | text | usage |
|---|---|---|---|
| SUCCESS / OK | #d4edda | inherit | `AUDIT_LOG` execution_status |
| WARN | #fff3cd | inherit | `AUDIT_LOG` execution_status |
| ERROR | #f8d7da | inherit | `AUDIT_LOG` execution_status |

### heatmap gradient (renewal_rate: low -> high)

| threshold | background | text |
|---|---|---|
| >= 80% | #0D47A1 | #ffffff |
| >= 70% | #1565C0 | #ffffff |
| >= 60% | #1976D2 | #ffffff |
| >= 50% | #42A5F5 | #222222 |
| < 50% | #BBDEFB | #222222 |

---

## chart type rules

use these rules to select the correct chart type for each use case.
**do NOT use `st.bar_chart` or `st.line_chart`** - use altair for all charts.
reasons: native streamlit charts cannot format axis values as percentages and do not support horizontal layout.

| use case | chart type | altair method |
|---|---|---|
| metric trend over time | line with points | `mark_line(color=..., point=True)` |
| single metric by category - SHORT labels (<=8 categories, codes or bands) | vertical bar (column) | `mark_bar(color=...)` + `alt.X("cat:N", sort="-y")` + `alt.Y("metric:Q")` |
| single metric by category - LONG labels (many categories or full text names) | horizontal bar | `mark_bar(color=...)` + `alt.Y("cat:N", sort="-x")` + `alt.X("metric:Q")` |
| outcome distribution by category (stacked) | horizontal stacked bar | `alt.Y(category)` + `alt.X(metric)` + `alt.Color(outcome)` |
| two-dimension breakdown (rows x cols -> value) | heatmap via pandas pivot + `st.dataframe(styled)` | `df.style.format(...).map(color_fn)` |

**vertical vs horizontal bar decision rule:**
- use vertical (column) when: category labels are SHORT (region codes: TX, MO; bands: 0_TO_5, 5_TO_10; outcomes: RENEWED), count <= 8
- use horizontal when: category labels are LONG (segment names, full text), count > 8, or when stacking outcomes
- `renewal rate by region` -> vertical (region codes are 2-letter)
- `avg premium change by renewal_outcome` -> vertical (outcome names are short, <= 4 values)
- `avg premium change by price_shock_band` -> vertical (band codes are short)
- `outcome distribution by segment` -> horizontal stacked (segment names are long)

---

## chart style defaults

apply these defaults to every altair chart unless a specific exception is noted.

### axes

- **percentage Y axis**: `alt.Y("...:Q", axis=alt.Axis(format=":.1%"))` for rates (renewal_rate, leakage_rate, etc.)
- **percentage Y axis (bands)**: `alt.Y("...:Q", axis=alt.Axis(format=":.0%"))` for premium_change_pct (whole percent sufficient)
- **categorical X axis with text labels**: always add `axis=alt.Axis(labelAngle=0)` - prevents diagonal labels
- **time X axis**: always add `title=None` to suppress the axis title; use adaptive granularity: day (<=30 days), week (31-180 days), month (>180 days)
- **axis titles - always explicit**: always set `title=` on both `alt.X()` and `alt.Y()`.
  never rely on altair defaults - they render raw field names (e.g. "renewal_outcome", "avg_change", "renewal_rate").
  titles must be sentence case with spaces: "Renewal rate", "Renewal outcome", "Average premium change".
  exception: time-series X axis uses `title=None` to suppress the axis title (see above).
- **time X axis - aggregation is mandatory**: aggregate dates in sql using `DATE_TRUNC` before charting. do NOT plot raw `renewal_date` values and rely on altair formatting to group them - that produces one point per policy (jagged, broken line). query pattern:
  ```sql
  SELECT DATE_TRUNC('month', renewal_date) AS period,
         SUM(is_renewed) * 1.0 / COUNT(*) AS renewal_rate
  FROM FACT_RENEWAL
  GROUP BY period ORDER BY period
  ```
  use `'day'`, `'week'`, or `'month'` in `DATE_TRUNC` based on the date range of filtered data. altair encoding: `alt.X("period:T", title=None)`

### legends

- **single-color charts** (fixed color on `mark_*`): do NOT add `alt.Color` encoding - no legend appears, which is correct
- **multi-color charts** (color encodes a dimension): use `alt.Color("FIELD:N", legend=alt.Legend(orient="top", title="..."))` - legend always on top
- **do NOT put `legend=` on `alt.X()` or `alt.Y()`** - it is not a valid parameter and causes `SchemaValidationError`

### stacked horizontal bar - label truncation

for segment labels (can be long): always set `axis=alt.Axis(labelLimit=200)` on the Y encoding.

---

## language conventions

### kpi card labels

- sentence case, no abbreviations
- correct: "Renewal rate", "Leakage rate", "Quote-to-bind rate", "Service delay index"
- incorrect: "Rnwl Rate", "LKG RATE", "QTB", "SvcDelayIdx"

### percentage display

- always 1 decimal place: "72.4%", "8.1%"
- exception: premium change band labels (whole percent is sufficient): "10%", "20%"

### filter labels

- date filter labels: "Renewal date from" and "Renewal date to" (two separate `st.date_input` widgets)
- always use `format="YYYY-MM-DD"` on all `st.date_input` calls - prevents locale-default YYYY/MM/DD display
- default date range: last 30 days (`max_date - timedelta(days=30)` to `max_date`)

### interactive controls

- button labels: imperative verb + object - "Submit flag", "Mark reviewed"
- text input placeholder: lowercase - "enter reason for flagging..."
- selectbox empty first option: empty string `""` (not "Select...", not "All")
- toggle label: descriptive noun phrase - "Final Offers Only"

### section headings

- title case for page titles: "Premium Pressure Analysis"
- sentence case for section headings within a page: "Flag for review"
- no trailing punctuation on headings

---

## heatmap implementation

the renewal_rate heatmap on page 2 uses `st.dataframe` with pandas styling.
use `.map()`, NOT `.applymap()` (`.applymap()` was removed in pandas 2.2).

```python
def color_heatmap(val):
    if val is None or pd.isna(val):
        return ""
    v = float(val)
    if v >= 0.80:
        return "background-color: #0D47A1; color: #ffffff"
    elif v >= 0.70:
        return "background-color: #1565C0; color: #ffffff"
    elif v >= 0.60:
        return "background-color: #1976D2; color: #ffffff"
    elif v >= 0.50:
        return "background-color: #42A5F5; color: #222222"
    else:
        return "background-color: #BBDEFB; color: #222222"

styled = pivot_df.style.format("{:.1%}").map(color_heatmap)
st.dataframe(styled, use_container_width=True)
```

---

## status color coding

for `AUDIT_LOG` tables (tab 2 - agent operations). use `.map()`, NOT `.applymap()`.

```python
def color_status(val):
    colors = {
        "SUCCESS": "background-color: #d4edda",
        "OK": "background-color: #d4edda",
        "WARN": "background-color: #fff3cd",
        "ERROR": "background-color: #f8d7da",
    }
    return colors.get(val, "")

styled = df.style.map(color_status, subset=["EXECUTION_STATUS"])
st.dataframe(styled, use_container_width=True)
```

## success criteria

- all charts use altair (no `st.bar_chart`, `st.line_chart`)
- primary color (#1565C0) used for all single-color positive-state charts
- accent color (#FFA726) used for LAPSED state only
- accent color (#FB8C00) used for NOT_TAKEN_UP state (distinct from LAPSED)
- all percentage axes formatted to 1 decimal place (except premium bands: 0 decimals)
- all categorical X axes with text labels have `labelAngle=0`
- all multi-color legends are `orient="top"`
- kpi labels are sentence case with no abbreviations
- `.map()` used (not `.applymap()`) for all pandas styling
- all `alt.X()` and `alt.Y()` encodings have explicit `title=` (except time-series X which uses `title=None`)

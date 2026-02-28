# Altair (Vega-Altair) - chart authoring reference

source: [Altair marks | Altair documentation](https://altair-viz.github.io/user_guide/marks/index.html)
source: [Altair encodings | Altair documentation](https://altair-viz.github.io/user_guide/encodings/index.html)
source: [Altair axis configuration | Altair documentation](https://altair-viz.github.io/user_guide/customization.html#adjusting-axis-labels)
source: [Altair legend configuration | Altair documentation](https://altair-viz.github.io/user_guide/customization.html#adjusting-the-legend)
source: [Altair data types | Altair documentation](https://altair-viz.github.io/user_guide/encodings/index.html#encoding-data-types)

---

## data type shorthands

Altair encoding shorthands append a type character after the field name:

| shorthand | type | use for |
|---|---|---|
| `"FIELD:Q"` | quantitative | numeric values (renewal_rate, premium_change_pct, count) |
| `"FIELD:N"` | nominal | unordered categories (region, segment, channel) |
| `"FIELD:O"` | ordinal | ordered categories (premium bands with a natural sort) |
| `"FIELD:T"` | temporal | dates and timestamps (renewal_date, period) |

```python
# examples of shorthand usage
alt.X("renewal_date:T")        # temporal axis
alt.Y("renewal_rate:Q")        # quantitative axis
alt.Color("renewal_status:N")  # nominal color encoding
```

---

## mark types used in this project

### mark_bar() - vertical or horizontal bar charts

```python
# vertical bar (single color, sorted descending)
alt.Chart(df).mark_bar(color="#1565C0").encode(
    alt.X("segment:N", sort="-y", axis=alt.Axis(labelAngle=0)),
    alt.Y("renewal_rate:Q", axis=alt.Axis(format=":.1%")),
    alt.Tooltip(["segment:N", "renewal_rate:Q"])
).properties(height=300)

# horizontal stacked bar (multi-color, outcome distribution)
alt.Chart(df).mark_bar().encode(
    alt.Y("segment:N", sort="-x", axis=alt.Axis(labelAngle=0, labelLimit=200)),
    alt.X("count:Q"),
    alt.Color("renewal_status:N", legend=alt.Legend(orient="top", title="Status")),
    alt.Tooltip(["segment:N", "renewal_status:N", "count:Q"])
).properties(height=350)
```

**key rules for bar charts:**
- always set `sort="-y"` (vertical) or `sort="-x"` (horizontal) on the primary value axis encoding for descending sort
- always set `labelAngle=0` on categorical axes to prevent diagonal labels
- for horizontal stacked bars: always set `labelLimit=200` on Y axis to prevent segment label truncation

### mark_line() with point=True - trend lines

```python
alt.Chart(df).mark_line(color="#1565C0", point=True).encode(
    alt.X("period:T", title=None),
    alt.Y("renewal_rate:Q", axis=alt.Axis(format=":.1%")),
    alt.Tooltip(["period:T", "renewal_rate:Q"])
).properties(height=300)
```

**key rules for line charts:**
- always use `point=True` on `mark_line()` to show data points at each date
- always set `title=None` on the time X axis to suppress the redundant "period" label
- use adaptive granularity:
  - `timeUnit="yearmonthdate"` for date ranges <= 30 days
  - `timeUnit="yearweek"` for date ranges <= 180 days
  - `timeUnit="yearmonth"` for date ranges > 180 days

---

## axis formatting

### percentage axes

```python
# 1 decimal place - use for rates (renewal_rate, leakage_rate, quote-to-bind rate)
alt.Y("renewal_rate:Q", axis=alt.Axis(format=":.1%"))

# 0 decimal places - use for premium change bands (10%, 20%, etc.)
alt.Y("premium_change_pct:Q", axis=alt.Axis(format=":.0%"))
```

### categorical axes - always suppress diagonal labels

```python
# labelAngle=0 prevents diagonal/rotated labels on categorical X axes
alt.X("segment:N", axis=alt.Axis(labelAngle=0))
alt.X("channel:N", sort="-y", axis=alt.Axis(labelAngle=0))
```

diagonal labels appear by default in Altair when labels are long. always set `labelAngle=0` for categorical axes.

### time axes - suppress title

```python
# title=None removes the "period" / "renewal_date" axis title (redundant noise)
alt.X("renewal_date:T", title=None)
```

### label truncation for horizontal bars

```python
# labelLimit=200 prevents long segment names from being cut off
alt.Y("segment:N", axis=alt.Axis(labelLimit=200, labelAngle=0))
```

---

## legend placement

| chart type | rule |
|---|---|
| single-color chart (color set on `mark_*`) | do NOT add `alt.Color` - no legend appears, which is correct |
| multi-color chart (color encodes a dimension) | use `alt.Color(..., legend=alt.Legend(orient="top", title="..."))` |

**do NOT put `legend=` on `alt.X()` or `alt.Y()`** - `legend` is not a valid parameter on those encodings and causes `SchemaValidationError`.

```python
# correct: legend on alt.Color
alt.Chart(df).mark_bar().encode(
    alt.Y("segment:N"),
    alt.X("count:Q"),
    alt.Color("renewal_status:N", legend=alt.Legend(orient="top", title="Renewal Status"))
)

# wrong: legend on alt.X or alt.Y
alt.Chart(df).mark_bar().encode(
    alt.Y("segment:N", legend=alt.Legend(...))   # SchemaValidationError
)
```

---

## tooltip

always add `alt.Tooltip` to charts for interactivity:

```python
# single-series chart
alt.Tooltip(["segment:N", "renewal_rate:Q"])

# multi-series chart
alt.Tooltip(["renewal_date:T", "renewal_rate:Q", "region:N"])
```

---

## complete chart examples

### line chart - renewal rate trend over time

```python
import altair as alt

chart = alt.Chart(df).mark_line(color="#1565C0", point=True).encode(
    alt.X("period:T", title=None),
    alt.Y("renewal_rate:Q", axis=alt.Axis(format=":.1%")),
    alt.Tooltip(["period:T", "renewal_rate:Q"])
).properties(height=300, title="Renewal Rate Trend")

st.altair_chart(chart, use_container_width=True)
```

### vertical bar chart - metric by category, sorted

```python
chart = alt.Chart(df).mark_bar(color="#1565C0").encode(
    alt.X("segment:N", sort="-y", axis=alt.Axis(labelAngle=0)),
    alt.Y("renewal_rate:Q", axis=alt.Axis(format=":.1%")),
    alt.Tooltip(["segment:N", "renewal_rate:Q"])
).properties(height=300)

st.altair_chart(chart, use_container_width=True)
```

### horizontal stacked bar - outcome distribution by segment

```python
chart = alt.Chart(df).mark_bar().encode(
    alt.Y("segment:N", sort="-x", axis=alt.Axis(labelAngle=0, labelLimit=200)),
    alt.X("count:Q"),
    alt.Color(
        "renewal_status:N",
        scale=alt.Scale(
            domain=["RENEWED", "LAPSED", "NOT_TAKEN_UP", "CANCELLED"],
            range=["#1565C0", "#FFA726", "#FFA726", "#FFA726"]
        ),
        legend=alt.Legend(orient="top", title="Status")
    ),
    alt.Tooltip(["segment:N", "renewal_status:N", "count:Q"])
).properties(height=350)

st.altair_chart(chart, use_container_width=True)
```

### heatmap - renewal rate by segment x channel

the heatmap uses `st.dataframe` with pandas styling, NOT Altair. see `brand-identity/SKILL.md` for the full implementation using `df.style.format(...).map(color_fn)`.

---

## using st.altair_chart

always use `st.altair_chart(chart, use_container_width=True)` to display Altair charts. this fills the column width and prevents charts from overflowing their containers.

**do NOT use** `st.bar_chart`, `st.line_chart`, or `st.scatter_chart` for dashboard charts. native Streamlit charts cannot:
- format percentage axes (no `format=":.1%"` support)
- sort bars by value
- place legends at the top
- support `horizontal=True` in `st.bar_chart` (does not exist in Streamlit 1.52)

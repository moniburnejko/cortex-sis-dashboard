# --- imports ---
import streamlit as st
from snowflake.snowpark.context import get_active_session
import altair as alt
import pandas as pd
from datetime import date as py_date, timedelta

# --- page config - MUST be the first st.* call ---
st.set_page_config(layout="wide")

# --- session and user context ---
session = get_active_session()
CURRENT_SIS_USER = st.user.user_name or "unknown"
APP_NAME = "renewal_radar"
DATABASE = "CORTEX_DB"
SCHEMA = "CORTEX_SCHEMA"

# --- cached data loader ---
@st.cache_data(ttl=300)
def load_filter_options():
    _session = get_active_session()
    regions = [r[0] for r in _session.sql(
        f"SELECT DISTINCT region FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL WHERE region IS NOT NULL ORDER BY region"
    ).collect()]
    segments = [r[0] for r in _session.sql(
        f"SELECT DISTINCT segment FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL WHERE segment IS NOT NULL ORDER BY segment"
    ).collect()]
    channels = [r[0] for r in _session.sql(
        f"SELECT DISTINCT channel FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL WHERE channel IS NOT NULL ORDER BY channel"
    ).collect()]
    raw = _session.sql(
        f"SELECT MIN(renewal_date), MAX(renewal_date) FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL"
    ).collect()[0]
    if raw[0] is None or raw[1] is None:
        st.error("No data in source table.")
        st.stop()
    min_date = py_date(raw[0].year, raw[0].month, raw[0].day)
    max_date = py_date(raw[1].year, raw[1].month, raw[1].day)
    return {
        "regions": regions, "segments": segments, "channels": channels,
        "min_date": min_date, "max_date": max_date
    }

# --- audit logger ---
def log_audit_event(action_type, action_category, page, component, action):
    session.call(
        f"{DATABASE}.{SCHEMA}.LOG_AUDIT_EVENT",
        action_type, action_category, APP_NAME, page, component, action,
        None, None, None, None, None,
        CURRENT_SIS_USER
    )

# --- filter options and whitelist lists ---
FILTER_OPTIONS = load_filter_options()
VALID_REGIONS = FILTER_OPTIONS["regions"]
VALID_SEGMENTS = FILTER_OPTIONS["segments"]
VALID_CHANNELS = FILTER_OPTIONS["channels"]
MIN_DATE = FILTER_OPTIONS["min_date"]
MAX_DATE = FILTER_OPTIONS["max_date"]

# --- display label mappings ---
REGION_LABELS = {
    "AR": "Arkansas", "KS": "Kansas", "LA": "Louisiana", "MO": "Missouri",
    "OK": "Oklahoma", "TN": "Tennessee", "TX": "Texas"
}

SEGMENT_LABELS = {
    "COMMERCIAL_PROPERTY": "Commercial property",
    "COMMERCIAL_VAN": "Commercial van",
    "HOME": "Home",
    "PERSONAL_AUTO": "Personal auto",
    "PERSONAL_MOTORBIKE": "Personal motorbike"
}

CHANNEL_LABELS = {"AGENT": "Agent", "BROKER": "Broker", "DIRECT": "Direct"}

OUTCOME_LABELS = {
    "RENEWED": "Renewed", "LAPSED": "Lapsed",
    "NOT_TAKEN_UP": "Not taken up", "CANCELLED": "Cancelled"
}

BAND_LABELS = {
    "0_TO_5": "0-5%", "5_TO_10": "5-10%", "10_TO_15": "10-15%", "GT_15": ">15%"
}

STATUS_LABELS = {"OPEN": "Open", "REVIEWED": "Reviewed"}

# Reverse mappings
REGION_LABELS_REV = {v: k for k, v in REGION_LABELS.items()}
SEGMENT_LABELS_REV = {v: k for k, v in SEGMENT_LABELS.items()}
CHANNEL_LABELS_REV = {v: k for k, v in CHANNEL_LABELS.items()}

# Custom sort orders (display label order)
OUTCOME_DISPLAY_ORDER = ["Renewed", "Lapsed", "Not taken up", "Cancelled"]
BAND_DISPLAY_ORDER = ["0-5%", "5-10%", "10-15%", ">15%"]

def to_display(value, category):
    """Convert raw database value to display label."""
    if pd.isna(value) or value is None:
        return value
    mappings = {
        "region": REGION_LABELS, "segment": SEGMENT_LABELS, "channel": CHANNEL_LABELS,
        "outcome": OUTCOME_LABELS, "band": BAND_LABELS, "status": STATUS_LABELS
    }
    return mappings.get(category, {}).get(value, value)

def from_display(value, category):
    """Convert display label to raw database value."""
    if pd.isna(value) or value is None or value == "":
        return value
    rev_mappings = {
        "region": REGION_LABELS_REV, "segment": SEGMENT_LABELS_REV, "channel": CHANNEL_LABELS_REV
    }
    return rev_mappings.get(category, {}).get(value, value)

# --- session state ---
if "sel_regions" not in st.session_state:
    st.session_state["sel_regions"] = list(VALID_REGIONS)
if "sel_segments" not in st.session_state:
    st.session_state["sel_segments"] = list(VALID_SEGMENTS)
if "sel_channels" not in st.session_state:
    st.session_state["sel_channels"] = list(VALID_CHANNELS)
if "date_from" not in st.session_state:
    st.session_state["date_from"] = MAX_DATE - timedelta(days=30)
if "date_to" not in st.session_state:
    st.session_state["date_to"] = MAX_DATE

# --- filter change callbacks ---
def log_filter_change_p1():
    """Callback for Page 1 filter changes"""
    log_audit_event("FILTER_CHANGE", "USER_INTERACTION",
                    "page_1_kpi_overview", "sidebar_filters", "multiselect_change")

def log_filter_change_p2():
    """Callback for Page 2 filter changes"""
    log_audit_event("FILTER_CHANGE", "USER_INTERACTION",
                    "page_2_premium_pressure", "sidebar_filters", "multiselect_change")

# --- navigation ---
page = st.sidebar.radio("Navigation", ["KPI Overview", "Premium Pressure", "Activity Log"])

# --- shared filters (sidebar) ---
st.sidebar.header("Filters")

# Determine which callback to use based on current page
if page == "KPI Overview":
    filter_callback = log_filter_change_p1
elif page == "Premium Pressure":
    filter_callback = log_filter_change_p2
else:
    filter_callback = None  # No logging for Activity Log page

sel_regions = st.sidebar.multiselect(
    "Region", VALID_REGIONS, key="sel_regions",
    format_func=lambda x: REGION_LABELS.get(x, x),
    on_change=filter_callback
)
sel_segments = st.sidebar.multiselect(
    "Segment", VALID_SEGMENTS, key="sel_segments",
    format_func=lambda x: SEGMENT_LABELS.get(x, x),
    on_change=filter_callback
)
sel_channels = st.sidebar.multiselect(
    "Channel", VALID_CHANNELS, key="sel_channels",
    format_func=lambda x: CHANNEL_LABELS.get(x, x),
    on_change=filter_callback
)
date_from = st.sidebar.date_input(
    "Renewal date from",
    value=st.session_state["date_from"],
    min_value=MIN_DATE,
    max_value=MAX_DATE,
    format="YYYY-MM-DD",
    on_change=filter_callback
)
date_to = st.sidebar.date_input(
    "Renewal date to",
    value=st.session_state["date_to"],
    min_value=MIN_DATE,
    max_value=MAX_DATE,
    format="YYYY-MM-DD",
    on_change=filter_callback
)

# --- page routing ---
if page == "KPI Overview":
    st.title("KPI Overview")
    
    # Validate filters
    valid_sel_regions = [r for r in sel_regions if r in VALID_REGIONS]
    valid_sel_segments = [s for s in sel_segments if s in VALID_SEGMENTS]
    valid_sel_channels = [c for c in sel_channels if c in VALID_CHANNELS]
    
    if not valid_sel_regions or not valid_sel_segments or not valid_sel_channels:
        st.warning("Please select at least one value for each filter.")
        st.stop()
    
    # Load data with filters
    @st.cache_data(ttl=300)
    def load_kpi_data(regions, segments, channels, date_from, date_to):
        _session = get_active_session()
        df = _session.table(f"{DATABASE}.{SCHEMA}.FACT_RENEWAL").to_pandas()
        df = df.rename(columns=str.lower)
        df = df[
            (df['region'].isin(regions)) &
            (df['segment'].isin(segments)) &
            (df['channel'].isin(channels)) &
            (df['renewal_date'] >= date_from) &
            (df['renewal_date'] <= date_to)
        ]
        return df
    
    df = load_kpi_data(valid_sel_regions, valid_sel_segments, valid_sel_channels, date_from, date_to)
    
    if df.empty:
        st.warning("No data available for selected filters.")
        st.stop()
    
    # Calculate KPIs
    renewal_rate = df['is_renewed'].sum() / len(df) if len(df) > 0 else 0
    leakage_rate = 1 - renewal_rate
    quote_to_bind = df['is_bound'].sum() / df['is_quoted'].sum() if df['is_quoted'].sum() > 0 else 0
    service_delay_idx = df['quote_tta'].mean() / df['target_tta_hours'].mean() if df['target_tta_hours'].mean() > 0 else 0
    
    # Display KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Renewal rate", f"{renewal_rate:.1%}")
    with col2:
        st.metric("Leakage rate", f"{leakage_rate:.1%}")
    with col3:
        st.metric("Quote-to-bind rate", f"{quote_to_bind:.1%}")
    with col4:
        st.metric("Service delay index", f"{service_delay_idx:.2f}")
    
    # Chart 1: Renewal rate trend over time
    st.subheader("Renewal rate trend over time")
    
    # Determine granularity based on date range
    date_range = (date_to - date_from).days
    if date_range <= 30:
        trunc_unit = 'day'
    elif date_range <= 180:
        trunc_unit = 'week'
    else:
        trunc_unit = 'month'
    
    # Aggregate in SQL using DATE_TRUNC
    @st.cache_data(ttl=300)
    def load_trend_data(regions, segments, channels, date_from, date_to, trunc_unit):
        _session = get_active_session()
        query = f"""
        SELECT 
            DATE_TRUNC('{trunc_unit}', renewal_date) AS period,
            SUM(is_renewed) * 1.0 / COUNT(*) AS renewal_rate
        FROM {DATABASE}.{SCHEMA}.FACT_RENEWAL
        WHERE region IN ('{"','".join(regions)}')
          AND segment IN ('{"','".join(segments)}')
          AND channel IN ('{"','".join(channels)}')
          AND renewal_date >= '{date_from}'
          AND renewal_date <= '{date_to}'
        GROUP BY period
        ORDER BY period
        """
        df = _session.sql(query).to_pandas()
        df = df.rename(columns=str.lower)
        return df
    
    trend_df = load_trend_data(valid_sel_regions, valid_sel_segments, valid_sel_channels, 
                                date_from, date_to, trunc_unit)
    
    if not trend_df.empty:
        trend_chart = alt.Chart(trend_df).mark_line(color="#1565C0", point=True).encode(
            x=alt.X('period:T', title=None),
            y=alt.Y('renewal_rate:Q', axis=alt.Axis(format=".1%"), title="Renewal rate"),
            tooltip=[
                alt.Tooltip('period:T', title="Period"),
                alt.Tooltip('renewal_rate:Q', format=".1%", title="Renewal rate")
            ]
        ).properties(height=300)
        
        st.altair_chart(trend_chart, use_container_width=True)
    else:
        st.info("No trend data available.")
    
    # Chart 2: Renewal rate by region
    st.subheader("Renewal rate by region")
    
    region_df = df.groupby('region').agg({'is_renewed': 'mean'}).reset_index()
    region_df.columns = ['region', 'renewal_rate']
    region_df['region_display'] = region_df['region'].map(REGION_LABELS)
    
    region_chart = alt.Chart(region_df).mark_bar(color="#1565C0").encode(
        x=alt.X('region_display:N', sort='-y', axis=alt.Axis(labelAngle=0), title="Region"),
        y=alt.Y('renewal_rate:Q', axis=alt.Axis(format=".1%"), title="Renewal rate"),
        tooltip=[
            alt.Tooltip('region_display:N', title="Region"),
            alt.Tooltip('renewal_rate:Q', format=".1%", title="Renewal rate")
        ]
    ).properties(height=300)
    
    st.altair_chart(region_chart, use_container_width=True)
    
    # Chart 3: Renewal outcome distribution by segment (stacked horizontal bar)
    st.subheader("Renewal outcome distribution by segment")
    
    outcome_df = df.groupby(['segment', 'renewal_outcome']).size().reset_index(name='n')
    outcome_df['pct'] = outcome_df.groupby('segment')['n'].transform(lambda x: outcome_df.loc[x.index, 'n'] / x.sum())
    outcome_df['segment_display'] = outcome_df['segment'].map(SEGMENT_LABELS)
    outcome_df['outcome_display'] = outcome_df['renewal_outcome'].map(OUTCOME_LABELS)
    
    outcome_chart = alt.Chart(outcome_df).mark_bar().encode(
        x=alt.X('n:Q', stack='normalize', axis=alt.Axis(format=".0%"), title="Share of policies"),
        y=alt.Y('segment_display:N', sort=alt.EncodingSortField('n', op='sum', order='descending'), 
                axis=alt.Axis(labelLimit=200), title="Segment"),
        color=alt.Color('outcome_display:N',
            scale=alt.Scale(
                domain=OUTCOME_DISPLAY_ORDER,
                range=["#1565C0", "#FFA726", "#FFA726", "#E53935"]
            ),
            legend=alt.Legend(orient="top", title="Outcome")
        ),
        order=alt.Order('outcome_display:N', sort='descending'),
        tooltip=[
            alt.Tooltip('segment_display:N', title="Segment"),
            alt.Tooltip('outcome_display:N', title="Outcome"),
            alt.Tooltip('pct:Q', format=".1%", title="Share"),
            alt.Tooltip('n:Q', title="Policies")
        ]
    ).properties(height=400)
    
    st.altair_chart(outcome_chart, use_container_width=True)

elif page == "Premium Pressure":
    st.title("Premium Pressure Analysis")
    
    # Page-specific filter: Final Offers Only
    final_offers_only = st.sidebar.toggle("Final Offers Only", value=True, on_change=log_filter_change_p2)
    
    # Validate filters
    valid_sel_regions = [r for r in sel_regions if r in VALID_REGIONS]
    valid_sel_segments = [s for s in sel_segments if s in VALID_SEGMENTS]
    valid_sel_channels = [c for c in sel_channels if c in VALID_CHANNELS]
    
    if not valid_sel_regions or not valid_sel_segments or not valid_sel_channels:
        st.warning("Please select at least one value for each filter.")
        st.stop()
    
    # Load premium event data
    @st.cache_data(ttl=300)
    def load_premium_data(regions, segments, channels, date_from, date_to, final_only):
        _session = get_active_session()
        query = f"""
        SELECT 
            policy_id, client_id, renewal_date, event_type, region, segment, channel,
            expiring_premium, offered_premium, discount_amt, discount_pct, renewal_outcome,
            is_final_offer,
            (offered_premium - expiring_premium) / NULLIF(expiring_premium, 0) AS premium_change_pct,
            CASE
                WHEN (offered_premium - expiring_premium) / NULLIF(expiring_premium, 0) <= 0.05 THEN '0_TO_5'
                WHEN (offered_premium - expiring_premium) / NULLIF(expiring_premium, 0) <= 0.10 THEN '5_TO_10'
                WHEN (offered_premium - expiring_premium) / NULLIF(expiring_premium, 0) <= 0.15 THEN '10_TO_15'
                ELSE 'GT_15'
            END AS price_shock_band
        FROM {DATABASE}.{SCHEMA}.FACT_PREMIUM_EVENT
        WHERE 1=1
        """
        if final_only:
            query += " AND is_final_offer = 1"
        
        df = _session.sql(query).to_pandas()
        df = df.rename(columns=str.lower)
        df = df[
            (df['region'].isin(regions)) &
            (df['segment'].isin(segments)) &
            (df['channel'].isin(channels)) &
            (df['renewal_date'] >= date_from) &
            (df['renewal_date'] <= date_to)
        ]
        return df
    
    df_premium = load_premium_data(valid_sel_regions, valid_sel_segments, valid_sel_channels, 
                                   date_from, date_to, final_offers_only)
    
    if df_premium.empty:
        st.warning("No data available for selected filters.")
        st.stop()
    
    # Calculate KPIs
    price_shocked = (df_premium['premium_change_pct'] > 0.10).sum() / len(df_premium) if len(df_premium) > 0 else 0
    avg_premium_change = df_premium['premium_change_pct'].mean()
    
    # Get flags count
    flags_count_result = session.sql(
        f"SELECT COUNT(*) as cnt FROM {DATABASE}.{SCHEMA}.RENEWAL_FLAGS WHERE status = 'OPEN'"
    ).collect()
    flags_count = flags_count_result[0]['CNT']
    
    # Display KPIs
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Policies price-shocked (>10%)", f"{price_shocked:.1%}")
    with col2:
        st.metric("Average premium change", f"{avg_premium_change:.1%}")
    with col3:
        st.metric("Flags for review", f"{flags_count}")
    
    # Chart 1: Average premium change by price shock band
    st.subheader("Average premium change by price shock band")
    
    band_df = df_premium.groupby('price_shock_band')['premium_change_pct'].mean().reset_index()
    band_df.columns = ['price_shock_band', 'avg_premium_change']
    band_order = ['0_TO_5', '5_TO_10', '10_TO_15', 'GT_15']
    band_df['price_shock_band'] = pd.Categorical(band_df['price_shock_band'], categories=band_order, ordered=True)
    band_df = band_df.sort_values('price_shock_band')
    band_df['band_display'] = band_df['price_shock_band'].map(BAND_LABELS)
    
    band_chart = alt.Chart(band_df).mark_bar(color="#1565C0").encode(
        x=alt.X('band_display:N', axis=alt.Axis(labelAngle=0), title="Price shock band", 
                sort=BAND_DISPLAY_ORDER),
        y=alt.Y('avg_premium_change:Q', axis=alt.Axis(format=".0%"), title="Average premium change"),
        tooltip=[
            alt.Tooltip('band_display:N', title="Band"),
            alt.Tooltip('avg_premium_change:Q', format=".1%", title="Avg change")
        ]
    ).properties(height=300)
    
    st.altair_chart(band_chart, use_container_width=True)
    
    # Chart 2: Average premium change by renewal outcome
    st.subheader("Average premium change by renewal outcome")
    
    # Load data without final_offers filter for this chart (all outcomes need data)
    @st.cache_data(ttl=300)
    def load_outcome_premium_data(regions, segments, channels, date_from, date_to):
        _session = get_active_session()
        query = f"""
        SELECT 
            r.renewal_outcome,
            AVG((e.offered_premium - e.expiring_premium) / NULLIF(e.expiring_premium, 0)) AS avg_change
        FROM {DATABASE}.{SCHEMA}.FACT_PREMIUM_EVENT e
        JOIN {DATABASE}.{SCHEMA}.FACT_RENEWAL r ON e.policy_id = r.policy_id
        WHERE e.region IN ('{"','".join(regions)}')
          AND e.segment IN ('{"','".join(segments)}')
          AND e.channel IN ('{"','".join(channels)}')
          AND e.renewal_date >= '{date_from}'
          AND e.renewal_date <= '{date_to}'
        GROUP BY r.renewal_outcome
        ORDER BY r.renewal_outcome
        """
        df = _session.sql(query).to_pandas()
        df = df.rename(columns=str.lower)
        return df
    
    outcome_prem_df = load_outcome_premium_data(valid_sel_regions, valid_sel_segments, 
                                                 valid_sel_channels, date_from, date_to)
    
    if not outcome_prem_df.empty:
        outcome_prem_df['outcome_display'] = outcome_prem_df['renewal_outcome'].map(OUTCOME_LABELS)
        
        outcome_prem_chart = alt.Chart(outcome_prem_df).mark_bar(color="#1565C0").encode(
            x=alt.X('outcome_display:N', axis=alt.Axis(labelAngle=0), title="Renewal outcome",
                    sort=OUTCOME_DISPLAY_ORDER),
            y=alt.Y('avg_change:Q', axis=alt.Axis(format=".1%"), title="Average premium change"),
            tooltip=[
                alt.Tooltip('outcome_display:N', title="Outcome"),
                alt.Tooltip('avg_change:Q', format=".1%", title="Avg change")
            ]
        ).properties(height=300)
        
        st.altair_chart(outcome_prem_chart, use_container_width=True)
    else:
        st.info("No outcome data available.")
    
    # Chart 3: Heatmap - price shock band x region -> renewal rate
    st.subheader("Renewal rate by price shock band and region")
    
    # Load renewal data for heatmap
    @st.cache_data(ttl=300)
    def load_heatmap_data(regions, segments, channels, date_from, date_to, final_only):
        _session = get_active_session()
        query = f"""
        SELECT 
            region,
            CASE
                WHEN (offered_premium - expiring_premium) / NULLIF(expiring_premium, 0) <= 0.05 THEN '0_TO_5'
                WHEN (offered_premium - expiring_premium) / NULLIF(expiring_premium, 0) <= 0.10 THEN '5_TO_10'
                WHEN (offered_premium - expiring_premium) / NULLIF(expiring_premium, 0) <= 0.15 THEN '10_TO_15'
                ELSE 'GT_15'
            END AS price_shock_band,
            CASE WHEN renewal_outcome = 'RENEWED' THEN 1 ELSE 0 END AS is_renewed
        FROM {DATABASE}.{SCHEMA}.FACT_PREMIUM_EVENT
        WHERE 1=1
        """
        if final_only:
            query += " AND is_final_offer = 1"
        
        df = _session.sql(query).to_pandas()
        df = df.rename(columns=str.lower)
        df = df[df['region'].isin(regions)]
        return df
    
    df_heatmap = load_heatmap_data(valid_sel_regions, valid_sel_segments, valid_sel_channels,
                                    date_from, date_to, final_offers_only)
    
    if not df_heatmap.empty:
        # Map to display labels before pivot
        df_heatmap['region_display'] = df_heatmap['region'].map(REGION_LABELS)
        df_heatmap['band_display'] = df_heatmap['price_shock_band'].map(BAND_LABELS)
        
        pivot_df = df_heatmap.pivot_table(
            index='band_display', 
            columns='region_display', 
            values='is_renewed', 
            aggfunc='mean'
        )
        
        # Reorder rows using display labels
        pivot_df = pivot_df.reindex(BAND_DISPLAY_ORDER)
        
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
    
    # Flag for review section
    st.subheader("Flag for review")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        flag_region_display = st.selectbox(
            "Region", [""] + [REGION_LABELS.get(r, r) for r in VALID_REGIONS]
        )
        flag_region = from_display(flag_region_display, "region") if flag_region_display else ""
    with col2:
        flag_segment_display = st.selectbox(
            "Segment", [""] + [SEGMENT_LABELS.get(s, s) for s in VALID_SEGMENTS]
        )
        flag_segment = from_display(flag_segment_display, "segment") if flag_segment_display else ""
    with col3:
        flag_channel_display = st.selectbox(
            "Channel", [""] + [CHANNEL_LABELS.get(c, c) for c in VALID_CHANNELS]
        )
        flag_channel = from_display(flag_channel_display, "channel") if flag_channel_display else ""
    
    flag_reason = st.text_input("Reason", placeholder="enter reason for flagging...")
    
    # Build scope
    scope_parts = []
    scope_region = None
    scope_segment = None
    scope_channel = None
    
    if flag_region:
        scope_parts.append("REGION")
        scope_region = flag_region
    if flag_segment:
        scope_parts.append("SEGMENT")
        scope_segment = flag_segment
    if flag_channel:
        scope_parts.append("CHANNEL")
        scope_channel = flag_channel
    
    scope = "_".join(scope_parts) if scope_parts else ""
    
    submit_enabled = len(scope_parts) > 0 and flag_reason.strip() != ""
    
    if st.button("Submit flag", disabled=not submit_enabled):
        flag_id = session.call(
            f"{DATABASE}.{SCHEMA}.INSERT_RENEWAL_FLAG",
            CURRENT_SIS_USER,   # p_flagged_by
            scope,              # p_scope
            scope_region,       # p_scope_region
            scope_segment,      # p_scope_segment
            scope_channel,      # p_scope_channel
            flag_reason         # p_flag_reason
        )
        
        log_audit_event("FLAG_ADDED", "USER_INTERACTION", "page_2_premium_pressure", 
                       "flag_for_review", "flag_submitted")
        
        st.success(f"Flag submitted: {flag_id}")

elif page == "Activity Log":
    st.title("Activity Log")
    
    tab1, tab2 = st.tabs(["User interactions", "Agent operations"])
    
    with tab1:
        st.subheader("User interactions")
        
        # Load user interactions
        user_df = session.sql(f"""
            SELECT event_timestamp, user_name, streamlit_page, action_type, 
                   streamlit_action, execution_status
            FROM {DATABASE}.{SCHEMA}.AUDIT_LOG
            WHERE streamlit_app_name = '{APP_NAME}'
              AND action_category = 'USER_INTERACTION'
            ORDER BY event_timestamp DESC
            LIMIT 200
        """).to_pandas()
        
        st.dataframe(user_df, use_container_width=True, hide_index=True)
        
        # Review flags section
        st.subheader("Review flags")
        
        # Filter controls
        col1, col2, col3 = st.columns(3)
        with col1:
            show_filter = st.selectbox("Show", ["Open", "All"])
        with col2:
            scope_filter = st.selectbox("Scope", ["All", "REGION", "SEGMENT", "CHANNEL"])
        with col3:
            reason_search = st.text_input("Reason search", placeholder="search flag reason...")
        
        # Load flags
        flags_query = f"""
            SELECT flag_id, status, scope, scope_region, scope_segment, scope_channel,
                   flag_reason, flagged_by, flagged_at
            FROM {DATABASE}.{SCHEMA}.RENEWAL_FLAGS
            ORDER BY flagged_at DESC
        """
        flags_df = session.sql(flags_query).to_pandas()
        flags_df = flags_df.rename(columns=str.lower)
        
        # Map display labels for table
        flags_df['status'] = flags_df['status'].map(lambda x: STATUS_LABELS.get(x, x))
        flags_df['scope_region'] = flags_df['scope_region'].map(lambda x: REGION_LABELS.get(x, x) if pd.notna(x) else x)
        flags_df['scope_segment'] = flags_df['scope_segment'].map(lambda x: SEGMENT_LABELS.get(x, x) if pd.notna(x) else x)
        flags_df['scope_channel'] = flags_df['scope_channel'].map(lambda x: CHANNEL_LABELS.get(x, x) if pd.notna(x) else x)
        
        # Apply filters
        if show_filter == "Open":
            flags_df = flags_df[flags_df['status'] == 'Open']
        
        if scope_filter != "All":
            if scope_filter == "REGION":
                flags_df = flags_df[flags_df['scope_region'].notna()]
            elif scope_filter == "SEGMENT":
                flags_df = flags_df[flags_df['scope_segment'].notna()]
            elif scope_filter == "CHANNEL":
                flags_df = flags_df[flags_df['scope_channel'].notna()]
        
        if reason_search:
            flags_df = flags_df[flags_df['flag_reason'].str.contains(reason_search, case=False, na=False)]
        
        # Add selection column
        if not flags_df.empty:
            flags_df.insert(0, 'select', False)
            
            edited_df = st.data_editor(
                flags_df,
                column_config={
                    "select": st.column_config.CheckboxColumn("Select", default=False)
                },
                hide_index=True,
                use_container_width=True,
                disabled=["flag_id", "status", "scope", "scope_region", "scope_segment", 
                         "scope_channel", "flag_reason", "flagged_by", "flagged_at"]
            )
            
            review_notes = st.text_area("Review notes", max_chars=500, 
                                       placeholder="optional notes for review...")
            
            selected_flags = edited_df[edited_df['select'] == True]
            
            if st.button("Mark reviewed", disabled=len(selected_flags) == 0):
                flag_ids = selected_flags['flag_id'].tolist()
                flag_ids_str = ",".join(flag_ids)
                
                session.call(
                    f"{DATABASE}.{SCHEMA}.UPDATE_RENEWAL_FLAG",
                    CURRENT_SIS_USER,   # p_reviewed_by
                    review_notes,       # p_notes
                    flag_ids_str        # p_flag_ids
                )
                
                log_audit_event("FLAG_REVIEWED", "USER_INTERACTION", "page_3_activity_log",
                               "review_flags", "mark_reviewed")
                
                st.success(f"Marked {len(flag_ids)} flag(s) as reviewed")
        else:
            st.info("No flags match the current filters.")
    
    with tab2:
        st.subheader("Agent operations")
        
        # Load agent operations
        agent_df = session.sql(f"""
            SELECT event_timestamp, user_name, action_type, execution_status, error_message
            FROM {DATABASE}.{SCHEMA}.AUDIT_LOG
            WHERE streamlit_app_name = '{APP_NAME}'
              AND action_category = 'AGENT_OPERATION'
            ORDER BY event_timestamp DESC
            LIMIT 100
        """).to_pandas()
        
        if not agent_df.empty:
            agent_df = agent_df.rename(columns=str.lower)
            
            def color_status(val):
                colors = {
                    "SUCCESS": "background-color: #d4edda",
                    "OK": "background-color: #d4edda",
                    "WARN": "background-color: #fff3cd",
                    "ERROR": "background-color: #f8d7da",
                }
                return colors.get(val, "")
            
            styled_agent = agent_df.style.map(color_status, subset=["execution_status"])
            st.dataframe(styled_agent, use_container_width=True, hide_index=True)
        else:
            st.info("No agent operations recorded yet.")

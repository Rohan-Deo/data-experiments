"""
Streamlit dashboard for Help Tickets analysis.
Run with:  cd help_tickets && streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd

from src.data_loader import (
    load_raw_tickets,
    load_combined_categories,
    get_batch_list,
    load_ticket_level,
    get_ticket_batch_list,
)
from src.analysis import (
    compute_kpis,
    overall_comparison,
    category_comparison,
    support_ticket_comparison,
    batch_comparison,
    resolution_metrics,
    top_batches,
)
from src.charts import (
    overall_ticket_bar,
    help_vs_support_stacked,
    help_support_pct_bar,
    category_comparison_chart,
    category_change_waterfall,
    support_change_bar,
    batch_scatter,
    resolution_grouped_bar,
    top_batches_bar,
    user_comparison_bar,
    category_treemap,
)
from src.ticket_analysis import (
    rating_distribution,
    rating_summary,
    csat_score,
    ec_summary,
    ec_comparison,
    status_distribution,
    open_ticket_summary,
    tat_summary,
    tat_by_ec,
    daily_ticket_trend,
    priority_distribution,
)
from src.ticket_charts import (
    rating_distribution_chart,
    csat_chart,
    ec_ticket_bar,
    ec_rating_bar,
    ec_resolution_bar,
    status_pie,
    status_grouped_bar,
    tat_box,
    tat_ec_bar,
    daily_trend_chart,
    daily_trend_stacked,
    priority_chart,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Help Tickets Analysis", layout="wide", page_icon="🎫")

# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_all_data():
    pre_raw, post_raw = load_raw_tickets()
    cat = load_combined_categories()
    agg_batches = get_batch_list()
    tkt_pre, tkt_post = load_ticket_level()
    tkt_batches = get_ticket_batch_list()
    all_batches = sorted(set(agg_batches + tkt_batches))
    return pre_raw, post_raw, cat, tkt_pre, tkt_post, all_batches


pre_raw, post_raw, cat_combined, tkt_pre_raw, tkt_post_raw, all_batches = load_all_data()

# ---------------------------------------------------------------------------
# Sidebar – batch filter
# ---------------------------------------------------------------------------
st.sidebar.title("Filters")
selected_batches = st.sidebar.multiselect(
    "Filter by Batch Name",
    options=all_batches,
    default=[],
    help="Leave empty to view all batches (overall level).",
)

if selected_batches:
    pre = pre_raw[pre_raw["Batch Name"].isin(selected_batches)].copy()
    post = post_raw[post_raw["Batch Name"].isin(selected_batches)].copy()
    cat = cat_combined[cat_combined["Batch Name"].isin(selected_batches)].copy()
    tkt_pre = tkt_pre_raw[tkt_pre_raw["Batch Name"].isin(selected_batches)].copy()
    tkt_post = tkt_post_raw[tkt_post_raw["Batch Name"].isin(selected_batches)].copy()
    filter_label = f"Filtered: {len(selected_batches)} batch(es)"
else:
    pre = pre_raw.copy()
    post = post_raw.copy()
    cat = cat_combined.copy()
    tkt_pre = tkt_pre_raw.copy()
    tkt_post = tkt_post_raw.copy()
    filter_label = "All Batches (Overall)"

tkt_all = pd.concat([tkt_pre, tkt_post], ignore_index=True)

st.sidebar.markdown(f"**Scope:** {filter_label}")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Pre period:** 26 Jan – 14 Feb  \n"
    "**Post period:** 15 Feb – 5 Mar  \n"
    "Help tickets introduced on 13-14 Feb."
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Rating note:**  \n"
    "- Help tickets: valid ratings are **1** or **5**  \n"
    "- Support tickets: valid ratings are **1–5**  \n"
    "- Unrated tickets are excluded from rating metrics"
)

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.title("Help Tickets – Pre vs Post Analysis")
st.caption(filter_label)

# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
kpis = compute_kpis(pre, post)

st.markdown("### Key Metrics")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Tickets (Pre)", f"{kpis['pre_total']:,}")
k2.metric("Total Tickets (Post)", f"{kpis['post_total']:,}", delta=f"{kpis['total_change_pct']:+.1f}%")
k3.metric("Help Tickets (Post)", f"{kpis['post_help']:,}",
          delta=f"{kpis['post_help_pct']:.1f}% of total")
k4.metric("Support Tickets (Post)", f"{kpis['post_support']:,}",
          delta=f"{kpis['support_change_pct']:+.1f}%", delta_color="inverse")

k5, k6, k7, k8 = st.columns(4)
k5.metric("Help Users (Pre)", f"{kpis['pre_unique_help_users']:,}")
k6.metric("Help Users (Post)", f"{kpis['post_unique_help_users']:,}")
k7.metric("Support Users (Pre)", f"{kpis['pre_unique_support_users']:,}")
k8.metric("Support Users (Post)", f"{kpis['post_unique_support_users']:,}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Tab layout
# ---------------------------------------------------------------------------
tab_overall, tab_categories, tab_support, tab_ratings, tab_ec, tab_status, tab_batches, tab_data = st.tabs([
    "Overall", "Categories", "Support Deep-Dive",
    "Ratings & CSAT", "EC Analysis", "Status & TAT",
    "Batch Comparison", "Raw Data",
])

# ===== TAB: Overall =====
with tab_overall:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(overall_ticket_bar(kpis["pre_total"], kpis["post_total"]), use_container_width=True)
    with col2:
        st.plotly_chart(
            help_vs_support_stacked(kpis["pre_help"], kpis["pre_support"],
                                    kpis["post_help"], kpis["post_support"]),
            use_container_width=True,
        )

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(help_support_pct_bar(kpis["pre_help_pct"], kpis["post_help_pct"]),
                        use_container_width=True)
    with col4:
        st.plotly_chart(user_comparison_bar(kpis), use_container_width=True)

    st.subheader("Daily Ticket Trend")
    trend = daily_ticket_trend(tkt_all)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(daily_trend_chart(trend), use_container_width=True)
    with c2:
        st.plotly_chart(daily_trend_stacked(trend), use_container_width=True)

    st.subheader("Resolution Rates (Aggregated Data)")
    res = resolution_metrics(pre, post)
    col5, col6 = st.columns([1, 2])
    with col5:
        st.dataframe(res.set_index("Period"), use_container_width=True)
    with col6:
        st.plotly_chart(resolution_grouped_bar(res), use_container_width=True)

    st.subheader("Overall Comparison Table")
    st.dataframe(overall_comparison(pre, post), use_container_width=True)

# ===== TAB: Categories =====
with tab_categories:
    cat_comp = category_comparison(cat)
    st.subheader("Category Ticket Comparison")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(category_comparison_chart(cat_comp), use_container_width=True)
    with col2:
        st.plotly_chart(category_change_waterfall(cat_comp), use_container_width=True)

    st.subheader("Category Distribution Treemaps")
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(category_treemap(cat, "pre"), use_container_width=True)
    with col4:
        st.plotly_chart(category_treemap(cat, "post"), use_container_width=True)

    st.subheader("Full Category Table")
    st.dataframe(cat_comp, use_container_width=True, height=400)

# ===== TAB: Support Deep-Dive =====
with tab_support:
    st.subheader("Support Tickets: Pre vs Post")
    support_comp = support_ticket_comparison(pre, post)

    col1, col2 = st.columns(2)
    with col1:
        total_support_pre = int(support_comp["Support Pre"].sum())
        total_support_post = int(support_comp["Support Post"].sum())
        st.metric("Total Support Pre", f"{total_support_pre:,}")
        st.metric("Total Support Post", f"{total_support_post:,}",
                  delta=f"{total_support_post - total_support_pre:+,}")
    with col2:
        st.plotly_chart(support_change_bar(support_comp, top_n=15), use_container_width=True)

    st.subheader("Support Ticket Change by Batch")
    st.dataframe(
        support_comp[support_comp["Support Pre"] + support_comp["Support Post"] > 0],
        use_container_width=True,
        height=400,
    )

# ===== TAB: Ratings & CSAT =====
with tab_ratings:
    st.subheader("Rating Analysis")
    st.info(
        "**Help tickets** can only be rated **1** or **5**. "
        "**Support tickets** can be rated **1–5**. "
        "Ratings outside these ranges and unrated tickets are excluded.",
        icon="ℹ️",
    )

    rat_dist = rating_distribution(tkt_all)
    rat_summ = rating_summary(tkt_all)
    csat_df = csat_score(tkt_all)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(rating_distribution_chart(rat_dist, "Help"), use_container_width=True)
    with col2:
        st.plotly_chart(rating_distribution_chart(rat_dist, "Support"), use_container_width=True)

    st.subheader("CSAT Score")
    st.caption("Help CSAT = % rated 5 out of valid rated tickets · Support CSAT = % rated ≥ 4")
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(csat_chart(csat_df), use_container_width=True)
    with col4:
        st.dataframe(csat_df, use_container_width=True)

    st.subheader("Rating Summary Table")
    st.dataframe(rat_summ, use_container_width=True)

# ===== TAB: EC Analysis =====
with tab_ec:
    st.subheader("EC (Experience Champion) Analysis")
    ec_data = ec_summary(tkt_all)

    period_sel = st.radio("Period", ["pre", "post"], format_func=lambda p: "Pre (26 Jan – 14 Feb)" if p == "pre" else "Post (15 Feb – 5 Mar)", horizontal=True, key="ec_period")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(ec_ticket_bar(ec_data, period_sel), use_container_width=True)
    with col2:
        st.plotly_chart(ec_rating_bar(ec_data, period_sel), use_container_width=True)

    st.plotly_chart(ec_resolution_bar(ec_data, period_sel), use_container_width=True)

    st.subheader("EC Comparison Pre vs Post")
    ec_comp = ec_comparison(tkt_all)
    st.dataframe(ec_comp, use_container_width=True, height=500)

    st.subheader("EC Detail Table")
    st.dataframe(
        ec_data[ec_data["Period"] == period_sel].reset_index(drop=True),
        use_container_width=True,
        height=400,
    )

# ===== TAB: Status & TAT =====
with tab_status:
    st.subheader("Ticket Status Distribution")
    status_dist = status_distribution(tkt_all)
    st.plotly_chart(status_grouped_bar(status_dist), use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.plotly_chart(status_pie(status_dist, "pre", "Support"), use_container_width=True)
    with col2:
        st.plotly_chart(status_pie(status_dist, "pre", "Help"), use_container_width=True)
    with col3:
        st.plotly_chart(status_pie(status_dist, "post", "Help"), use_container_width=True)
    with col4:
        st.plotly_chart(status_pie(status_dist, "post", "Support"), use_container_width=True)

    st.subheader("Open / Re-opened Tickets")
    open_summ = open_ticket_summary(tkt_all)
    st.dataframe(open_summ, use_container_width=True)

    st.subheader("Turnaround Time (TAT)")
    tat_summ = tat_summary(tkt_all)
    col5, col6 = st.columns([1, 2])
    with col5:
        st.dataframe(tat_summ, use_container_width=True)
    with col6:
        st.plotly_chart(tat_box(tkt_all), use_container_width=True)

    st.subheader("TAT by EC")
    tat_period = st.radio("Period", ["pre", "post"], format_func=lambda p: "Pre" if p == "pre" else "Post", horizontal=True, key="tat_period")
    tat_ec_data = tat_by_ec(tkt_all)
    st.plotly_chart(tat_ec_bar(tat_ec_data, tat_period), use_container_width=True)

    st.subheader("Priority Distribution")
    prio = priority_distribution(tkt_all)
    st.plotly_chart(priority_chart(prio), use_container_width=True)

# ===== TAB: Batch Comparison =====
with tab_batches:
    st.subheader("Batch-Level Comparison")

    b_comp = batch_comparison(pre, post)
    st.plotly_chart(batch_scatter(b_comp), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top 10 Batches – Pre**")
        st.plotly_chart(top_batches_bar(top_batches(pre, 10), "(Pre)"), use_container_width=True)
    with col2:
        st.markdown("**Top 10 Batches – Post**")
        st.plotly_chart(top_batches_bar(top_batches(post, 10), "(Post)"), use_container_width=True)

    st.subheader("Full Batch Comparison Table")
    st.dataframe(b_comp, use_container_width=True, height=500)

# ===== TAB: Raw Data =====
with tab_data:
    st.subheader("Aggregated Ticket Data")
    data_period = st.radio("Period", ["Pre", "Post"], horizontal=True, key="raw_period")
    if data_period == "Pre":
        st.dataframe(pre, use_container_width=True, height=400)
    else:
        st.dataframe(post, use_container_width=True, height=400)

    st.subheader("Category Data")
    cat_period = st.radio("Period", ["Pre", "Post"], horizontal=True, key="cat_period")
    st.dataframe(
        cat[cat["period"] == cat_period.lower()],
        use_container_width=True,
        height=400,
    )

    st.subheader("Ticket-Level Data")
    tkt_period = st.radio("Period", ["Pre", "Post"], horizontal=True, key="tkt_period")
    display_tkt = tkt_pre if tkt_period == "Pre" else tkt_post
    st.caption(f"{len(display_tkt):,} tickets")
    st.dataframe(display_tkt, use_container_width=True, height=500)

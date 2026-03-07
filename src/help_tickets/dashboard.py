"""
Streamlit dashboard for Help Tickets analysis.
Run with: streamlit run help_tickets/dashboard.py
"""

import streamlit as st
import pandas as pd
import sys, os
from pathlib import Path

# Add src folder to Python path
SRC_DIR = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC_DIR))

from src.data_loader import (
    load_raw_tickets,
    load_combined_categories,
    get_batch_list,
)
from src.analysis import (
    compute_kpis,
    overall_comparison,
    category_comparison,
    support_ticket_comparison,
    batch_comparison,
    resolution_metrics,
    top_batches,
    top_categories_by_batch,
    category_summary_by_period,
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
    category_by_batch_stacked,
    category_by_batch_heatmap,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Help Tickets Analysis", layout="wide", page_icon="🎫")

# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------

@st.cache_data
def load_data():
    pre, post = load_raw_tickets()
    cat = load_combined_categories()
    batches = get_batch_list()
    return pre, post, cat, batches


pre_raw, post_raw, cat_combined, all_batches = load_data()

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
    filter_label = f"Filtered: {len(selected_batches)} batch(es)"
else:
    pre = pre_raw.copy()
    post = post_raw.copy()
    cat = cat_combined.copy()
    filter_label = "All Batches (Overall)"

st.sidebar.markdown(f"**Scope:** {filter_label}")
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Pre period:** 26 Jan – 14 Feb  \n"
    "**Post period:** 15 Feb – 5 Mar  \n"
    "Help tickets introduced on 13-14 Feb."
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
tab_overall, tab_categories, tab_support, tab_batches, tab_data = st.tabs([
    "Overall", "Categories", "Support Deep-Dive", "Batch Comparison", "Raw Data"
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

    st.subheader("Resolution Rates")
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

    # ---- Category mix by batch (respects batch filter) ----
    st.subheader("Category mix by batch")
    st.caption(
        "Top categories per batch in Pre and Post. When no batch filter is applied, "
        "the top batches by combined volume are shown. Use the sidebar to filter by batch."
    )

    # Batch list: filtered selection or top N by combined (pre+post) volume
    if selected_batches:
        batch_list_cat = selected_batches
        max_batches_note = f"Showing {len(batch_list_cat)} selected batch(es)."
    else:
        pre_totals = pre.set_index("Batch Name")["Total Tickets"]
        post_totals = post.set_index("Batch Name")["Total Tickets"]
        combined_vol = pre_totals.add(post_totals, fill_value=0).sort_values(ascending=False)
        max_batches = 16
        batch_list_cat = combined_vol.head(max_batches).index.tolist()
        max_batches_note = f"Showing top {len(batch_list_cat)} batches by combined (Pre + Post) ticket volume."

    top_n_cat_per_batch = st.sidebar.slider(
        "Top N categories per batch (category-by-batch view)",
        min_value=3,
        max_value=8,
        value=5,
        help="Number of top categories to show for each batch in Pre and Post.",
    )

    if batch_list_cat:
        cat_by_batch_df = top_categories_by_batch(cat, batch_list_cat, top_n_cat=top_n_cat_per_batch)
        st.caption(max_batches_note)

        fig_pre_cb, fig_post_cb = category_by_batch_stacked(cat_by_batch_df)
        stacked_pre_tab, stacked_post_tab = st.tabs(["Pre view", "Post view"])
        with stacked_pre_tab:
            st.plotly_chart(fig_pre_cb, use_container_width=True)
        with stacked_post_tab:
            st.plotly_chart(fig_post_cb, use_container_width=True)

        with st.expander("Heatmap view – Category × Batch (Pre and Post)"):
            heatmap_pre_tab, heatmap_post_tab = st.tabs(["Pre heatmap", "Post heatmap"])
            with heatmap_pre_tab:
                st.plotly_chart(category_by_batch_heatmap(cat_by_batch_df, "pre"), use_container_width=True)
            with heatmap_post_tab:
                st.plotly_chart(category_by_batch_heatmap(cat_by_batch_df, "post"), use_container_width=True)

        with st.expander("Category-by-batch data table"):
            st.dataframe(cat_by_batch_df, use_container_width=True, height=400)
    else:
        st.info("No batches in scope. Select batches in the sidebar or ensure data is loaded.")

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

    st.subheader("Support Ticket Categories (Pre)")
    cat_pre_support = cat[cat["period"] == "pre"].groupby("Category", as_index=False)["Total Tickets"].sum()
    cat_pre_support = cat_pre_support.sort_values("Total Tickets", ascending=False)
    st.dataframe(cat_pre_support, use_container_width=True)

    st.subheader("Support Ticket Categories (Post)")
    cat_post_support = cat[cat["period"] == "post"].groupby("Category", as_index=False)["Total Tickets"].sum()
    cat_post_support = cat_post_support.sort_values("Total Tickets", ascending=False)
    st.dataframe(cat_post_support, use_container_width=True)

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
    st.subheader("Raw Ticket Data")
    data_period = st.radio("Period", ["Pre", "Post"], horizontal=True, key="raw_period")
    if data_period == "Pre":
        st.dataframe(pre, use_container_width=True, height=500)
    else:
        st.dataframe(post, use_container_width=True, height=500)

    st.subheader("Category Data")
    cat_period = st.radio("Period", ["Pre", "Post"], horizontal=True, key="cat_period")
    st.dataframe(
        cat[cat["period"] == cat_period.lower()],
        use_container_width=True,
        height=500,
    )

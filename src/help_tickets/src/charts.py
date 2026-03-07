"""
Plotly chart builders for the help-tickets dashboard.
Each function returns a plotly Figure object.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLORS = {
    "pre": "#636EFA",
    "post": "#EF553B",
    "help": "#00CC96",
    "support": "#AB63FA",
    "neutral": "#FFA15A",
}

PRE_LABEL = "Pre (26 Jan – 14 Feb)"
POST_LABEL = "Post (15 Feb – 5 Mar)"


def overall_ticket_bar(pre_total: int, post_total: int) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(
            x=[PRE_LABEL, POST_LABEL],
            y=[pre_total, post_total],
            marker_color=[COLORS["pre"], COLORS["post"]],
            text=[pre_total, post_total],
            textposition="outside",
        )
    ])
    fig.update_layout(
        title="Overall Ticket Volume: Pre vs Post",
        yaxis_title="Total Tickets",
        xaxis_title="Period",
        showlegend=False,
        height=400,
    )
    return fig


def help_vs_support_stacked(pre_help: int, pre_support: int,
                            post_help: int, post_support: int) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(name="Help Tickets", x=[PRE_LABEL, POST_LABEL],
               y=[pre_help, post_help], marker_color=COLORS["help"],
               text=[pre_help, post_help], textposition="inside"),
        go.Bar(name="Support Tickets", x=[PRE_LABEL, POST_LABEL],
               y=[pre_support, post_support], marker_color=COLORS["support"],
               text=[pre_support, post_support], textposition="inside"),
    ])
    fig.update_layout(
        barmode="stack",
        title="Help vs Support Ticket Split",
        yaxis_title="Tickets",
        height=400,
    )
    return fig


def help_support_pct_bar(pre_help_pct: float, post_help_pct: float) -> go.Figure:
    fig = go.Figure(data=[
        go.Bar(name="Help %", x=[PRE_LABEL, POST_LABEL],
               y=[pre_help_pct, 100 - pre_help_pct if pre_help_pct else 0],
               marker_color=COLORS["help"]),
    ])
    fig = go.Figure(data=[
        go.Bar(name="Help %", x=[PRE_LABEL, POST_LABEL],
               y=[pre_help_pct, post_help_pct], marker_color=COLORS["help"],
               text=[f"{pre_help_pct}%", f"{post_help_pct}%"], textposition="outside"),
        go.Bar(name="Support %", x=[PRE_LABEL, POST_LABEL],
               y=[100 - pre_help_pct, 100 - post_help_pct], marker_color=COLORS["support"],
               text=[f"{round(100 - pre_help_pct, 1)}%", f"{round(100 - post_help_pct, 1)}%"],
               textposition="outside"),
    ])
    fig.update_layout(
        barmode="group",
        title="Help vs Support Ticket Percentage",
        yaxis_title="Percentage",
        height=400,
    )
    return fig


def category_comparison_chart(cat_comp: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Grouped bar chart comparing top N categories pre vs post."""
    df = cat_comp.head(top_n).copy()
    fig = go.Figure(data=[
        go.Bar(name="Pre", x=df["Category"], y=df["Pre"], marker_color=COLORS["pre"]),
        go.Bar(name="Post", x=df["Category"], y=df["Post"], marker_color=COLORS["post"]),
    ])
    fig.update_layout(
        barmode="group",
        title=f"Top {top_n} Categories: Pre vs Post",
        xaxis_title="Category",
        yaxis_title="Total Tickets",
        xaxis_tickangle=-45,
        height=500,
    )
    return fig


def category_change_waterfall(cat_comp: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Horizontal bar chart showing category ticket change (post - pre)."""
    df = cat_comp.sort_values("Change").tail(top_n).copy()
    colors = [COLORS["post"] if v >= 0 else COLORS["pre"] for v in df["Change"]]
    fig = go.Figure(data=[
        go.Bar(
            y=df["Category"],
            x=df["Change"],
            orientation="h",
            marker_color=colors,
            text=df["Change"].astype(int),
            textposition="outside",
        )
    ])
    fig.update_layout(
        title="Category Ticket Change (Post − Pre)",
        xaxis_title="Change in Tickets",
        height=500,
    )
    return fig


def support_change_bar(support_comp: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Show batches with biggest support ticket change."""
    df = support_comp.dropna(subset=["Change"]).copy()
    df = df[df["Support Pre"] + df["Support Post"] > 0]
    df = df.sort_values("Change").head(top_n)
    colors = [COLORS["post"] if v >= 0 else COLORS["pre"] for v in df["Change"]]
    fig = go.Figure(data=[
        go.Bar(
            y=df["Batch Name"],
            x=df["Change"],
            orientation="h",
            marker_color=colors,
            text=df["Change"].astype(int),
            textposition="outside",
        )
    ])
    fig.update_layout(
        title=f"Top {top_n} Batches – Support Ticket Change",
        xaxis_title="Change in Support Tickets",
        height=500,
    )
    return fig


def batch_scatter(batch_comp: pd.DataFrame) -> go.Figure:
    """Scatter plot of pre vs post total tickets per batch."""
    df = batch_comp[(batch_comp["Total Tickets Pre"] > 0) | (batch_comp["Total Tickets Post"] > 0)].copy()
    fig = px.scatter(
        df,
        x="Total Tickets Pre",
        y="Total Tickets Post",
        hover_name="Batch Name",
        size="Total Tickets Post",
        color="Ticket Change",
        color_continuous_scale="RdYlGn",
        title="Batch-Level Ticket Volume: Pre vs Post",
        height=500,
    )
    max_val = max(df["Total Tickets Pre"].max(), df["Total Tickets Post"].max()) * 1.1
    fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                  line=dict(dash="dash", color="gray"))
    return fig


def resolution_grouped_bar(res_df: pd.DataFrame) -> go.Figure:
    """Grouped bars for resolution rates."""
    fig = go.Figure(data=[
        go.Bar(name="Help Resolution %",
               x=res_df["Period"], y=res_df["Help Resolution Rate %"],
               marker_color=COLORS["help"],
               text=res_df["Help Resolution Rate %"].apply(lambda v: f"{v}%"),
               textposition="outside"),
        go.Bar(name="Support Resolution %",
               x=res_df["Period"], y=res_df["Support Resolution Rate %"],
               marker_color=COLORS["support"],
               text=res_df["Support Resolution Rate %"].apply(lambda v: f"{v}%"),
               textposition="outside"),
    ])
    fig.update_layout(
        barmode="group",
        title="Resolution Rates: Help vs Support",
        yaxis_title="Resolution Rate %",
        height=400,
    )
    return fig


def top_batches_bar(df: pd.DataFrame, title_suffix: str = "") -> go.Figure:
    """Horizontal bar for top batches by total tickets."""
    fig = go.Figure(data=[
        go.Bar(name="Help", y=df["Batch Name"], x=df["Total Help Tickets"],
               orientation="h", marker_color=COLORS["help"]),
        go.Bar(name="Support", y=df["Batch Name"], x=df["Total Support Tickets"],
               orientation="h", marker_color=COLORS["support"]),
    ])
    fig.update_layout(
        barmode="stack",
        title=f"Top Batches by Volume {title_suffix}",
        xaxis_title="Tickets",
        height=450,
        yaxis=dict(autorange="reversed"),
    )
    return fig


def user_comparison_bar(kpis: dict) -> go.Figure:
    """Compare unique help/support users pre vs post."""
    fig = go.Figure(data=[
        go.Bar(name="Help Users", x=[PRE_LABEL, POST_LABEL],
               y=[kpis["pre_unique_help_users"], kpis["post_unique_help_users"]],
               marker_color=COLORS["help"],
               text=[kpis["pre_unique_help_users"], kpis["post_unique_help_users"]],
               textposition="outside"),
        go.Bar(name="Support Users", x=[PRE_LABEL, POST_LABEL],
               y=[kpis["pre_unique_support_users"], kpis["post_unique_support_users"]],
               marker_color=COLORS["support"],
               text=[kpis["pre_unique_support_users"], kpis["post_unique_support_users"]],
               textposition="outside"),
    ])
    fig.update_layout(
        barmode="group",
        title="Unique Users: Help vs Support",
        yaxis_title="Users",
        height=400,
    )
    return fig


def category_treemap(cat_df: pd.DataFrame, period: str) -> go.Figure:
    """Treemap of category distribution for a given period."""
    df = cat_df[cat_df["period"] == period].groupby("Category", as_index=False)["Total Tickets"].sum()
    df = df[df["Total Tickets"] > 0].sort_values("Total Tickets", ascending=False)
    fig = px.treemap(
        df, path=["Category"], values="Total Tickets",
        title=f"Category Distribution – {'Pre' if period == 'pre' else 'Post'}",
        height=450,
    )
    return fig


def category_by_batch_stacked(cat_by_batch_df: pd.DataFrame) -> tuple[go.Figure, go.Figure]:
    """
    Two stacked bar charts: top categories per batch for Pre and for Post.
    cat_by_batch_df must have columns: Batch Name, period, Category, Total Tickets.
    Returns (fig_pre, fig_post). Batch order is by total tickets (desc) within each period.
    """
    if cat_by_batch_df.empty:
        empty = go.Figure().update_layout(title="No data", height=400)
        return empty, empty

    def _make_stacked(period_label: str, period_key: str, color_map: dict) -> go.Figure:
        sub = cat_by_batch_df[cat_by_batch_df["period"] == period_key]
        if sub.empty:
            return go.Figure().update_layout(title=f"{period_label} – No data", height=400)
        # Order batches by total tickets (desc) so top batch at top
        batch_totals = sub.groupby("Batch Name")["Total Tickets"].sum().sort_values(ascending=True)
        batch_order = batch_totals.index.tolist()
        fig = px.bar(
            sub,
            y="Batch Name",
            x="Total Tickets",
            color="Category",
            orientation="h",
            barmode="stack",
            category_orders={"Batch Name": batch_order},
            color_discrete_map=color_map,
        )
        fig.update_layout(
            title=f"Top categories by batch – {period_label}",
            xaxis_title="Total Tickets",
            yaxis_title="Batch",
            height=max(500, len(batch_order) * 22 + 130),
            yaxis=dict(autorange="reversed"),
            xaxis=dict(title_standoff=30, automargin=True),
            margin=dict(t=80, r=20, b=155, l=20),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.32,
                xanchor="left",
                x=0,
                title_text="Category",
            ),
        )
        return fig

    # Use a consistent color set for categories (plotly default palette)
    categories = cat_by_batch_df["Category"].unique().tolist()
    color_list = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    color_map = {c: color_list[i % len(color_list)] for i, c in enumerate(categories)}

    fig_pre = _make_stacked("Pre (26 Jan – 14 Feb)", "pre", color_map)
    fig_post = _make_stacked("Post (15 Feb – 5 Mar)", "post", color_map)
    return fig_pre, fig_post


def category_by_batch_heatmap(cat_by_batch_df: pd.DataFrame, period: str) -> go.Figure:
    """Heatmap: batches (Y) x categories (X), color = ticket count. One period only."""
    sub = cat_by_batch_df[cat_by_batch_df["period"] == period].copy()
    if sub.empty:
        return go.Figure().update_layout(title=f"No data – {period}", height=400)
    pivot = sub.pivot_table(
        index="Batch Name", columns="Category", values="Total Tickets", fill_value=0
    )
    # Order batches by row sum (desc)
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    fig = px.imshow(
        pivot,
        labels=dict(x="Category", y="Batch", color="Tickets"),
        aspect="auto",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        title=f"Category mix by batch – {'Pre' if period == 'pre' else 'Post'}",
        height=max(350, pivot.shape[0] * 24),
        xaxis_tickangle=-45,
    )
    return fig

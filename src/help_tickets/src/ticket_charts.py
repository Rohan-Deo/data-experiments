"""
Plotly chart builders for ticket-level analysis (ratings, EC, status, TAT, trends).
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLORS = {
    "pre": "#636EFA",
    "post": "#EF553B",
    "help": "#00CC96",
    "support": "#AB63FA",
}

PRE_LABEL = "Pre (26 Jan – 14 Feb)"
POST_LABEL = "Post (15 Feb – 5 Mar)"

_PERIOD_MAP = {"pre": PRE_LABEL, "post": POST_LABEL}


def _period_label(p: str) -> str:
    return _PERIOD_MAP.get(p, p)


# ---------------------------------------------------------------------------
# Rating charts
# ---------------------------------------------------------------------------

def rating_distribution_chart(dist_df: pd.DataFrame, ticket_type: str) -> go.Figure:
    """Grouped bar of rating counts for a given ticket type, pre vs post."""
    df = dist_df[dist_df["Ticket Type"] == ticket_type].copy()
    df["Period Label"] = df["period"].map(_period_label)
    fig = px.bar(
        df, x="Rating", y="Count", color="Period Label",
        barmode="group",
        color_discrete_map={PRE_LABEL: COLORS["pre"], POST_LABEL: COLORS["post"]},
        title=f"Rating Distribution – {ticket_type} Tickets (Valid Ratings Only)",
        text="Count",
    )
    valid_ratings = [1, 5] if ticket_type == "Help" else [1, 2, 3, 4, 5]
    fig.update_xaxes(tickvals=valid_ratings)
    fig.update_layout(height=400)
    return fig


def csat_chart(csat_df: pd.DataFrame) -> go.Figure:
    """Bar chart of CSAT % by ticket type and period."""
    df = csat_df.copy()
    df["Period Label"] = df["Period"].map(_period_label)
    fig = px.bar(
        df, x="Ticket Type", y="CSAT %", color="Period Label",
        barmode="group",
        text="CSAT %",
        color_discrete_map={PRE_LABEL: COLORS["pre"], POST_LABEL: COLORS["post"]},
        title="CSAT Score (Help: % rated 5 | Support: % rated ≥ 4)",
    )
    fig.update_layout(height=400, yaxis_range=[0, 105])
    return fig


def rating_summary_table_chart(summary_df: pd.DataFrame) -> go.Figure:
    """Heatmap-style table of rating summary."""
    df = summary_df.copy()
    df["Period Label"] = df["Period"].map(_period_label)
    fig = go.Figure(data=[go.Table(
        header=dict(values=list(df.columns), fill_color="#2d2d2d", font=dict(color="white")),
        cells=dict(values=[df[c] for c in df.columns], fill_color="#f9f9f9"),
    )])
    fig.update_layout(title="Rating Summary", height=250)
    return fig


# ---------------------------------------------------------------------------
# EC Name charts
# ---------------------------------------------------------------------------

def ec_ticket_bar(ec_df: pd.DataFrame, period: str, top_n: int = 15) -> go.Figure:
    """Stacked bar of tickets per EC (help vs support) for a period."""
    df = ec_df[ec_df["Period"] == period].nlargest(top_n, "Total Tickets")
    fig = go.Figure(data=[
        go.Bar(name="Help", y=df["Ec Name"], x=df["Help Tickets"],
               orientation="h", marker_color=COLORS["help"]),
        go.Bar(name="Support", y=df["Ec Name"], x=df["Support Tickets"],
               orientation="h", marker_color=COLORS["support"]),
    ])
    fig.update_layout(
        barmode="stack",
        title=f"Top {top_n} ECs by Ticket Volume – {_period_label(period)}",
        xaxis_title="Tickets", height=500,
        yaxis=dict(autorange="reversed"),
    )
    return fig


def ec_rating_bar(ec_df: pd.DataFrame, period: str, top_n: int = 15) -> go.Figure:
    """Bar chart of avg rating per EC for a period (only ECs with rated tickets)."""
    df = ec_df[(ec_df["Period"] == period) & (ec_df["Rated Tickets"] > 0)].copy()
    df = df.nlargest(top_n, "Rated Tickets")
    fig = go.Figure(data=[
        go.Bar(
            y=df["Ec Name"], x=df["Avg Rating"], orientation="h",
            marker_color=COLORS["post"],
            text=df["Avg Rating"], textposition="outside",
        )
    ])
    fig.update_layout(
        title=f"Avg Rating per EC – {_period_label(period)} (ECs with ≥1 rated ticket)",
        xaxis_title="Avg Rating", xaxis_range=[0, 5.5], height=500,
        yaxis=dict(autorange="reversed"),
    )
    return fig


def ec_resolution_bar(ec_df: pd.DataFrame, period: str, top_n: int = 15) -> go.Figure:
    """Resolution rate per EC."""
    df = ec_df[(ec_df["Period"] == period) & (ec_df["Total Tickets"] > 10)].copy()
    df = df.nsmallest(top_n, "Resolution Rate %")
    fig = go.Figure(data=[
        go.Bar(
            y=df["Ec Name"], x=df["Resolution Rate %"], orientation="h",
            marker_color=COLORS["pre"],
            text=df["Resolution Rate %"].apply(lambda v: f"{v}%"), textposition="outside",
        )
    ])
    fig.update_layout(
        title=f"Lowest Resolution Rates – {_period_label(period)} (ECs with >10 tickets)",
        xaxis_title="Resolution Rate %", xaxis_range=[0, 105], height=500,
        yaxis=dict(autorange="reversed"),
    )
    return fig


# ---------------------------------------------------------------------------
# Status charts
# ---------------------------------------------------------------------------

def status_pie(df: pd.DataFrame, period: str, ticket_type: str) -> go.Figure:
    """Pie chart of status distribution."""
    sub = df[(df["period"] == period) & (df["Ticket Type"] == ticket_type)].copy()
    fig = px.pie(
        sub, names="Status", values="Count",
        title=f"Status – {ticket_type} ({_period_label(period)})",
        hole=0.35, height=380,
    )
    return fig


def status_grouped_bar(df: pd.DataFrame) -> go.Figure:
    """Grouped bar showing status counts across periods and types."""
    df = df.copy()
    df["Label"] = df["period"].map(_period_label) + " – " + df["Ticket Type"]
    fig = px.bar(
        df, x="Status", y="Count", color="Label", barmode="group",
        title="Status Distribution by Period & Type",
        height=450,
    )
    return fig


# ---------------------------------------------------------------------------
# TAT charts
# ---------------------------------------------------------------------------

def tat_box(tickets_df: pd.DataFrame) -> go.Figure:
    """Box plot of TAT by period and ticket type. Cap at 99th percentile for readability."""
    df = tickets_df[tickets_df["Ticket Closure Tat"].notna()].copy()
    cap = df["Ticket Closure Tat"].quantile(0.99)
    df = df[df["Ticket Closure Tat"] <= cap]
    df["Group"] = df["period"].map(_period_label) + " – " + df["Ticket Type"]
    fig = px.box(
        df, x="Group", y="Ticket Closure Tat",
        color="Ticket Type",
        color_discrete_map={"Help": COLORS["help"], "Support": COLORS["support"]},
        title="TAT Distribution (capped at P99)",
        height=450,
    )
    fig.update_yaxes(title="TAT (minutes)")
    return fig


def tat_ec_bar(tat_ec_df: pd.DataFrame, period: str, top_n: int = 15) -> go.Figure:
    """Top N ECs by median TAT."""
    df = tat_ec_df[tat_ec_df["period"] == period].nlargest(top_n, "Median TAT (min)")
    fig = go.Figure(data=[
        go.Bar(
            y=df["Ec Name"], x=df["Median TAT (min)"], orientation="h",
            marker_color=COLORS["post"],
            text=df["Median TAT (min)"].round(0).astype(int),
            textposition="outside",
        )
    ])
    fig.update_layout(
        title=f"Highest Median TAT by EC – {_period_label(period)}",
        xaxis_title="Median TAT (min)", height=500,
        yaxis=dict(autorange="reversed"),
    )
    return fig


# ---------------------------------------------------------------------------
# Daily trend chart
# ---------------------------------------------------------------------------

def daily_trend_chart(trend_df: pd.DataFrame) -> go.Figure:
    """Line chart of daily ticket volume by type."""
    fig = px.line(
        trend_df, x="Created Date", y="Count", color="Ticket Type",
        color_discrete_map={"Help": COLORS["help"], "Support": COLORS["support"]},
        title="Daily Ticket Volume",
        markers=True, height=420,
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="Tickets")
    return fig


def daily_trend_stacked(trend_df: pd.DataFrame) -> go.Figure:
    """Stacked area chart of daily ticket volume."""
    fig = px.area(
        trend_df, x="Created Date", y="Count", color="Ticket Type",
        color_discrete_map={"Help": COLORS["help"], "Support": COLORS["support"]},
        title="Daily Ticket Volume (Stacked)",
        height=420,
    )
    return fig


# ---------------------------------------------------------------------------
# Priority chart
# ---------------------------------------------------------------------------

def priority_chart(prio_df: pd.DataFrame) -> go.Figure:
    """Grouped bar of priority distribution."""
    df = prio_df.copy()
    df["Label"] = df["period"].map(_period_label) + " – " + df["Ticket Type"]
    fig = px.bar(
        df, x="Priority", y="Count", color="Label", barmode="group",
        title="Priority Distribution", height=450,
    )
    return fig

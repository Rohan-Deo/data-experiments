"""
Ticket-level analysis: ratings, EC performance, status, TAT, daily trends.
All functions accept a ticket-level DataFrame so batch filters can be applied upstream.
"""

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Rating analysis
# ---------------------------------------------------------------------------

def rating_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Count of each rating value, split by Ticket Type and period.
    Only includes *valid* ratings (Help: 1/5, Support: 1-5)."""
    rated = df[df["Valid Rating"]].copy()
    return (
        rated.groupby(["period", "Ticket Type", "Rating"], as_index=False)
        .size()
        .rename(columns={"size": "Count"})
        .sort_values(["period", "Ticket Type", "Rating"])
    )


def rating_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Average rating, count rated, % rated — by period and type (valid ratings only)."""
    rows = []
    for (period, ttype), grp in df.groupby(["period", "Ticket Type"]):
        total = len(grp)
        valid = grp[grp["Valid Rating"]]
        rated_count = len(valid)
        avg = valid["Rating"].mean() if rated_count > 0 else np.nan
        pct_rated = round(rated_count / max(total, 1) * 100, 2)
        pct_5 = round(
            (valid["Rating"] == 5).sum() / max(rated_count, 1) * 100, 2
        ) if rated_count > 0 else 0
        pct_1 = round(
            (valid["Rating"] == 1).sum() / max(rated_count, 1) * 100, 2
        ) if rated_count > 0 else 0
        rows.append({
            "Period": period,
            "Ticket Type": ttype,
            "Total Tickets": total,
            "Rated Tickets": rated_count,
            "% Rated": pct_rated,
            "Avg Rating": round(avg, 2) if not np.isnan(avg) else None,
            "% Rating = 5": pct_5,
            "% Rating = 1": pct_1,
        })
    return pd.DataFrame(rows)


def csat_score(df: pd.DataFrame) -> pd.DataFrame:
    """CSAT = % of rated tickets with rating >= 4 (Support) or == 5 (Help).
    Calculated separately so we don't compare apples to oranges."""
    rows = []
    for (period, ttype), grp in df.groupby(["period", "Ticket Type"]):
        valid = grp[grp["Valid Rating"]]
        rated = len(valid)
        if ttype == "Help":
            satisfied = (valid["Rating"] == 5).sum()
        else:
            satisfied = (valid["Rating"] >= 4).sum()
        csat = round(satisfied / max(rated, 1) * 100, 2)
        rows.append({
            "Period": period,
            "Ticket Type": ttype,
            "Rated Tickets": rated,
            "Satisfied": int(satisfied),
            "CSAT %": csat,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# EC Name analysis
# ---------------------------------------------------------------------------

def ec_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per EC Name: ticket counts, resolution rate, avg TAT, avg rating."""
    rows = []
    for (ec, period), grp in df.groupby(["Ec Name", "period"]):
        total = len(grp)
        help_count = (grp["Ticket Type"] == "Help").sum()
        support_count = (grp["Ticket Type"] == "Support").sum()
        resolved = grp["Status"].isin(["resolved", "closed"]).sum()
        res_rate = round(resolved / max(total, 1) * 100, 2)
        avg_tat = round(grp["Ticket Closure Tat"].mean(), 2) if grp["Ticket Closure Tat"].notna().any() else None
        valid = grp[grp["Valid Rating"]]
        avg_rating = round(valid["Rating"].mean(), 2) if len(valid) > 0 else None
        rated_count = len(valid)
        rows.append({
            "Ec Name": ec,
            "Period": period,
            "Total Tickets": total,
            "Help Tickets": int(help_count),
            "Support Tickets": int(support_count),
            "Resolved/Closed": int(resolved),
            "Resolution Rate %": res_rate,
            "Avg TAT (min)": avg_tat,
            "Rated Tickets": rated_count,
            "Avg Rating": avg_rating,
        })
    return pd.DataFrame(rows).sort_values(["Period", "Total Tickets"], ascending=[True, False])


def ec_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Side-by-side EC metrics pre vs post."""
    summary = ec_summary(df)
    pre_ec = summary[summary["Period"] == "pre"].drop(columns=["Period"]).rename(
        columns=lambda c: f"{c} (Pre)" if c != "Ec Name" else c
    )
    post_ec = summary[summary["Period"] == "post"].drop(columns=["Period"]).rename(
        columns=lambda c: f"{c} (Post)" if c != "Ec Name" else c
    )
    merged = pre_ec.merge(post_ec, on="Ec Name", how="outer").fillna(0)
    merged["Ticket Change"] = merged["Total Tickets (Post)"] - merged["Total Tickets (Pre)"]
    return merged.sort_values("Total Tickets (Post)", ascending=False)


def ec_rating_detail(df: pd.DataFrame) -> pd.DataFrame:
    """Per EC, per ticket type: avg valid rating and count."""
    rows = []
    for (ec, period, ttype), grp in df.groupby(["Ec Name", "period", "Ticket Type"]):
        valid = grp[grp["Valid Rating"]]
        rows.append({
            "Ec Name": ec,
            "Period": period,
            "Ticket Type": ttype,
            "Tickets": len(grp),
            "Rated": len(valid),
            "Avg Rating": round(valid["Rating"].mean(), 2) if len(valid) > 0 else None,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Status analysis
# ---------------------------------------------------------------------------

def status_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Ticket count by status, period, and type."""
    return (
        df.groupby(["period", "Ticket Type", "Status"], as_index=False)
        .size()
        .rename(columns={"size": "Count"})
        .sort_values(["period", "Ticket Type", "Count"], ascending=[True, True, False])
    )


def open_ticket_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Tickets still open or re-opened, by type and period."""
    pending = df[df["Status"].isin(["open", "re-opened"])].copy()
    return (
        pending.groupby(["period", "Ticket Type"], as_index=False)
        .agg(Open_Count=("Ticket ID", "count"))
        .sort_values(["period", "Open_Count"], ascending=[True, False])
    )


# ---------------------------------------------------------------------------
# TAT (Ticket Closure Turnaround Time) analysis
# ---------------------------------------------------------------------------

def tat_summary(df: pd.DataFrame) -> pd.DataFrame:
    """TAT statistics by period and ticket type."""
    rows = []
    for (period, ttype), grp in df.groupby(["period", "Ticket Type"]):
        tat = grp["Ticket Closure Tat"].dropna()
        if len(tat) == 0:
            continue
        rows.append({
            "Period": period,
            "Ticket Type": ttype,
            "Count": len(tat),
            "Mean TAT (min)": round(tat.mean(), 2),
            "Median TAT (min)": round(tat.median(), 2),
            "P90 TAT (min)": round(tat.quantile(0.9), 2),
            "Max TAT (min)": round(tat.max(), 2),
        })
    return pd.DataFrame(rows)


def tat_by_ec(df: pd.DataFrame) -> pd.DataFrame:
    """Median TAT per EC per period."""
    return (
        df.groupby(["Ec Name", "period"], as_index=False)["Ticket Closure Tat"]
        .median()
        .rename(columns={"Ticket Closure Tat": "Median TAT (min)"})
        .sort_values(["period", "Median TAT (min)"])
    )


# ---------------------------------------------------------------------------
# Daily trend
# ---------------------------------------------------------------------------

def daily_ticket_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Daily ticket count by type."""
    return (
        df.groupby(["Created Date", "Ticket Type"], as_index=False)
        .size()
        .rename(columns={"size": "Count"})
        .sort_values("Created Date")
    )


# ---------------------------------------------------------------------------
# Priority analysis
# ---------------------------------------------------------------------------

def priority_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Ticket count by priority, period, type."""
    df = df.copy()
    df["Priority"] = df["Priority"].fillna("Not Set")
    return (
        df.groupby(["period", "Ticket Type", "Priority"], as_index=False)
        .size()
        .rename(columns={"size": "Count"})
        .sort_values(["period", "Ticket Type", "Count"], ascending=[True, True, False])
    )

"""
Compute analysis metrics comparing pre vs post help-ticket introduction.
All functions accept DataFrames so they can work with filtered (batch-level) data.
"""

import pandas as pd
from .data_loader import load_raw_tickets, load_combined_categories, load_combined_raw


# ---------------------------------------------------------------------------
# Overall aggregation helpers
# ---------------------------------------------------------------------------

def _aggregate_raw(df: pd.DataFrame) -> pd.Series:
    """Summarize a raw-tickets DataFrame into a single row of totals."""
    return pd.Series({
        "Total Tickets": df["Total Tickets"].sum(),
        "Total Help Tickets": df["Total Help Tickets"].sum(),
        "Total Support Tickets": df["Total Support Tickets"].sum(),
        "Help - Open": df["Help - Open"].sum(),
        "Help - Resolved": df["Help - Resolved"].sum(),
        "Help - Reopened": df["Help - Reopened"].sum(),
        "Help - Closed": df["Help - Closed"].sum(),
        "Support - Open": df["Support - Open"].sum(),
        "Support - Resolved": df["Support - Resolved"].sum(),
        "Support - Reopened": df["Support - Reopened"].sum(),
        "Support - Closed": df["Support - Closed"].sum(),
        "Total Users": df["Number of Users in Batch"].sum(),
        "Total Active Users": df["Number of Active Users in Batch"].sum(),
        "Unique Users - Help": df["Unique Users - Help"].sum(),
        "Unique Users - Support": df["Unique Users - Support"].sum(),
        "Unique Users - Both": df["Unique Users - Both Help & Support"].sum(),
        "Active Batches": (df["Total Tickets"] > 0).sum(),
    })


def overall_comparison(pre: pd.DataFrame, post: pd.DataFrame) -> pd.DataFrame:
    """Side-by-side comparison of overall metrics for pre vs post."""
    pre_agg = _aggregate_raw(pre)
    post_agg = _aggregate_raw(post)
    comp = pd.DataFrame({"Pre (26 Jan – 14 Feb)": pre_agg, "Post (15 Feb – 5 Mar)": post_agg})
    comp["Change"] = comp["Post (15 Feb – 5 Mar)"] - comp["Pre (26 Jan – 14 Feb)"]
    comp["Change %"] = pd.to_numeric(
        comp["Change"] / comp["Pre (26 Jan – 14 Feb)"].replace(0, pd.NA) * 100,
        errors="coerce",
    ).round(2)
    return comp


# ---------------------------------------------------------------------------
# Category-level analysis
# ---------------------------------------------------------------------------

def category_summary_by_period(cat_df: pd.DataFrame) -> pd.DataFrame:
    """Total tickets per category per period."""
    return (
        cat_df.groupby(["period", "Category"], as_index=False)["Total Tickets"]
        .sum()
        .sort_values(["period", "Total Tickets"], ascending=[True, False])
    )


def category_comparison(cat_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot table showing each category's total in pre vs post, with change."""
    summary = category_summary_by_period(cat_df)
    pivot = summary.pivot_table(
        index="Category", columns="period", values="Total Tickets", fill_value=0
    )
    pivot.columns = ["Post", "Pre"]
    if "Pre" not in pivot.columns:
        pivot["Pre"] = 0
    if "Post" not in pivot.columns:
        pivot["Post"] = 0
    pivot = pivot[["Pre", "Post"]]
    pivot["Change"] = pivot["Post"] - pivot["Pre"]
    pivot["Change %"] = pd.to_numeric(
        pivot["Change"] / pivot["Pre"].replace(0, pd.NA) * 100, errors="coerce"
    ).round(2)
    return pivot.sort_values("Post", ascending=False).reset_index()


# ---------------------------------------------------------------------------
# Support ticket deep-dive
# ---------------------------------------------------------------------------

def support_ticket_comparison(pre: pd.DataFrame, post: pd.DataFrame) -> pd.DataFrame:
    """Per-batch comparison of support ticket counts pre vs post."""
    pre_support = pre[["Batch Name", "Total Support Tickets"]].rename(
        columns={"Total Support Tickets": "Support Pre"}
    )
    post_support = post[["Batch Name", "Total Support Tickets"]].rename(
        columns={"Total Support Tickets": "Support Post"}
    )
    merged = pre_support.merge(post_support, on="Batch Name", how="outer").fillna(0)
    merged["Change"] = merged["Support Post"] - merged["Support Pre"]
    merged["Change %"] = pd.to_numeric(
        merged["Change"] / merged["Support Pre"].replace(0, pd.NA) * 100, errors="coerce"
    ).round(2)
    return merged.sort_values("Support Pre", ascending=False)


# ---------------------------------------------------------------------------
# Batch-level summary
# ---------------------------------------------------------------------------

def batch_comparison(pre: pd.DataFrame, post: pd.DataFrame) -> pd.DataFrame:
    """Merge pre and post for the same batch showing key columns side by side."""
    cols = ["Batch Name", "Total Tickets", "Total Help Tickets", "Total Support Tickets",
            "Help Ticket %", "Support Ticket %", "Tickets per Active User"]

    pre_sub = pre[cols].copy()
    post_sub = post[cols].copy()

    merged = pre_sub.merge(post_sub, on="Batch Name", suffixes=(" Pre", " Post"), how="outer").fillna(0)
    merged["Ticket Change"] = merged["Total Tickets Post"] - merged["Total Tickets Pre"]
    merged["Ticket Change %"] = pd.to_numeric(
        merged["Ticket Change"] / merged["Total Tickets Pre"].replace(0, pd.NA) * 100, errors="coerce"
    ).round(2)
    return merged.sort_values("Total Tickets Pre", ascending=False)


# ---------------------------------------------------------------------------
# Top-level KPI cards
# ---------------------------------------------------------------------------

def compute_kpis(pre: pd.DataFrame, post: pd.DataFrame) -> dict:
    """Return a dict of headline KPIs for the dashboard."""
    pre_total = int(pre["Total Tickets"].sum())
    post_total = int(post["Total Tickets"].sum())
    pre_support = int(pre["Total Support Tickets"].sum())
    post_support = int(post["Total Support Tickets"].sum())
    pre_help = int(pre["Total Help Tickets"].sum())
    post_help = int(post["Total Help Tickets"].sum())

    return {
        "pre_total": pre_total,
        "post_total": post_total,
        "total_change_pct": round((post_total - pre_total) / max(pre_total, 1) * 100, 2),
        "pre_support": pre_support,
        "post_support": post_support,
        "support_change_pct": round((post_support - pre_support) / max(pre_support, 1) * 100, 2),
        "pre_help": pre_help,
        "post_help": post_help,
        "help_change_pct": round((post_help - pre_help) / max(pre_help, 1) * 100, 2),
        "post_help_pct": round(post_help / max(post_total, 1) * 100, 2),
        "pre_help_pct": round(pre_help / max(pre_total, 1) * 100, 2),
        "pre_active_batches": int((pre["Total Tickets"] > 0).sum()),
        "post_active_batches": int((post["Total Tickets"] > 0).sum()),
        "pre_unique_help_users": int(pre["Unique Users - Help"].sum()),
        "post_unique_help_users": int(post["Unique Users - Help"].sum()),
        "pre_unique_support_users": int(pre["Unique Users - Support"].sum()),
        "post_unique_support_users": int(post["Unique Users - Support"].sum()),
    }


# ---------------------------------------------------------------------------
# Resolution / open-ticket metrics
# ---------------------------------------------------------------------------

def resolution_metrics(pre: pd.DataFrame, post: pd.DataFrame) -> pd.DataFrame:
    """Compare open vs resolved rates for help and support tickets."""
    rows = []
    for label, df in [("Pre", pre), ("Post", post)]:
        help_total = df["Total Help Tickets"].sum()
        support_total = df["Total Support Tickets"].sum()
        rows.append({
            "Period": label,
            "Help Resolved": int(df["Help - Resolved"].sum()),
            "Help Open": int(df["Help - Open"].sum()),
            "Help Reopened": int(df["Help - Reopened"].sum()),
            "Help Resolution Rate %": round(
                df["Help - Resolved"].sum() / max(help_total, 1) * 100, 2
            ),
            "Support Resolved": int(df["Support - Resolved"].sum()),
            "Support Open": int(df["Support - Open"].sum()),
            "Support Reopened": int(df["Support - Reopened"].sum()),
            "Support Resolution Rate %": round(
                df["Support - Resolved"].sum() / max(support_total, 1) * 100, 2
            ),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Ticket concentration (top N batches)
# ---------------------------------------------------------------------------

def top_batches(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Return top N batches by total tickets."""
    return (
        df.nlargest(n, "Total Tickets")[["Batch Name", "Total Tickets", "Total Help Tickets",
                                          "Total Support Tickets", "Help Ticket %"]]
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Category-by-batch (top categories per batch, pre vs post)
# ---------------------------------------------------------------------------

def top_categories_by_batch(cat_df: pd.DataFrame, batches: list[str], top_n_cat: int = 5) -> pd.DataFrame:
    """
    For each batch in batches, return top N categories in pre and in post with ticket counts.
    Returns a long-format table: Batch Name, period, rank, Category, Total Tickets.
    """
    rows = []
    for batch in batches:
        sub = cat_df[cat_df["Batch Name"] == batch]
        for period in ["pre", "post"]:
            period_sub = sub[sub["period"] == period].nlargest(top_n_cat, "Total Tickets")
            for r, (_, row) in enumerate(period_sub.iterrows(), 1):
                rows.append({
                    "Batch Name": batch,
                    "period": period,
                    "rank": r,
                    "Category": row["Category"],
                    "Total Tickets": int(row["Total Tickets"]),
                })
    return pd.DataFrame(rows)

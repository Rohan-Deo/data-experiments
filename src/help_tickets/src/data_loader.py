"""
Load and clean ticket CSV data for pre and post help-ticket periods.
Handles category normalization and column alignment between the two periods.
"""

import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

RAW_PRE_FILE = "tickets_raw_26jan_14feb.csv"
RAW_POST_FILE = "tickets_raw_15_feb_onwards.csv"
CAT_PRE_FILE = "ticket_categories_26jan_14feb.csv"
CAT_POST_FILE = "ticket_categories_15_feb_onwards.csv"
TICKET_PRE_FILE = "st_tickets_26jan_14feb.csv"
TICKET_POST_FILE = "st_tickets_15_feb_onwards.csv"

CATEGORY_NORMALIZATION_MAP = {
    "studentkit": "student-kit",
    "campusconnect": "campus-connect",
    "referrals": "referral",
    "nbfc-isa-glide": "isa-emi-nbfc-glide-related",
    "missed-evaluation-submission": "missed-evaluation",
    "curriculum-query": "program-related-query",
}

SHARED_RAW_COLUMNS = [
    "Batch Name",
    "Total Tickets",
    "Total Help Tickets",
    "Help - Open",
    "Help - Resolved",
    "Help - Reopened",
    "Help - Closed",
    "Total Support Tickets",
    "Support - Open",
    "Support - Resolved",
    "Support - Reopened",
    "Support - Closed",
    "Number of Users in Batch",
    "Number of Active Users in Batch",
    "Unique Users - Help",
    "Unique Users - Support",
    "Unique Users - Both Help & Support",
]


def _read_csv(filename: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, filename))


def _normalize_category(cat: str) -> str:
    """Map variant category names to a single canonical form."""
    key = cat.strip().lower()
    return CATEGORY_NORMALIZATION_MAP.get(key, key)


def load_raw_tickets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (pre_df, post_df) with aligned columns and a 'period' label."""
    pre = _read_csv(RAW_PRE_FILE)
    post = _read_csv(RAW_POST_FILE)

    # Drop percentage columns from post so both DataFrames share the same schema
    for col in ["% Help Tickets", "% Support Tickets"]:
        if col in post.columns:
            post = post.drop(columns=[col])

    pre["period"] = "pre"
    post["period"] = "post"

    # Compute derived metrics
    for df in [pre, post]:
        help_pct = df["Total Help Tickets"] / df["Total Tickets"].replace(0, pd.NA) * 100
        df["Help Ticket %"] = pd.to_numeric(help_pct, errors="coerce").fillna(0).round(2)

        support_pct = df["Total Support Tickets"] / df["Total Tickets"].replace(0, pd.NA) * 100
        df["Support Ticket %"] = pd.to_numeric(support_pct, errors="coerce").fillna(0).round(2)

        tpau = df["Total Tickets"] / df["Number of Active Users in Batch"].replace(0, pd.NA)
        df["Tickets per Active User"] = pd.to_numeric(tpau, errors="coerce").fillna(0).round(4)

    return pre, post


def load_category_tickets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (pre_cat, post_cat) with normalized category names and period label."""
    pre = _read_csv(CAT_PRE_FILE)
    post = _read_csv(CAT_POST_FILE)

    for df in [pre, post]:
        df["Category"] = df["Category"].apply(_normalize_category)

    pre["period"] = "pre"
    post["period"] = "post"

    return pre, post


def load_combined_raw() -> pd.DataFrame:
    """Return a single DataFrame with both periods stacked."""
    pre, post = load_raw_tickets()
    return pd.concat([pre, post], ignore_index=True)


def load_combined_categories() -> pd.DataFrame:
    """Return a single DataFrame with category data from both periods, aggregated after normalization."""
    pre, post = load_category_tickets()
    combined = pd.concat([pre, post], ignore_index=True)

    agg_cols = {"Total Tickets": "sum", "Open": "sum", "Reopened": "sum", "Total Open + Reopened": "sum"}
    combined = (
        combined.groupby(["Batch Name", "Category", "period"], as_index=False)
        .agg(agg_cols)
    )
    return combined


def get_batch_list() -> list[str]:
    """Return sorted list of unique batch names across both periods."""
    pre, post = load_raw_tickets()
    batches = sorted(set(pre["Batch Name"].tolist() + post["Batch Name"].tolist()))
    return batches


# ---------------------------------------------------------------------------
# Ticket-level data (st_tickets files)
# ---------------------------------------------------------------------------

def _parse_ticket_df(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """Clean and enrich a single ticket-level DataFrame."""
    df = df.copy()
    df["period"] = period
    df["Ticket Type"] = df["Tags"].apply(
        lambda x: "Help" if x == "Help FAQ Ticket" else "Support"
    )
    df["Created At"] = pd.to_datetime(df["Created At"], format="mixed", dayfirst=False)
    df["Created Date"] = df["Created At"].dt.date
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")

    # Valid ratings: Help → {1, 5}, Support → {1, 2, 3, 4, 5}
    valid_help = df["Ticket Type"] == "Help"
    valid_support = df["Ticket Type"] == "Support"
    df["Valid Rating"] = False
    df.loc[valid_help & df["Rating"].isin([1, 5]), "Valid Rating"] = True
    df.loc[valid_support & df["Rating"].isin([1, 2, 3, 4, 5]), "Valid Rating"] = True

    df["Ticket Closure Tat"] = pd.to_numeric(df["Ticket Closure Tat"], errors="coerce")
    df["Status"] = df["Status"].str.strip().str.lower()
    df["Ec Name"] = df["Ec Name"].str.strip()
    return df


def load_ticket_level() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (pre, post) ticket-level DataFrames, cleaned and enriched."""
    pre = _parse_ticket_df(_read_csv(TICKET_PRE_FILE), "pre")
    post = _parse_ticket_df(_read_csv(TICKET_POST_FILE), "post")
    return pre, post


def load_combined_ticket_level() -> pd.DataFrame:
    pre, post = load_ticket_level()
    return pd.concat([pre, post], ignore_index=True)


def get_ticket_batch_list() -> list[str]:
    """Batch names appearing in ticket-level data."""
    pre, post = load_ticket_level()
    return sorted(
        set(pre["Batch Name"].dropna().tolist() + post["Batch Name"].dropna().tolist())
    )

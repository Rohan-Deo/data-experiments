"""
Collect analysis metrics into a single structure for use in narrative summary generation.
Returns dicts and tables that can be serialized for an LLM prompt.
Includes optional ticket-level ratings/CSAT when st_tickets files are present.
"""

import pandas as pd

from .data_loader import (
    load_raw_tickets,
    load_combined_categories,
    load_ticket_level,
    ticket_level_files_exist,
)
from .analysis import (
    compute_kpis,
    overall_comparison,
    category_comparison,
    support_ticket_comparison,
    batch_comparison,
    resolution_metrics,
    top_batches,
    top_categories_by_batch,
)
from . import ticket_analysis


def gather_all_metrics():
    """
    Load data, run all analyses, and return a dict of metrics and string summaries
    suitable for inclusion in a stakeholder summary prompt.
    """
    pre, post = load_raw_tickets()
    cat = load_combined_categories()

    kpis = compute_kpis(pre, post)
    overall = overall_comparison(pre, post)
    resolution = resolution_metrics(pre, post)
    cat_comp = category_comparison(cat)
    support_comp = support_ticket_comparison(pre, post)
    batch_comp = batch_comparison(pre, post)
    top_pre = top_batches(pre, 10)
    top_post = top_batches(post, 10)

    # Batches to show category breakdown (top by combined pre+post volume)
    pre_totals = pre.set_index("Batch Name")["Total Tickets"]
    post_totals = post.set_index("Batch Name")["Total Tickets"]
    combined = pre_totals.add(post_totals, fill_value=0).sort_values(ascending=False)
    top_batch_names = combined.head(14).index.tolist()
    category_by_batch_df = top_categories_by_batch(cat, top_batch_names, top_n_cat=4)

    # Top N for narrative (avoid huge tables)
    n_cat = 12
    n_support_batches = 12
    n_batch_comp = 15

    def df_to_str(df: pd.DataFrame, max_rows: int | None = None) -> str:
        sub = df.head(max_rows) if max_rows else df
        return sub.to_string(index=False)

    out = {
        "kpis": kpis,
        "overall_table": overall.to_string(),
        "resolution_table": resolution.to_string(index=False),
        "resolution_df": resolution,
        "category_table": df_to_str(cat_comp, n_cat),
        "category_full": cat_comp,
        "support_by_batch_table": df_to_str(
            support_comp[support_comp["Support Pre"] + support_comp["Support Post"] > 0],
            n_support_batches,
        ),
        "support_total_change": int(support_comp["Support Post"].sum() - support_comp["Support Pre"].sum()),
        "batch_comparison_table": df_to_str(batch_comp, n_batch_comp),
        "top_batches_pre": top_pre.to_string(index=False),
        "top_batches_post": top_post.to_string(index=False),
        "pre_batches_count": int((pre["Total Tickets"] > 0).sum()),
        "post_batches_count": int((post["Total Tickets"] > 0).sum()),
        "has_ratings": False,
        "category_by_batch_table": category_by_batch_df.to_string(index=False),
    }

    # Ticket-level ratings/CSAT when st_tickets files exist
    if ticket_level_files_exist():
        try:
            pre_tl, post_tl = load_ticket_level()
            combined_tickets = pd.concat([pre_tl, post_tl], ignore_index=True)
            rating_summary_df = ticket_analysis.rating_summary(combined_tickets)
            csat_df = ticket_analysis.csat_score(combined_tickets)
            rating_dist_df = ticket_analysis.rating_distribution(combined_tickets)
            out["has_ratings"] = True
            out["ratings_summary_table"] = rating_summary_df.to_string(index=False)
            out["csat_table"] = csat_df.to_string(index=False)
            out["rating_distribution_table"] = rating_dist_df.to_string(index=False)
        except Exception as e:
            import warnings
            warnings.warn(f"Ticket-level ratings not loaded: {e}", UserWarning)
            out["has_ratings"] = False

    return out


def metrics_to_prompt_text(data: dict) -> str:
    """Turn gathered metrics into a single text block for the LLM prompt."""
    k = data["kpis"]
    sections = [
        "## Overall KPIs",
        f"Pre period (26 Jan – 14 Feb): Total tickets = {k['pre_total']:,}; Help = {k['pre_help']:,} ({k['pre_help_pct']}% of total); Support = {k['pre_support']:,}. "
        f"Unique Help users = {k['pre_unique_help_users']:,}; Unique Support users = {k['pre_unique_support_users']:,}. "
        f"Active batches = {k['pre_active_batches']}.",
        f"Post period (15 Feb – 5 Mar): Total tickets = {k['post_total']:,}; Help = {k['post_help']:,} ({k['post_help_pct']}% of total); Support = {k['post_support']:,}. "
        f"Unique Help users = {k['post_unique_help_users']:,}; Unique Support users = {k['post_unique_support_users']:,}. "
        f"Active batches = {k['post_active_batches']}.",
        f"Change: Total tickets {k['total_change_pct']:+.1f}%; Support tickets {k['support_change_pct']:+.1f}%; Help tickets {k['help_change_pct']:+.1f}%.",
        "",
        "## Resolution rates (Help vs Support, Pre vs Post)",
        data["resolution_table"],
        "",
        "## Overall comparison (all aggregated metrics)",
        data["overall_table"],
        "",
        "## Top categories by ticket volume (Pre vs Post, with change)",
        data["category_table"],
        "",
        "## Support ticket change by batch (sample of batches with activity)",
        f"Total support ticket change across all batches: {data['support_total_change']:+,}.",
        data["support_by_batch_table"],
        "",
        "## Batch-level comparison (sample: total tickets, help/support split, change)",
        data["batch_comparison_table"],
        "",
        "## Top 10 batches by volume – Pre",
        data["top_batches_pre"],
        "",
        "## Top 10 batches by volume – Post",
        data["top_batches_post"],
        "",
        "## Category mix by batch (top 4 categories per batch, pre and post)",
        "Use this to describe which batches had which category shifts.",
        data["category_by_batch_table"],
    ]

    if data.get("has_ratings") and data.get("ratings_summary_table"):
        sections.extend([
            "",
            "## Ratings and CSAT (ticket-level; valid ratings only)",
            "Definitions: Help tickets use a 1–5 scale but only 1 and 5 are valid; Support uses 1–5 (all valid). "
            "CSAT for Help = % of rated tickets with rating 5; CSAT for Support = % of rated tickets with rating >= 4.",
            "",
            "### Rating summary (by period and ticket type: total tickets, rated count, % rated, avg rating, % rating=5, % rating=1)",
            data["ratings_summary_table"],
            "",
            "### CSAT (satisfied count and CSAT %)",
            data["csat_table"],
            "",
            "### Rating distribution (count per rating value, by period and type)",
            data["rating_distribution_table"],
        ])
    else:
        sections.append(
            "\n[Note: Ticket-level ratings data (st_tickets CSVs) was not provided or failed to load. "
            "Do not add a Ratings or CSAT section; if you mention ratings at all, state that rating data was not available for this run.]"
        )

    return "\n".join(sections)

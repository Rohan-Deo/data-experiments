# Help Tickets – High-Level Stakeholder Summary

This document summarizes the ticket data used in the Help Tickets analysis and dashboard. All numbers and trends described here can be **verified in the interactive dashboard** by running:

```bash
streamlit run dashboard.py
```
(from the `help_tickets` directory)

---

## 1. Data Sources and Time Periods

### Data files (in `help_tickets/data/`)

| File | Content | Period |
|------|--------|--------|
| `tickets_raw_26jan_14feb.csv` | Aggregated ticket counts per batch (Help + Support, status breakdowns, user counts) | **Pre** |
| `tickets_raw_15_feb_onwards.csv` | Same structure | **Post** |
| `ticket_categories_26jan_14feb.csv` | Tickets per category per batch | **Pre** |
| `ticket_categories_15_feb_onwards.csv` | Same structure | **Post** |

### Period definitions

- **Pre:** 26 Jan – 14 Feb (before Help tickets were introduced).
- **Post:** 15 Feb – 5 Mar (after Help tickets were introduced; rollout around 13–14 Feb).

**Ticket types**

- **Help tickets:** FAQ-style, 1–5 rating scale (only 1 and 5 are valid).
- **Support tickets:** Full support; 1–5 rating scale (all values valid).

---

## 2. Overall-Level: Pre vs Post

### What the dashboard shows

- **Total tickets** – Pre total vs Post total, with **change %**.
- **Help vs Support split** – Counts and **% of total** in each period (Help % increases in Post once the feature is live).
- **Unique users** – Unique users who raised Help tickets vs Support tickets in each period.
- **Resolution rates** – % of Help and Support tickets that are Resolved (vs Open / Reopened / Closed), for Pre and Post.

### How to verify

- **Dashboard → Key Metrics (top row):** Total Tickets (Pre/Post), Help Tickets (Post), Support Tickets (Post), and the four user metrics.
- **Dashboard → Overall tab:**  
  - “Overall Ticket Volume” and “Help vs Support Ticket Split” charts.  
  - “Help vs Support Ticket Percentage” and “Unique Users: Help vs Support” charts.  
  - “Resolution Rates” table and “Resolution Rates: Help vs Support” chart.  
  - “Overall Comparison Table” (all aggregated metrics Pre vs Post with Change and Change %).

### What to read from it

- **Total volume:** Did overall ticket count go up or down from Pre to Post, and by how much?
- **Mix:** What % of tickets are Help vs Support in Post? (Help % is a direct outcome of the new flow.)
- **Resolution:** How do Help and Support resolution rates compare between Pre and Post?
- **Reach:** How many unique users used Help vs Support in each period?

---

## 3. Batch-Level: Pre vs Post

### What the dashboard shows

- **Per-batch comparison** – For each batch: Total Tickets, Total Help Tickets, Total Support Tickets, Help %, Support %, and Tickets per Active User in **Pre** and **Post**, plus **Ticket Change** and **Ticket Change %**.
- **Support deep-dive** – Per-batch **Support** ticket counts in Pre vs Post, with **Change** and **Change %** (so you can see which batches had the largest support change).
- **Top batches** – Top 10 batches by total tickets in Pre and in Post (stacked Help vs Support).
- **Scatter** – Each point = one batch; X = Total Tickets Pre, Y = Total Tickets Post (points above the diagonal = more tickets in Post).

### How to verify

- **Dashboard → Batch Comparison tab:**  
  - “Batch-Level Comparison” scatter.  
  - “Top 10 Batches – Pre” and “Top 10 Batches – Post” charts.  
  - “Full Batch Comparison Table” (all batches, all comparison columns).
- **Dashboard → Support Deep-Dive tab:**  
  - “Support Tickets: Pre vs Post” metrics and “Support Ticket Change by Batch” table.  
  - “Support Ticket Categories” tables for Pre and Post.
- **Sidebar:** Use “Filter by Batch Name” to restrict to specific batches; all KPIs and tabs then show **batch-level** (filtered) results, so you can verify batch-level statements for a subset.

### What to read from it

- **Which batches** drove the most tickets in Pre vs Post.
- **Where support went down** (or up) after Help was introduced (Support Change by Batch).
- **Consistency** – Do some batches show very different Pre vs Post behaviour (e.g. big changes in total or in Help %)?

---

## 4. Category-Level View

### What the dashboard shows

- **Category comparison table** – Each category’s total tickets in **Pre** and **Post**, with **Change** and **Change %**.
- **Charts** – Top categories Pre vs Post (grouped bar); category ticket **change** (Post − Pre) as a horizontal bar; treemaps of category distribution for Pre and Post.

### How to verify

- **Dashboard → Categories tab:**  
  - “Category Ticket Comparison” (chart + full category table).  
  - “Category Distribution Treemaps” for Pre and Post.  
  - “Full Category Table” (all categories with Pre, Post, Change, Change %).

### What to read from it

- **Which categories** have the most tickets in each period.
- **Which categories** grew or shrank the most after Help was introduced (change and change %).
- **Shift in mix** – e.g. more “FAQ-style” categories in Post if users route via Help.

---

## 5. Ratings-Related Information

### Definitions (used in ticket-level analysis)

- **Help tickets:** Valid ratings are **1** (negative) and **5** (positive).  
  - **CSAT (Help):** % of rated Help tickets with rating = 5.
- **Support tickets:** Valid ratings are **1–5**.  
  - **CSAT (Support):** % of rated Support tickets with rating ≥ 4.

Other metrics in the analysis code (when ticket-level data is available): average rating, % rated, % rating = 5, % rating = 1, rating distribution by period and type, and per-EC rating summaries.

### Where this appears

- **Aggregate CSVs** in `data/` do **not** contain rating columns; ratings exist only in **ticket-level** data (e.g. `st_tickets_*.csv` when present).
- The **dashboard** currently uses only the aggregate raw and category CSVs, so it does **not** show ratings. All **overall** and **batch-level** metrics above are verifiable without ratings.
- The **analysis code** (`ticket_analysis.py`, `ticket_charts.py`) already defines rating distribution, rating summary, and CSAT for ticket-level data. When ticket-level files are loaded and wired into the dashboard (or a separate view), the same definitions above will be used and can be verified there.

### For stakeholders

- **Pre vs Post:** In Post, Help tickets use a 1/5 scale; Support keeps 1–5. CSAT is defined separately for Help (% = 5) and Support (% ≥ 4).
- **Batch-level:** When ticket-level data is available, ratings and CSAT can be broken down by batch in the same way as other batch-level metrics.

---

## 6. Quick Verification Checklist

| Claim | Where to verify |
|-------|------------------|
| Overall ticket volume change (Pre vs Post) | Key Metrics + Overall tab → “Overall Ticket Volume” + “Overall Comparison Table” |
| Help vs Support split and % | Key Metrics + Overall tab → “Help vs Support” charts and table |
| Resolution rates (Help vs Support, Pre vs Post) | Overall tab → “Resolution Rates” table and chart |
| Unique users (Help vs Support, Pre vs Post) | Key Metrics + Overall tab → “Unique Users” chart |
| Batch-level ticket and support change | Batch Comparison tab (table + scatter); Support Deep-Dive tab (Support by batch) |
| Top batches Pre vs Post | Batch Comparison tab → “Top 10 Batches” charts |
| Category mix and category-level change | Categories tab → comparison chart, table, treemaps |
| Filter to specific batches | Sidebar → “Filter by Batch Name”; all tabs then show filtered overall/batch-level view |

---

## 7. Summary

- **Data:** Pre (26 Jan–14 Feb) and Post (15 Feb–5 Mar) aggregate ticket and category CSVs; ticket-level (and thus ratings) use separate files when available.
- **Overall:** The dashboard gives Pre vs Post totals, Help vs Support mix, resolution rates, and unique users; all verifiable in the **Overall** tab and top **Key Metrics**.
- **Batch-level:** Per-batch totals, Help/Support split, support change, and top batches are in **Batch Comparison** and **Support Deep-Dive**; use the **batch filter** to check specific batches.
- **Categories:** **Categories** tab provides category-level Pre vs Post counts, change, and distribution (treemaps).
- **Ratings:** Defined for Help (1/5, CSAT = % rated = 5) and Support (1–5, CSAT = % rated ≥ 4); implemented in ticket-level analysis and available for reporting once ticket-level data is connected to the dashboard.

Using the dashboard filters and tabs above, every high-level statement in this summary can be checked and reproduced from the same CSVs that feed the analysis.

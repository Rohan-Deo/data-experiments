"""
Generate the stakeholder summary from live data using the OpenAI API.
Run from the repo root: python -m src.help_tickets.generate_summary
Or from help_tickets: python generate_summary.py (with PYTHONPATH or run from data_experiments).
"""
import os
import sys
from pathlib import Path

# Project root (data_experiments) for .env
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Help tickets dir so "from src.xxx" resolves to help_tickets/src/xxx
HELP_TICKETS_DIR = Path(__file__).resolve().parent
if str(HELP_TICKETS_DIR) not in sys.path:
    sys.path.insert(0, str(HELP_TICKETS_DIR))

# Load .env from repo root
def _load_dotenv():
    try:
        from dotenv import load_dotenv
        env_path = REPO_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


def build_prompt(metrics_text: str) -> list[dict]:
    """Build the OpenAI chat messages for stakeholder summary generation."""
    system = (
        "You are writing a concise, high-level stakeholder summary for leadership. "
        "Use only the metric values and tables provided. Do not write a manual or how-to; "
        "write an actual summarization with real numbers and brief interpretation. "
        "Do NOT spend space stating that Help adoption increased in the post period (that is obvious). "
        "Instead, focus on: "
        "(1) How categories changed pre vs post—which categories grew or shrank overall and, importantly, "
        "in which batches these shifts were strongest (use the 'Category mix by batch' table). "
        "(2) Which specific batches had the largest ticket volume increases vs decreases (use batch-level comparison and support-by-batch tables). "
        "(3) Resolution and support-ticket reduction by batch, and any other patterns in the data. "
        "If a Ratings and CSAT section is provided in the metrics, include a dedicated subsection summarizing "
        "rating coverage (% rated), average ratings, CSAT by period and ticket type, and pre vs post interpretation. "
        "If the metrics include a note that ticket-level ratings data was not provided, do not add a Ratings section; "
        "you may add one short sentence that rating data was not available for this run. "
        "Use clear headings and short paragraphs. Output valid markdown."
    )
    user = (
        "Below are the computed metrics for the Help Tickets pre vs post analysis. "
        "Pre = 26 Jan – 14 Feb (before Help tickets); Post = 15 Feb – 5 Mar (after). "
        "Write a single stakeholder summary that emphasizes: category changes by batch, which batches had ticket "
        "increases vs decreases, resolution and support patterns, and (when provided) ratings/CSAT. "
        "Use actual numbers throughout.\n\n"
        "---\n\n"
        + metrics_text
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def generate_summary_with_openai(metrics_text: str) -> str:
    """Call OpenAI API and return the assistant message content."""
    _load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY not set. Add it to .env in the project root.")

    model = os.getenv("OPENAI_MODEL", "gpt-5.1")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        messages = build_prompt(metrics_text)
        resp = client.chat.completions.create(model=model, messages=messages)
        return resp.choices[0].message.content or ""
    except Exception as e:
        err = str(e).lower()
        if "model" in err or "gpt-4.1" in err or "gpt-5.1" in err or "not found" in err:
            # Fallback if gpt-4.1 is not available
            model = "gpt-4.1"
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            messages = build_prompt(metrics_text)
            resp = client.chat.completions.create(model=model, messages=messages)
            return resp.choices[0].message.content or ""
        raise


def main():
    from src.summary_metrics import gather_all_metrics, metrics_to_prompt_text

    # Run from help_tickets so data_loader finds data/
    help_tickets_dir = Path(__file__).resolve().parent
    os.chdir(help_tickets_dir)

    data = gather_all_metrics()
    metrics_text = metrics_to_prompt_text(data)
    summary = generate_summary_with_openai(metrics_text)

    out_path = help_tickets_dir / "STAKEHOLDER_SUMMARY.md"
    out_path.write_text(summary, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

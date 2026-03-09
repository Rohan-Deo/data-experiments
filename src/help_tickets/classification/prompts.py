"""
Build prompts for question-bank generation from help tickets.
"""
from typing import Iterable

import pandas as pd


def _format_tickets_chunk(chunk: pd.DataFrame) -> str:
    """Format a chunk of tickets as numbered lines for the prompt."""
    lines = []
    for i, row in chunk.iterrows():
        title = (row["Title"] or "").strip()
        message = (row["Message"] or "").strip()
        category = (row["Category"] or "").strip()
        # Truncate very long messages to avoid blowing context
        if len(message) > 1200:
            message = message[:1200] + "... [truncated]"
        lines.append(f"[Category: {category}]\nTitle: {title}\nMessage: {message}")
    return "\n\n---\n\n".join(lines)


def build_question_bank_prompt(
    tickets_chunk: pd.DataFrame,
    chunk_index: int,
    total_chunks: int,
    max_questions: int,
) -> str:
    """
    Build the user prompt for the LLM to generate a question bank from tickets.

    Instructs the LLM to identify recurring/similar questions across the
    tickets and output canonical questions mapped to category.

    Args:
        tickets_chunk: DataFrame with Title, Message, Category.
        chunk_index: 0-based index of this chunk (for context in prompt).
        total_chunks: Total number of chunks.
        max_questions: Maximum number of questions to emit for this chunk.

    Returns:
        Full user prompt string.
    """
    tickets_text = _format_tickets_chunk(tickets_chunk)
    chunk_info = f"This is chunk {chunk_index + 1} of {total_chunks}." if total_chunks > 1 else ""

    return f"""You are analyzing student help tickets to build a QUESTION BANK of reusable FAQ-style questions. Students often describe hyper-specific situations (e.g. "my team NAPZS", "immersion from Feb 20 to Mar 7", "exam at 4:30 AM London time"). Your job is to extract the GENERIC, recurring question that applies to many similar tickets, not to reproduce the specific scenario.

STYLE (match FAQ reference):
- GENERAL and REUSABLE: Strip all personal/situational specifics. No names, dates, team names, batch IDs, exam center names, or specific assignment IDs.
- SHORT and DIRECT: One main idea per question. Avoid run-on questions with multiple sub-questions.
- FAQ-like phrasing: "When will I...?", "How can I...?", "Where can I find...?", "What should I do?", "Could you please...?", "I am unable to... What should I do?"
- A ticket like "I selected 28th but my team presents on 22nd, how do I change?" → "How can I change my presentation date to match my team's slot?"
- A ticket like "I'm on immersion Feb 20–Mar 7, can't take the test" → "I missed an evaluation due to immersion. What can I do?"
- A ticket about mobile phone storage at exam center → "Can I carry my mobile phone during the exam and is there secure storage?"

{chunk_info}

INSTRUCTIONS:
1. Read every ticket's Title and Message (and its Category).
2. Identify the underlying, generic question—what would ANY student in this situation ask?
3. Group tickets with the same underlying question into one canonical FAQ question.
4. Write questions that are GENERAL enough to appear in an FAQ: reusable across many students, no specifics.
5. For each question, use the exact Category from the tickets (e.g. "product-support", "evaluation", "attendance-query").
6. Add a SUB_CATEGORY: a finer-grained topic within the category (e.g. evaluation → "missed-evaluation", "result", "proctoring"; product-support → "lms-learning-management-system", "assignment", "lecture"; student-kit → "student-kit"). Use kebab-case. Sub-category can equal category when there is no natural subdivision.
7. Focus on recurring themes only. DROP one-off or highly niche cases unless they clearly represent a broader FAQ-worthy theme.
8. This is a REDUCTION task, not an extraction task. Do NOT create one question per ticket.
9. Output at most {max_questions} questions for this chunk. Fewer is better if that captures the batch well.
10. Prefer broader questions that absorb nearby variants rather than splitting into tiny distinctions.
11. Output ONLY a valid JSON array of objects with keys "question", "category", and "sub_category". No markdown, no explanation.

Example format (general FAQ style, with sub_category like the reference):
[
  {{"question": "How can I change my presentation date to match my team's slot?", "category": "product-support", "sub_category": "product-support"}},
  {{"question": "When will I get my student kit?", "category": "student-kit", "sub_category": "student-kit"}},
  {{"question": "I missed an evaluation. What can I do?", "category": "evaluation", "sub_category": "missed-evaluation"}},
  {{"question": "My attendance shows absent even though I attended. What should I do?", "category": "attendance-query", "sub_category": "attendance-query"}}
]

TICKETS TO ANALYZE:

{tickets_text}

OUTPUT: Return only the JSON array of {{"question", "category", "sub_category"}} objects, nothing else."""


def build_consolidation_prompt(
    candidate_rows: Iterable[dict],
    min_questions: int,
    max_questions: int,
) -> str:
    """
    Build prompt to consolidate chunk-level candidates into the final bank.

    Args:
        candidate_rows: Iterable of dicts with question/category/sub_category/support_count.
        min_questions: Preferred lower target bound.
        max_questions: Hard upper cap for final output.

    Returns:
        Full consolidation prompt.
    """
    formatted_candidates = []
    for row in candidate_rows:
        support = row.get("support_count", 1)
        formatted_candidates.append(
            "\n".join(
                [
                    f"Support Count: {support}",
                    f"Category: {row['category']}",
                    f"Sub Category: {row['sub_category']}",
                    f"Question: {row['question']}",
                ]
            )
        )

    candidates_text = "\n\n---\n\n".join(formatted_candidates)

    return f"""You are consolidating candidate FAQ questions generated from many chunks of student help tickets. The current candidate list is too granular. Your job is to MERGE overlapping candidates and produce a compact, representative final question bank.

FINAL BANK GOAL:
- Produce a final bank with broad coverage across categories and sub-categories.
- Prefer representative, reusable questions over narrow variants.
- Use support counts to prefer themes that recur more often.
- HARD CAP: output no more than {max_questions} questions.
- TARGET RANGE: aim for roughly {min_questions}-{max_questions} questions only if there are enough genuinely distinct themes.

RULES:
1. Merge paraphrases and near-duplicates into one best canonical question.
2. Merge overly narrow variants into a broader FAQ question when they belong to the same underlying issue.
3. Keep category coverage broad: do not let one category dominate with dozens of tiny variants.
4. Keep sub-category coverage sensible: retain important sub-topics, but collapse redundant sub-category variants when needed.
5. Prefer higher-support candidates when choosing between similar questions.
6. Drop highly niche, person-specific, or low-signal questions unless they clearly represent a recurring theme.
7. Keep the same output schema: "question", "category", "sub_category".
8. Output ONLY a valid JSON array. No markdown, no explanation.

GOOD CONSOLIDATION EXAMPLES:
- "I have not received my admit card yet. When will I get it?" + "Where can I find my exam details?" -> "I have not received my admit card or exam details yet. When and where will I get them?"
- "Attendance not marked for live class" + "Attendance shows absent after watching session" -> "My attendance shows absent even though I attended or watched the session. What should I do?"
- "Cannot access lecture recording" + "Recorded class not playing" -> "I am unable to access lecture recordings. What should I do?"

CANDIDATE QUESTIONS:

{candidates_text}

OUTPUT: Return only the JSON array of {{"question", "category", "sub_category"}} objects, nothing else."""

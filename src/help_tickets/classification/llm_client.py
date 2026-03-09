"""
OpenAI client for question-bank generation (model: gpt-5.1 only).
"""
import json
import os
from typing import List

from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

QUESTION_BANK_MODEL = "gpt-5.1"
DEFAULT_TEMPERATURE = 0.0


def get_client() -> OpenAI:
    """Return OpenAI client using OPENAI_API_KEY from environment."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    return OpenAI(api_key=api_key)


def _parse_question_bank_response(content: str) -> List[dict]:
    """
    Parse LLM response into list of {"question": str, "category": str, "sub_category": str}.
    Handles markdown code blocks and trailing text.
    """
    text = content.strip()
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        text = text[start:end] if end != -1 else text[start:]
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        text = text[start:end] if end != -1 else text[start:]
    text = text.strip()
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON array")
    out = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        q = item.get("question") or item.get("Question")
        c = item.get("category") or item.get("Category")
        if q and c:
            sub = item.get("sub_category") or item.get("Sub Category") or c
            out.append(
                {
                    "question": str(q).strip(),
                    "category": str(c).strip(),
                    "sub_category": str(sub).strip(),
                }
            )
    return out


def get_question_bank_from_prompt(
    user_prompt: str,
    model: str = QUESTION_BANK_MODEL,
    # max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
) -> List[dict]:
    """
    Call OpenAI (gpt-5.1) with the given prompt and return parsed question bank.

    Args:
        user_prompt: Full user message for question-bank generation.
        model: Model ID (default gpt-5.1).
        max_tokens: Max tokens for completion.
        temperature: Sampling temperature.

    Returns:
        List of {"question": str, "category": str, "sub_category": str}.
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert at analyzing student support tickets and distilling them into a clear question bank. You always respond with valid JSON only, no markdown or extra text unless it is the JSON array.",
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        # max_tokens=max_tokens,
    )
    content = response.choices[0].message.content or ""
    return _parse_question_bank_response(content)

from __future__ import annotations

import os
from typing import Optional


class ExplanationGenerator:
    """Optional LLM-backed explanations with a deterministic local fallback."""

    def __init__(self) -> None:
        self._use_openai = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("USE_OPENAI_EXPLANATIONS") == "1"

    def render(self, row: dict, student: dict) -> str:
        if self._use_openai:
            llm_result = self._render_with_openai(row, student)
            if llm_result:
                return llm_result
        return self._render_template(row, student)

    def _render_with_openai(self, row: dict, student: dict) -> Optional[str]:
        try:
            from openai import OpenAI
        except Exception:
            return None

        try:
            client = OpenAI()
            prompt = (
                "Write one sentence for a middle-school book recommendation. "
                "Do not mention personal data or scores. "
                f"Student grade: {student['grade']}. "
                f"Candidate title: {row['title']}. "
                f"Genre: {row['genre']}. "
                f"Reason signal: {row['strategy']}. "
                f"Anchor title: {row['anchor_title']}."
            )
            response = client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                input=prompt,
                max_output_tokens=60,
            )
            text = getattr(response, "output_text", "")
            return text.strip() or None
        except Exception:
            return None

    def _render_template(self, row: dict, student: dict) -> str:
        if row["strategy"] == "collaborative":
            return (
                f"Because you checked out {row['anchor_title']} and readers with a similar pattern also borrowed {row['title']}, "
                f"this is a strong next pick for grade {student['grade']}."
            )
        if row["strategy"] == "cold_start":
            return (
                f"You are early in your reading history, so this pick leans on {row['genre'].lower()} themes and what is landing well with readers in grade {student['grade']}."
            )
        return (
            f"Because {row['title']} overlaps with the themes in {row['anchor_title']} and still fits your grade band, it is a useful adjacent recommendation."
        )
"""AI answer evaluation with rubric-based scoring and model answers."""

import json
import logging
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Heuristic keyword signals used when the LLM is unavailable.
STRONG_SIGNALS = {
    "because",
    "therefore",
    "trade-off",
    "tradeoff",
    "however",
    "specifically",
    "for example",
    "e.g.",
    "first",
    "then",
    "finally",
    "result",
    "impact",
    "improved",
    "reduced",
    "increased",
}
WEAK_SIGNALS = {"i don't know", "no idea", "not sure", "maybe", "i guess"}
STAR_SIGNALS = {
    "situation": ["in my previous", "at my last job", "when i was", "there was a time"],
    "task": ["i was responsible", "my goal", "i needed to", "i had to"],
    "action": ["i decided", "i implemented", "i built", "i led", "i created", "i did"],
    "result": ["as a result", "this led to", "we achieved", "improved", "reduced", "increased"],
}


class EvaluationServiceError(Exception):
    """Custom exception for evaluation service errors."""


class EvaluationService:
    """Evaluates candidate answers with rubric scoring and model answers."""

    def __init__(self, gemini_service=None):
        self.gemini_service = gemini_service

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        question_type: str = "technical",
    ) -> dict[str, Any]:
        """Evaluate a candidate answer.

        Tries the LLM first for a structured rubric score; falls back to a
        deterministic heuristic so the platform degrades gracefully when the
        AI service is unavailable.
        """
        if self.gemini_service is not None:
            try:
                result = self._evaluate_with_llm(question, answer, question_type)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"LLM evaluation failed, using heuristic: {e}")

        return self._evaluate_heuristic(question, answer, question_type)

    def generate_model_answer(
        self,
        question: str,
        question_type: str = "technical",
    ) -> Optional[str]:
        """Generate a model answer for a question via the LLM."""
        if self.gemini_service is None:
            return None
        try:
            prompt = (
                f"Provide a concise, high-quality model answer (150-250 words) "
                f"for this {question_type} interview question:\n\n{question}\n\n"
                "Answer directly with no preamble."
            )
            response = self.gemini_service.generate_content(prompt)
            return response.strip() if response else None
        except Exception as e:
            logger.warning(f"Model answer generation failed: {e}")
            return None

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------
    def _evaluate_with_llm(
        self,
        question: str,
        answer: str,
        question_type: str,
    ) -> Optional[dict[str, Any]]:
        star_note = (
            "(For behavioral questions, completeness uses the STAR " "framework: Situation, Task, Action, Result.)"
            if question_type == "behavioral"
            else ""
        )
        prompt = f"""You are an expert interviewer evaluating a candidate's answer.

Question ({question_type}): {question}

Candidate's answer: {answer}

Evaluate on three dimensions, each scored 0-10:
- technical: correctness and depth of technical content
- communication: clarity, structure, and conciseness
- completeness: how completely the answer addresses the question
{star_note}

Return ONLY a JSON object with this structure and no other text:
{{
  "technical": <0-10>,
  "communication": <0-10>,
  "completeness": <0-10>,
  "overall": <0-10>,
  "strengths": ["..."],
  "gaps": ["..."],
  "tips": ["..."],
  "next_action": "one of: probe_deeper, follow_up, move_on, redirect"
}}
"""
        response = self.gemini_service.generate_content(prompt)
        if not response:
            return None
        return self._parse_llm_evaluation(response)

    @staticmethod
    def _parse_llm_evaluation(text: str) -> Optional[dict[str, Any]]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end <= start:
            return None
        try:
            data = json.loads(cleaned[start:end])
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        # Normalize and clamp scores.
        for key in ("technical", "communication", "completeness", "overall"):
            try:
                data[key] = max(0.0, min(10.0, float(data.get(key, 0))))
            except (TypeError, ValueError):
                data[key] = 0.0
        data.setdefault("strengths", [])
        data.setdefault("gaps", [])
        data.setdefault("tips", [])
        data.setdefault("next_action", "move_on")
        return data

    # ------------------------------------------------------------------
    # Heuristic fallback
    # ------------------------------------------------------------------
    def _evaluate_heuristic(
        self,
        question: str,
        answer: str,
        question_type: str,
    ) -> dict[str, Any]:
        lower = answer.lower()
        words = answer.split()
        word_count = len(words)

        # Communication: length and structure.
        communication = min(10.0, 2.0 + word_count / 12.0)
        if word_count < 10:
            communication = min(communication, 3.0)

        # Technical: presence of strong signals vs weak signals.
        strong_hits = sum(1 for s in STRONG_SIGNALS if s in lower)
        weak_hits = sum(1 for s in WEAK_SIGNALS if s in lower)
        technical = max(0.0, min(10.0, 3.0 + strong_hits * 1.5 - weak_hits * 3.0))

        # Completeness: STAR for behavioral, coverage for technical.
        if question_type == "behavioral":
            star_hits = sum(1 for signals in STAR_SIGNALS.values() if any(s in lower for s in signals))
            completeness = min(10.0, 2.0 + star_hits * 2.0)
        else:
            completeness = max(0.0, min(10.0, 2.0 + word_count / 15.0 + strong_hits))

        overall = round((technical + communication + completeness) / 3.0, 1)

        strengths = []
        gaps = []
        if word_count >= 40:
            strengths.append("Provided a detailed, thorough answer")
        elif word_count < 15:
            gaps.append("Answer was too brief; add specifics and examples")
        if weak_hits:
            gaps.append("Avoid uncertain phrasing like 'I don't know' without a follow-up plan")
        if question_type == "behavioral" and star_hits < 2:
            gaps.append("Use the STAR structure: Situation, Task, Action, Result")

        next_action = "probe_deeper" if overall < 5 else ("follow_up" if overall < 7 else "move_on")

        return {
            "technical": round(technical, 1),
            "communication": round(communication, 1),
            "completeness": round(completeness, 1),
            "overall": overall,
            "strengths": strengths,
            "gaps": gaps,
            "tips": self._tips_for(question_type, overall),
            "next_action": next_action,
        }

    @staticmethod
    def _tips_for(question_type: str, score: float) -> list[str]:
        if score >= 7:
            return ["Strong answer. Practice conciseness to keep it under 2 minutes."]
        if question_type == "behavioral":
            return [
                "Structure answers with STAR: Situation, Task, Action, Result.",
                "Quantify outcomes (e.g., 'reduced latency by 40%').",
            ]
        return [
            "State the approach first, then trade-offs, then complexity.",
            "Mention edge cases and how you would test your solution.",
        ]

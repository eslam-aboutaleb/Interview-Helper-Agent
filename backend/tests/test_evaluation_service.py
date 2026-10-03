"""Tests for the evaluation service: LLM path, parsing, and heuristics."""

from services.evaluation_service import EvaluationService


class FakeGemini:
    """Returns canned responses or raises."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.prompts = []

    def generate_content(self, prompt):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.response


class TestLLMEvaluationPath:
    def test_llm_evaluation_success(self):
        gemini = FakeGemini(
            response=(
                '{"technical": 8, "communication": 7, "completeness": 9, "overall": 8, '
                '"strengths": ["clear"], "gaps": ["more detail"], "tips": ["be concise"], '
                '"next_action": "follow_up"}'
            )
        )
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(
            question="Design a rate limiter.",
            answer="I would use a token bucket with Redis.",
            question_type="technical",
        )
        assert result["technical"] == 8.0
        assert result["overall"] == 8.0
        assert result["strengths"] == ["clear"]
        assert result["next_action"] == "follow_up"

    def test_llm_evaluation_behavioral_prompt_mentions_star(self):
        gemini = FakeGemini(response='{"technical": 5, "communication": 5, "completeness": 5, "overall": 5}')
        service = EvaluationService(gemini_service=gemini)
        service.evaluate_answer(
            question="Tell me about a conflict.",
            answer="I resolved it.",
            question_type="behavioral",
        )
        assert "STAR" in gemini.prompts[0]

    def test_llm_evaluation_clamps_scores(self):
        gemini = FakeGemini(response='{"technical": 99, "communication": -5, "completeness": "abc", "overall": 50}')
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(question="Q", answer="A", question_type="technical")
        assert result["technical"] == 10.0
        assert result["communication"] == 0.0
        assert result["completeness"] == 0.0
        assert result["overall"] == 10.0

    def test_llm_evaluation_defaults_missing_fields(self):
        gemini = FakeGemini(response='{"technical": 5, "communication": 5, "completeness": 5, "overall": 5}')
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(question="Q", answer="A")
        assert result["strengths"] == []
        assert result["gaps"] == []
        assert result["tips"] == []
        assert result["next_action"] == "move_on"

    def test_llm_evaluation_markdown_fenced(self):
        gemini = FakeGemini(
            response='```json\n{"technical": 6, "communication": 6, "completeness": 6, "overall": 6}\n```'
        )
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(question="Q", answer="A")
        assert result["overall"] == 6.0

    def test_llm_empty_response_falls_back_to_heuristic(self):
        gemini = FakeGemini(response=None)
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(
            question="Q",
            answer="A decent answer with because and therefore.",
        )
        assert "overall" in result

    def test_llm_invalid_json_falls_back_to_heuristic(self):
        gemini = FakeGemini(response="not json at all")
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(question="Q", answer="A decent answer with because.")
        assert "overall" in result

    def test_llm_exception_falls_back_to_heuristic(self):
        gemini = FakeGemini(error=RuntimeError("provider down"))
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(question="Q", answer="A decent answer with because.")
        assert "overall" in result

    def test_llm_non_dict_json_falls_back(self):
        gemini = FakeGemini(response='["a", "b"]')
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(question="Q", answer="A decent answer with because.")
        assert "overall" in result

    def test_llm_no_json_braces_falls_back(self):
        gemini = FakeGemini(response="plain text without braces")
        service = EvaluationService(gemini_service=gemini)
        result = service.evaluate_answer(question="Q", answer="A decent answer with because.")
        assert "overall" in result


class TestParseLLMEvaluation:
    def test_parse_valid(self):
        result = EvaluationService._parse_llm_evaluation(
            '{"technical": 7, "communication": 6, "completeness": 8, "overall": 7}'
        )
        assert result["technical"] == 7.0

    def test_parse_surrounding_prose(self):
        result = EvaluationService._parse_llm_evaluation(
            'Here is the evaluation: {"technical": 7, "communication": 6, '
            '"completeness": 8, "overall": 7} hope it helps'
        )
        assert result["overall"] == 7.0

    def test_parse_no_braces_returns_none(self):
        assert EvaluationService._parse_llm_evaluation("no braces here") is None

    def test_parse_invalid_json_returns_none(self):
        assert EvaluationService._parse_llm_evaluation("{invalid json}") is None

    def test_parse_non_dict_returns_none(self):
        assert EvaluationService._parse_llm_evaluation("[1, 2, 3]") is None


class TestModelAnswer:
    def test_model_answer_success(self):
        gemini = FakeGemini(response="  A model answer.  ")
        service = EvaluationService(gemini_service=gemini)
        answer = service.generate_model_answer(question="Explain how HTTPS works?", question_type="technical")
        assert answer == "A model answer."

    def test_model_answer_no_llm(self):
        service = EvaluationService(gemini_service=None)
        assert service.generate_model_answer(question="Q") is None

    def test_model_answer_empty_response(self):
        gemini = FakeGemini(response="")
        service = EvaluationService(gemini_service=gemini)
        assert service.generate_model_answer(question="Q") is None

    def test_model_answer_exception(self):
        gemini = FakeGemini(error=RuntimeError("down"))
        service = EvaluationService(gemini_service=gemini)
        assert service.generate_model_answer(question="Q") is None


class TestHeuristicEvaluation:
    def setup_method(self):
        self.service = EvaluationService(gemini_service=None)

    def test_weak_answer_flags(self):
        result = self.service.evaluate_answer(
            question="What is a closure?",
            answer="I don't know, maybe no idea",
            question_type="technical",
        )
        assert result["technical"] < 3.0
        assert any("uncertain" in g for g in result["gaps"])

    def test_brief_answer_gap(self):
        result = self.service.evaluate_answer(
            question="What is a closure?", answer="It is a function.", question_type="technical"
        )
        assert any("brief" in g for g in result["gaps"])

    def test_detailed_answer_strength(self):
        result = self.service.evaluate_answer(
            question="Explain how a distributed cache works?",
            answer=" ".join(["word"] * 50),
            question_type="technical",
        )
        assert any("detailed" in s for s in result["strengths"])

    def test_behavioral_missing_star_gap(self):
        result = self.service.evaluate_answer(
            question="Tell me about a time you failed.",
            answer="It was a normal day at work with some things happening around.",
            question_type="behavioral",
        )
        assert any("STAR" in g for g in result["gaps"])

    def test_next_action_probe_deeper(self):
        result = self.service.evaluate_answer(question="Q", answer="I don't know", question_type="technical")
        assert result["next_action"] == "probe_deeper"

    def test_next_action_follow_up(self):
        result = self.service.evaluate_answer(
            question="Q",
            answer="Because the trade-off matters, I chose Redis. Specifically, for caching.",
            question_type="technical",
        )
        assert result["next_action"] == "follow_up"

    def test_next_action_move_on(self):
        result = self.service.evaluate_answer(
            question="Q",
            answer=(
                "Because the trade-off matters, I chose Redis. Specifically, for caching. "
                "For example, we reduced latency. As a result, throughput improved. "
                "Therefore, the system scaled. However, we monitored carefully. "
                "First, we measured. Then, we optimized. Finally, we deployed. "
                "The impact was significant and improved reliability."
            ),
            question_type="technical",
        )
        assert result["next_action"] == "move_on"

    def test_tips_for_strong_score(self):
        tips = EvaluationService._tips_for("technical", 8.0)
        assert "conciseness" in tips[0]

    def test_tips_for_behavioral(self):
        tips = EvaluationService._tips_for("behavioral", 5.0)
        assert any("STAR" in t for t in tips)

    def test_tips_for_technical(self):
        tips = EvaluationService._tips_for("technical", 5.0)
        assert any("trade-offs" in t for t in tips)

    def test_communication_capped_for_short_answers(self):
        result = self.service.evaluate_answer(question="Q", answer="short", question_type="technical")
        assert result["communication"] <= 3.0

    def test_scores_within_bounds(self):
        result = self.service.evaluate_answer(question="Q", answer="word " * 500, question_type="behavioral")
        for key in ("technical", "communication", "completeness", "overall"):
            assert 0 <= result[key] <= 10

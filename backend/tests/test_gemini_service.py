"""Unit tests for the question generation service."""

import pytest

from services.gemini_service import GeminiService, GeminiServiceError
from services.llm_service import LLMServiceError


class FakeLLM:
    """Scripted LLM that returns canned responses or raises."""

    def __init__(self, responses=None, error=None):
        self.responses = responses or []
        self.error = error
        self.calls = []

    def complete(self, prompt, temperature=None, max_tokens=None):
        self.calls.append({"prompt": prompt, "temperature": temperature})
        if self.error:
            raise self.error
        if not self.responses:
            return ""
        return self.responses.pop(0)


@pytest.fixture()
def service():
    return GeminiService(llm_service=FakeLLM())


class TestValidation:
    def test_empty_job_title(self, service):
        with pytest.raises(GeminiServiceError):
            service.generate_questions(job_title="   ", count=1)

    def test_non_string_job_title(self, service):
        with pytest.raises(GeminiServiceError):
            service.generate_questions(job_title=123, count=1)

    def test_count_too_low(self, service):
        with pytest.raises(GeminiServiceError):
            service.generate_questions(job_title="SWE", count=0)

    def test_count_too_high(self, service):
        with pytest.raises(GeminiServiceError):
            service.generate_questions(job_title="SWE", count=101)

    def test_invalid_question_type(self, service):
        with pytest.raises(GeminiServiceError):
            service.generate_questions(job_title="SWE", count=1, question_type="invalid")


class TestGeneration:
    def test_json_response_parsed(self):
        llm = FakeLLM(
            responses=[
                '[{"question": "What is a closure in Python?", "type": "technical", '
                '"difficulty": 3, "tags": "python,closures"}]'
            ]
        )
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="technical")
        assert len(questions) == 1
        assert questions[0]["question_text"] == "What is a closure in Python?"
        assert questions[0]["question_type"] == "technical"
        assert questions[0]["difficulty"] == 3
        assert questions[0]["tags"] == "python,closures"

    def test_markdown_fenced_json(self):
        llm = FakeLLM(
            responses=['```json\n[{"question": "Explain the reactor pattern in networking?", ' '"difficulty": 4}]\n```']
        )
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1)
        assert len(questions) == 1
        assert questions[0]["difficulty"] == 4

    def test_difficulty_clamped(self):
        llm = FakeLLM(
            responses=['[{"question": "Explain how garbage collection works in runtimes?", "difficulty": 99}]']
        )
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1)
        assert questions[0]["difficulty"] == 5

    def test_invalid_difficulty_defaults(self):
        llm = FakeLLM(responses=['[{"question": "Explain how caches improve latency?", "difficulty": "abc"}]'])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1)
        assert questions[0]["difficulty"] == 3

    def test_missing_tags_fall_back_to_job_title(self):
        llm = FakeLLM(responses=['[{"question": "Explain how load balancers distribute traffic?"}]'])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("Software Engineer", count=1)
        assert questions[0]["tags"] == "software,engineer"

    def test_mixed_type_uses_response_type(self):
        llm = FakeLLM(
            responses=['[{"question": "Tell me about a time you handled a conflict on a team?", "type": "behavioral"}]']
        )
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="mixed")
        assert questions[0]["question_type"] == "behavioral"

    def test_mixed_type_invalid_response_type_defaults_technical(self):
        llm = FakeLLM(responses=['[{"question": "Explain how indexes speed up queries?", "type": "weird"}]'])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="mixed")
        assert questions[0]["question_type"] == "technical"

    def test_requested_type_overrides_response(self):
        llm = FakeLLM(
            responses=['[{"question": "Explain how transactions ensure consistency?", "type": "behavioral"}]']
        )
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="technical")
        assert questions[0]["question_type"] == "technical"

    def test_empty_question_entry_skipped(self):
        llm = FakeLLM(responses=['[{"question": "   "}, {"question": "Explain how DNS resolves names?"}]'])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=2)
        assert len(questions) == 1

    def test_non_dict_entries_skipped(self):
        llm = FakeLLM(responses=['["not-a-dict", {"question": "Explain how HTTPS encrypts traffic?"}]'])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=2)
        assert len(questions) == 1

    def test_json_not_a_list(self):
        llm = FakeLLM(responses=['{"question": "no array here"}'])
        service = GeminiService(llm_service=llm)
        # A JSON object is not a valid response: both the JSON and
        # text parsers yield nothing, so generation fails outright.
        with pytest.raises(GeminiServiceError):
            service.generate_questions("SWE", count=1)

    def test_invalid_json_falls_back_to_text(self):
        llm = FakeLLM(responses=["1. What is a hash map?\n2. How does a linked list work?\n"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=2)
        assert len(questions) == 2
        assert questions[0]["question_text"] == "What is a hash map?"

    def test_text_fallback_with_q_prefix(self):
        llm = FakeLLM(responses=["Q: Explain how a B-tree indexes data?\nQ2: Describe how caches work?"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=2)
        assert len(questions) == 2
        assert questions[0]["question_text"] == "Explain how a B-tree indexes data?"

    def test_text_fallback_dash_prefix(self):
        llm = FakeLLM(responses=["- Explain how routers forward packets?\n- Describe how firewalls filter traffic?"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=2)
        assert len(questions) == 2

    def test_text_fallback_question_prefix(self):
        llm = FakeLLM(responses=["Question 1: Explain how compilers translate source code?"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1)
        assert len(questions) == 1

    def test_text_fallback_parenthesis_prefix(self):
        llm = FakeLLM(responses=["1) Explain how mutexes prevent race conditions?"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1)
        assert len(questions) == 1

    def test_text_fallback_behavioral_inference(self):
        llm = FakeLLM(responses=["Tell me about a time you showed leadership in a team?"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="mixed")
        assert questions[0]["question_type"] == "behavioral"

    def test_text_fallback_difficulty_inference(self):
        llm = FakeLLM(responses=["Explain senior architecture design patterns for complex systems?"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="mixed")
        assert questions[0]["difficulty"] == 5

    def test_text_fallback_entry_level_difficulty(self):
        llm = FakeLLM(responses=["What is a basic variable in programming?"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="mixed")
        assert questions[0]["difficulty"] == 2

    def test_text_fallback_long_question_difficulty(self):
        llm = FakeLLM(
            responses=[
                "Explain how a distributed consensus algorithm handles network partitions "
                "and leader elections across multiple data centers with replication "
                "and automatic failover for mission critical workloads at scale?"
            ]
        )
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="mixed")
        assert questions[0]["difficulty"] == 4

    def test_text_fallback_tags_generation(self):
        llm = FakeLLM(responses=["Explain how database indexing and query optimization work?"])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1, question_type="mixed")
        assert "database" in questions[0]["tags"]
        assert "optimization" in questions[0]["tags"]

    def test_llm_failure_then_simplified_prompt_success(self):
        llm = FakeLLM(responses=['[{"question": "Explain how consistent hashing distributes keys?", "difficulty": 3}]'])
        llm.error = None
        # First call raises, second succeeds.
        calls = {"n": 0}

        def flaky_complete(prompt, temperature=None, max_tokens=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise LLMServiceError("transient")
            return '[{"question": "Explain how retries provide at-least-once delivery?", "difficulty": 2}]'

        llm.complete = flaky_complete
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1)
        assert len(questions) == 1

    def test_empty_response_triggers_retry(self):
        llm = FakeLLM(responses=["", '[{"question": "Explain how websockets enable full-duplex communication?"}]'])
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=1)
        assert len(questions) == 1

    def test_all_attempts_fail_raises(self):
        llm = FakeLLM(error=LLMServiceError("down"))
        service = GeminiService(llm_service=llm)
        with pytest.raises(GeminiServiceError):
            service.generate_questions("SWE", count=1)

    def test_result_limited_to_requested_count(self):
        llm = FakeLLM(
            responses=[
                "["
                + ",".join(
                    f'{{"question": "Explain how mechanism number {i} works in operating systems?"}}' for i in range(5)
                )
                + "]"
            ]
        )
        service = GeminiService(llm_service=llm)
        questions = service.generate_questions("SWE", count=2)
        assert len(questions) == 2

    def test_generate_content_returns_none_on_error(self):
        llm = FakeLLM(error=LLMServiceError("down"))
        service = GeminiService(llm_service=llm)
        assert service.generate_content("prompt") is None

    def test_generate_content_success(self):
        llm = FakeLLM(responses=["some content"])
        service = GeminiService(llm_service=llm)
        assert service.generate_content("prompt") == "some content"


class TestPromptBuilding:
    def test_build_prompt_technical(self, service):
        prompt = service._build_prompt("SWE", 3, "technical")
        assert "technical skills" in prompt
        assert "3" in prompt

    def test_build_prompt_behavioral(self, service):
        prompt = service._build_prompt("SWE", 3, "behavioral")
        assert "soft skills" in prompt

    def test_build_prompt_mixed(self, service):
        prompt = service._build_prompt("SWE", 3, "mixed")
        assert "mix of technical" in prompt

    def test_build_simplified_prompt(self, service):
        prompt = service._build_simplified_prompt("SWE", 2, "mixed")
        assert "Generate 2 interview questions" in prompt
        assert '"type": "technical"' in prompt

    def test_extract_json_from_response(self):
        cleaned = GeminiService._extract_json_from_response('```json\n[{"a": 1}]\n```')
        assert cleaned == '[{"a": 1}]'

    def test_extract_json_plain(self):
        cleaned = GeminiService._extract_json_from_response('[{"a": 1}]')
        assert cleaned == '[{"a": 1}]'

    def test_parse_response_exception_returns_empty(self, monkeypatch):
        service = GeminiService(llm_service=FakeLLM())
        monkeypatch.setattr(service, "_try_parse_json", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
        monkeypatch.setattr(service, "_try_parse_text", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("y")))
        assert service._parse_response("anything", "SWE", "technical") == []

    def test_format_question_exception_returns_none(self, monkeypatch):
        service = GeminiService(llm_service=FakeLLM())
        monkeypatch.setattr(
            GeminiService,
            "_determine_question_type",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
        )
        assert service._format_question({"question": "Explain how compilers work?"}, "SWE", "technical") is None

    def test_create_text_question_exception_returns_none(self, monkeypatch):
        service = GeminiService(llm_service=FakeLLM())
        monkeypatch.setattr(
            GeminiService,
            "_infer_question_type",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
        )
        assert service._create_text_question("Explain how compilers work?", "SWE", "mixed") is None

    def test_create_text_question_empty_returns_none(self):
        service = GeminiService(llm_service=FakeLLM())
        assert service._create_text_question("   ", "SWE", "mixed") is None

    def test_is_question_line_variants(self):
        assert GeminiService._is_question_line("What is a closure?")
        assert GeminiService._is_question_line("Q: something")
        assert GeminiService._is_question_line("Q3: something")
        assert GeminiService._is_question_line("- something")
        assert GeminiService._is_question_line("Question 2: something")
        assert GeminiService._is_question_line("1. something")
        assert GeminiService._is_question_line("1) something")
        assert not GeminiService._is_question_line("just a statement")
        assert not GeminiService._is_question_line("")

    def test_clean_question_text_variants(self):
        assert GeminiService._clean_question_text("Q: What is a closure?") == "What is a closure?"
        assert GeminiService._clean_question_text("Question: What is a closure?") == "What is a closure?"
        assert GeminiService._clean_question_text("- What is a closure?") == "What is a closure?"
        assert GeminiService._clean_question_text("1. What is a closure?") == "What is a closure?"
        assert GeminiService._clean_question_text("1) What is a closure?") == "What is a closure?"
        assert GeminiService._clean_question_text("What is a closure?") == "What is a closure?"

    def test_generate_tags_no_keywords(self):
        tags = GeminiService._generate_tags("a plain sentence", "SWE")
        assert tags == "swe"

    def test_infer_question_type_fixed(self):
        assert GeminiService._infer_question_type("anything", "behavioral") == "behavioral"

    def test_determine_question_type_fixed(self):
        assert GeminiService._determine_question_type({}, "technical") == "technical"

    def test_unexpected_error_in_generate_questions(self, monkeypatch):
        service = GeminiService(llm_service=FakeLLM())
        monkeypatch.setattr(
            service, "_validate_generation_params", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        with pytest.raises(GeminiServiceError):
            service.generate_questions("SWE", count=1)

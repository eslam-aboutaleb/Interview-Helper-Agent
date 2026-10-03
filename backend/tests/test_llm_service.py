"""Tests for the LiteLLM abstraction layer."""

import pytest

from services.llm_service import LLMService, LLMServiceError


class FakeResponse:
    def __init__(self, content):
        class _Choice:
            def __init__(self, content):
                class _Message:
                    def __init__(self, content):
                        self.content = content

                self.message = _Message(content)

        self.choices = [_Choice(content)]


class FakeLitellm:
    """Records calls and returns canned responses."""

    def __init__(self, responses=None, raise_for=None):
        self.responses = responses or {}
        self.raise_for = raise_for or set()
        self.calls = []

    def completion(self, **kwargs):
        self.calls.append(kwargs)
        model = kwargs["model"]
        if model in self.raise_for:
            raise RuntimeError(f"provider {model} down")
        if model in self.responses:
            return FakeResponse(self.responses[model])
        return FakeResponse("fallback output")


@pytest.fixture()
def llm_service(monkeypatch):
    """LLMService with a deterministic fake litellm module."""
    fake = FakeLitellm()
    service = LLMService(
        model="gemini/gemini-1.5-flash",
        fallback_models=["openai/gpt-4o-mini"],
    )
    monkeypatch.setattr(service, "_litellm", fake)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    service._fake = fake
    return service


class TestLLMService:
    def test_complete_uses_primary_model(self, llm_service):
        llm_service._fake.responses = {"gemini/gemini-1.5-flash": "primary answer"}
        result = llm_service.complete("Hello")
        assert result == "primary answer"
        assert llm_service._fake.calls[0]["model"] == "gemini/gemini-1.5-flash"

    def test_complete_falls_back_on_failure(self, llm_service):
        llm_service._fake.raise_for = {"gemini/gemini-1.5-flash"}
        llm_service._fake.responses = {"openai/gpt-4o-mini": "fallback answer"}
        result = llm_service.complete("Hello")
        assert result == "fallback answer"
        assert len(llm_service._fake.calls) == 2

    def test_complete_skips_unconfigured_providers(self, llm_service, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY")
        llm_service._fake.responses = {"openai/gpt-4o-mini": "openai answer"}
        result = llm_service.complete("Hello")
        assert result == "openai answer"
        # Only the openai model should have been attempted.
        assert [c["model"] for c in llm_service._fake.calls] == ["openai/gpt-4o-mini"]

    def test_complete_raises_when_all_fail(self, llm_service):
        llm_service._fake.raise_for = {"gemini/gemini-1.5-flash", "openai/gpt-4o-mini"}
        with pytest.raises(LLMServiceError):
            llm_service.complete("Hello")

    def test_complete_sends_system_prompt(self, llm_service):
        llm_service._fake.responses = {"gemini/gemini-1.5-flash": "ok"}
        llm_service.complete("Hi", system="You are an interviewer.")
        messages = llm_service._fake.calls[0]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_complete_json_parses_object(self, llm_service):
        llm_service._fake.responses = {"gemini/gemini-1.5-flash": '{"a": 1}'}
        assert llm_service.complete_json("Give JSON") == {"a": 1}

    def test_complete_json_parses_array(self, llm_service):
        llm_service._fake.responses = {"gemini/gemini-1.5-flash": '[{"q": "one"}, {"q": "two"}]'}
        assert llm_service.complete_json("Give JSON") == [{"q": "one"}, {"q": "two"}]

    def test_complete_json_tolerates_markdown_fences(self, llm_service):
        llm_service._fake.responses = {"gemini/gemini-1.5-flash": '```json\n{"a": 1}\n```'}
        assert llm_service.complete_json("Give JSON") == {"a": 1}

    def test_complete_json_returns_none_on_garbage(self, llm_service):
        llm_service._fake.responses = {"gemini/gemini-1.5-flash": "no json here"}
        assert llm_service.complete_json("Give JSON") is None

    def test_is_configured_local_provider(self):
        service = LLMService(model="ollama/llama3")
        assert service.is_configured() is True

    def test_provider_of(self):
        assert LLMService.provider_of("openai/gpt-4o") == "openai"
        assert LLMService.provider_of("gpt-4o") == "openai"

    def test_model_chain_deduplicates(self):
        service = LLMService(
            model="openai/gpt-4o-mini",
            fallback_models=["openai/gpt-4o-mini", "gemini/gemini-1.5-flash"],
        )
        assert service._model_chain() == [
            "openai/gpt-4o-mini",
            "gemini/gemini-1.5-flash",
        ]

"""Provider-agnostic LLM client built on LiteLLM.

This module is the single entry point for every LLM call in the
application. It decouples the app from any specific provider: the
active model is selected with the ``LLM_MODEL`` environment variable
(e.g. ``gemini/gemini-1.5-flash``, ``openai/gpt-4o-mini``,
``anthropic/claude-3-5-haiku-20241022``) and a fallback chain can
be configured with ``LLM_FALLBACK_MODELS``.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Provider prefix (the part before the "/" in a LiteLLM model name)
# mapped to the environment variable that holds its API key.
PROVIDER_KEY_ENV: Dict[str, str] = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
    "azure": "AZURE_API_KEY",
    "vertex_ai": "VERTEX_AI_PROJECT_ID",
    "bedrock": "AWS_ACCESS_KEY_ID",
}

DEFAULT_MODEL = "gemini/gemini-1.5-flash"
DEFAULT_FALLBACK_MODELS = "openai/gpt-4o-mini,anthropic/claude-3-5-haiku-20241022"
DEFAULT_TIMEOUT = 60
DEFAULT_MAX_RETRIES = 2
DEFAULT_TEMPERATURE = 0.7


class LLMServiceError(Exception):
    """Raised when every configured LLM provider fails."""


class LLMService:
    """Thin wrapper around ``litellm.completion`` with a fallback chain.

    The service tries the primary model first and walks the fallback
    list on failure, so a single provider outage degrades gracefully
    instead of taking the platform down.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        fallback_models: Optional[List[str]] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.model = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)
        if fallback_models is None:
            fallback_env = os.getenv("LLM_FALLBACK_MODELS", DEFAULT_FALLBACK_MODELS)
            fallback_models = [m.strip() for m in fallback_env.split(",") if m.strip()]
        self.fallback_models = fallback_models
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", str(DEFAULT_TIMEOUT)))
        self.max_retries = (
            max_retries if max_retries is not None else int(os.getenv("LLM_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
        )
        self.temperature = (
            temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
        )
        self._litellm: Optional[Any] = None

    # ------------------------------------------------------------------
    # Lazy litellm import so a missing install does not break app startup.
    # ------------------------------------------------------------------
    @property
    def litellm(self) -> Any:
        if self._litellm is None:
            try:
                import litellm

                litellm.suppress_debug_info = True
                self._litellm = litellm
            except ImportError as e:
                raise LLMServiceError(f"litellm is not installed: {e}")
        return self._litellm

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _model_chain(self) -> List[str]:
        """Primary model followed by the deduplicated fallback list."""
        chain = [self.model]
        for model in self.fallback_models:
            if model != self.model:
                chain.append(model)
        return chain

    @staticmethod
    def provider_of(model: str) -> str:
        """Extract the provider prefix from a LiteLLM model name."""
        return model.split("/", 1)[0] if "/" in model else "openai"

    def is_configured(self, model: Optional[str] = None) -> bool:
        """Check whether the API key for a model's provider is present.

        Local providers (ollama) and unknown providers are assumed to
        be usable and are left to litellm to decide.
        """
        model = model or self.model
        provider = self.provider_of(model)
        if provider in {"ollama", "local"}:
            return True
        env_var = PROVIDER_KEY_ENV.get(provider)
        if env_var is None:
            return True
        return bool(os.getenv(env_var))

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a text completion, walking the fallback chain.

        Raises:
            LLMServiceError: If every model in the chain fails.
        """
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        errors: List[str] = []
        for model in self._model_chain():
            if not self.is_configured(model):
                logger.debug(f"Skipping {model}: no API key configured")
                continue
            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": (temperature if temperature is not None else self.temperature),
                "timeout": self.timeout,
                "num_retries": self.max_retries,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            try:
                response = self.litellm.completion(**kwargs)
                content = response.choices[0].message.content
                if content and content.strip():
                    logger.info(f"LLM response served by {model}")
                    return content.strip()
                errors.append(f"{model}: empty response")
            except Exception as e:
                errors.append(f"{model}: {e}")
                logger.warning(f"LLM call to {model} failed: {e}")

        raise LLMServiceError("All LLM providers failed: " + "; ".join(errors))

    def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[Union[Dict[str, Any], List[Any]]]:
        """Generate a completion and parse it as JSON.

        Returns None when the response contains no parseable JSON, so
        callers can apply their own fallback.
        """
        text = self.complete(
            prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return self.parse_json(text)

    @staticmethod
    def parse_json(text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
        """Extract and parse a JSON object or array from LLM output.

        Tolerates markdown code fences and surrounding prose.
        """
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        candidates: List[str] = []
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            candidates.append(cleaned[start:end])
        bracket_start = cleaned.find("[")
        bracket_end = cleaned.rfind("]") + 1
        if bracket_start != -1 and bracket_end > bracket_start:
            candidates.append(cleaned[bracket_start:bracket_end])

        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        return None

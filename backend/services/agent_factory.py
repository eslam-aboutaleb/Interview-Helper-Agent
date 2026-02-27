"""
Agent Factory module.

Implements the Factory design pattern for creating LLM agent instances.
Supports multiple providers (currently Google Gemini via LangChain) and
allows easy extension to other providers in the future.
"""

import os
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import BaseMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """Abstract base class that every concrete agent must implement."""

    @abstractmethod
    def invoke(self, messages: list[BaseMessage]):
        """Send a list of messages to the LLM and return the response."""
        ...

    @property
    @abstractmethod
    def provider(self) -> AgentProvider:
        """Return the provider enum value for this agent."""
        ...


# ---------------------------------------------------------------------------
# Concrete agents
# ---------------------------------------------------------------------------

class GeminiAgent(BaseAgent):
    """Concrete agent backed by Google Gemini via LangChain.

    Tries each model name in *model_names* in order, falling back to the
    next one if initialisation fails.
    """

    DEFAULT_MODEL_NAMES = ["gemini-1.5-pro", "gemini-pro"]

    def __init__(
        self,
        api_key: str,
        temperature: float = 0.7,
        top_p: float = 0.95,
        top_k: int = 40,
        max_output_tokens: int = 4096,
        model_names: Optional[list[str]] = None,
    ) -> None:
        self._api_key = api_key
        self._temperature = temperature
        self._top_p = top_p
        self._top_k = top_k
        self._max_output_tokens = max_output_tokens
        self._model_names = model_names or self.DEFAULT_MODEL_NAMES
        self._llm = self._build_llm()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_llm(self) -> ChatGoogleGenerativeAI:
        """Attempt to build a ChatGoogleGenerativeAI instance.

        Iterates over *self._model_names* and returns the first one that
        initialises successfully.

        Raises:
            RuntimeError: If every model name fails.
        """
        last_error: Optional[Exception] = None
        for model_name in self._model_names:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=self._api_key,
                    temperature=self._temperature,
                    top_p=self._top_p,
                    top_k=self._top_k,
                    max_output_tokens=self._max_output_tokens,
                    convert_system_message_to_human=True,
                )
                logger.info("GeminiAgent: initialised with model '%s'", model_name)
                return llm
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "GeminiAgent: failed to initialise model '%s': %s",
                    model_name,
                    exc,
                )

        raise RuntimeError(
            f"GeminiAgent: all model initialisations failed. "
            f"Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def invoke(self, messages: list[BaseMessage]):
        """Invoke the underlying LLM with *messages* and return the response."""
        return self._llm.invoke(messages)

    @property
    def provider(self) -> AgentProvider:
        return AgentProvider.GEMINI


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class AgentFactory:
    """Factory for creating :class:`BaseAgent` instances.

    Usage::

        agent = AgentFactory.create(
            provider=AgentProvider.GEMINI,
            temperature=0.5,
        )
        response = agent.invoke([HumanMessage(content="Hello")])

    The factory reads provider-specific credentials from environment variables
    so callers do not need to pass secrets explicitly.  Pass keyword arguments
    to override defaults (e.g. *temperature*, *model_names*).
    """

    # Registry maps provider enum → factory function
    _registry: dict[AgentProvider, type[BaseAgent]] = {
        AgentProvider.GEMINI: GeminiAgent,
    }

    @classmethod
    def create(
        cls,
        provider: AgentProvider = AgentProvider.GEMINI,
        **kwargs,
    ) -> BaseAgent:
        """Create and return a :class:`BaseAgent` for *provider*.

        Args:
            provider: Which LLM provider to use (default: GEMINI).
            **kwargs: Extra keyword arguments forwarded to the concrete agent
                      constructor (e.g. ``temperature``, ``model_names``).

        Returns:
            A fully initialised :class:`BaseAgent` instance.

        Raises:
            ValueError: If *provider* is not registered.
            RuntimeError: If the underlying agent cannot be initialised
                          (e.g. missing API key or all models fail).
        """
        if provider not in cls._registry:
            raise ValueError(
                f"AgentFactory: unknown provider '{provider}'. "
                f"Registered providers: {list(cls._registry)}"
            )

        agent_cls = cls._registry[provider]

        # Inject provider-specific credentials from environment
        if provider == AgentProvider.GEMINI:
            api_key = kwargs.pop("api_key", None) or os.getenv("GEMINI_API_KEY", "")
            if not api_key or api_key == "your-gemini-api-key":
                raise RuntimeError(
                    "AgentFactory: GEMINI_API_KEY environment variable is not set "
                    "or contains a placeholder value."
                )
            return agent_cls(api_key=api_key, **kwargs)

        # Generic fallback (for future providers that don't need special handling)
        return agent_cls(**kwargs)

    @classmethod
    def register(cls, provider: AgentProvider, agent_cls: type[BaseAgent]) -> None:
        """Register a new provider → agent class mapping.

        This allows third-party code to extend the factory without modifying
        this module.

        Args:
            provider: The :class:`AgentProvider` enum value.
            agent_cls: A concrete subclass of :class:`BaseAgent`.
        """
        cls._registry[provider] = agent_cls
        logger.info("AgentFactory: registered provider '%s' → %s", provider, agent_cls)

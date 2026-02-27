"""
Gemini Service module.

Provides AI-powered interview question generation backed by Google Gemini.
Prompts are loaded from ``backend/prompts/prompts.json`` so they can be
edited without touching Python code.  LLM instantiation is delegated to
:class:`~services.agent_factory.AgentFactory` (Factory design pattern).
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from langchain.schema import HumanMessage

from services.agent_factory import AgentFactory, AgentProvider, BaseAgent

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------

_PROMPTS_PATH = Path(__file__).parent.parent / "prompts" / "prompts.json"


def _load_prompts() -> dict:
    """Load and return the prompts dictionary from the JSON file.

    Raises:
        FileNotFoundError: If the prompts file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    with _PROMPTS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


# Cache prompts at module level (reload on import)
_PROMPTS: dict = _load_prompts()


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class GeminiServiceError(Exception):
    """Custom exception for Gemini service errors."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class GeminiService:
    """Service for generating interview questions using Google Gemini via LangChain.

    Prompts are loaded from ``prompts/prompts.json``.
    LLM instances are created through :class:`AgentFactory` (Factory pattern).

    This service provides AI-powered question generation with fallback
    mechanisms and multiple parsing strategies for robustness.
    """

    # Constants for configuration
    MAX_GENERATION_ATTEMPTS = 2
    DEFAULT_TEMPERATURE = 0.7
    RETRY_TEMPERATURE = 0.5
    DEFAULT_COUNT = 5
    MAX_COUNT = 100
    DEFAULT_DIFFICULTY = 3
    MIN_DIFFICULTY = 1
    MAX_DIFFICULTY = 5
    VALID_QUESTION_TYPES = {"technical", "behavioral", "mixed"}

    def __init__(self) -> None:
        """Validate the API key.  LLM creation is deferred to call time.

        Raises:
            GeminiServiceError: If the API key is missing or a placeholder.
        """
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key or api_key == "your-gemini-api-key":
                msg = (
                    "GEMINI_API_KEY environment variable not set "
                    "or using placeholder value"
                )
                logger.warning(msg)
                raise GeminiServiceError(msg)

            self._api_key = api_key
            logger.info("Gemini API key validated successfully")

        except GeminiServiceError:
            raise
        except Exception as exc:
            raise GeminiServiceError(
                f"Failed to initialise Gemini service: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Agent creation via factory
    # ------------------------------------------------------------------

    def _get_agent(self, temperature: float = DEFAULT_TEMPERATURE) -> BaseAgent:
        """Create a :class:`BaseAgent` via :class:`AgentFactory`.

        Args:
            temperature: Sampling temperature for generation.

        Returns:
            A fully initialised :class:`BaseAgent`.

        Raises:
            GeminiServiceError: If the factory cannot create an agent.
        """
        try:
            return AgentFactory.create(
                provider=AgentProvider.GEMINI,
                api_key=self._api_key,
                temperature=temperature,
            )
        except Exception as exc:
            raise GeminiServiceError(
                f"AgentFactory failed to create agent: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_questions(
        self,
        job_title: str,
        count: int = DEFAULT_COUNT,
        question_type: str = "mixed",
    ) -> List[Dict]:
        """Generate interview questions using Gemini AI via LangChain.

        Uses a multi-attempt strategy with fallback to simplified prompts
        if needed.

        Args:
            job_title: The position title to generate questions for.
            count: Number of questions to generate (default: 5, max: 100).
            question_type: Type of questions – ``'technical'``,
                ``'behavioral'``, or ``'mixed'``.

        Returns:
            List of question dictionaries with formatted fields.

        Raises:
            GeminiServiceError: If generation fails or parameters are invalid.
        """
        try:
            self._validate_generation_params(job_title, count, question_type)

            logger.info(
                "Generating %d %s questions for '%s'",
                count,
                question_type,
                job_title,
            )

            # First attempt with standard prompt
            questions = self._attempt_question_generation(
                job_title, count, question_type, is_simplified=False
            )

            # If we didn't get enough, try with simplified prompt
            remaining = count - len(questions)
            if remaining > 0:
                logger.info(
                    "First attempt yielded %d/%d questions. Trying simplified prompt.",
                    len(questions),
                    count,
                )
                additional = self._attempt_question_generation(
                    job_title, remaining, question_type, is_simplified=True
                )
                questions.extend(additional)

            if questions:
                logger.info("Successfully generated %d questions", len(questions))
                return questions[:count]

            raise GeminiServiceError(
                f"Failed to generate any valid questions for '{job_title}'"
            )

        except GeminiServiceError:
            raise
        except Exception as exc:
            logger.error("Error generating questions: %s", exc)
            raise GeminiServiceError(f"Failed to generate questions: {exc}") from exc

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_generation_params(
        self,
        job_title: str,
        count: int,
        question_type: str,
    ) -> None:
        """Validate generation parameters.

        Raises:
            GeminiServiceError: If any parameter is invalid.
        """
        if not job_title or not isinstance(job_title, str) or not job_title.strip():
            raise GeminiServiceError("job_title must be a non-empty string")

        if not isinstance(count, int) or count < 1 or count > self.MAX_COUNT:
            raise GeminiServiceError(
                f"count must be between 1 and {self.MAX_COUNT}"
            )

        if question_type not in self.VALID_QUESTION_TYPES:
            raise GeminiServiceError(
                f"question_type must be one of {self.VALID_QUESTION_TYPES}"
            )

    # ------------------------------------------------------------------
    # Generation attempts
    # ------------------------------------------------------------------

    def _attempt_question_generation(
        self,
        job_title: str,
        count: int,
        question_type: str,
        is_simplified: bool = False,
        max_attempts: Optional[int] = None,
    ) -> List[Dict]:
        """Make multiple attempts to generate questions with adaptive temperature.

        Args:
            job_title: The position title.
            count: Number of questions needed.
            question_type: Type of questions.
            is_simplified: Whether to use the simplified prompt.
            max_attempts: Maximum number of generation attempts.

        Returns:
            List of generated question dictionaries.
        """
        if max_attempts is None:
            max_attempts = self.MAX_GENERATION_ATTEMPTS

        questions: List[Dict] = []

        for attempt in range(1, max_attempts + 1):
            try:
                prompt = (
                    self._build_simplified_prompt(job_title, count, question_type)
                    if is_simplified
                    else self._build_prompt(job_title, count, question_type)
                )

                # Reduce temperature on retry for more deterministic results
                temperature = (
                    self.RETRY_TEMPERATURE if attempt > 1 else self.DEFAULT_TEMPERATURE
                )

                logger.info(
                    "Attempt %d/%d with temperature=%.2f",
                    attempt,
                    max_attempts,
                    temperature,
                )

                agent = self._get_agent(temperature=temperature)
                response = agent.invoke([HumanMessage(content=prompt)])

                response_text = (
                    response.content
                    if hasattr(response, "content")
                    else str(response)
                )

                if not response_text or not response_text.strip():
                    logger.warning("Attempt %d: empty response from model", attempt)
                    continue

                new_questions = self._parse_response(
                    response_text, job_title, question_type
                )
                questions.extend(new_questions)

                if len(questions) >= count:
                    break

            except Exception as exc:  # noqa: BLE001
                logger.warning("Attempt %d error: %s", attempt, exc)
                if attempt == max_attempts:
                    logger.error(
                        "All %d attempts failed for '%s'", max_attempts, job_title
                    )

        return questions

    # ------------------------------------------------------------------
    # Prompt builders (load from JSON)
    # ------------------------------------------------------------------

    def _build_prompt(
        self, job_title: str, count: int, question_type: str
    ) -> str:
        """Build the standard prompt from the JSON template.

        Args:
            job_title: The position title.
            count: Number of questions to generate.
            question_type: Type of questions.

        Returns:
            Rendered prompt string.
        """
        cfg = _PROMPTS["question_generation"]["standard"]

        focus = cfg["focus"][question_type]
        instruction = cfg["instruction"][question_type]
        difficulty_scale = cfg["difficulty_scale"]
        output_format = cfg["output_format"]
        output_constraint = cfg["output_constraint"]

        type_placeholder = (
            question_type if question_type != "mixed" else "technical or behavioral"
        )

        return (
            f"{cfg['system_context'].format(job_title=job_title)}\n\n"
            f"Task: {cfg['task'].format(count=count, job_title=job_title)}\n"
            f"Focus on {focus}.\n\n"
            f"{instruction}\n\n"
            f"{difficulty_scale}\n\n"
            f"{output_format.format(question_type_placeholder=type_placeholder)}\n\n"
            f"{output_constraint}"
        )

    def _build_simplified_prompt(
        self, job_title: str, count: int, question_type: str
    ) -> str:
        """Build the simplified prompt from the JSON template.

        Args:
            job_title: The position title.
            count: Number of questions to generate.
            question_type: Type of questions.

        Returns:
            Rendered simplified prompt string.
        """
        cfg = _PROMPTS["question_generation"]["simplified"]
        default_type = question_type if question_type != "mixed" else "technical"
        return cfg["template"].format(
            count=count,
            job_title=job_title,
            question_type=question_type,
            default_type=default_type,
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        response_text: str,
        job_title: str,
        question_type: str,
    ) -> List[Dict]:
        """Parse Gemini response and extract questions.

        Tries JSON parsing first with fallback to text parsing.

        Args:
            response_text: The raw response from Gemini.
            job_title: The position title.
            question_type: Type of questions.

        Returns:
            List of formatted question dictionaries.
        """
        try:
            questions = self._try_parse_json(response_text, job_title, question_type)
            if questions:
                return questions

            logger.info("JSON parsing failed, attempting text parsing")
            return self._try_parse_text(response_text, job_title, question_type)

        except Exception as exc:
            logger.error("Error parsing response: %s", exc)
            return []

    def _try_parse_json(
        self,
        response_text: str,
        job_title: str,
        question_type: str,
    ) -> List[Dict]:
        """Try to parse response as JSON.

        Returns:
            List of question dictionaries if successful, empty list otherwise.
        """
        questions: List[Dict] = []

        try:
            cleaned = self._extract_json_from_response(response_text)
            if not cleaned:
                logger.debug("Could not extract JSON from response")
                return []

            start = cleaned.find("[")
            end = cleaned.rfind("]") + 1

            if start == -1 or end <= start:
                logger.debug("No JSON array found in response")
                return []

            questions_data = json.loads(cleaned[start:end])

            if not isinstance(questions_data, list):
                logger.warning("JSON is not a list")
                return []

            for q in questions_data:
                if isinstance(q, dict) and "question" in q:
                    question = self._format_question(q, job_title, question_type)
                    if question:
                        questions.append(question)

            logger.info(
                "Successfully parsed %d questions from JSON", len(questions)
            )

        except json.JSONDecodeError as exc:
            logger.debug("JSON parsing error: %s", exc)
        except Exception as exc:
            logger.debug("Unexpected error parsing JSON: %s", exc)

        return questions

    @staticmethod
    def _extract_json_from_response(response_text: str) -> str:
        """Strip markdown code-block markers from *response_text*.

        Returns:
            Cleaned text with markdown markers removed.
        """
        cleaned = response_text.strip()
        for marker in ("```json", "```"):
            if cleaned.startswith(marker):
                cleaned = cleaned.replace(marker, "", 1)
            if cleaned.endswith("```"):
                cleaned = cleaned[: cleaned.rfind("```")]
        return cleaned.strip()

    def _format_question(
        self,
        question_data: Dict,
        job_title: str,
        question_type: str,
    ) -> Optional[Dict]:
        """Format and validate a question from parsed data.

        Returns:
            Formatted question dictionary, or ``None`` if invalid.
        """
        try:
            question_text = question_data.get("question", "").strip()
            if not question_text:
                logger.debug("Question text is empty")
                return None

            q_type = self._determine_question_type(question_data, question_type)
            difficulty = self._extract_difficulty(question_data)
            tags = question_data.get("tags", "").strip() or job_title.lower().replace(
                " ", ","
            )

            return {
                "job_title": job_title,
                "question_text": question_text,
                "question_type": q_type,
                "difficulty": difficulty,
                "tags": tags,
            }

        except Exception as exc:
            logger.debug("Error formatting question: %s", exc)
            return None

    @staticmethod
    def _determine_question_type(question_data: Dict, requested_type: str) -> str:
        """Determine appropriate question type.

        Returns:
            Validated question type string.
        """
        if requested_type != "mixed":
            return requested_type

        q_type = question_data.get("type", "technical")
        return q_type if q_type in {"technical", "behavioral"} else "technical"

    @staticmethod
    def _extract_difficulty(question_data: Dict) -> int:
        """Extract and validate difficulty level.

        Returns:
            Difficulty level between 1 and 5.
        """
        try:
            difficulty = int(
                question_data.get("difficulty", GeminiService.DEFAULT_DIFFICULTY)
            )
            return max(
                GeminiService.MIN_DIFFICULTY,
                min(difficulty, GeminiService.MAX_DIFFICULTY),
            )
        except (ValueError, TypeError):
            return GeminiService.DEFAULT_DIFFICULTY

    def _try_parse_text(
        self,
        response_text: str,
        job_title: str,
        question_type: str,
    ) -> List[Dict]:
        """Parse response as plain text when JSON parsing fails.

        Returns:
            List of question dictionaries.
        """
        questions: List[Dict] = []

        for line in response_text.split("\n"):
            line = line.strip()
            if not line or not self._is_question_line(line):
                continue

            question_text = self._clean_question_text(line)
            question = self._create_text_question(question_text, job_title, question_type)
            if question:
                questions.append(question)

        logger.info("Parsed %d questions from text", len(questions))
        return questions

    @staticmethod
    def _is_question_line(line: str) -> bool:
        """Return ``True`` if *line* looks like a question."""
        if "?" in line:
            return True
        if line.startswith(("Q:", "Q1:", "Q2:", "Q3:", "Q4:", "Q5:", "-")):
            return True
        if line.startswith(("Question 1:", "Question 2:")):
            return True
        if line and line[0].isdigit() and len(line) > 2 and line[1:3] in (". ", ") "):
            return True
        return False

    @staticmethod
    def _clean_question_text(line: str) -> str:
        """Remove common prefixes from a question line."""
        if ":" in line:
            parts = line.split(":", 1)
            if parts[0].strip().lower().startswith(("q", "question")):
                return parts[1].strip()
        if line.startswith("-"):
            return line[1:].strip()
        if line and line[0].isdigit() and len(line) > 2 and line[1:3] in (". ", ") "):
            space_idx = line.find(" ")
            if space_idx > 0:
                return line[space_idx + 1 :].strip()
        return line

    def _create_text_question(
        self,
        question_text: str,
        job_title: str,
        question_type: str,
    ) -> Optional[Dict]:
        """Create a question dict from plain-text format.

        Returns:
            Formatted question dictionary, or ``None`` if invalid.
        """
        try:
            if not question_text or not question_text.strip():
                return None

            q_type = self._infer_question_type(question_text, question_type)
            difficulty = self._infer_difficulty(question_text)
            tags = self._generate_tags(question_text, job_title)

            return {
                "job_title": job_title,
                "question_text": question_text.strip(),
                "question_type": q_type,
                "difficulty": difficulty,
                "tags": tags,
            }

        except Exception as exc:
            logger.debug("Error creating text question: %s", exc)
            return None

    @staticmethod
    def _infer_question_type(question_text: str, requested_type: str) -> str:
        """Infer question type from content when type is ``'mixed'``."""
        if requested_type != "mixed":
            return requested_type

        behavioral_keywords = {
            "experience",
            "team",
            "conflict",
            "leadership",
            "challenge",
            "difficult",
            "situation",
            "example",
            "disagree",
            "feedback",
            "mistake",
            "proud",
            "improve",
            "strength",
            "weakness",
            "worked with",
        }

        text_lower = question_text.lower()
        if any(kw in text_lower for kw in behavioral_keywords):
            return "behavioral"
        return "technical"

    @staticmethod
    def _infer_difficulty(question_text: str) -> int:
        """Estimate difficulty level based on question content."""
        text_lower = question_text.lower()
        word_count = len(question_text.split())

        if any(
            kw in text_lower
            for kw in ["senior", "advanced", "complex", "architecture", "design"]
        ):
            return GeminiService.MAX_DIFFICULTY

        if any(
            kw in text_lower
            for kw in ["basic", "simple", "beginner", "fundamental"]
        ):
            return 2

        if word_count > 25:
            return 4

        return GeminiService.DEFAULT_DIFFICULTY

    @staticmethod
    def _generate_tags(question_text: str, job_title: str) -> str:
        """Generate comma-separated tags from question keywords and job title."""
        tags = job_title.lower().replace(" ", ",")

        keywords = {
            "design",
            "algorithm",
            "data structure",
            "architecture",
            "database",
            "performance",
            "scalability",
            "leadership",
            "teamwork",
            "communication",
            "problem-solving",
            "api",
            "testing",
            "deployment",
            "security",
            "optimization",
        }

        text_lower = question_text.lower()
        additional = [
            kw.replace(" ", "_") for kw in keywords if kw in text_lower
        ]

        if additional:
            tags += "," + ",".join(additional)

        return tags

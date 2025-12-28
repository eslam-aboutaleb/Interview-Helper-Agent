import google.generativeai as genai
import os
import json
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()


class GeminiServiceError(Exception):
    """Custom exception for Gemini service errors"""
    pass


class GeminiService:
    """Service for generating interview questions using Google's Gemini API.
    
    This service provides AI-powered question generation with fallback mechanisms
    and multiple parsing strategies for robustness.
    """
    
    # Cache for model initialization
    _model = None
    _api_configured = False
    
    # Constants for configuration
    MAX_GENERATION_ATTEMPTS = 2
    DEFAULT_TEMPERATURE = 0.7
    RETRY_TEMPERATURE = 0.5
    DEFAULT_COUNT = 5
    MAX_COUNT = 100
    DEFAULT_DIFFICULTY = 3
    MIN_DIFFICULTY = 1
    MAX_DIFFICULTY = 5
    VALID_QUESTION_TYPES = {'technical', 'behavioral', 'mixed'}
    MODEL_NAMES = ['gemini-1.5-pro', 'gemini-pro']
    
    def __init__(self):
        """Initialize Gemini service and configure the API connection (lazy model loading).
        
        Raises:
            GeminiServiceError: If API key is not properly configured
        """
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key or api_key == "your-gemini-api-key":
                error_msg = "GEMINI_API_KEY environment variable not set or using placeholder value"
                logger.warning(error_msg)
                raise GeminiServiceError(error_msg)
            
            # Only configure API once
            if not GeminiService._api_configured:
                genai.configure(api_key=api_key)
                GeminiService._api_configured = True
                logger.info("Gemini API configured successfully")
        
        except GeminiServiceError:
            raise
        except Exception as e:
            raise GeminiServiceError(f"Failed to initialize Gemini service: {str(e)}")
    
    def _get_model(self):
        """Lazily initialize the model on first use.
        
        Tries multiple model names with fallback mechanism.
        
        Returns:
            genai.GenerativeModel: Initialized Gemini model
            
        Raises:
            GeminiServiceError: If all model initialization attempts fail
        """
        if GeminiService._model is not None:
            return GeminiService._model
        
        last_error = None
        for model_name in self.MODEL_NAMES:
            try:
                GeminiService._model = genai.GenerativeModel(model_name)
                logger.info(f"Successfully initialized {model_name} model")
                return GeminiService._model
            
            except Exception as e:
                last_error = e
                logger.warning(f"Failed to initialize {model_name}: {str(e)}")
                continue
        
        # All attempts failed
        raise GeminiServiceError(
            f"Failed to initialize any Gemini model. Last error: {str(last_error)}"
        )
    
    @property
    def model(self):
        """Property to access model with lazy initialization.
        
        Returns:
            genai.GenerativeModel: Initialized Gemini model
        """
        return self._get_model()

    def generate_questions(
        self,
        job_title: str,
        count: int = DEFAULT_COUNT,
        question_type: str = "mixed"
    ) -> List[Dict]:
        """Generate interview questions using Gemini AI.
        
        Uses a multi-attempt strategy with fallback to simplified prompts if needed.
        
        Args:
            job_title: The position title to generate questions for
            count: Number of questions to generate (default: 5, max: 100)
            question_type: Type of questions - 'technical', 'behavioral', or 'mixed'
            
        Returns:
            List of question dictionaries with formatted fields
            
        Raises:
            GeminiServiceError: If generation fails or invalid parameters
        """
        try:
            # Validate inputs
            self._validate_generation_params(job_title, count, question_type)
            
            logger.info(f"Generating {count} {question_type} questions for {job_title}")
            
            # First attempt with standard prompt
            questions = self._attempt_question_generation(
                job_title, count, question_type, is_simplified=False
            )
            
            # If we didn't get enough questions, try with simplified prompt
            remaining = count - len(questions)
            if remaining > 0:
                logger.info(f"First attempt yielded {len(questions)}/{count} questions. Trying simplified prompt.")
                additional_questions = self._attempt_question_generation(
                    job_title, remaining, question_type, is_simplified=True
                )
                questions.extend(additional_questions)
            
            # Return questions, limited to requested count
            if questions:
                logger.info(f"Successfully generated {len(questions)} questions")
                return questions[:count]
            else:
                raise GeminiServiceError(
                    f"Failed to generate any valid questions for {job_title}"
                )
        
        except GeminiServiceError:
            raise
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            raise GeminiServiceError(f"Failed to generate questions: {str(e)}")
    
    def _validate_generation_params(
        self,
        job_title: str,
        count: int,
        question_type: str
    ) -> None:
        """Validate generation parameters.
        
        Args:
            job_title: The position title
            count: Number of questions to generate
            question_type: Type of questions
            
        Raises:
            GeminiServiceError: If any parameter is invalid
        """
        if not job_title or not isinstance(job_title, str) or not job_title.strip():
            raise GeminiServiceError("job_title must be a non-empty string")
        
        if not isinstance(count, int) or count < 1 or count > self.MAX_COUNT:
            raise GeminiServiceError(f"count must be between 1 and {self.MAX_COUNT}")
        
        if question_type not in self.VALID_QUESTION_TYPES:
            raise GeminiServiceError(
                f"question_type must be one of {self.VALID_QUESTION_TYPES}"
            )
            
    def _attempt_question_generation(
        self,
        job_title: str,
        count: int,
        question_type: str,
        is_simplified: bool = False,
        max_attempts: int = None
    ) -> List[Dict]:
        """Make multiple attempts to generate questions with adaptive temperature.
        
        Args:
            job_title: The position title
            count: Number of questions needed
            question_type: Type of questions
            is_simplified: Whether to use simplified prompt
            max_attempts: Maximum number of generation attempts
            
        Returns:
            List of generated question dictionaries
        """
        if max_attempts is None:
            max_attempts = self.MAX_GENERATION_ATTEMPTS
        
        questions = []
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Build appropriate prompt
                if is_simplified:
                    prompt = self._build_simplified_prompt(job_title, count, question_type)
                else:
                    prompt = self._build_prompt(job_title, count, question_type)
                
                # Reduce temperature on retry for more deterministic results
                temperature = self.RETRY_TEMPERATURE if attempt > 1 else self.DEFAULT_TEMPERATURE
                
                logger.info(f"Attempt {attempt}/{max_attempts} with temperature={temperature}")
                
                # Generate content with proper error handling
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        top_p=0.95,
                        top_k=40,
                        max_output_tokens=4096,
                    )
                )
                
                if not response or not response.text:
                    logger.warning(f"Attempt {attempt}: Empty response from model")
                    continue
                
                # Parse response
                new_questions = self._parse_response(response.text, job_title, question_type)
                questions.extend(new_questions)
                
                # If we got enough questions, break early
                if len(questions) >= count:
                    break
            
            except Exception as e:
                logger.warning(f"Attempt {attempt} error: {str(e)}")
                if attempt == max_attempts:
                    logger.error(f"All {max_attempts} attempts failed for {job_title}")
        
        return questions

    def _build_simplified_prompt(self, job_title: str, count: int, question_type: str) -> str:
        """Build a simplified prompt for Gemini AI when standard prompt fails.
        
        Args:
            job_title: The position title
            count: Number of questions to generate
            question_type: Type of questions
            
        Returns:
            Simplified prompt string
        """
        return f"""
Generate {count} interview questions for a {job_title} position.
Make them {question_type} questions.
Return ONLY a valid JSON array like this:
[{{"question": "Question text here", "type": "{question_type if question_type != 'mixed' else 'technical'}", "difficulty": 3, "tags": "relevant,tags"}}]
"""
        
    def _build_prompt(self, job_title: str, count: int, question_type: str) -> str:
        """Build standard prompt for Gemini AI.
        
        Args:
            job_title: The position title
            count: Number of questions to generate
            question_type: Type of questions
            
        Returns:
            Detailed prompt string
        """
        if question_type == "technical":
            focus = "technical skills, coding problems, system design, and domain-specific knowledge"
            instruction = "Ensure questions are technically relevant to the specific role and include problems that test their expertise."
        elif question_type == "behavioral":
            focus = "soft skills, past experiences, teamwork, leadership, and problem-solving scenarios"
            instruction = "Create scenario-based questions that reveal how the candidate handles real workplace situations."
        else:
            focus = "a mix of technical skills and behavioral aspects"
            instruction = "Balance technical and behavioral questions to assess both skills and cultural fit."

        return f"""
You are an expert technical interviewer with deep knowledge of {job_title} roles.

Task: Generate {count} high-quality, realistic interview questions for a {job_title} position.
Focus on {focus}.

{instruction}

Include a range of difficulty levels (1-5 scale) where:
- Level 1: Entry-level/basic knowledge questions
- Level 3: Mid-level experience questions 
- Level 5: Senior/expert level questions

Format your response as a well-formed JSON array ONLY with this structure:
[
  {{
    "question": "Your detailed question here...",
    "type": "{question_type if question_type != 'mixed' else 'technical or behavioral'}",
    "difficulty": number between 1-5,
    "tags": "comma,separated,relevant,keywords"
  }}
]

Do not include any explanations, markdown formatting, or additional text outside of the JSON array.
"""

    def _parse_response(
        self,
        response_text: str,
        job_title: str,
        question_type: str
    ) -> List[Dict]:
        """Parse Gemini response and extract questions.
        
        Tries JSON parsing first with fallback to text parsing for robustness.
        
        Args:
            response_text: The raw response from Gemini
            job_title: The position title
            question_type: Type of questions
            
        Returns:
            List of formatted question dictionaries
        """
        try:
            # First try to parse as JSON
            questions = self._try_parse_json(response_text, job_title, question_type)
            
            # If JSON parsing succeeded, return results
            if questions:
                return questions
            
            # Fallback to text parsing
            logger.info("JSON parsing failed, attempting text parsing")
            questions = self._try_parse_text(response_text, job_title, question_type)
            return questions
        
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            return []
        
    def _try_parse_json(
        self,
        response_text: str,
        job_title: str,
        question_type: str
    ) -> List[Dict]:
        """Try to parse response as JSON.
        
        Args:
            response_text: The raw response text
            job_title: The position title
            question_type: Type of questions
            
        Returns:
            List of question dictionaries if successful, empty list otherwise
        """
        questions = []
        
        try:
            # Clean up response text to extract JSON
            cleaned_text = self._extract_json_from_response(response_text)
            
            if not cleaned_text:
                logger.debug("Could not extract JSON from response")
                return []
            
            # Try to find and parse the JSON array
            start_idx = cleaned_text.find('[')
            end_idx = cleaned_text.rfind(']') + 1
            
            if start_idx == -1 or end_idx <= start_idx:
                logger.debug("No JSON array found in response")
                return []
            
            json_str = cleaned_text[start_idx:end_idx]
            
            # Attempt to parse the JSON
            questions_data = json.loads(json_str)
            
            if not isinstance(questions_data, list):
                logger.warning("JSON is not a list")
                return []
            
            # Process each question
            for q in questions_data:
                if isinstance(q, dict) and "question" in q:
                    question = self._format_question(q, job_title, question_type)
                    if question:
                        questions.append(question)
            
            logger.info(f"Successfully parsed {len(questions)} questions from JSON")
        
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parsing error: {str(e)}")
        except Exception as e:
            logger.debug(f"Unexpected error parsing JSON: {str(e)}")
        
        return questions
    
    @staticmethod
    def _extract_json_from_response(response_text: str) -> str:
        """Extract JSON content from response with markdown cleanup.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Cleaned text with markdown markers removed
        """
        cleaned = response_text.strip()
        
        # Remove markdown code block markers
        markers = ["```json", "```"]
        for marker in markers:
            if cleaned.startswith(marker):
                cleaned = cleaned.replace(marker, "", 1)
            if cleaned.endswith("```"):
                cleaned = cleaned[:cleaned.rfind("```")]
        
        return cleaned.strip()
        
    def _format_question(
        self,
        question_data: Dict,
        job_title: str,
        question_type: str
    ) -> Optional[Dict]:
        """Format and validate a question from parsed data.
        
        Args:
            question_data: Raw question data from response
            job_title: The position title
            question_type: Type of questions
            
        Returns:
            Formatted question dictionary, or None if invalid
        """
        try:
            # Validate question text
            question_text = question_data.get("question", "").strip()
            if not question_text:
                logger.debug("Question text is empty")
                return None
            
            # Determine question type
            q_type = self._determine_question_type(question_data, question_type)
            
            # Extract and validate difficulty
            difficulty = self._extract_difficulty(question_data)
            
            # Extract tags
            tags = question_data.get("tags", "").strip()
            if not tags:
                tags = job_title.lower().replace(" ", ",")
            
            return {
                "job_title": job_title,
                "question_text": question_text,
                "question_type": q_type,
                "difficulty": difficulty,
                "tags": tags
            }
        
        except Exception as e:
            logger.debug(f"Error formatting question: {str(e)}")
            return None
    
    @staticmethod
    def _determine_question_type(question_data: Dict, requested_type: str) -> str:
        """Determine appropriate question type.
        
        Args:
            question_data: Question data from response
            requested_type: Requested question type
            
        Returns:
            Validated question type
        """
        if requested_type != "mixed":
            return requested_type
        
        # Use type from response if available
        q_type = question_data.get("type", "technical")
        
        # Validate type
        if q_type not in {'technical', 'behavioral'}:
            return 'technical'
        
        return q_type
    
    @staticmethod
    def _extract_difficulty(question_data: Dict) -> int:
        """Extract and validate difficulty level.
        
        Args:
            question_data: Question data from response
            
        Returns:
            Difficulty level between 1 and 5
        """
        try:
            difficulty = int(question_data.get("difficulty", GeminiService.DEFAULT_DIFFICULTY))
            return max(
                GeminiService.MIN_DIFFICULTY,
                min(difficulty, GeminiService.MAX_DIFFICULTY)
            )
        except (ValueError, TypeError):
            return GeminiService.DEFAULT_DIFFICULTY
        
    def _try_parse_text(
        self,
        response_text: str,
        job_title: str,
        question_type: str
    ) -> List[Dict]:
        """Parse response as plain text when JSON parsing fails.
        
        Args:
            response_text: The raw response text
            job_title: The position title
            question_type: Type of questions
            
        Returns:
            List of question dictionaries
        """
        questions = []
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if line is a question
            if not self._is_question_line(line):
                continue
            
            # Clean up question format
            question_text = self._clean_question_text(line)
            
            # Create question from text
            question = self._create_text_question(question_text, job_title, question_type)
            if question:
                questions.append(question)
        
        logger.info(f"Parsed {len(questions)} questions from text")
        return questions
    
    @staticmethod
    def _is_question_line(line: str) -> bool:
        """Check if a line appears to be a question.
        
        Args:
            line: Line to check
            
        Returns:
            True if line looks like a question
        """
        if '?' in line:
            return True
        
        if line.startswith(('Q:', 'Q1:', 'Q2:', 'Q3:', 'Q4:', 'Q5:', '-')):
            return True
        
        if line.startswith(('Question 1:', 'Question 2:')):
            return True
        
        # Check for numbered format "1. " or "1) "
        if line and line[0].isdigit() and len(line) > 2:
            if line[1:3] in ('. ', ') '):
                return True
        
        return False
    
    @staticmethod
    def _clean_question_text(line: str) -> str:
        """Clean up question format by removing prefixes.
        
        Args:
            line: Raw line from response
            
        Returns:
            Cleaned question text
        """
        # Remove "Q:" or "Question:" prefixes
        if ':' in line:
            parts = line.split(':', 1)
            if parts[0].strip().lower().startswith(('q', 'question')):
                return parts[1].strip()
        
        # Remove dash prefix
        if line.startswith('-'):
            return line[1:].strip()
        
        # Remove numbered prefix "1. " or "1) "
        if line and line[0].isdigit() and len(line) > 2 and line[1:3] in ('. ', ') '):
            space_idx = line.find(' ')
            if space_idx > 0:
                return line[space_idx + 1:].strip()
        
        return line
        
    def _create_text_question(
        self,
        question_text: str,
        job_title: str,
        question_type: str
    ) -> Optional[Dict]:
        """Create a question from plain text format.
        
        Args:
            question_text: The extracted question text
            job_title: The position title
            question_type: Type of questions
            
        Returns:
            Formatted question dictionary, or None if invalid
        """
        try:
            if not question_text or not question_text.strip():
                return None
            
            # Determine question type
            q_type = self._infer_question_type(question_text, question_type)
            
            # Estimate difficulty based on content
            difficulty = self._infer_difficulty(question_text)
            
            # Generate tags based on keywords
            tags = self._generate_tags(question_text, job_title)
            
            return {
                "job_title": job_title,
                "question_text": question_text.strip(),
                "question_type": q_type,
                "difficulty": difficulty,
                "tags": tags
            }
        
        except Exception as e:
            logger.debug(f"Error creating text question: {str(e)}")
            return None
    
    @staticmethod
    def _infer_question_type(question_text: str, requested_type: str) -> str:
        """Infer question type from content if type is 'mixed'.
        
        Args:
            question_text: The question text
            requested_type: Requested question type
            
        Returns:
            Inferred question type
        """
        if requested_type != "mixed":
            return requested_type
        
        # Keywords that suggest behavioral questions
        behavioral_keywords = {
            'experience', 'team', 'conflict', 'leadership',
            'challenge', 'difficult', 'situation', 'example',
            'disagree', 'feedback', 'mistake', 'proud',
            'improve', 'strength', 'weakness', 'worked with'
        }
        
        text_lower = question_text.lower()
        if any(keyword in text_lower for keyword in behavioral_keywords):
            return "behavioral"
        
        return "technical"
    
    @staticmethod
    def _infer_difficulty(question_text: str) -> int:
        """Estimate difficulty level based on question content.
        
        Args:
            question_text: The question text
            
        Returns:
            Estimated difficulty level
        """
        text_lower = question_text.lower()
        word_count = len(question_text.split())
        
        # Advanced/Senior indicators
        if any(kw in text_lower for kw in ['senior', 'advanced', 'complex', 'architecture', 'design']):
            return GeminiService.MAX_DIFFICULTY
        
        # Entry-level indicators
        if any(kw in text_lower for kw in ['basic', 'simple', 'beginner', 'fundamental']):
            return 2
        
        # Longer questions tend to be more complex
        if word_count > 25:
            return 4
        
        return GeminiService.DEFAULT_DIFFICULTY
    
    @staticmethod
    def _generate_tags(question_text: str, job_title: str) -> str:
        """Generate tags based on keywords in question and job title.
        
        Args:
            question_text: The question text
            job_title: The job title
            
        Returns:
            Comma-separated tags
        """
        tags = job_title.lower().replace(" ", ",")
        
        # Keywords to extract as tags
        keywords = {
            'design', 'algorithm', 'data structure', 'architecture',
            'database', 'performance', 'scalability', 'leadership',
            'teamwork', 'communication', 'problem-solving', 'api',
            'testing', 'deployment', 'security', 'optimization'
        }
        
        text_lower = question_text.lower()
        additional_tags = []
        
        for keyword in keywords:
            if keyword in text_lower:
                additional_tags.append(keyword.replace(" ", "_"))
        
        if additional_tags:
            tags += ',' + ','.join(additional_tags)
        
        return tags


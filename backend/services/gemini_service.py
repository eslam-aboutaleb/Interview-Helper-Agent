import google.generativeai as genai
import os
import json
import logging
from typing import List, Dict
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class GeminiService:
    def __init__(self):
        """Initialize Gemini service and configure the API connection."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your-gemini-api-key":
            logger.warning("GEMINI_API_KEY not set or using placeholder value.")
        
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Try to initialize with the best available model
        try:
            # Try the updated model naming
            self.model = genai.GenerativeModel('gemini-1.5-pro')
            logger.info("Using gemini-1.5-pro model")
        except Exception:
            try:
                # Try the original model name
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("Using gemini-pro model")
            except Exception:
                # Last resort - use whatever model is available
                try:
                    available_models = genai.list_models()
                    for model in available_models:
                        if "gemini" in model.name.lower() and "pro" in model.name.lower():
                            logger.info(f"Using available model: {model.name}")
                            self.model = genai.GenerativeModel(model.name)
                            break
                    else:
                        # If no Gemini models found, raise error
                        raise Exception("No Gemini Pro models available in your API key")
                except Exception as e:
                    logger.error(f"Error finding available models: {e}")
                    raise Exception("Failed to initialize any Gemini model")

    def generate_questions(self, job_title: str, count: int = 5, question_type: str = "mixed") -> List[Dict]:
        """Generate interview questions using Gemini AI.
        
        Args:
            job_title: The position title to generate questions for
            count: Number of questions to generate
            question_type: Type of questions (technical, behavioral, or mixed)
            
        Returns:
            List of question dictionaries with formatted fields
            
        Raises:
            Exception: If generation fails after multiple attempts
        """
        logger.info(f"Generating {count} {question_type} questions for {job_title}")
        
        try:
            # First attempt with standard prompt
            questions = self._attempt_question_generation(
                job_title, count, question_type, is_simplified=False)
            
            # If we didn't get enough questions, try with simplified prompt
            remaining = count - len(questions)
            if remaining > 0:
                logger.info(f"First attempt yielded {len(questions)}/{count} questions. Trying with simplified prompt.")
                additional_questions = self._attempt_question_generation(
                    job_title, remaining, question_type, is_simplified=True)
                questions.extend(additional_questions)
            
            # Return questions, limited to requested count
            if questions:
                logger.info(f"Generated {len(questions)} questions successfully")
                return questions[:count]
            else:
                raise Exception("Failed to generate any valid questions after multiple attempts")
            
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            raise Exception(f"Failed to generate questions: {e}")
            
    def _attempt_question_generation(self, job_title: str, count: int, 
                                    question_type: str, is_simplified: bool = False,
                                    max_attempts: int = 2) -> List[Dict]:
        """Make multiple attempts to generate questions.
        
        Args:
            job_title: The position title
            count: Number of questions needed
            question_type: Type of questions
            is_simplified: Whether to use simplified prompt
            max_attempts: Maximum number of generation attempts
            
        Returns:
            List of generated question dictionaries
        """
        questions = []
        attempt = 0
        
        while len(questions) < count and attempt < max_attempts:
            attempt += 1
            try:
                # Build appropriate prompt
                if is_simplified:
                    prompt = self._build_simplified_prompt(job_title, count, question_type)
                else:
                    prompt = self._build_prompt(job_title, count, question_type)
                
                # Configure generation parameters
                temperature = 0.5 if attempt > 1 else 0.7  # Reduce temperature on retry
                
                # Generate content
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        top_p=0.95,
                        top_k=40,
                        max_output_tokens=4096,
                    )
                )
                
                # Parse response
                new_questions = self._parse_response(response.text, job_title, question_type)
                questions.extend(new_questions)
                
                # If we got enough questions, break early
                if len(questions) >= count:
                    break
                    
            except Exception as e:
                logger.warning(f"Error on attempt {attempt}: {e}")
        
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

    def _parse_response(self, response_text: str, job_title: str, question_type: str) -> List[Dict]:
        """Parse Gemini response and extract questions.
        
        This method tries to parse JSON first, and falls back to text parsing if needed.
        
        Args:
            response_text: The raw response from Gemini
            job_title: The position title
            question_type: Type of questions
            
        Returns:
            List of formatted question dictionaries
        """
        # First try to parse as JSON
        questions = self._try_parse_json(response_text, job_title, question_type)
        
        # If JSON parsing failed, try text parsing as fallback
        if not questions:
            logger.info("JSON parsing failed, attempting to parse as text")
            questions = self._try_parse_text(response_text, job_title, question_type)
            
        return questions
        
    def _try_parse_json(self, response_text: str, job_title: str, question_type: str) -> List[Dict]:
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
            cleaned_text = response_text.strip()
            
            # Remove markdown code block markers if present
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text.replace("```json", "", 1)
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text.replace("```", "", 1)
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:cleaned_text.rfind("```")]
                
            cleaned_text = cleaned_text.strip()
            
            # Try to find the JSON array
            start_idx = cleaned_text.find('[')
            end_idx = cleaned_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = cleaned_text[start_idx:end_idx]
                
                # Attempt to parse the JSON
                questions_data = json.loads(json_str)
                
                if isinstance(questions_data, list):
                    for q in questions_data:
                        if isinstance(q, dict) and "question" in q:
                            # Format the question data
                            question = self._format_question(q, job_title, question_type)
                            questions.append(question)
                
                logger.info(f"Successfully parsed {len(questions)} questions from JSON")
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error parsing response: {e}")
            
        return questions
        
    def _format_question(self, question_data: Dict, job_title: str, question_type: str) -> Dict:
        """Format and validate a question from parsed data.
        
        Args:
            question_data: Raw question data from response
            job_title: The position title
            question_type: Type of questions
            
        Returns:
            Formatted question dictionary
        """
        # For "mixed" type, use the type from the response
        q_type = question_data.get("type", "technical") 
        if question_type != "mixed":
            # Override with requested type if not mixed
            q_type = question_type
        
        # Validate type
        if q_type not in ["technical", "behavioral"]:
            q_type = "technical"
            
        # Extract and validate difficulty
        try:
            difficulty = int(question_data.get("difficulty", 3))
            difficulty = max(1, min(difficulty, 5))  # Ensure between 1-5
        except (ValueError, TypeError):
            difficulty = 3
        
        # Extract tags
        tags = question_data.get("tags", "")
        if not tags:
            tags = job_title.lower().replace(" ", ",")
        
        return {
            "job_title": job_title,
            "question_text": question_data.get("question", ""),
            "question_type": q_type,
            "difficulty": difficulty,
            "tags": tags
        }
        
    def _try_parse_text(self, response_text: str, job_title: str, question_type: str) -> List[Dict]:
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
                
            # Check for various question formats
            is_question_line = (
                ('?' in line) or 
                line.startswith('Q:') or 
                line.startswith('-') or
                (line[0].isdigit() and line[1:3] in ['. ', ') ']) or  # "1. " or "1) "
                any(line.startswith(prefix) for prefix in ['Q1:', 'Q2:', 'Q3:', 'Q4:', 'Q5:', 'Question 1:', 'Question 2:'])
            )
            
            if is_question_line:
                # Clean up question format
                if ':' in line and line.split(':', 1)[0].strip().lower().startswith(('q', 'question')):
                    line = line.split(':', 1)[1].strip()
                elif line.startswith('-'):
                    line = line[1:].strip()
                elif line[0].isdigit() and line[1:3] in ['. ', ') ']:
                    line = line[line.find(' ')+1:].strip()
                
                # Create question with appropriate type and difficulty
                question = self._create_text_question(line, job_title, question_type)
                questions.append(question)
        
        logger.info(f"Parsed {len(questions)} questions from text")
        return questions
        
    def _create_text_question(self, question_text: str, job_title: str, question_type: str) -> Dict:
        """Create a question from plain text format.
        
        Args:
            question_text: The extracted question text
            job_title: The position title
            question_type: Type of questions
            
        Returns:
            Formatted question dictionary
        """
        # Determine question type
        q_type = question_type
        if question_type == "mixed":
            # Try to determine type based on content
            behavioral_keywords = ['experience', 'team', 'conflict', 'leadership', 
                                  'challenge', 'difficult', 'situation', 'example',
                                  'disagree', 'feedback', 'mistake', 'proud',
                                  'improve', 'strength', 'weakness']
            
            if any(keyword in question_text.lower() for keyword in behavioral_keywords):
                q_type = "behavioral"
            else:
                q_type = "technical"
        
        # Estimate difficulty based on question complexity and length
        difficulty = 3  # Default medium difficulty
        if len(question_text.split()) > 25:  # Longer questions tend to be more complex
            difficulty = 4
        if any(keyword in question_text.lower() for keyword in ['senior', 'advanced', 'complex']):
            difficulty = 5
        if any(keyword in question_text.lower() for keyword in ['basic', 'simple', 'beginner']):
            difficulty = 2
        
        # Generate tags based on keywords in the question
        tags = job_title.lower().replace(' ', ',')
        keywords = ['design', 'algorithm', 'data structure', 'architecture', 
                   'database', 'performance', 'scalability', 'leadership',
                   'teamwork', 'communication', 'problem-solving']
        
        additional_tags = []
        for keyword in keywords:
            if keyword.lower() in question_text.lower():
                additional_tags.append(keyword.lower().replace(' ', '_'))
        
        if additional_tags:
            tags += ',' + ','.join(additional_tags)
        
        # Return formatted question
        return {
            "job_title": job_title,
            "question_text": question_text,
            "question_type": q_type,
            "difficulty": difficulty,
            "tags": tags
        }

    def _build_prompt(self, job_title: str, count: int, question_type: str) -> str:
        """Build prompt for Gemini AI"""
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

    def _parse_gemini_response(self, response_text: str, job_title: str, question_type: str) -> List[Dict]:
        """Parse Gemini response and extract questions"""
        questions = []
        
        try:
            # Clean up response text to extract JSON
            # Look for JSON array pattern [...]
            cleaned_text = response_text.strip()
            
            # Remove markdown code block markers if present
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text.replace("```json", "", 1)
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text.replace("```", "", 1)
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:cleaned_text.rfind("```")]
                
            cleaned_text = cleaned_text.strip()
            
            # Try to find the JSON array
            start_idx = cleaned_text.find('[')
            end_idx = cleaned_text.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = cleaned_text[start_idx:end_idx]
                
                # Attempt to parse the JSON
                questions_data = json.loads(json_str)
                
                if isinstance(questions_data, list):
                    for q in questions_data:
                        if isinstance(q, dict) and "question" in q:
                            # For "mixed" type, use the type from the response
                            q_type = q.get("type", "technical") 
                            if question_type != "mixed":
                                # Override with requested type if not mixed
                                q_type = question_type
                            
                            # Validate type
                            if q_type not in ["technical", "behavioral"]:
                                q_type = "technical"
                                
                            # Extract and validate difficulty
                            try:
                                difficulty = int(q.get("difficulty", 3))
                                difficulty = max(1, min(difficulty, 5))  # Ensure between 1-5
                            except (ValueError, TypeError):
                                difficulty = 3
                            
                            # Extract tags
                            tags = q.get("tags", "")
                            if not tags:
                                tags = job_title.lower().replace(" ", ",")
                            
                            questions.append({
                                "job_title": job_title,
                                "question_text": q.get("question", ""),
                                "question_type": q_type,
                                "difficulty": difficulty,
                                "tags": tags
                            })
                
                print(f"Successfully parsed {len(questions)} questions from JSON")
                return questions
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
        except Exception as e:
            print(f"Unexpected error parsing response: {e}")
        
        # If we get here, JSON parsing failed - try to parse as text
        print("JSON parsing failed, attempting to parse as text")
        return self._parse_text_response(response_text, job_title, question_type)

    def _parse_text_response(self, response_text: str, job_title: str, question_type: str) -> List[Dict]:
        """Parse text response when JSON parsing fails"""
        questions = []
        lines = response_text.split('\n')
        
        # Look for patterns like: "1. Question text", "Q1: Question text", etc.
        question_pattern = False
        current_question = ""
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check for various question formats
            is_question_line = (
                ('?' in line) or 
                line.startswith('Q:') or 
                line.startswith('-') or
                (line[0].isdigit() and line[1:3] in ['. ', ') ']) or  # "1. " or "1) "
                any(line.startswith(prefix) for prefix in ['Q1:', 'Q2:', 'Q3:', 'Q4:', 'Q5:', 'Question 1:', 'Question 2:'])
            )
            
            if is_question_line:
                # Clean up question format
                if ':' in line and line.split(':', 1)[0].strip().lower().startswith(('q', 'question')):
                    line = line.split(':', 1)[1].strip()
                elif line.startswith('-'):
                    line = line[1:].strip()
                elif line[0].isdigit() and line[1:3] in ['. ', ') ']:
                    line = line[line.find(' ')+1:].strip()
                
                # Determine question type
                q_type = question_type
                if question_type == "mixed":
                    # Try to determine type based on content
                    behavioral_keywords = ['experience', 'team', 'conflict', 'leadership', 
                                          'challenge', 'difficult', 'situation', 'example',
                                          'disagree', 'feedback', 'mistake', 'proud',
                                          'improve', 'strength', 'weakness']
                    
                    if any(keyword in line.lower() for keyword in behavioral_keywords):
                        q_type = "behavioral"
                    else:
                        q_type = "technical"
                
                # Estimate difficulty based on question complexity and length
                difficulty = 3  # Default medium difficulty
                if len(line.split()) > 25:  # Longer questions tend to be more complex
                    difficulty = 4
                if 'senior' in line.lower() or 'advanced' in line.lower() or 'complex' in line.lower():
                    difficulty = 5
                if 'basic' in line.lower() or 'simple' in line.lower() or 'beginner' in line.lower():
                    difficulty = 2
                
                # Generate tags based on keywords in the question
                tags = job_title.lower().replace(' ', ',')
                keywords = ['design', 'algorithm', 'data structure', 'architecture', 
                           'database', 'performance', 'scalability', 'leadership',
                           'teamwork', 'communication', 'problem-solving']
                
                additional_tags = []
                for keyword in keywords:
                    if keyword.lower() in line.lower():
                        additional_tags.append(keyword.lower().replace(' ', '_'))
                
                if additional_tags:
                    tags += ',' + ','.join(additional_tags)
                
                # Add the question
                questions.append({
                    "job_title": job_title,
                    "question_text": line,
                    "question_type": q_type,
                    "difficulty": difficulty,
                    "tags": tags
                })
        
        print(f"Parsed {len(questions)} questions from text")
        return questions

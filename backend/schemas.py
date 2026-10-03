from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime


class QuestionBase(BaseModel):
    """Shared fields for creating and updating interview questions.

    Declares the common validation rules (length limits, allowed
    characters, difficulty range) that the create and update schemas
    inherit.
    """

    job_title: str = Field(
        ..., min_length=2, max_length=100, description="Job title for the question", example="Senior Software Engineer"
    )
    question_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The interview question text",
        example="Describe your experience with system design",
    )
    question_type: str = Field(..., description="Type: 'technical' or 'behavioral'", example="technical")
    difficulty: Optional[int] = Field(1, ge=1, le=5, description="Difficulty level 1-5")
    is_flagged: Optional[bool] = Field(False, description="Whether question is flagged")
    tags: Optional[str] = Field(
        None, max_length=500, description="Comma-separated tags", example="python,design,scalability"
    )

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        """Validate and clean job title"""
        if not v or not v.strip():
            raise ValueError("job_title cannot be empty")

        v = v.strip()
        if len(v) < 2:
            raise ValueError("job_title must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("job_title must not exceed 100 characters")

        # Check for invalid characters
        if not all(c.isalnum() or c.isspace() or c in ["-", "+", ".", "#"] for c in v):
            raise ValueError("job_title contains invalid characters")

        return v

    @field_validator("question_text")
    @classmethod
    def validate_question_text(cls, v: str) -> str:
        """Validate and clean question text"""
        if not v or not v.strip():
            raise ValueError("question_text cannot be empty")

        v = v.strip()
        if len(v) < 10:
            raise ValueError("question_text must be at least 10 characters")
        if len(v) > 2000:
            raise ValueError("question_text must not exceed 2000 characters")

        return v

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: str) -> str:
        """Validate question type"""
        valid_types = {"technical", "behavioral", "mixed"}
        if v.lower() not in valid_types:
            raise ValueError(f"question_type must be one of {valid_types}")

        return v.lower()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean tags"""
        if v is None:
            return None

        if not v.strip():
            return None

        v = v.strip()
        if len(v) > 500:
            raise ValueError("tags must not exceed 500 characters")

        # Validate tag format (comma-separated alphanumeric)
        tags_list = [tag.strip() for tag in v.split(",")]
        invalid_tags = [tag for tag in tags_list if not all(c.isalnum() or c in ["_", "-"] for c in tag)]

        if invalid_tags:
            raise ValueError(
                f"Invalid tag format: {invalid_tags}. Tags must be alphanumeric with underscores or dashes"
            )

        return ",".join(tags_list)


class QuestionCreate(QuestionBase):
    """Schema for creating a new question"""

    pass


class QuestionUpdate(BaseModel):
    """Schema for updating a question - all fields optional"""

    difficulty: Optional[int] = Field(None, ge=1, le=5, description="Difficulty level 1-5")
    is_flagged: Optional[bool] = Field(None, description="Whether question is flagged")
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated tags")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean tags"""
        if v is None:
            return None

        if not v.strip():
            return None

        v = v.strip()
        if len(v) > 500:
            raise ValueError("tags must not exceed 500 characters")

        # Validate tag format
        tags_list = [tag.strip() for tag in v.split(",")]
        invalid_tags = [tag for tag in tags_list if not all(c.isalnum() or c in ["_", "-"] for c in tag)]

        if invalid_tags:
            raise ValueError(f"Invalid tag format: {invalid_tags}")

        return ",".join(tags_list)


class Question(QuestionBase):
    """Schema for a question with database-generated fields"""

    id: int = Field(..., gt=0, description="Question ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class QuestionGenerateRequest(BaseModel):
    """Schema for requesting AI-generated questions"""

    job_title: str = Field(
        ..., min_length=2, max_length=100, description="Job title to generate questions for", example="Backend Engineer"
    )
    count: Optional[int] = Field(5, ge=1, le=100, description="Number of questions to generate (1-100)")
    question_type: Optional[str] = Field(
        "mixed", description="'technical', 'behavioral', or 'mixed'", example="technical"
    )

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        """Validate job title"""
        if not v or not v.strip():
            raise ValueError("job_title cannot be empty")

        v = v.strip()
        if len(v) < 2:
            raise ValueError("job_title must be at least 2 characters")

        return v

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: Optional[int]) -> Optional[int]:
        """Validate count"""
        if v is None:
            return 5

        if v < 1:
            raise ValueError("count must be at least 1")
        if v > 100:
            raise ValueError("count cannot exceed 100")

        return v

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate question type"""
        if v is None:
            return "mixed"

        valid_types = {"technical", "behavioral", "mixed"}
        if v.lower() not in valid_types:
            raise ValueError(f"question_type must be one of {valid_types}")

        return v.lower()


class QuestionSetCreate(BaseModel):
    """Schema for creating a new question set"""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Name of the question set", example="Python Interview Questions"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Description of the question set",
        example="A comprehensive set of Python interview questions for backend roles",
    )
    job_title: str = Field(
        ..., min_length=2, max_length=100, description="Job title for the question set", example="Python Developer"
    )
    question_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of question IDs to include (1-1000 questions)",
        example=[1, 2, 3, 4, 5],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate set name"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")

        v = v.strip()
        if len(v) > 200:
            raise ValueError("name must not exceed 200 characters")

        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate set description"""
        if v is None:
            return None

        if not v.strip():
            return None

        v = v.strip()
        if len(v) > 1000:
            raise ValueError("description must not exceed 1000 characters")

        return v

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        """Validate job title"""
        if not v or not v.strip():
            raise ValueError("job_title cannot be empty")

        v = v.strip()
        if len(v) < 2:
            raise ValueError("job_title must be at least 2 characters")

        return v

    @field_validator("question_ids")
    @classmethod
    def validate_question_ids(cls, v: List[int]) -> List[int]:
        """Validate question IDs"""
        if not v:
            raise ValueError("question_ids cannot be empty")

        if len(v) > 1000:
            raise ValueError("question_ids cannot contain more than 1000 questions")

        # Check for valid IDs
        invalid_ids = [qid for qid in v if not isinstance(qid, int) or qid <= 0]
        if invalid_ids:
            raise ValueError(f"Invalid question IDs: {invalid_ids}. All IDs must be positive integers")

        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("question_ids contains duplicate values")

        return v


class QuestionSet(BaseModel):
    """Schema for a question set with database-generated fields"""

    id: int = Field(..., gt=0, description="Question Set ID")
    name: str = Field(..., description="Name of the question set")
    description: Optional[str] = Field(None, description="Description of the question set")
    job_title: str = Field(..., description="Job title for the question set")
    question_ids: str = Field(..., description="JSON string of question IDs")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserRatingCreate(BaseModel):
    """Schema for creating a new rating"""

    question_id: int = Field(..., gt=0, description="ID of the question being rated", example=1)
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0", example=4.5)
    feedback: Optional[str] = Field(
        None, max_length=1000, description="Optional feedback text", example="Great question, very practical"
    )

    @field_validator("question_id")
    @classmethod
    def validate_question_id(cls, v: int) -> int:
        """Validate question ID"""
        if v <= 0:
            raise ValueError("question_id must be a positive integer")

        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: float) -> float:
        """Validate rating value"""
        if v < 1.0 or v > 5.0:
            raise ValueError("rating must be between 1.0 and 5.0")

        return round(v, 1)  # Round to 1 decimal place

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: Optional[str]) -> Optional[str]:
        """Validate feedback text"""
        if v is None:
            return None

        if not v.strip():
            return None

        v = v.strip()
        if len(v) > 1000:
            raise ValueError("feedback must not exceed 1000 characters")

        return v


class UserRating(BaseModel):
    """Schema for a rating with database-generated fields"""

    id: int = Field(..., gt=0, description="Rating ID")
    question_id: int = Field(..., gt=0, description="ID of the rated question")
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating value between 1.0 and 5.0")
    feedback: Optional[str] = Field(None, description="User feedback text")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: str = Field(..., min_length=3, max_length=255, description="User email", example="user@example.com")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    full_name: Optional[str] = Field(None, max_length=200, description="Display name")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize the email to lowercase and require an ``@``."""
        v = v.strip().lower()
        if "@" not in v:
            raise ValueError("email must contain @")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    email: str = Field(..., min_length=3, max_length=255, description="User email")
    password: str = Field(..., min_length=1, description="User password")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize the email to lowercase."""
        return v.strip().lower()


class UserResponse(BaseModel):
    """Schema for a user without sensitive fields."""

    id: int = Field(..., gt=0, description="User ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="Display name")
    role: str = Field(..., description="Access role: 'user' or 'admin'")
    is_active: bool = Field(..., description="Whether the account is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for an authentication token response."""

    token: str = Field(..., description="Session token")
    user: UserResponse = Field(..., description="Authenticated user")


class AdminUserUpdate(BaseModel):
    """Schema for admin updates to a user account."""

    role: Optional[str] = Field(None, description="New role: 'user' or 'admin'")
    is_active: Optional[bool] = Field(None, description="Whether the account is active")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate the role value."""
        if v is None:
            return None
        v = v.strip().lower()
        if v not in {"user", "admin"}:
            raise ValueError("role must be 'user' or 'admin'")
        return v


class AdminStatsResponse(BaseModel):
    """Schema for the admin platform overview."""

    total_users: int = Field(..., ge=0, description="Total registered users")
    active_users: int = Field(..., ge=0, description="Users with active accounts")
    admin_count: int = Field(..., ge=0, description="Users with the admin role")
    total_questions: int = Field(..., ge=0, description="Total questions in the bank")
    flagged_questions: int = Field(..., ge=0, description="Questions flagged for review")
    total_documents: int = Field(..., ge=0, description="Uploaded resumes/JDs")
    total_interview_sessions: int = Field(..., ge=0, description="Mock interview sessions")
    completed_sessions: int = Field(..., ge=0, description="Completed interview sessions")
    total_evaluations: int = Field(..., ge=0, description="Answer evaluations recorded")
    average_score: Optional[float] = Field(None, description="Mean overall evaluation score")
    recent_users: int = Field(..., ge=0, description="Users registered in the last 7 days")


class QuestionHistoryResponse(BaseModel):
    """Schema for a question history entry."""

    id: int = Field(..., gt=0, description="History entry ID")
    user_id: Optional[int] = Field(None, description="ID of the acting user")
    question_id: Optional[int] = Field(None, description="ID of the related question")
    action: str = Field(..., description="Action performed")
    context: Optional[dict] = Field(None, description="Additional context")
    created_at: datetime = Field(..., description="Action timestamp")

    model_config = ConfigDict(from_attributes=True)


class UserDocumentCreate(BaseModel):
    """Schema for uploading a document (metadata only; content is multipart)."""

    document_type: str = Field(..., description="'resume' or 'jd'")
    filename: str = Field(..., max_length=255, description="Original filename")

    @field_validator("document_type")
    @classmethod
    def validate_document_type(cls, v: str) -> str:
        """Restrict the document type to ``resume`` or ``jd``."""
        v = v.strip().lower()
        if v not in {"resume", "jd"}:
            raise ValueError("document_type must be 'resume' or 'jd'")
        return v


class UserDocumentResponse(BaseModel):
    """Schema for a stored document."""

    id: int = Field(..., gt=0, description="Document ID")
    user_id: int = Field(..., description="Owning user ID")
    document_type: str = Field(..., description="'resume' or 'jd'")
    filename: Optional[str] = Field(None, description="Original filename")
    parsed_metadata: Optional[dict] = Field(None, description="Extracted structured data")
    created_at: datetime = Field(..., description="Upload timestamp")

    model_config = ConfigDict(from_attributes=True)


class SkillGapResponse(BaseModel):
    """Schema for a resume-vs-JD skill gap analysis."""

    match_percentage: float = Field(..., ge=0, le=100, description="Match percentage")
    matched_skills: list[str] = Field(..., description="Skills present in both")
    missing_skills: list[str] = Field(..., description="Required skills missing from resume")
    extra_skills: list[str] = Field(..., description="Resume skills not required")
    summary: str = Field(..., description="Human-readable summary")


class InterviewSessionCreate(BaseModel):
    """Schema for starting a mock interview."""

    job_title: str = Field(..., min_length=2, max_length=100, description="Target role")
    session_type: str = Field("mixed", description="'technical', 'behavioral', or 'mixed'")
    difficulty: int = Field(3, ge=1, le=5, description="Starting difficulty (1-5)")
    max_turns: int = Field(7, ge=1, le=20, description="Number of questions")
    document_id: Optional[int] = Field(None, description="Resume/JD document ID")

    @field_validator("session_type")
    @classmethod
    def validate_session_type(cls, v: str) -> str:
        """Restrict the session type to technical, behavioral, or mixed."""
        v = v.strip().lower()
        if v not in {"technical", "behavioral", "mixed"}:
            raise ValueError("session_type must be 'technical', 'behavioral', or 'mixed'")
        return v


class InterviewSessionResponse(BaseModel):
    """Schema for an interview session."""

    id: int = Field(..., gt=0, description="Session ID")
    user_id: int = Field(..., description="User ID")
    job_title: str = Field(..., description="Target role")
    session_type: str = Field(..., description="Session type")
    difficulty: int = Field(..., ge=1, le=5, description="Current difficulty")
    target_difficulty: int = Field(..., ge=1, le=5, description="Starting difficulty")
    status: str = Field(..., description="'active' or 'completed'")
    current_turn: int = Field(..., ge=0, description="Questions asked so far")
    max_turns: int = Field(..., ge=1, le=20, description="Total questions")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    model_config = ConfigDict(from_attributes=True)


class InterviewAnswerRequest(BaseModel):
    """Schema for submitting a candidate answer."""

    answer: str = Field(..., min_length=1, max_length=10000, description="Candidate's answer")


class InterviewTurnResponse(BaseModel):
    """Schema for the result of one interview turn."""

    completed: bool = Field(..., description="Whether the session ended")
    next_question: Optional[str] = Field(None, description="Next interviewer question")
    evaluation: dict = Field(..., description="Scoring and feedback for the answer")
    current_difficulty: Optional[int] = Field(None, description="Adapted difficulty")
    turn: Optional[int] = Field(None, description="Current turn number")
    summary: Optional[dict] = Field(None, description="Final summary when completed")


class InterviewMessageResponse(BaseModel):
    """Schema for an interview message."""

    id: int = Field(..., gt=0, description="Message ID")
    session_id: int = Field(..., description="Parent session ID")
    role: str = Field(..., description="'interviewer', 'candidate', or 'system'")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class AnswerEvaluationResponse(BaseModel):
    """Schema for a stored answer evaluation."""

    id: int = Field(..., gt=0, description="Evaluation ID")
    session_id: int = Field(..., description="Parent session ID")
    overall_score: float = Field(..., ge=0, le=10, description="Overall score (0-10)")
    technical_score: float = Field(..., ge=0, le=10, description="Technical score")
    communication_score: float = Field(..., ge=0, le=10, description="Communication score")
    completeness_score: float = Field(..., ge=0, le=10, description="Completeness score")
    feedback: Optional[dict] = Field(None, description="Strengths, gaps, tips")
    next_action: Optional[str] = Field(None, description="Orchestrator directive")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class ModelAnswerRequest(BaseModel):
    """Schema for requesting a model answer."""

    question: str = Field(..., min_length=10, max_length=2000, description="Question text")
    question_type: str = Field("technical", description="'technical' or 'behavioral'")

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: str) -> str:
        """Restrict the question type to technical or behavioral."""
        v = v.strip().lower()
        if v not in {"technical", "behavioral"}:
            raise ValueError("question_type must be 'technical' or 'behavioral'")
        return v


class ModelAnswerResponse(BaseModel):
    """Schema for a model answer response."""

    question: str = Field(..., description="The question")
    model_answer: Optional[str] = Field(None, description="AI-generated model answer")


class StatsResponse(BaseModel):
    """Schema for platform statistics response"""

    # Time-series helpers for the dashboard charts. Bucket keys are always
    # ``YYYY-MM-DD`` strings so the payload is identical whether the underlying
    # bucket expression returned a PostgreSQL timestamptz or SQLite text.
    class DailyCount(BaseModel):
        """One day of a daily count series."""

        date: str = Field(..., description="UTC calendar day the bucket covers (YYYY-MM-DD)", example="2026-10-03")
        count: int = Field(0, ge=0, description="Number of records in the bucket", example=7)

    class DailyEvaluationCount(BaseModel):
        """One day of the evaluation series, including the mean overall score."""

        date: str = Field(..., description="UTC calendar day the bucket covers (YYYY-MM-DD)", example="2026-10-03")
        average_score: Optional[float] = Field(
            None,
            ge=0.0,
            le=10.0,
            description="Mean overall score for the day, null when the day has no evaluations",
        )
        count: int = Field(0, ge=0, description="Number of evaluations recorded on the day", example=4)

    class DifficultyCount(BaseModel):
        """Question count for a single difficulty level."""

        difficulty: int = Field(..., ge=1, le=5, description="Difficulty level (1-5)", example=3)
        count: int = Field(0, ge=0, description="Questions recorded at this difficulty level", example=12)

    class WeeklyScore(BaseModel):
        """One ISO week of the average score trend."""

        week_start: str = Field(..., description="Monday starting the ISO week (YYYY-MM-DD)", example="2026-09-28")
        average_score: Optional[float] = Field(
            None,
            ge=0.0,
            le=10.0,
            description="Mean overall score for the week, null when the week has no evaluations",
        )
        count: int = Field(0, ge=0, description="Evaluations recorded during the week", example=9)

    total_questions: int = Field(..., ge=0, description="Total number of questions in the system", example=150)
    questions_by_type: dict = Field(
        ..., description="Count of questions grouped by type", example={"technical": 90, "behavioral": 60}
    )
    questions_by_job_title: dict = Field(
        ...,
        description="Count of questions grouped by job title",
        example={"Python Developer": 45, "Backend Engineer": 60},
    )
    average_difficulty: float = Field(
        ...,
        ge=0.0,
        le=5.0,
        description="Average difficulty level across all questions (0.0 when no questions exist)",
        example=3.2,
    )
    flagged_questions: int = Field(..., ge=0, description="Total number of flagged questions", example=5)
    total_question_sets: int = Field(..., ge=0, description="Total number of question sets", example=10)
    signups_last_7_days: List[DailyCount] = Field(
        default_factory=list,
        description="Signup counts for each of the last 7 days, zero-filled and ascending by date",
    )
    evaluations_last_7_days: List[DailyEvaluationCount] = Field(
        default_factory=list,
        description="Evaluation count and mean score for each of the last 7 days, zero-filled and ascending by date",
    )
    difficulty_distribution: List[DifficultyCount] = Field(
        default_factory=list,
        description="Question count per difficulty level, always one entry per level 1-5",
    )
    average_score_trend: List[WeeklyScore] = Field(
        default_factory=list,
        description=(
            "Mean overall score per ISO week over the last 8 weeks, ascending by week start. Empty when the "
            "window contains no evaluations."
        ),
    )

    @model_validator(mode="after")
    def validate_stats(self):
        """Validate statistics consistency"""
        if self.total_questions < 0:
            raise ValueError("total_questions cannot be negative")

        if self.flagged_questions < 0:
            raise ValueError("flagged_questions cannot be negative")

        if self.flagged_questions > self.total_questions:
            raise ValueError("flagged_questions cannot exceed total_questions")

        if self.total_question_sets < 0:
            raise ValueError("total_question_sets cannot be negative")

        return self

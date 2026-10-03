from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, CheckConstraint, Index, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import validates, relationship
from database import Base


class User(Base):
    """SQLAlchemy model for platform users."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True, comment="Unique user email address")
    hashed_password = Column(String(255), nullable=False, comment="Bcrypt hashed password")
    full_name = Column(String(200), nullable=True, comment="User display name")
    role = Column(
        String(20), nullable=False, default="user", server_default="user", comment="Access role: 'user' or 'admin'"
    )
    is_active = Column(Boolean, default=True, nullable=False, comment="Whether the account is active")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="Last update timestamp")
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment="Last successful login timestamp")

    __table_args__ = (
        CheckConstraint("LENGTH(email) <= 255", name="check_email_length"),
        CheckConstraint("role IN ('user', 'admin')", name="check_user_role"),
        Index("idx_users_email", "email", unique=True),
        Index("idx_users_created_at", "created_at"),
        Index("idx_users_role", "role"),
    )

    questions = relationship("Question", back_populates="user")
    history = relationship("QuestionHistory", back_populates="user")

    @property
    def is_admin(self) -> bool:
        """Whether the user holds the admin role."""
        return self.role == "admin"

    @validates("email")
    def validate_email(self, key, value):
        """Validate email before setting."""
        if not value or not str(value).strip():
            raise ValueError("email cannot be empty")
        value = str(value).strip().lower()
        if len(value) > 255:
            raise ValueError("email must not exceed 255 characters")
        if "@" not in value:
            raise ValueError("email must contain @")
        return value

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class UserSession(Base):
    """SQLAlchemy model for user sessions / auth tokens."""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the user who owns this session",
    )
    token_hash = Column(String(255), nullable=False, index=True, comment="Hashed session token")
    expires_at = Column(DateTime(timezone=True), nullable=False, comment="Session expiration timestamp")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )
    last_used_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Last time the session was used"
    )

    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_token_hash", "token_hash"),
        Index("idx_sessions_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id})>"


class UserDocument(Base):
    """SQLAlchemy model for uploaded resumes and job descriptions."""

    __tablename__ = "user_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the user who uploaded the document",
    )
    document_type = Column(String(20), nullable=False, comment="Type: 'resume' or 'jd'")
    filename = Column(String(255), nullable=True, comment="Original filename")
    content_text = Column(Text, nullable=False, comment="Extracted plain-text content")
    parsed_metadata = Column(JSON, nullable=True, comment="Structured data extracted from the document")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )

    __table_args__ = (
        CheckConstraint("document_type IN ('resume', 'jd')", name="check_document_type"),
        Index("idx_documents_user_id", "user_id"),
        Index("idx_documents_type", "document_type"),
    )

    user = relationship("User")

    @validates("document_type")
    def validate_document_type(self, key, value):
        valid = {"resume", "jd"}
        value = str(value).strip().lower()
        if value not in valid:
            raise ValueError(f"document_type must be one of {valid}")
        return value

    def __repr__(self):
        return f"<UserDocument(id={self.id}, user_id={self.user_id}, type='{self.document_type}')>"


class InterviewSession(Base):
    """SQLAlchemy model for a mock interview session."""

    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the user being interviewed",
    )
    job_title = Column(String(100), nullable=False, comment="Target job title")
    session_type = Column(
        String(20), nullable=False, default="mixed", comment="Type: 'technical', 'behavioral', or 'mixed'"
    )
    difficulty = Column(Integer, nullable=False, default=3, comment="Current adaptive difficulty (1-5)")
    target_difficulty = Column(Integer, nullable=False, default=3, comment="Starting difficulty chosen by the user")
    status = Column(String(20), nullable=False, default="active", comment="Status: 'active' or 'completed'")
    current_turn = Column(Integer, nullable=False, default=0, comment="Number of questions asked so far")
    max_turns = Column(Integer, nullable=False, default=7, comment="Maximum number of questions in the session")
    document_id = Column(
        Integer,
        ForeignKey("user_documents.id", ondelete="SET NULL"),
        nullable=True,
        comment="Resume/JD document used for personalization",
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="Last update timestamp")
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="Completion timestamp")

    __table_args__ = (
        CheckConstraint("session_type IN ('technical', 'behavioral', 'mixed')", name="check_session_type"),
        CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="check_session_difficulty"),
        CheckConstraint("status IN ('active', 'completed')", name="check_session_status"),
        Index("idx_interview_sessions_user_id", "user_id"),
        Index("idx_interview_sessions_status", "status"),
    )

    user = relationship("User")
    messages = relationship("InterviewMessage", back_populates="session", cascade="all, delete-orphan")
    evaluations = relationship("AnswerEvaluation", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<InterviewSession(id={self.id}, user_id={self.user_id}, status='{self.status}')>"


class InterviewMessage(Base):
    """SQLAlchemy model for a single message in an interview session."""

    __tablename__ = "interview_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the parent session",
    )
    role = Column(String(20), nullable=False, comment="Role: 'interviewer', 'candidate', or 'system'")
    content = Column(Text, nullable=False, comment="Message content")
    question_id = Column(Integer, nullable=True, comment="ID of the related question, if any")
    context = Column("metadata", JSON, nullable=True, comment="Additional context (scores, follow-ups)")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )

    __table_args__ = (
        CheckConstraint("role IN ('interviewer', 'candidate', 'system')", name="check_message_role"),
        Index("idx_messages_session_id", "session_id"),
    )

    session = relationship("InterviewSession", back_populates="messages")

    def __repr__(self):
        return f"<InterviewMessage(id={self.id}, session_id={self.session_id}, role='{self.role}')>"


class AnswerEvaluation(Base):
    """SQLAlchemy model for an AI evaluation of a candidate's answer."""

    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the parent session",
    )
    message_id = Column(Integer, nullable=True, comment="ID of the candidate message being evaluated")
    question_id = Column(Integer, nullable=True, comment="ID of the question being answered")
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the user who answered",
    )
    overall_score = Column(Float, nullable=False, comment="Overall score (0-10)")
    technical_score = Column(Float, nullable=False, default=0.0, comment="Technical correctness (0-10)")
    communication_score = Column(Float, nullable=False, default=0.0, comment="Communication clarity (0-10)")
    completeness_score = Column(Float, nullable=False, default=0.0, comment="STAR/completeness (0-10)")
    feedback = Column(JSON, nullable=True, comment="Structured feedback (strengths, gaps, tips)")
    model_answer = Column(Text, nullable=True, comment="AI-generated model answer for comparison")
    next_action = Column(
        String(30), nullable=True, comment="Orchestrator directive: probe_deeper, follow_up, move_on, redirect"
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )

    __table_args__ = (
        CheckConstraint("overall_score >= 0 AND overall_score <= 10", name="check_overall_score_range"),
        Index("idx_evaluations_session_id", "session_id"),
        Index("idx_evaluations_user_id", "user_id"),
    )

    session = relationship("InterviewSession", back_populates="evaluations")

    def __repr__(self):
        return f"<AnswerEvaluation(id={self.id}, session_id={self.session_id}, score={self.overall_score})>"


class QuestionHistory(Base):
    """SQLAlchemy model for tracking user interactions with questions."""

    __tablename__ = "question_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID of the user who performed the action",
    )
    question_id = Column(Integer, nullable=True, index=True, comment="ID of the question the action relates to")
    action = Column(
        String(50), nullable=False, comment="Action performed: generated, viewed, rated, flagged, created, deleted"
    )
    context = Column("metadata", JSON, nullable=True, comment="Additional context about the action")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Action timestamp")

    __table_args__ = (
        CheckConstraint(
            "action IN ('generated', 'viewed', 'rated', 'flagged', 'created', 'deleted')", name="check_history_action"
        ),
        Index("idx_history_user_id", "user_id"),
        Index("idx_history_question_id", "question_id"),
        Index("idx_history_action", "action"),
        Index("idx_history_created_at", "created_at"),
    )

    user = relationship("User", back_populates="history")

    @validates("action")
    def validate_action(self, key, value):
        """Validate action before setting."""
        valid_actions = {"generated", "viewed", "rated", "flagged", "created", "deleted"}
        value = str(value).strip().lower()
        if value not in valid_actions:
            raise ValueError(f"action must be one of {valid_actions}")
        return value

    def __repr__(self):
        return f"<QuestionHistory(id={self.id}, user_id={self.user_id}, action='{self.action}')>"


class Question(Base):
    """SQLAlchemy model for interview questions with validation constraints"""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="ID of the user who created this question",
    )
    job_title = Column(String(100), nullable=False, index=True, comment="Job title for the question (2-100 chars)")
    question_text = Column(Text, nullable=False, comment="The interview question text (10-2000 chars)")
    question_type = Column(String(50), nullable=False, comment="Type: 'technical', 'behavioral', or 'mixed'")
    difficulty = Column(Integer, default=1, nullable=False, comment="Difficulty level 1-5")
    is_flagged = Column(Boolean, default=False, nullable=False, comment="Whether question is flagged")
    tags = Column(String(500), nullable=True, comment="Comma-separated tags")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="Last update timestamp")

    # Add constraints at table level
    __table_args__ = (
        CheckConstraint("LENGTH(job_title) >= 2 AND LENGTH(job_title) <= 100", name="check_job_title_length"),
        CheckConstraint(
            "LENGTH(question_text) >= 10 AND LENGTH(question_text) <= 2000", name="check_question_text_length"
        ),
        CheckConstraint("question_type IN ('technical', 'behavioral', 'mixed')", name="check_question_type"),
        CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="check_difficulty_range"),
        Index("idx_job_title_type", "job_title", "question_type"),
        Index("idx_is_flagged", "is_flagged"),
        Index("idx_created_at", "created_at"),
        Index("idx_questions_user_id", "user_id"),
    )

    user = relationship("User", back_populates="questions")

    @validates("job_title")
    def validate_job_title(self, key, value):
        """Validate job title before setting"""
        if not value or not str(value).strip():
            raise ValueError("job_title cannot be empty")

        value = str(value).strip()
        if len(value) < 2:
            raise ValueError("job_title must be at least 2 characters")
        if len(value) > 100:
            raise ValueError("job_title must not exceed 100 characters")

        # Check for invalid characters
        if not all(c.isalnum() or c.isspace() or c in ["-", "+", ".", "#"] for c in value):
            raise ValueError("job_title contains invalid characters")

        return value

    @validates("question_text")
    def validate_question_text(self, key, value):
        """Validate question text before setting"""
        if not value or not str(value).strip():
            raise ValueError("question_text cannot be empty")

        value = str(value).strip()
        if len(value) < 10:
            raise ValueError("question_text must be at least 10 characters")
        if len(value) > 2000:
            raise ValueError("question_text must not exceed 2000 characters")

        return value

    @validates("question_type")
    def validate_question_type(self, key, value):
        """Validate question type before setting"""
        valid_types = {"technical", "behavioral", "mixed"}
        value = str(value).lower().strip()

        if value not in valid_types:
            raise ValueError(f"question_type must be one of {valid_types}")

        return value

    @validates("difficulty")
    def validate_difficulty(self, key, value):
        """Validate difficulty level before setting"""
        if value is None:
            return 1

        value = int(value)
        if value < 1 or value > 5:
            raise ValueError("difficulty must be between 1 and 5")

        return value

    @validates("tags")
    def validate_tags(self, key, value):
        """Validate and clean tags before setting"""
        if value is None:
            return None

        value = str(value).strip()
        if not value:
            return None

        if len(value) > 500:
            raise ValueError("tags must not exceed 500 characters")

        # Validate tag format
        tags_list = [tag.strip() for tag in value.split(",")]
        invalid_tags = [tag for tag in tags_list if not all(c.isalnum() or c in ["_", "-"] for c in tag)]

        if invalid_tags:
            raise ValueError(f"Invalid tag format: {invalid_tags}")

        return ",".join(tags_list)

    def __repr__(self):
        return (
            f"<Question(id={self.id}, job_title='{self.job_title}', "
            f"type='{self.question_type}', difficulty={self.difficulty})>"
        )


class QuestionSet(Base):
    """SQLAlchemy model for question sets with validation constraints"""

    __tablename__ = "question_sets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="Name of the question set (1-200 chars)")
    description = Column(Text, nullable=True, comment="Description of the question set (max 1000 chars)")
    job_title = Column(String(100), nullable=False, index=True, comment="Job title for the question set (2-100 chars)")
    question_ids = Column(Text, nullable=False, comment="JSON string of question IDs")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="Last update timestamp")

    # Add constraints at table level
    __table_args__ = (
        CheckConstraint("LENGTH(name) >= 1 AND LENGTH(name) <= 200", name="check_set_name_length"),
        CheckConstraint("LENGTH(job_title) >= 2 AND LENGTH(job_title) <= 100", name="check_set_job_title_length"),
        Index("idx_set_job_title", "job_title"),
        Index("idx_set_created_at", "created_at"),
    )

    @validates("name")
    def validate_name(self, key, value):
        """Validate set name before setting"""
        if not value or not str(value).strip():
            raise ValueError("name cannot be empty")

        value = str(value).strip()
        if len(value) > 200:
            raise ValueError("name must not exceed 200 characters")

        return value

    @validates("description")
    def validate_description(self, key, value):
        """Validate set description before setting"""
        if value is None:
            return None

        value = str(value).strip()
        if not value:
            return None

        if len(value) > 1000:
            raise ValueError("description must not exceed 1000 characters")

        return value

    @validates("job_title")
    def validate_job_title(self, key, value):
        """Validate job title before setting"""
        if not value or not str(value).strip():
            raise ValueError("job_title cannot be empty")

        value = str(value).strip()
        if len(value) < 2:
            raise ValueError("job_title must be at least 2 characters")
        if len(value) > 100:
            raise ValueError("job_title must not exceed 100 characters")

        return value

    @validates("question_ids")
    def validate_question_ids(self, key, value):
        """Validate question IDs JSON before setting"""
        if not value or not str(value).strip():
            raise ValueError("question_ids cannot be empty")

        value = str(value).strip()
        # Basic JSON validation (more thorough validation in schemas)
        if not (value.startswith("[") and value.endswith("]")):
            raise ValueError("question_ids must be valid JSON array format")

        return value

    def __repr__(self):
        return f"<QuestionSet(id={self.id}, name='{self.name}', job_title='{self.job_title}')>"


class UserRating(Base):
    """SQLAlchemy model for user ratings with validation constraints"""

    __tablename__ = "user_ratings"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, nullable=False, index=True, comment="ID of the rated question")
    rating = Column(Float, nullable=False, comment="Rating value between 1.0 and 5.0")
    feedback = Column(Text, nullable=True, comment="Optional user feedback (max 1000 chars)")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Creation timestamp"
    )

    # Add constraints at table level
    __table_args__ = (
        CheckConstraint("question_id > 0", name="check_question_id_positive"),
        CheckConstraint("rating >= 1.0 AND rating <= 5.0", name="check_rating_range"),
        Index("idx_rating_question_id", "question_id"),
        Index("idx_rating_created_at", "created_at"),
    )

    @validates("question_id")
    def validate_question_id(self, key, value):
        """Validate question ID before setting"""
        if value is None:
            raise ValueError("question_id cannot be null")

        value = int(value)
        if value <= 0:
            raise ValueError("question_id must be a positive integer")

        return value

    @validates("rating")
    def validate_rating(self, key, value):
        """Validate rating value before setting"""
        if value is None:
            raise ValueError("rating cannot be null")

        value = float(value)
        if value < 1.0 or value > 5.0:
            raise ValueError("rating must be between 1.0 and 5.0")

        # Round to 1 decimal place
        return round(value, 1)

    @validates("feedback")
    def validate_feedback(self, key, value):
        """Validate feedback text before setting"""
        if value is None:
            return None

        value = str(value).strip()
        if not value:
            return None

        if len(value) > 1000:
            raise ValueError("feedback must not exceed 1000 characters")

        return value

    def __repr__(self):
        return f"<UserRating(id={self.id}, question_id={self.question_id}, rating={self.rating})>"

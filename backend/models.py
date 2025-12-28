from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, CheckConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from database import Base


class Question(Base):
    """SQLAlchemy model for interview questions with validation constraints"""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Job title for the question (2-100 chars)"
    )
    question_text = Column(
        Text,
        nullable=False,
        comment="The interview question text (10-2000 chars)"
    )
    question_type = Column(
        String(50),
        nullable=False,
        comment="Type: 'technical', 'behavioral', or 'mixed'"
    )
    difficulty = Column(
        Integer,
        default=1,
        nullable=False,
        comment="Difficulty level 1-5"
    )
    is_flagged = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether question is flagged"
    )
    tags = Column(
        String(500),
        nullable=True,
        comment="Comma-separated tags"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp"
    )
    
    # Add constraints at table level
    __table_args__ = (
        CheckConstraint('LENGTH(job_title) >= 2 AND LENGTH(job_title) <= 100', name='check_job_title_length'),
        CheckConstraint('LENGTH(question_text) >= 10 AND LENGTH(question_text) <= 2000', name='check_question_text_length'),
        CheckConstraint("question_type IN ('technical', 'behavioral', 'mixed')", name='check_question_type'),
        CheckConstraint('difficulty >= 1 AND difficulty <= 5', name='check_difficulty_range'),
        Index('idx_job_title_type', 'job_title', 'question_type'),
        Index('idx_is_flagged', 'is_flagged'),
        Index('idx_created_at', 'created_at'),
    )
    
    @validates('job_title')
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
        if not all(c.isalnum() or c.isspace() or c in ['-', '+', '.', '#'] for c in value):
            raise ValueError("job_title contains invalid characters")
        
        return value
    
    @validates('question_text')
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
    
    @validates('question_type')
    def validate_question_type(self, key, value):
        """Validate question type before setting"""
        valid_types = {'technical', 'behavioral', 'mixed'}
        value = str(value).lower().strip()
        
        if value not in valid_types:
            raise ValueError(f"question_type must be one of {valid_types}")
        
        return value
    
    @validates('difficulty')
    def validate_difficulty(self, key, value):
        """Validate difficulty level before setting"""
        if value is None:
            return 1
        
        value = int(value)
        if value < 1 or value > 5:
            raise ValueError("difficulty must be between 1 and 5")
        
        return value
    
    @validates('tags')
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
        tags_list = [tag.strip() for tag in value.split(',')]
        invalid_tags = [tag for tag in tags_list if not all(c.isalnum() or c in ['_', '-'] for c in tag)]
        
        if invalid_tags:
            raise ValueError(f"Invalid tag format: {invalid_tags}")
        
        return ','.join(tags_list)
    
    def __repr__(self):
        return f"<Question(id={self.id}, job_title='{self.job_title}', type='{self.question_type}', difficulty={self.difficulty})>"

class QuestionSet(Base):
    """SQLAlchemy model for question sets with validation constraints"""
    __tablename__ = "question_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(
        String(200),
        nullable=False,
        comment="Name of the question set (1-200 chars)"
    )
    description = Column(
        Text,
        nullable=True,
        comment="Description of the question set (max 1000 chars)"
    )
    job_title = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Job title for the question set (2-100 chars)"
    )
    question_ids = Column(
        Text,
        nullable=False,
        comment="JSON string of question IDs"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp"
    )
    
    # Add constraints at table level
    __table_args__ = (
        CheckConstraint('LENGTH(name) >= 1 AND LENGTH(name) <= 200', name='check_set_name_length'),
        CheckConstraint('LENGTH(job_title) >= 2 AND LENGTH(job_title) <= 100', name='check_set_job_title_length'),
        Index('idx_set_job_title', 'job_title'),
        Index('idx_set_created_at', 'created_at'),
    )
    
    @validates('name')
    def validate_name(self, key, value):
        """Validate set name before setting"""
        if not value or not str(value).strip():
            raise ValueError("name cannot be empty")
        
        value = str(value).strip()
        if len(value) > 200:
            raise ValueError("name must not exceed 200 characters")
        
        return value
    
    @validates('description')
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
    
    @validates('job_title')
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
    
    @validates('question_ids')
    def validate_question_ids(self, key, value):
        """Validate question IDs JSON before setting"""
        if not value or not str(value).strip():
            raise ValueError("question_ids cannot be empty")
        
        value = str(value).strip()
        # Basic JSON validation (more thorough validation in schemas)
        if not (value.startswith('[') and value.endswith(']')):
            raise ValueError("question_ids must be valid JSON array format")
        
        return value
    
    def __repr__(self):
        return f"<QuestionSet(id={self.id}, name='{self.name}', job_title='{self.job_title}')>"

class UserRating(Base):
    """SQLAlchemy model for user ratings with validation constraints"""
    __tablename__ = "user_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer,
        nullable=False,
        index=True,
        comment="ID of the rated question"
    )
    rating = Column(
        Float,
        nullable=False,
        comment="Rating value between 1.0 and 5.0"
    )
    feedback = Column(
        Text,
        nullable=True,
        comment="Optional user feedback (max 1000 chars)"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    
    # Add constraints at table level
    __table_args__ = (
        CheckConstraint('question_id > 0', name='check_question_id_positive'),
        CheckConstraint('rating >= 1.0 AND rating <= 5.0', name='check_rating_range'),
        Index('idx_rating_question_id', 'question_id'),
        Index('idx_rating_created_at', 'created_at'),
    )
    
    @validates('question_id')
    def validate_question_id(self, key, value):
        """Validate question ID before setting"""
        if value is None:
            raise ValueError("question_id cannot be null")
        
        value = int(value)
        if value <= 0:
            raise ValueError("question_id must be a positive integer")
        
        return value
    
    @validates('rating')
    def validate_rating(self, key, value):
        """Validate rating value before setting"""
        if value is None:
            raise ValueError("rating cannot be null")
        
        value = float(value)
        if value < 1.0 or value > 5.0:
            raise ValueError("rating must be between 1.0 and 5.0")
        
        # Round to 1 decimal place
        return round(value, 1)
    
    @validates('feedback')
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
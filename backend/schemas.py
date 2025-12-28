from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime

class QuestionBase(BaseModel):
    job_title: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Job title for the question",
        example="Senior Software Engineer"
    )
    question_text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The interview question text",
        example="Describe your experience with system design"
    )
    question_type: str = Field(
        ...,
        description="Type: 'technical' or 'behavioral'",
        example="technical"
    )
    difficulty: Optional[int] = Field(
        1,
        ge=1,
        le=5,
        description="Difficulty level 1-5"
    )
    is_flagged: Optional[bool] = Field(
        False,
        description="Whether question is flagged"
    )
    tags: Optional[str] = Field(
        None,
        max_length=500,
        description="Comma-separated tags",
        example="python,design,scalability"
    )
    
    @field_validator('job_title')
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
        if not all(c.isalnum() or c.isspace() or c in ['-', '+', '.', '#'] for c in v):
            raise ValueError("job_title contains invalid characters")
        
        return v
    
    @field_validator('question_text')
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
    
    @field_validator('question_type')
    @classmethod
    def validate_question_type(cls, v: str) -> str:
        """Validate question type"""
        valid_types = {'technical', 'behavioral', 'mixed'}
        if v.lower() not in valid_types:
            raise ValueError(f"question_type must be one of {valid_types}")
        
        return v.lower()
    
    @field_validator('tags')
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
        tags_list = [tag.strip() for tag in v.split(',')]
        invalid_tags = [tag for tag in tags_list if not all(c.isalnum() or c in ['_', '-'] for c in tag)]
        
        if invalid_tags:
            raise ValueError(f"Invalid tag format: {invalid_tags}. Tags must be alphanumeric with underscores or dashes")
        
        return ','.join(tags_list)

class QuestionCreate(QuestionBase):
    """Schema for creating a new question"""
    pass


class QuestionUpdate(BaseModel):
    """Schema for updating a question - all fields optional"""
    difficulty: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Difficulty level 1-5"
    )
    is_flagged: Optional[bool] = Field(
        None,
        description="Whether question is flagged"
    )
    tags: Optional[str] = Field(
        None,
        max_length=500,
        description="Comma-separated tags"
    )
    
    @field_validator('tags')
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
        tags_list = [tag.strip() for tag in v.split(',')]
        invalid_tags = [tag for tag in tags_list if not all(c.isalnum() or c in ['_', '-'] for c in tag)]
        
        if invalid_tags:
            raise ValueError(f"Invalid tag format: {invalid_tags}")
        
        return ','.join(tags_list)

class Question(QuestionBase):
    """Schema for a question with database-generated fields"""
    id: int = Field(..., gt=0, description="Question ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        from_attributes = True

class QuestionGenerateRequest(BaseModel):
    """Schema for requesting AI-generated questions"""
    job_title: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Job title to generate questions for",
        example="Backend Engineer"
    )
    count: Optional[int] = Field(
        5,
        ge=1,
        le=100,
        description="Number of questions to generate (1-100)"
    )
    question_type: Optional[str] = Field(
        "mixed",
        description="'technical', 'behavioral', or 'mixed'",
        example="technical"
    )
    
    @field_validator('job_title')
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        """Validate job title"""
        if not v or not v.strip():
            raise ValueError("job_title cannot be empty")
        
        v = v.strip()
        if len(v) < 2:
            raise ValueError("job_title must be at least 2 characters")
        
        return v
    
    @field_validator('count')
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
    
    @field_validator('question_type')
    @classmethod
    def validate_question_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate question type"""
        if v is None:
            return "mixed"
        
        valid_types = {'technical', 'behavioral', 'mixed'}
        if v.lower() not in valid_types:
            raise ValueError(f"question_type must be one of {valid_types}")
        
        return v.lower()

class QuestionSetCreate(BaseModel):
    """Schema for creating a new question set"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of the question set",
        example="Python Interview Questions"
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Description of the question set",
        example="A comprehensive set of Python interview questions for backend roles"
    )
    job_title: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Job title for the question set",
        example="Python Developer"
    )
    question_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of question IDs to include (1-1000 questions)",
        example=[1, 2, 3, 4, 5]
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate set name"""
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        
        v = v.strip()
        if len(v) > 200:
            raise ValueError("name must not exceed 200 characters")
        
        return v
    
    @field_validator('description')
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
    
    @field_validator('job_title')
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        """Validate job title"""
        if not v or not v.strip():
            raise ValueError("job_title cannot be empty")
        
        v = v.strip()
        if len(v) < 2:
            raise ValueError("job_title must be at least 2 characters")
        
        return v
    
    @field_validator('question_ids')
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
    
    class Config:
        from_attributes = True

class UserRatingCreate(BaseModel):
    """Schema for creating a new rating"""
    question_id: int = Field(
        ...,
        gt=0,
        description="ID of the question being rated",
        example=1
    )
    rating: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Rating from 1.0 to 5.0",
        example=4.5
    )
    feedback: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional feedback text",
        example="Great question, very practical"
    )
    
    @field_validator('question_id')
    @classmethod
    def validate_question_id(cls, v: int) -> int:
        """Validate question ID"""
        if v <= 0:
            raise ValueError("question_id must be a positive integer")
        
        return v
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v: float) -> float:
        """Validate rating value"""
        if v < 1.0 or v > 5.0:
            raise ValueError("rating must be between 1.0 and 5.0")
        
        return round(v, 1)  # Round to 1 decimal place
    
    @field_validator('feedback')
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
    rating: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Rating value between 1.0 and 5.0"
    )
    feedback: Optional[str] = Field(None, description="User feedback text")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    """Schema for platform statistics response"""
    total_questions: int = Field(
        ...,
        ge=0,
        description="Total number of questions in the system",
        example=150
    )
    questions_by_type: dict = Field(
        ...,
        description="Count of questions grouped by type",
        example={"technical": 90, "behavioral": 60}
    )
    questions_by_job_title: dict = Field(
        ...,
        description="Count of questions grouped by job title",
        example={"Python Developer": 45, "Backend Engineer": 60}
    )
    average_difficulty: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Average difficulty level across all questions",
        example=3.2
    )
    flagged_questions: int = Field(
        ...,
        ge=0,
        description="Total number of flagged questions",
        example=5
    )
    total_question_sets: int = Field(
        ...,
        ge=0,
        description="Total number of question sets",
        example=10
    )
    
    @model_validator(mode='after')
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
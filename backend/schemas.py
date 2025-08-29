from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class QuestionBase(BaseModel):
    job_title: str = Field(..., description="Job title for the question")
    question_text: str = Field(..., description="The interview question text")
    question_type: str = Field(..., description="Type: 'technical' or 'behavioral'")
    difficulty: Optional[int] = Field(1, description="Difficulty level 1-5")
    is_flagged: Optional[bool] = Field(False, description="Whether question is flagged")
    tags: Optional[str] = Field(None, description="Comma-separated tags")

class QuestionCreate(QuestionBase):
    pass

class QuestionUpdate(BaseModel):
    difficulty: Optional[int] = None
    is_flagged: Optional[bool] = None
    tags: Optional[str] = None

class Question(QuestionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class QuestionGenerateRequest(BaseModel):
    job_title: str = Field(..., description="Job title to generate questions for")
    count: Optional[int] = Field(5, description="Number of questions to generate")
    question_type: Optional[str] = Field("mixed", description="'technical', 'behavioral', or 'mixed'")

class QuestionSetCreate(BaseModel):
    name: str = Field(..., description="Name of the question set")
    description: Optional[str] = Field(None, description="Description of the question set")
    job_title: str = Field(..., description="Job title for the question set")
    question_ids: List[int] = Field(..., description="List of question IDs to include")

class QuestionSet(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    job_title: str
    question_ids: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UserRatingCreate(BaseModel):
    question_id: int = Field(..., description="ID of the question being rated")
    rating: float = Field(..., ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    feedback: Optional[str] = Field(None, description="Optional feedback text")

class UserRating(BaseModel):
    id: int
    question_id: int
    rating: float
    feedback: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total_questions: int
    questions_by_type: dict
    questions_by_job_title: dict
    average_difficulty: float
    flagged_questions: int
    total_question_sets: int
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.sql import func
from database import Base

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    job_title = Column(String(255), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # "technical" or "behavioral"
    difficulty = Column(Integer, default=1)  # 1-5 scale
    is_flagged = Column(Boolean, default=False)
    tags = Column(String(500))  # Comma-separated tags
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class QuestionSet(Base):
    __tablename__ = "question_sets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    job_title = Column(String(255), nullable=False)
    question_ids = Column(Text)  # JSON string of question IDs
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class UserRating(Base):
    __tablename__ = "user_ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    rating = Column(Float, nullable=False)  # 1.0-5.0
    feedback = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
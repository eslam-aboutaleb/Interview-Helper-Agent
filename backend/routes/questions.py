from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json

# Import database connection handler
from database import get_db
# Import database models
from models import Question, QuestionSet, UserRating
# Import Pydantic schemas for request/response validation
from schemas import (
    QuestionCreate, Question as QuestionSchema, QuestionUpdate,
    QuestionGenerateRequest, QuestionSetCreate, QuestionSet as QuestionSetSchema,
    UserRatingCreate, UserRating as UserRatingSchema
)
# Import AI service for question generation
from services.gemini_service import GeminiService

# Initialize FastAPI router for question-related endpoints
router = APIRouter()
# Initialize Gemini AI service
gemini_service = GeminiService()

@router.post("/generate", response_model=List[QuestionSchema])
async def generate_questions(
    request: QuestionGenerateRequest,
    db: Session = Depends(get_db)
):
    """Generate new interview questions using AI
    
    Args:
        request: Contains job_title, count, and question_type for generation
        db: Database session dependency
        
    Returns:
        List of generated Question objects saved to database
        
    Raises:
        HTTPException: If generation or database operations fail
    """
    try:
        # Call Gemini AI service to generate interview questions based on parameters
        generated_questions = gemini_service.generate_questions(
            job_title=request.job_title,
            count=request.count,
            question_type=request.question_type
        )
        
        # Save each generated question to the database
        saved_questions = []
        for q_data in generated_questions:
            question = Question(**q_data)  # Create ORM object from dict
            db.add(question)
            db.commit()  # Commit each question individually
            db.refresh(question)  # Refresh to get auto-generated values like ID
            saved_questions.append(question)
        
        return saved_questions
    
    except Exception as e:
        # Rollback transaction on error to maintain database integrity
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {str(e)}")

@router.get("/", response_model=List[QuestionSchema])
async def get_questions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    job_title: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    flagged_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get questions with filtering options
    
    Args:
        skip: Number of records to skip (pagination offset)
        limit: Maximum number of records to return (pagination limit)
        job_title: Optional filter for job title (partial match)
        question_type: Optional filter for question type (exact match)
        flagged_only: If True, return only flagged questions
        db: Database session dependency
        
    Returns:
        List of Question objects matching the filter criteria
    """
    # Build the base query
    query = db.query(Question)
    
    # Apply filters based on parameters if provided
    if job_title:
        # Case-insensitive partial matching for job title
        query = query.filter(Question.job_title.ilike(f"%{job_title}%"))
    
    if question_type:
        # Exact matching for question type
        query = query.filter(Question.question_type == question_type)
    
    if flagged_only:
        # Filter only flagged questions
        query = query.filter(Question.is_flagged == True)
    
    # Execute query with pagination
    questions = query.offset(skip).limit(limit).all()
    return questions

@router.get("/{question_id}", response_model=QuestionSchema)
async def get_question(question_id: int, db: Session = Depends(get_db)):
    """Get a specific question by ID
    
    Args:
        question_id: The unique identifier of the question
        db: Database session dependency
        
    Returns:
        Question object if found
        
    Raises:
        HTTPException: If question with provided ID doesn't exist
    """
    # Query for specific question by ID
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        # Return 404 if question not found
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.post("/", response_model=QuestionSchema)
async def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    """Create a new question manually
    
    Args:
        question: Pydantic model containing question data
        db: Database session dependency
        
    Returns:
        Created Question object with database-generated ID
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Convert Pydantic model to dictionary and create ORM object
        db_question = Question(**question.dict())
        # Add to session and commit to database
        db.add(db_question)
        db.commit()
        # Refresh to get auto-generated values
        db.refresh(db_question)
        return db_question
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create question: {str(e)}")

@router.put("/{question_id}", response_model=QuestionSchema)
async def update_question(
    question_id: int,
    question_update: QuestionUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing question
    
    Args:
        question_id: The unique identifier of the question to update
        question_update: Pydantic model with fields to update (only provided fields are updated)
        db: Database session dependency
        
    Returns:
        Updated Question object
        
    Raises:
        HTTPException: If question not found or update operation fails
    """
    # First check if the question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Convert Pydantic model to dict, excluding unset fields (None values)
    update_data = question_update.dict(exclude_unset=True)
    # Update only the fields that were provided
    for field, value in update_data.items():
        setattr(question, field, value)
    
    try:
        # Commit changes to database
        db.commit()
        # Refresh to get updated values
        db.refresh(question)
        return question
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update question: {str(e)}")

@router.delete("/{question_id}")
async def delete_question(question_id: int, db: Session = Depends(get_db)):
    """Delete a question
    
    Args:
        question_id: The unique identifier of the question to delete
        db: Database session dependency
        
    Returns:
        Success message dictionary
        
    Raises:
        HTTPException: If question not found or delete operation fails
    """
    # First check if the question exists
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    try:
        # Remove from database
        db.delete(question)
        db.commit()
        return {"message": "Question deleted successfully"}
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete question: {str(e)}")

@router.post("/sets", response_model=QuestionSetSchema)
async def create_question_set(question_set: QuestionSetCreate, db: Session = Depends(get_db)):
    """Create a new question set
    
    Args:
        question_set: Pydantic model containing set data and question IDs
        db: Database session dependency
        
    Returns:
        Created QuestionSet object with database-generated ID
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Convert question IDs list to JSON string for storage
        question_ids_json = json.dumps(question_set.question_ids)
        # Create new QuestionSet object
        db_set = QuestionSet(
            name=question_set.name,
            description=question_set.description,
            job_title=question_set.job_title,
            question_ids=question_ids_json  # Store as JSON string in database
        )
        # Add to session and commit to database
        db.add(db_set)
        db.commit()
        # Refresh to get auto-generated values
        db.refresh(db_set)
        return db_set
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create question set: {str(e)}")

@router.get("/sets/", response_model=List[QuestionSetSchema])
async def get_question_sets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all question sets
    
    Args:
        skip: Number of records to skip (pagination offset)
        limit: Maximum number of records to return (pagination limit)
        db: Database session dependency
        
    Returns:
        List of QuestionSet objects with pagination
    """
    # Query all sets with pagination
    sets = db.query(QuestionSet).offset(skip).limit(limit).all()
    return sets

@router.post("/rate", response_model=UserRatingSchema)
async def rate_question(rating: UserRatingCreate, db: Session = Depends(get_db)):
    """Rate a question
    
    Args:
        rating: Pydantic model containing rating data (question_id, rating_value)
        db: Database session dependency
        
    Returns:
        Created UserRating object with database-generated ID
        
    Raises:
        HTTPException: If database operation fails
    """
    try:
        # Create new UserRating object from request data
        db_rating = UserRating(**rating.dict())
        # Add to session and commit to database
        db.add(db_rating)
        db.commit()
        # Refresh to get auto-generated values
        db.refresh(db_rating)
        return db_rating
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to rate question: {str(e)}")

@router.get("/job-titles/", response_model=List[str])
async def get_job_titles(db: Session = Depends(get_db)):
    """Get all unique job titles
    
    Args:
        db: Database session dependency
        
    Returns:
        List of unique job title strings from the questions table
    """
    # Query for distinct job titles in the database
    job_titles = db.query(Question.job_title).distinct().all()
    # Convert from list of tuples to list of strings
    return [title[0] for title in job_titles]
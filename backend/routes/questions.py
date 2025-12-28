from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from pydantic import Field

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

@router.post("/generate", response_model=List[QuestionSchema], status_code=status.HTTP_201_CREATED)
async def generate_questions(
    request: QuestionGenerateRequest = Field(..., description="Question generation parameters including job title, count, and type"),
    db: Session = Depends(get_db)
):
    """Generate new interview questions using AI
    
    Args:
        request: Contains job_title, count, and question_type for generation
        db: Database session dependency
        
    Returns:
        List of generated Question objects saved to database
        
    Raises:
        HTTPException 400: If request parameters are invalid
        HTTPException 500: If generation or database operations fail
        HTTPException 503: If AI service is unavailable
    """
    try:
        if not request.job_title or not request.job_title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="job_title cannot be empty"
            )
        
        if request.count < 1 or request.count > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="count must be between 1 and 100"
            )
        
        # Call Gemini AI service to generate interview questions based on parameters
        generated_questions = gemini_service.generate_questions(
            job_title=request.job_title,
            count=request.count,
            question_type=request.question_type
        )
        
        if not generated_questions:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service failed to generate questions"
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
    
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        # Rollback transaction on error to maintain database integrity
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions: {str(e)}"
        )

@router.get("/", response_model=List[QuestionSchema], status_code=status.HTTP_200_OK)
async def get_questions(
    skip: int = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
        title="Pagination Offset"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return (max 1000)",
        title="Pagination Limit"
    ),
    job_title: Optional[str] = Query(
        None,
        description="Filter by job title (case-insensitive partial match)",
        title="Job Title Filter"
    ),
    question_type: Optional[str] = Query(
        None,
        description="Filter by question type: 'technical' or 'behavioral'",
        title="Question Type Filter"
    ),
    flagged_only: bool = Query(
        False,
        description="If True, return only flagged questions",
        title="Flagged Questions Only"
    ),
    db: Session = Depends(get_db)
):
    """Get questions with filtering and pagination options
    
    Returns paginated list of questions with optional filtering by job title, type, and flagged status.
    
    Raises:
        HTTPException 400: If pagination parameters are invalid
        HTTPException 500: If database query fails
    """
    try:
        # Build the base query
        query = db.query(Question)
        
        # Apply filters based on parameters if provided
        if job_title and job_title.strip():
            # Case-insensitive partial matching for job title
            query = query.filter(Question.job_title.ilike(f"%{job_title}%"))
        
        if question_type:
            # Validate question type
            if question_type not in ['technical', 'behavioral', 'mixed']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="question_type must be 'technical', 'behavioral', or 'mixed'"
                )
            # Exact matching for question type
            query = query.filter(Question.question_type == question_type)
        
        if flagged_only:
            # Filter only flagged questions
            query = query.filter(Question.is_flagged == True)
        
        # Execute query with pagination
        questions = query.offset(skip).limit(limit).all()
        return questions
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve questions: {str(e)}"
        )

@router.get("/{question_id}", response_model=QuestionSchema, status_code=status.HTTP_200_OK)
async def get_question(
    question_id: int = Field(..., gt=0, description="Unique identifier of the question"),
    db: Session = Depends(get_db)
):
    """Get a specific question by ID
    
    Returns a single question with all its details.
    
    Raises:
        HTTPException 400: If question_id is invalid
        HTTPException 404: If question with provided ID doesn't exist
        HTTPException 500: If database query fails
    """
    try:
        if question_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_id must be a positive integer"
            )
        
        # Query for specific question by ID
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            # Return 404 if question not found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID {question_id} not found"
            )
        return question
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve question: {str(e)}"
        )

@router.post("/", response_model=QuestionSchema, status_code=status.HTTP_201_CREATED)
async def create_question(
    question: QuestionCreate = Field(..., description="Question data to create"),
    db: Session = Depends(get_db)
):
    """Create a new question manually
    
    Creates a new question in the database with the provided data.
    
    Args:
        question: Pydantic model containing question data
        db: Database session dependency
        
    Returns:
        Created Question object with database-generated ID and timestamps
        
    Raises:
        HTTPException 400: If question data is invalid or incomplete
        HTTPException 409: If duplicate question exists
        HTTPException 500: If database operation fails
    """
    try:
        # Validate question data
        if not question.question_text or not question.question_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_text cannot be empty"
            )
        
        if question.question_type not in ['technical', 'behavioral', 'mixed']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_type must be 'technical', 'behavioral', or 'mixed'"
            )
        
        if question.difficulty and (question.difficulty < 1 or question.difficulty > 5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="difficulty must be between 1 and 5"
            )
        
        # Convert Pydantic model to dictionary and create ORM object
        db_question = Question(**question.dict())
        # Add to session and commit to database
        db.add(db_question)
        db.commit()
        # Refresh to get auto-generated values
        db.refresh(db_question)
        return db_question
    
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}"
        )
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question: {str(e)}"
        )

@router.put("/{question_id}", response_model=QuestionSchema, status_code=status.HTTP_200_OK)
async def update_question(
    question_id: int = Field(..., gt=0, description="Unique identifier of the question to update"),
    question_update: QuestionUpdate = Field(..., description="Fields to update"),
    db: Session = Depends(get_db)
):
    """Update an existing question
    
    Partially or fully updates a question. Only provided fields are updated.
    
    Args:
        question_id: The unique identifier of the question to update
        question_update: Pydantic model with fields to update
        db: Database session dependency
        
    Returns:
        Updated Question object with new values
        
    Raises:
        HTTPException 400: If question_id is invalid or update data is invalid
        HTTPException 404: If question not found
        HTTPException 500: If update operation fails
    """
    try:
        # Validate question_id
        if question_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_id must be a positive integer"
            )
        
        # First check if the question exists
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID {question_id} not found"
            )
        
        # Validate update data
        update_data = question_update.dict(exclude_unset=True)
        
        if 'difficulty' in update_data and update_data['difficulty']:
            if update_data['difficulty'] < 1 or update_data['difficulty'] > 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="difficulty must be between 1 and 5"
                )
        
        # Update only the fields that were provided
        for field, value in update_data.items():
            setattr(question, field, value)
        
        # Commit changes to database
        db.commit()
        # Refresh to get updated values
        db.refresh(question)
        return question
    
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}"
        )
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update question: {str(e)}"
        )

@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int = Field(..., gt=0, description="Unique identifier of the question to delete"),
    db: Session = Depends(get_db)
):
    """Delete a question
    
    Permanently removes a question from the database.
    
    Args:
        question_id: The unique identifier of the question to delete
        db: Database session dependency
        
    Returns:
        No content on success
        
    Raises:
        HTTPException 400: If question_id is invalid
        HTTPException 404: If question not found
        HTTPException 500: If delete operation fails
    """
    try:
        # Validate question_id
        if question_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_id must be a positive integer"
            )
        
        # First check if the question exists
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID {question_id} not found"
            )
        
        # Remove from database
        db.delete(question)
        db.commit()
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete question: {str(e)}"
        )

@router.post("/sets", response_model=QuestionSetSchema, status_code=status.HTTP_201_CREATED)
async def create_question_set(
    question_set: QuestionSetCreate = Field(..., description="Question set data including name and question IDs"),
    db: Session = Depends(get_db)
):
    """Create a new question set
    
    Creates a collection of questions under a single set for organized management.
    
    Args:
        question_set: Pydantic model containing set data and question IDs
        db: Database session dependency
        
    Returns:
        Created QuestionSet object with database-generated ID and timestamps
        
    Raises:
        HTTPException 400: If set data is invalid or question IDs are invalid
        HTTPException 404: If one or more question IDs don't exist
        HTTPException 500: If database operation fails
    """
    try:
        # Validate set data
        if not question_set.name or not question_set.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name cannot be empty"
            )
        
        if not question_set.job_title or not question_set.job_title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="job_title cannot be empty"
            )
        
        if not question_set.question_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_ids list cannot be empty"
            )
        
        # Verify all question IDs exist
        for q_id in question_set.question_ids:
            question = db.query(Question).filter(Question.id == q_id).first()
            if not question:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Question with ID {q_id} not found"
                )
        
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
    
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}"
        )
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create question set: {str(e)}"
        )

@router.get("/sets/", response_model=List[QuestionSetSchema], status_code=status.HTTP_200_OK)
async def get_question_sets(
    skip: int = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
        title="Pagination Offset"
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return (max 1000)",
        title="Pagination Limit"
    ),
    db: Session = Depends(get_db)
):
    """Get all question sets
    
    Retrieves paginated list of all question sets in the system.
    
    Args:
        skip: Number of records to skip (pagination offset)
        limit: Maximum number of records to return (pagination limit)
        db: Database session dependency
        
    Returns:
        List of QuestionSet objects with pagination
        
    Raises:
        HTTPException 400: If pagination parameters are invalid
        HTTPException 500: If database query fails
    """
    try:
        # Query all sets with pagination
        sets = db.query(QuestionSet).offset(skip).limit(limit).all()
        return sets
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve question sets: {str(e)}"
        )

@router.post("/rate", response_model=UserRatingSchema, status_code=status.HTTP_201_CREATED)
async def rate_question(
    rating: UserRatingCreate = Field(..., description="Rating data including question_id, rating value (1-5), and optional feedback"),
    db: Session = Depends(get_db)
):
    """Rate a question
    
    Allows users to provide ratings and feedback for questions.
    
    Args:
        rating: Pydantic model containing rating data (question_id, rating_value)
        db: Database session dependency
        
    Returns:
        Created UserRating object with database-generated ID and timestamp
        
    Raises:
        HTTPException 400: If rating data is invalid
        HTTPException 404: If question doesn't exist
        HTTPException 500: If database operation fails
    """
    try:
        # Verify question exists
        question = db.query(Question).filter(Question.id == rating.question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Question with ID {rating.question_id} not found"
            )
        
        # Validate rating value
        if rating.rating < 1.0 or rating.rating > 5.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="rating must be between 1.0 and 5.0"
            )
        
        # Create new UserRating object from request data
        db_rating = UserRating(**rating.dict())
        # Add to session and commit to database
        db.add(db_rating)
        db.commit()
        # Refresh to get auto-generated values
        db.refresh(db_rating)
        return db_rating
    
    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {str(e)}"
        )
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rate question: {str(e)}"
        )

@router.get("/job-titles/", response_model=List[str], status_code=status.HTTP_200_OK)
async def get_job_titles(db: Session = Depends(get_db)):
    """Get all unique job titles
    
    Retrieves a list of all distinct job titles from questions in the database.
    Useful for filtering and categorization.
    
    Args:
        db: Database session dependency
        
    Returns:
        List of unique job title strings
        
    Raises:
        HTTPException 500: If database query fails
    """
    try:
        # Query for distinct job titles in the database
        job_titles = db.query(Question.job_title).distinct().all()
        # Convert from list of tuples to list of strings, filter out None values
        return [title[0] for title in job_titles if title[0]]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve job titles: {str(e)}"
        )
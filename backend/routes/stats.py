from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Question, QuestionSet, UserRating
from schemas import StatsResponse

router = APIRouter()

@router.get("/", response_model=StatsResponse, status_code=status.HTTP_200_OK)
async def get_stats(db: Session = Depends(get_db)):
    """Get comprehensive platform statistics
    
    Retrieves aggregated statistics including total questions, breakdown by type and job title,
    average difficulty, flagged questions count, and total question sets.
    
    Args:
        db: Database session dependency
        
    Returns:
        StatsResponse object containing all platform statistics
        
    Raises:
        HTTPException 500: If database query or aggregation fails
    """
    try:
        # Total questions
        total_questions = db.query(func.count(Question.id)).scalar() or 0
        
        # Questions by type
        type_stats = db.query(
            Question.question_type,
            func.count(Question.id)
        ).group_by(Question.question_type).all()
        
        questions_by_type = {type_name: count for type_name, count in type_stats if type_name}
        
        # Questions by job title
        job_stats = db.query(
            Question.job_title,
            func.count(Question.id)
        ).group_by(Question.job_title).all()
        
        questions_by_job_title = {job_title: count for job_title, count in job_stats if job_title}
        
        # Average difficulty
        avg_difficulty = db.query(func.avg(Question.difficulty)).scalar() or 0.0
        
        # Flagged questions
        flagged_count = db.query(func.count(Question.id)).filter(Question.is_flagged == True).scalar() or 0
        
        # Total question sets
        total_sets = db.query(func.count(QuestionSet.id)).scalar() or 0
        
        return StatsResponse(
            total_questions=total_questions,
            questions_by_type=questions_by_type,
            questions_by_job_title=questions_by_job_title,
            average_difficulty=float(avg_difficulty),
            flagged_questions=flagged_count,
            total_question_sets=total_sets
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )
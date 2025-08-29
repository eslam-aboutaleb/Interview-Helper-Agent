from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Question, QuestionSet, UserRating
from schemas import StatsResponse

router = APIRouter()

@router.get("/", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get platform statistics"""
    
    # Total questions
    total_questions = db.query(func.count(Question.id)).scalar()
    
    # Questions by type
    type_stats = db.query(
        Question.question_type,
        func.count(Question.id)
    ).group_by(Question.question_type).all()
    
    questions_by_type = {type_name: count for type_name, count in type_stats}
    
    # Questions by job title
    job_stats = db.query(
        Question.job_title,
        func.count(Question.id)
    ).group_by(Question.job_title).all()
    
    questions_by_job_title = {job_title: count for job_title, count in job_stats}
    
    # Average difficulty
    avg_difficulty = db.query(func.avg(Question.difficulty)).scalar() or 0.0
    
    # Flagged questions
    flagged_count = db.query(func.count(Question.id)).filter(Question.is_flagged == True).scalar()
    
    # Total question sets
    total_sets = db.query(func.count(QuestionSet.id)).scalar()
    
    return StatsResponse(
        total_questions=total_questions,
        questions_by_type=questions_by_type,
        questions_by_job_title=questions_by_job_title,
        average_difficulty=float(avg_difficulty),
        flagged_questions=flagged_count,
        total_question_sets=total_sets
    )
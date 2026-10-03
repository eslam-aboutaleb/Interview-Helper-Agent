from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Any, Dict, Iterator, List, Optional, Tuple
import csv
import io
import json
import logging

# Import database connection handler
from database import get_db

# Import database models
from models import Question, QuestionSet, UserRating, User

# Import Pydantic schemas for request/response validation
from schemas import (
    QuestionCreate,
    Question as QuestionSchema,
    QuestionUpdate,
    QuestionGenerateRequest,
    QuestionSetCreate,
    QuestionSet as QuestionSetSchema,
    UserRatingCreate,
    UserRating as UserRatingSchema,
)

# Import AI service for question generation
from services.gemini_service import GeminiService, GeminiServiceError

# Import history tracking
from services.history_service import record_action

# Import auth dependency
from deps import get_current_user, get_optional_user

# Initialize FastAPI router for question-related endpoints
router = APIRouter()

logger = logging.getLogger(__name__)

# Columns scanned by the free-text search, in priority order.
SEARCH_COLUMNS = (Question.question_text, Question.job_title, Question.tags)

# Column order used by the CSV export.
CSV_EXPORT_COLUMNS = (
    "id",
    "job_title",
    "question_text",
    "question_type",
    "difficulty",
    "is_flagged",
    "tags",
    "created_at",
)

# Supported values for the ``format`` query parameter of the export endpoint.
EXPORT_FORMATS = ("json", "csv")

# Leading characters that make a spreadsheet treat a cell as a formula.
# Tab and carriage return are included because Excel also honours them.
CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# Lazy singleton for the Gemini service so a missing/invalid API key does not
# crash the application at import time.
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """Dependency that lazily initializes the Gemini service on first use."""
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service


def escape_like(term: str) -> str:
    """Escape LIKE wildcards so a user term is matched literally.

    Values are always passed to the driver as bound parameters; escaping only
    prevents ``%`` and ``_`` from turning into unintended wildcards.
    """
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_search_filter(dialect_name: str, term: str) -> Tuple[Any, Optional[Any]]:
    """Build the full-text search predicate for the active dialect.

    Postgres uses ``to_tsvector``/``websearch_to_tsquery`` computed on the fly
    over ``question_text``, ``job_title`` and ``tags``; every other dialect
    (SQLite in tests) falls back to a case-insensitive ``ILIKE`` over the same
    columns.

    Args:
        dialect_name: ``db.bind.dialect.name`` — read at query time so the
            module still imports cleanly on dialects without tsvector support.
        term: The already-stripped, non-empty search term.

    Returns:
        A ``(criterion, rank)`` tuple. ``rank`` is a relevance expression on
        Postgres and ``None`` on dialects without ranking support.
    """
    if dialect_name == "postgresql":
        document = func.concat_ws(
            " ",
            func.coalesce(Question.question_text, ""),
            func.coalesce(Question.job_title, ""),
            func.coalesce(Question.tags, ""),
        )
        tsvector = func.to_tsvector("english", document)
        tsquery = func.websearch_to_tsquery("english", term)
        return tsvector.op("@@")(tsquery), func.ts_rank(tsvector, tsquery).label("rank")

    pattern = f"%{escape_like(term)}%"
    criterion = or_(*(column.ilike(pattern, escape="\\") for column in SEARCH_COLUMNS))
    return criterion, None


def apply_question_filters(
    query,
    dialect_name: str,
    job_title: Optional[str] = None,
    question_type: Optional[str] = None,
    flagged_only: bool = False,
    q: Optional[str] = None,
    company: Optional[str] = None,
) -> Tuple[Any, Optional[Any]]:
    """Apply the shared list/export filters to a ``Question`` query.

    Args:
        query: The base ``db.query(Question)`` query.
        dialect_name: Active SQLAlchemy dialect name (see ``build_search_filter``).
        job_title: Optional case-insensitive partial job-title filter.
        question_type: Optional exact type filter.
        flagged_only: When True, restrict to flagged questions.
        q: Optional free-text search term.
        company: Optional case-insensitive partial company filter.

    Returns:
        A ``(query, rank)`` tuple where ``rank`` is the relevance expression
        for ordering, or ``None`` when the dialect has no ranking support.

    Raises:
        HTTPException 400: If ``question_type`` is not a supported value.
    """
    if job_title and job_title.strip():
        query = query.filter(Question.job_title.ilike(f"%{escape_like(job_title.strip())}%", escape="\\"))

    if company and company.strip():
        query = query.filter(Question.company.ilike(f"%{escape_like(company.strip())}%", escape="\\"))

    if question_type:
        if question_type not in ["technical", "behavioral", "mixed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_type must be 'technical', 'behavioral', or 'mixed'",
            )
        query = query.filter(Question.question_type == question_type)

    if flagged_only:
        query = query.filter(Question.is_flagged)

    rank = None
    if q and q.strip():
        criterion, rank = build_search_filter(dialect_name, q.strip())
        query = query.filter(criterion)

    if rank is not None:
        query = query.order_by(rank.desc(), Question.created_at.desc())
    else:
        query = query.order_by(Question.created_at.desc())

    return query, rank


def sanitize_csv_cell(value: Any) -> str:
    """Neutralize spreadsheet formula injection in an exported CSV cell.

    A leading ``=``, ``+``, ``-`` or ``@`` (or a leading tab/carriage return)
    is prefixed with a single quote so spreadsheets render the value as text.
    """
    text = "" if value is None else str(value)
    if text[:1] in CSV_INJECTION_PREFIXES:
        return f"'{text}"
    return text


def questions_csv_document(questions: List[Question]) -> str:
    """Render questions as a properly quoted CSV document."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_EXPORT_COLUMNS)
    for question in questions:
        writer.writerow([sanitize_csv_cell(getattr(question, column, "")) for column in CSV_EXPORT_COLUMNS])
    return buffer.getvalue()


def questions_json_chunks(questions: List[Question]) -> Iterator[str]:
    """Yield a JSON array of questions one serialized element at a time.

    Streaming keeps memory flat for large banks and still produces a single
    valid JSON document.
    """
    yield "["
    for index, question in enumerate(questions):
        serialized = QuestionSchema.model_validate(question).model_dump_json()
        yield f"{'' if index == 0 else ','}{serialized}"
    yield "]"


def format_validation_error(exc: ValidationError) -> str:
    """Flatten a Pydantic validation error into one readable message."""
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc']) or 'entry'}: {error['msg']}" for error in exc.errors()
    )


@router.post("/generate", response_model=List[QuestionSchema], status_code=status.HTTP_201_CREATED)
async def generate_questions(
    request: QuestionGenerateRequest,
    db: Session = Depends(get_db),
    gemini_service: GeminiService = Depends(get_gemini_service),
    current_user: User = Depends(get_current_user),
):
    """Generate new interview questions using AI

    Args:
        request: Contains job_title, count, question_type, and optional company
        db: Database session dependency
        gemini_service: Lazily-initialized Gemini service
        current_user: Authenticated user

    Returns:
        List of generated Question objects saved to database

    Raises:
        HTTPException 400: If request parameters are invalid
        HTTPException 401: If the caller is not authenticated
        HTTPException 500: If generation or database operations fail
        HTTPException 503: If AI service is unavailable
    """
    try:
        if not request.job_title or not request.job_title.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="job_title cannot be empty")

        if request.count < 1 or request.count > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="count must be between 1 and 100")

        # Call Gemini AI service to generate interview questions based on parameters
        generated_questions = gemini_service.generate_questions(
            job_title=request.job_title, count=request.count, question_type=request.question_type
        )

        if not generated_questions:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI service failed to generate questions"
            )

        # Save each generated question to the database
        saved_questions = []
        for q_data in generated_questions:
            q_data["user_id"] = current_user.id
            # Company mode: tag the whole batch with the requested company.
            q_data["company"] = request.company
            question = Question(**q_data)  # Create ORM object from dict
            db.add(question)
            db.commit()  # Commit each question individually
            db.refresh(question)  # Refresh to get auto-generated values like ID
            saved_questions.append(question)

        # Track generation in user history
        if saved_questions:
            record_action(
                db,
                action="generated",
                user_id=current_user.id,
                context={
                    "job_title": request.job_title,
                    "question_type": request.question_type,
                    "company": request.company,
                    "count": len(saved_questions),
                    "question_ids": [q.id for q in saved_questions],
                },
            )

        return saved_questions

    except HTTPException:
        db.rollback()
        raise
    except GeminiServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"AI service unavailable: {str(e)}")
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        # Rollback transaction on error to maintain database integrity
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate questions: {str(e)}"
        )


@router.get("/", response_model=List[QuestionSchema], status_code=status.HTTP_200_OK)
async def get_questions(
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination", title="Pagination Offset"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return (max 1000)", title="Pagination Limit"
    ),
    q: Optional[str] = Query(
        None,
        max_length=200,
        description="Free-text search across question text, job title, and tags",
        title="Search Query",
    ),
    job_title: Optional[str] = Query(
        None, description="Filter by job title (case-insensitive partial match)", title="Job Title Filter"
    ),
    question_type: Optional[str] = Query(
        None, description="Filter by question type: 'technical' or 'behavioral'", title="Question Type Filter"
    ),
    flagged_only: bool = Query(
        False, description="If True, return only flagged questions", title="Flagged Questions Only"
    ),
    company: Optional[str] = Query(
        None,
        max_length=100,
        description="Filter by company (case-insensitive partial match)",
        title="Company Filter",
    ),
    db: Session = Depends(get_db),
):
    """Get questions with filtering, full-text search, and pagination options

    Returns a paginated list of questions with optional filtering by job title,
    type, company, and flagged status. When ``q`` is provided the search runs
    against ``question_text``, ``job_title`` and ``tags`` using Postgres
    full-text search (ordered by relevance) or an ILIKE fallback on other
    dialects (ordered by ``created_at``).

    Args:
        skip: Number of records to skip (pagination offset)
        limit: Maximum number of records to return
        q: Free-text search term; blank values fall through to the normal list
        job_title: Case-insensitive partial job-title filter
        question_type: Exact question-type filter
        flagged_only: Return only flagged questions
        company: Case-insensitive partial company filter
        db: Database session dependency

    Returns:
        List of Question objects matching the filters

    Raises:
        HTTPException 400: If pagination or filter parameters are invalid
        HTTPException 500: If database query fails
    """
    try:
        # Build the base query and apply the shared filters
        query, _ = apply_question_filters(
            db.query(Question),
            dialect_name=db.bind.dialect.name,
            job_title=job_title,
            question_type=question_type,
            flagged_only=flagged_only,
            q=q,
            company=company,
        )

        # Execute query with pagination
        questions = query.offset(skip).limit(limit).all()
        return questions

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve questions: {str(e)}"
        )


# NOTE: /export and /import are declared before the /{question_id} routes on
# purpose — a dynamic path declared first would swallow them.
@router.get("/export")
async def export_questions(
    format: str = Query("json", description="Export format: 'json' or 'csv'", title="Export Format"),
    q: Optional[str] = Query(
        None,
        max_length=200,
        description="Free-text search across question text, job title, and tags",
        title="Search Query",
    ),
    job_title: Optional[str] = Query(
        None, description="Filter by job title (case-insensitive partial match)", title="Job Title Filter"
    ),
    question_type: Optional[str] = Query(
        None, description="Filter by question type: 'technical' or 'behavioral'", title="Question Type Filter"
    ),
    flagged_only: bool = Query(
        False, description="If True, export only flagged questions", title="Flagged Questions Only"
    ),
    company: Optional[str] = Query(
        None,
        max_length=100,
        description="Filter by company (case-insensitive partial match)",
        title="Company Filter",
    ),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export questions as a downloadable JSON or CSV file

    Streams the questions reachable with the existing visibility model (all
    questions are shared in this app) using the same filters as the list
    endpoint. CSV cells starting with ``=``, ``+``, ``-`` or ``@`` are
    prefixed with a single quote to prevent spreadsheet formula injection.

    Args:
        format: 'json' or 'csv'
        q: Optional free-text search term
        job_title: Optional case-insensitive partial job-title filter
        question_type: Optional exact question-type filter
        flagged_only: Export only flagged questions
        company: Optional case-insensitive partial company filter
        db: Database session dependency

    Returns:
        A StreamingResponse with the file as an attachment

    Raises:
        HTTPException 400: If format is not 'json' or 'csv', or a filter is invalid
        HTTPException 500: If the database query fails
    """
    export_format = (format or "").strip().lower()
    if export_format not in EXPORT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="format must be 'json' or 'csv'",
        )

    try:
        query, _ = apply_question_filters(
            db.query(Question),
            dialect_name=db.bind.dialect.name,
            job_title=job_title,
            question_type=question_type,
            flagged_only=flagged_only,
            q=q,
            company=company,
        )
        questions = query.all()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to export questions: {str(e)}"
        )

    headers = {"Content-Disposition": f'attachment; filename="questions.{export_format}"'}

    if export_format == "csv":
        return StreamingResponse(
            iter([questions_csv_document(questions)]),
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )

    return StreamingResponse(
        questions_json_chunks(questions),
        media_type="application/json",
        headers=headers,
    )


@router.post("/import")
async def import_questions(
    payload: List[Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import questions from a JSON array

    Each entry is validated independently against ``QuestionCreate``; invalid
    entries are skipped and reported instead of failing the whole batch.

    Args:
        payload: JSON array of question objects (``QuestionCreate`` shape)
        db: Database session dependency
        current_user: Authenticated user

    Returns:
        Summary dict with ``imported``, ``skipped`` and per-entry ``errors``

    Raises:
        HTTPException 400: If the payload is empty
        HTTPException 401: If the caller is not authenticated
        HTTPException 422: If the body is not a JSON array
        HTTPException 500: If the batch cannot be committed
    """
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payload must contain at least one question",
        )

    imported = 0
    skipped = 0
    errors: List[Dict[str, Any]] = []

    for index, entry in enumerate(payload):
        # Validate the entry on its own so one bad record cannot reject the batch.
        try:
            if not isinstance(entry, dict):
                raise ValueError("entry must be a JSON object")
            data = QuestionCreate.model_validate(entry).model_dump()
            data["user_id"] = current_user.id
            question = Question(**data)
        except ValidationError as exc:
            skipped += 1
            errors.append({"index": index, "error": format_validation_error(exc)})
            continue
        except ValueError as exc:
            skipped += 1
            errors.append({"index": index, "error": str(exc)})
            continue

        # A savepoint keeps a database-level failure scoped to this entry.
        try:
            with db.begin_nested():
                db.add(question)
                db.flush()
            imported += 1
        except (IntegrityError, ValueError) as exc:
            skipped += 1
            errors.append({"index": index, "error": str(getattr(exc, "orig", None) or exc)})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to import questions: {str(e)}"
        )

    # Track the import in user history
    if imported:
        record_action(
            db,
            action="created",
            user_id=current_user.id,
            context={"source": "import", "count": imported},
        )

    return {"imported": imported, "skipped": skipped, "errors": errors}


@router.get("/companies/", response_model=List[str], status_code=status.HTTP_200_OK)
async def get_companies(db: Session = Depends(get_db)):
    """Get all distinct companies

    Retrieves a sorted list of the distinct non-empty companies tagged on
    questions in the database. Useful for the company filter dropdown.

    NOTE: like ``/export``, ``/import`` and ``/job-titles/``, this static path
    is declared ahead of the ``/{question_id}`` route so the dynamic route
    cannot swallow it.

    Args:
        db: Database session dependency

    Returns:
        List of unique company strings

    Raises:
        HTTPException 500: If database query fails
    """
    try:
        companies = (
            db.query(Question.company)
            .filter(Question.company.isnot(None))
            .filter(Question.company != "")
            .distinct()
            .order_by(Question.company)
            .all()
        )
        return [company[0] for company in companies if company[0]]

    except Exception:
        logger.exception("Failed to retrieve companies")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/{question_id}", response_model=QuestionSchema, status_code=status.HTTP_200_OK)
async def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
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
                status_code=status.HTTP_400_BAD_REQUEST, detail="question_id must be a positive integer"
            )

        # Query for specific question by ID
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            # Return 404 if question not found
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with ID {question_id} not found"
            )
        # Track the view in user history
        if current_user:
            record_action(db, action="viewed", user_id=current_user.id, question_id=question.id)
        return question

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve question: {str(e)}"
        )


@router.post("/", response_model=QuestionSchema, status_code=status.HTTP_201_CREATED)
async def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new question manually

    Creates a new question in the database with the provided data.

    Args:
        question: Pydantic model containing question data
        db: Database session dependency
        current_user: Authenticated user

    Returns:
        Created Question object with database-generated ID and timestamps

    Raises:
        HTTPException 400: If question data is invalid or incomplete
        HTTPException 401: If the caller is not authenticated
        HTTPException 409: If duplicate question exists
        HTTPException 500: If database operation fails
    """
    try:
        # Validate question data
        if not question.question_text or not question.question_text.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="question_text cannot be empty")

        if question.question_type not in ["technical", "behavioral", "mixed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_type must be 'technical', 'behavioral', or 'mixed'",
            )

        if question.difficulty and (question.difficulty < 1 or question.difficulty > 5):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="difficulty must be between 1 and 5")

        # Convert Pydantic model to dictionary and create ORM object
        data = question.model_dump()
        data["user_id"] = current_user.id
        db_question = Question(**data)
        # Add to session and commit to database
        db.add(db_question)
        db.commit()
        # Refresh to get auto-generated values
        db.refresh(db_question)
        # Track creation in user history
        record_action(db, action="created", user_id=current_user.id, question_id=db_question.id)
        return db_question

    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data: {str(e)}")
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create question: {str(e)}"
        )


@router.put("/{question_id}", response_model=QuestionSchema, status_code=status.HTTP_200_OK)
async def update_question(
    question_id: int,
    question_update: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing question

    Partially or fully updates a question. Only provided fields are updated.

    Args:
        question_id: The unique identifier of the question to update
        question_update: Pydantic model with fields to update
        db: Database session dependency
        current_user: Authenticated user

    Returns:
        Updated Question object with new values

    Raises:
        HTTPException 400: If question_id is invalid or update data is invalid
        HTTPException 401: If the caller is not authenticated
        HTTPException 404: If question not found
        HTTPException 500: If update operation fails
    """
    try:
        # Validate question_id
        if question_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="question_id must be a positive integer"
            )

        # First check if the question exists
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with ID {question_id} not found"
            )

        # Validate update data
        update_data = question_update.model_dump(exclude_unset=True)

        if "difficulty" in update_data and update_data["difficulty"]:
            if update_data["difficulty"] < 1 or update_data["difficulty"] > 5:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="difficulty must be between 1 and 5"
                )

        # Update only the fields that were provided
        for field, value in update_data.items():
            setattr(question, field, value)

        # Commit changes to database
        db.commit()
        # Refresh to get updated values
        db.refresh(question)
        # Track flag changes in user history
        if "is_flagged" in update_data:
            record_action(
                db,
                action="flagged",
                user_id=current_user.id,
                question_id=question.id,
                context={"is_flagged": question.is_flagged},
            )
        return question

    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data: {str(e)}")
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update question: {str(e)}"
        )


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a question

    Permanently removes a question from the database.

    Args:
        question_id: The unique identifier of the question to delete
        db: Database session dependency
        current_user: Authenticated user

    Returns:
        No content on success

    Raises:
        HTTPException 400: If question_id is invalid
        HTTPException 401: If the caller is not authenticated
        HTTPException 404: If question not found
        HTTPException 500: If delete operation fails
    """
    try:
        # Validate question_id
        if question_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="question_id must be a positive integer"
            )

        # First check if the question exists
        question = db.query(Question).filter(Question.id == question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with ID {question_id} not found"
            )

        # Track deletion in user history before removing
        record_action(db, action="deleted", user_id=current_user.id, question_id=question.id)
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete question: {str(e)}"
        )


@router.post("/sets", response_model=QuestionSetSchema, status_code=status.HTTP_201_CREATED)
async def create_question_set(
    question_set: QuestionSetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new question set

    Creates a collection of questions under a single set for organized management.

    Args:
        question_set: Pydantic model containing set data and question IDs
        db: Database session dependency
        current_user: Authenticated user

    Returns:
        Created QuestionSet object with database-generated ID and timestamps

    Raises:
        HTTPException 400: If set data is invalid or question IDs are invalid
        HTTPException 401: If the caller is not authenticated
        HTTPException 404: If one or more question IDs don't exist
        HTTPException 500: If database operation fails
    """
    try:
        # Validate set data
        if not question_set.name or not question_set.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name cannot be empty")

        if not question_set.job_title or not question_set.job_title.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="job_title cannot be empty")

        if not question_set.question_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="question_ids list cannot be empty")

        # Verify all question IDs exist
        for q_id in question_set.question_ids:
            question = db.query(Question).filter(Question.id == q_id).first()
            if not question:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with ID {q_id} not found")

        # Convert question IDs list to JSON string for storage
        question_ids_json = json.dumps(question_set.question_ids)
        # Create new QuestionSet object
        db_set = QuestionSet(
            name=question_set.name,
            description=question_set.description,
            job_title=question_set.job_title,
            question_ids=question_ids_json,  # Store as JSON string in database
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data: {str(e)}")
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create question set: {str(e)}"
        )


@router.get("/sets/", response_model=List[QuestionSetSchema], status_code=status.HTTP_200_OK)
async def get_question_sets(
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination", title="Pagination Offset"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return (max 1000)", title="Pagination Limit"
    ),
    db: Session = Depends(get_db),
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve question sets: {str(e)}"
        )


@router.post("/rate", response_model=UserRatingSchema, status_code=status.HTTP_201_CREATED)
async def rate_question(
    rating: UserRatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rate a question

    Allows users to provide ratings and feedback for questions.

    Args:
        rating: Pydantic model containing rating data (question_id, rating_value)
        db: Database session dependency
        current_user: Authenticated user

    Returns:
        Created UserRating object with database-generated ID and timestamp

    Raises:
        HTTPException 400: If rating data is invalid
        HTTPException 401: If the caller is not authenticated
        HTTPException 404: If question doesn't exist
        HTTPException 500: If database operation fails
    """
    try:
        # Verify question exists
        question = db.query(Question).filter(Question.id == rating.question_id).first()
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with ID {rating.question_id} not found"
            )

        # Validate rating value
        if rating.rating < 1.0 or rating.rating > 5.0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rating must be between 1.0 and 5.0")

        # Create new UserRating object from request data
        db_rating = UserRating(**rating.model_dump())
        # Add to session and commit to database
        db.add(db_rating)
        db.commit()
        # Refresh to get auto-generated values
        db.refresh(db_rating)
        # Track rating in user history
        record_action(
            db,
            action="rated",
            user_id=current_user.id,
            question_id=rating.question_id,
            context={"rating": db_rating.rating},
        )
        return db_rating

    except HTTPException:
        db.rollback()
        raise
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data: {str(e)}")
    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to rate question: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve job titles: {str(e)}"
        )

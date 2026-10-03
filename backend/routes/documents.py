"""Document upload and analysis routes (resume / job description)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User, UserDocument
from schemas import (
    UserDocumentResponse,
    SkillGapResponse,
)
from services import document_service

router = APIRouter()


@router.post("/upload", response_model=UserDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document_type: str = Query(..., regex="^(resume|jd)$"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a resume or job description (PDF, DOCX, or TXT)."""
    filename = file.filename or "document"
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    text = document_service.extract_text(filename, file_bytes)
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract text from the file. Use a text-based PDF, DOCX, or TXT.",
        )

    if document_type == "resume":
        parsed = document_service.parse_resume(text)
    else:
        parsed = document_service.parse_job_description(text)

    doc = UserDocument(
        user_id=current_user.id,
        document_type=document_type,
        filename=filename,
        content_text=text,
        parsed_metadata=parsed,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return UserDocumentResponse.model_validate(doc)


@router.get("/", response_model=list[UserDocumentResponse], status_code=status.HTTP_200_OK)
async def list_documents(
    document_type: Optional[str] = Query(None, regex="^(resume|jd)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's uploaded documents."""
    query = db.query(UserDocument).filter(UserDocument.user_id == current_user.id)
    if document_type:
        query = query.filter(UserDocument.document_type == document_type)
    return [UserDocumentResponse.model_validate(d) for d in query.order_by(UserDocument.created_at.desc()).all()]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document."""
    doc = db.query(UserDocument).filter(UserDocument.id == document_id, UserDocument.user_id == current_user.id).first()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    db.delete(doc)
    db.commit()


@router.post("/skill-gap", response_model=SkillGapResponse, status_code=status.HTTP_200_OK)
async def compute_skill_gap(
    resume_id: int = Query(..., gt=0, description="Resume document ID"),
    jd_id: int = Query(..., gt=0, description="Job description document ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare a resume against a job description and surface skill gaps."""
    resume = (
        db.query(UserDocument).filter(UserDocument.id == resume_id, UserDocument.user_id == current_user.id).first()
    )
    jd = db.query(UserDocument).filter(UserDocument.id == jd_id, UserDocument.user_id == current_user.id).first()
    if resume is None or jd is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Both resume_id and jd_id must reference your documents",
        )

    resume_meta = resume.parsed_metadata or document_service.parse_resume(resume.content_text)
    jd_meta = jd.parsed_metadata or document_service.parse_job_description(jd.content_text)
    gap = document_service.compute_skill_gap(resume_meta, jd_meta)
    return SkillGapResponse(**gap)

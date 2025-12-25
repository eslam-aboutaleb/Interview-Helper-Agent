from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from dotenv import load_dotenv
import logging

from database import get_db, engine
from models import Base
from routes import questions, stats
from services.gemini_service import GeminiService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Create FastAPI app first (faster than table creation)
app = FastAPI(
    title="Interview Prep Platform",
    description="AI-powered interview question generation and management platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:80", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy initialization flags
_db_initialized = False
_gemini_service = None

def ensure_db_initialized():
    """Initialize database tables on first use (lazy initialization)"""
    global _db_initialized
    if not _db_initialized:
        try:
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            _db_initialized = True
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

def get_gemini_service():
    """Get or initialize Gemini service lazily"""
    global _gemini_service
    if _gemini_service is None:
        try:
            logger.info("Initializing Gemini service...")
            _gemini_service = GeminiService()
            logger.info("Gemini service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {e}")
            raise
    return _gemini_service

# Include routers
app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

@app.on_event("startup")
async def startup_event():
    """Initialize critical resources after app starts"""
    try:
        ensure_db_initialized()
        logger.info("Startup event completed successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")

@app.get("/")
async def root():
    return {"message": "Interview Prep Platform API", "version": "1.0.0"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Fast health check without heavy operations"""
    try:
        # Use text() for explicit SQL
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
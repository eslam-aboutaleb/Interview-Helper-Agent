from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from dotenv import load_dotenv
import logging

from database import get_db, engine
from models import Base
from routes import questions, stats, auth, documents, interviews, admin, learning

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def ensure_db_initialized() -> None:
    """Initialize database tables on first use (lazy initialization).

    This is a development fallback. In production, schema changes are
    managed with Alembic migrations (``alembic upgrade head``); this
    ``create_all`` call only ensures tables exist when migrations have
    not been run (e.g. local development against a fresh database).
    """
    try:
        logger.info(
            "Ensuring database tables exist (create_all fallback; "
            "use 'alembic upgrade head' for managed schema changes)..."
        )
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables ensured successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # Startup
    try:
        ensure_db_initialized()
        logger.info("Startup event completed successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")
    yield
    # Shutdown
    logger.info("Application shutting down")


# Create FastAPI app first (faster than table creation)
app = FastAPI(
    title="Interview Prep Platform",
    description="AI-powered interview question generation and management platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - origins configurable via environment
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:80,http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(interviews.router, prefix="/api/interviews", tags=["interviews"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(learning.router, prefix="/api/learning", tags=["learning"])


@app.get("/")
async def root():
    return {"message": "Interview Prep Platform API", "version": "1.0.0"}


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Fast health check without heavy operations."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

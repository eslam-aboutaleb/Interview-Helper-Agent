from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import get_db, engine
from models import Base
from routes import questions, stats
from services.gemini_service import GeminiService

# Load environment variables
load_dotenv()

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Interview Prep Platform",
    description="AI-powered interview question generation and management platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini service
gemini_service = GeminiService()

# Include routers
app.include_router(questions.router, prefix="/api/questions", tags=["questions"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])

@app.get("/")
async def root():
    return {"message": "Interview Prep Platform API", "version": "1.0.0"}

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
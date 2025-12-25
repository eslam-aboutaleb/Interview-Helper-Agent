from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/interview_prep")

# Optimize connection pool for better performance
engine = create_engine(
    DATABASE_URL,
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Max overflow connections
    pool_pre_ping=True,  # Test connections before using (avoid stale connections)
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False,  # Disable SQL logging for performance
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
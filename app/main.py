from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import get_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for AI-powered workout planning, nutrition tracking, and analytics.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies API responsiveness and database connectivity.
    Executes 'SELECT 1' against PostgreSQL.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}",
        )

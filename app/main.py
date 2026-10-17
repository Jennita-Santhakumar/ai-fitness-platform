from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.workouts import router as workouts_router
from app.api.sessions import router as sessions_router
from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import PlanGenerationError

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for AI-powered workout planning, nutrition tracking, and analytics.",
    version="0.1.0",
)

# Exception Handlers
@app.exception_handler(PlanGenerationError)
async def plan_generation_exception_handler(request: Request, exc: PlanGenerationError):
    """Maps custom PlanGenerationError to HTTP 502 Bad Gateway."""
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "detail": exc.message,
            "errors": exc.details.get("errors", []),
        },
    )

# Include API Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(workouts_router)
app.include_router(sessions_router)


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

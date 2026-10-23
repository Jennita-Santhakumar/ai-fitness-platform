from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.workouts import router as workouts_router
from app.api.sessions import router as sessions_router
from app.api.plans import router as plans_router
from app.api.tasks import router as tasks_router
from app.api.briefings import router as briefings_router
from app.api.reviews import router as reviews_router
from app.api.strava import router as strava_router
from app.api.nutrition import router as nutrition_router
from app.core.config import settings
from app.core.db import get_db
from app.core.exceptions import PlanGenerationError

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for AI-powered workout planning, nutrition tracking, and analytics.",
    version="0.1.0",
)

# CORS Configuration (Milestone 4, Day 26)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(plans_router)
app.include_router(tasks_router)
app.include_router(briefings_router)
app.include_router(reviews_router)
app.include_router(strava_router)
app.include_router(nutrition_router)


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

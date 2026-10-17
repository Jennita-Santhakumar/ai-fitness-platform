from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.llm.resilience import generate_plan_with_failover
from app.models.plan import PlanRecord
from app.models.user import User
from app.schemas.plan_record import PlanGenerateRequest, PlanRecordRead

router = APIRouter(prefix="/plans", tags=["Workout Plans"])


@router.post(
    "/generate",
    response_model=PlanRecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate and persist a customized workout plan using AI",
    description="Invokes the LLM failover engine to generate a multi-week plan, then persists the plan record.",
)
def generate_workout_plan(
    request: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates an AI workout plan with failover and stores it in the database."""
    inputs = request.model_dump()
    plan, provider_name, _ = generate_plan_with_failover(inputs=inputs)

    plan_record = PlanRecord(
        user_id=current_user.id,
        inputs=inputs,
        plan=plan.model_dump(),
        provider=provider_name,
        is_active=False,
    )
    db.add(plan_record)
    db.commit()
    db.refresh(plan_record)

    return plan_record


@router.get(
    "",
    response_model=List[PlanRecordRead],
    summary="List all generated plans for the authenticated user",
)
def list_plans(
    limit: int = Query(default=10, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Items to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve paginated plans owned by current user."""
    plans = (
        db.query(PlanRecord)
        .filter(PlanRecord.user_id == current_user.id)
        .order_by(PlanRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return plans


@router.get(
    "/{plan_id}",
    response_model=PlanRecordRead,
    summary="Get a specific plan by ID",
)
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a specific plan by ID with strict ownership validation."""
    plan_record = (
        db.query(PlanRecord)
        .filter(PlanRecord.id == plan_id, PlanRecord.user_id == current_user.id)
        .first()
    )
    if not plan_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )
    return plan_record

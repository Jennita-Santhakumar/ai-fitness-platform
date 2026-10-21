from fastapi import APIRouter, Depends, status
from celery.result import AsyncResult

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.tasks import TaskStatusResponse
from app.worker import celery_app

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


@router.get(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get status of a background task",
    description="Polls Celery result backend for the current status and output of an asynchronous job.",
)
def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Checks the status of a Celery background task by task_id.
    
    States returned:
    - 'pending': waiting in broker queue or unstarted
    - 'started': currently being processed by a worker
    - 'success': completed successfully, returning plan_id and provider
    - 'failure': failed with an exception, returning the error details
    """
    async_result = AsyncResult(task_id, app=celery_app)
    state = async_result.state

    if state == "SUCCESS":
        result_data = async_result.result or {}
        if isinstance(result_data, dict):
            return TaskStatusResponse(
                task_id=task_id,
                status="success",
                plan_id=result_data.get("plan_id"),
                provider=result_data.get("provider"),
            )
        return TaskStatusResponse(
            task_id=task_id,
            status="success",
        )
    elif state in ("FAILURE", "REVOKED"):
        return TaskStatusResponse(
            task_id=task_id,
            status="failure",
            error=str(async_result.result),
        )
    elif state in ("PENDING", "RECEIVED"):
        return TaskStatusResponse(
            task_id=task_id,
            status="pending",
        )
    else:
        return TaskStatusResponse(
            task_id=task_id,
            status="started",
        )

from typing import Optional
from pydantic import BaseModel


class TaskInitResponse(BaseModel):
    """Returned immediately upon queuing a background job."""
    task_id: str
    status: str = "pending"


class TaskStatusResponse(BaseModel):
    """Returned when polling the status of a background job."""
    task_id: str
    status: str
    plan_id: Optional[int] = None
    provider: Optional[str] = None
    error: Optional[str] = None

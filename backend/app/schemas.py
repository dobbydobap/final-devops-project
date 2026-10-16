from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Status = Literal["PENDING", "IN_PROGRESS", "SUBMITTED"]
Priority = Literal["LOW", "MEDIUM", "HIGH"]

class AssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    course: str = Field(min_length=1, max_length=120)
    notes: str = ""
    due_date: date | None = None
    priority: Priority = "MEDIUM"
    status: Status = "PENDING"

class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    course: str | None = Field(default=None, min_length=1, max_length=120)
    notes: str | None = None
    due_date: date | None = None
    priority: Priority | None = None
    status: Status | None = None

class AssignmentOut(AssignmentCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class StatsOut(BaseModel):
    total: int
    pending: int
    inProgress: int
    submitted: int
    overdue: int

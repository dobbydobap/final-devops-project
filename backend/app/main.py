from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .db import Base, engine, get_db
from .models import Assignment
from .schemas import AssignmentCreate, AssignmentOut, AssignmentUpdate, StatsOut

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Production containers run Alembic before Uvicorn; create_all keeps local runs self-contained.
    # (on_event was removed in Starlette 1.0, so this uses the lifespan handler instead.)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

def get_or_404(db: Session, assignment_id: int) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment

@app.get("/")
def root():
    return {"service": settings.app_name, "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "UP"}

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(select(func.count(Assignment.id)))
    return {"status": "READY"}

@app.get("/api/assignments", response_model=list[AssignmentOut])
def list_assignments(course: str | None = None, db: Session = Depends(get_db)):
    # Soonest deadline first; assignments without a due date go to the end.
    query = select(Assignment).order_by(Assignment.due_date.is_(None), Assignment.due_date, Assignment.id.desc())
    if course:
        query = query.where(Assignment.course == course)
    return list(db.scalars(query))

@app.get("/api/assignments/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    rows = db.execute(select(Assignment.status, func.count(Assignment.id)).group_by(Assignment.status)).all()
    counts = {status: count for status, count in rows}
    overdue = db.scalar(
        select(func.count(Assignment.id)).where(Assignment.due_date < date.today(), Assignment.status != "SUBMITTED")
    )
    return StatsOut(
        total=sum(counts.values()),
        pending=counts.get("PENDING", 0),
        inProgress=counts.get("IN_PROGRESS", 0),
        submitted=counts.get("SUBMITTED", 0),
        overdue=overdue or 0,
    )

@app.get("/api/assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment(assignment_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, assignment_id)

@app.post("/api/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: AssignmentCreate, db: Session = Depends(get_db)):
    assignment = Assignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

@app.put("/api/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(assignment_id: int, payload: AssignmentUpdate, db: Session = Depends(get_db)):
    assignment = get_or_404(db, assignment_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(assignment, key, value)
    db.commit()
    db.refresh(assignment)
    return assignment

@app.delete("/api/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    assignment = get_or_404(db, assignment_id)
    db.delete(assignment)
    db.commit()

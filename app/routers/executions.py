from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db

router = APIRouter(prefix="/executions", tags=["executions"])


@router.post("", response_model=schemas.SessionExecutionOut)
def upsert_execution(payload: schemas.SessionExecutionUpsert, db: Session = Depends(get_db)):
    user = db.get(models.User, payload.user_id)
    if not user:
        raise HTTPException(404, "user not found")

    planned_session = db.get(models.PlannedSession, payload.planned_session_id)
    if not planned_session:
        raise HTTPException(404, "planned session not found")

    execution = (
        db.query(models.SessionExecution)
        .filter(
            models.SessionExecution.user_id == payload.user_id,
            models.SessionExecution.planned_session_id == payload.planned_session_id,
        )
        .first()
    )

    if not execution:
        execution = models.SessionExecution(**payload.model_dump())
        db.add(execution)
    else:
        execution.status = payload.status
        execution.completed_distance_km = payload.completed_distance_km
        execution.duration_sec = payload.duration_sec
        execution.rpe = payload.rpe
        execution.notes = payload.notes

    db.commit()
    db.refresh(execution)
    return execution


@router.get("/plan/{plan_id}")
def plan_completion(plan_id: UUID, user_id: UUID, db: Session = Depends(get_db)):
    sessions = db.query(models.PlannedSession).filter(models.PlannedSession.plan_id == plan_id).all()
    if not sessions:
        raise HTTPException(404, "plan not found or no sessions")

    session_ids = [s.id for s in sessions]

    executions = (
        db.query(models.SessionExecution)
        .filter(
            models.SessionExecution.user_id == user_id,
            models.SessionExecution.planned_session_id.in_(session_ids),
        )
        .all()
    )

    done_count = sum(1 for e in executions if e.status == "done")
    completion_rate = round(done_count / len(sessions), 2) if sessions else 0.0

    return {
        "ok": True,
        "plan_id": str(plan_id),
        "user_id": str(user_id),
        "total_sessions": len(sessions),
        "logged_sessions": len(executions),
        "done_sessions": done_count,
        "completion_rate": completion_rate,
    }

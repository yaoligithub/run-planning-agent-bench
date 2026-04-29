from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.db import get_db
from app.planner import compute_target_volume, generate_sessions

router = APIRouter(prefix="/plans", tags=["plans"])


def _to_unit(km: float | None, unit: Literal["km", "mi"]) -> float | None:
    if km is None:
        return None
    if unit == "mi":
        return round(km * 0.621371, 2)
    return round(km, 2)


def _elev_to_unit(elev_m: int | None, unit: Literal["km", "mi"]) -> float | None:
    if elev_m is None:
        return None
    if unit == "mi":
        return round(float(elev_m) * 3.28084, 1)
    return round(float(elev_m), 1)


def _serialize_plan(plan: models.TrainingPlan, unit: Literal["km", "mi"] = "km"):
    sessions = sorted(plan.sessions, key=lambda s: s.session_date)
    return {
        "id": str(plan.id),
        "user_id": str(plan.user_id),
        "goal_id": str(plan.goal_id) if plan.goal_id else None,
        "week_start": plan.week_start,
        "week_end": plan.week_end,
        "planned_volume_km": float(plan.planned_volume_km),
        "planned_volume": _to_unit(float(plan.planned_volume_km), unit),
        "volume_unit": unit,
        "rationale": plan.rationale,
        "sessions": [
            {
                "session_date": s.session_date,
                "session_type": s.session_type,
                "target_distance_km": float(s.target_distance_km) if s.target_distance_km is not None else None,
                "target_distance": _to_unit(float(s.target_distance_km), unit)
                if s.target_distance_km is not None
                else None,
                "distance_unit": unit,
                "target_hr_zone": s.target_hr_zone,
                "target_elevation_gain_m": s.target_elevation_gain_m,
                "target_elevation_gain": _elev_to_unit(s.target_elevation_gain_m, unit),
                "elevation_unit": "ft" if unit == "mi" else "m",
                "notes": s.notes,
            }
            for s in sessions
        ],
    }


def _derive_inputs_from_recent_4w(
    db: Session,
    user_id,
    weekly_days: int,
    week_start,
):
    end_dt = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)
    start_dt = end_dt - timedelta(days=28)

    activities = (
        db.query(models.Activity)
        .filter(
            models.Activity.user_id == user_id,
            models.Activity.started_at >= start_dt,
            models.Activity.started_at < end_dt,
        )
        .all()
    )

    if not activities:
        return None

    total_km_4w = sum((a.distance_m or 0) for a in activities) / 1000
    total_elev_m_4w = sum((a.elevation_gain_m or 0) for a in activities)
    weekly_km = round(max(total_km_4w / 4, 1.0), 1)

    runs_per_week = len(activities) / 4
    compliance = round(min(1.0, runs_per_week / max(weekly_days, 1)), 2)

    last7_start = end_dt - timedelta(days=7)
    last7_km = sum((a.distance_m or 0) for a in activities if a.started_at >= last7_start) / 1000
    ratio = (last7_km / weekly_km) if weekly_km > 0 else 1.0

    elev_per_km = (total_elev_m_4w / total_km_4w) if total_km_4w > 0 else 0.0

    if ratio >= 1.4:
        fatigue = 7
    elif ratio >= 1.2:
        fatigue = 5
    else:
        fatigue = 3

    # Hill load adjustment: sustained climbing load should bias toward conservatism.
    if elev_per_km >= 30:
        fatigue = min(10, fatigue + 2)
    elif elev_per_km >= 20:
        fatigue = min(10, fatigue + 1)

    recent7_elev_m = sum((a.elevation_gain_m or 0) for a in activities if a.started_at >= last7_start)
    weekly_elev_baseline_m = int(round(total_elev_m_4w / 4.0)) if total_elev_m_4w > 0 else 0
    # weekly climb cap: 28d weekly baseline * 1.2, and if last 7d already high, tighten to *1.05
    cap_factor = 1.05 if (weekly_elev_baseline_m > 0 and recent7_elev_m > weekly_elev_baseline_m * 1.25) else 1.2
    weekly_elev_cap_m = int(round(weekly_elev_baseline_m * cap_factor)) if weekly_elev_baseline_m > 0 else None

    source_text = (
        f"auto-derived from last 4w ({len(activities)} runs, {round(total_km_4w, 1)} km, "
        f"elev {int(round(total_elev_m_4w, 0))} m, {round(elev_per_km, 1)} m/km, "
        f"7d elev {int(round(recent7_elev_m,0))} m)"
    )
    return weekly_km, compliance, fatigue, source_text, weekly_elev_cap_m


@router.post("/generate", response_model=schemas.PlanOut)
def generate_plan(payload: schemas.PlanGenerateIn, db: Session = Depends(get_db)):
    goal = db.get(models.TrainingGoal, payload.goal_id)
    if not goal:
        raise HTTPException(404, "goal not found")

    derived = None
    if payload.auto_derive_inputs:
        derived = _derive_inputs_from_recent_4w(db, payload.user_id, goal.weekly_days, payload.week_start)

    if derived:
        base_volume_km, compliance, fatigue_score, source_text, weekly_elev_cap_m = derived
    else:
        source_text = "manual/default inputs"
        manual_base = payload.base_volume_km if payload.base_volume_km is not None else 30.0
        base_volume_km = manual_base * 1.60934 if payload.distance_unit == "mi" else manual_base
        compliance = payload.compliance if payload.compliance is not None else 0.8
        fatigue_score = payload.fatigue_score if payload.fatigue_score is not None else 3
        weekly_elev_cap_m = None

    target_volume, reason = compute_target_volume(
        base_volume_km, compliance, fatigue_score
    )
    reason = f"{reason} | {source_text}"
    if goal.race_elevation_gain_m:
        terrain_mode = "trail" if (goal.goal_type or "") in {"50k", "50mi", "100k", "100mi"} else "road"
        reason += f" | race elevation {int(goal.race_elevation_gain_m)}m | terrain_mode={terrain_mode}"

    plan = models.TrainingPlan(
        user_id=payload.user_id,
        goal_id=payload.goal_id,
        week_start=payload.week_start,
        week_end=payload.week_start + timedelta(days=6),
        planned_volume_km=target_volume,
        rationale=reason,
    )
    db.add(plan)
    db.flush()

    weeks_to_race = None
    if goal.target_date:
        delta_days = (goal.target_date - payload.week_start).days
        weeks_to_race = max(0, delta_days // 7)

    sessions = generate_sessions(
        payload.week_start,
        goal.weekly_days,
        target_volume,
        goal.long_run_day,
        goal.race_elevation_gain_m,
        weeks_to_race,
        weekly_elev_cap_m,
        goal.goal_type,
    )
    for s in sessions:
        db.add(models.PlannedSession(plan_id=plan.id, **s))

    db.commit()

    plan_with_sessions = (
        db.query(models.TrainingPlan)
        .options(joinedload(models.TrainingPlan.sessions))
        .filter(models.TrainingPlan.id == plan.id)
        .first()
    )
    return _serialize_plan(plan_with_sessions, payload.distance_unit)


@router.get("/current", response_model=schemas.PlanOut)
def current_plan(
    user_id: str,
    distance_unit: Literal["km", "mi"] = Query(default="km"),
    week_scope: Literal["latest", "last_week", "this_week", "next_week"] = Query(default="latest"),
    db: Session = Depends(get_db),
):
    q = (
        db.query(models.TrainingPlan)
        .options(joinedload(models.TrainingPlan.sessions))
        .filter(models.TrainingPlan.user_id == user_id)
    )

    if week_scope in {"last_week", "this_week", "next_week"}:
        today = date.today()
        this_monday = today - timedelta(days=today.weekday())
        if week_scope == "last_week":
            target_week_start = this_monday - timedelta(days=7)
        elif week_scope == "this_week":
            target_week_start = this_monday
        else:
            target_week_start = this_monday + timedelta(days=7)
        plan = (
            q.filter(models.TrainingPlan.week_start == target_week_start)
            .order_by(models.TrainingPlan.created_at.desc())
            .first()
        )
    else:
        plan = q.order_by(models.TrainingPlan.week_start.desc(), models.TrainingPlan.created_at.desc()).first()

    if not plan:
        raise HTTPException(404, f"no plan for {week_scope}")
    return _serialize_plan(plan, distance_unit)

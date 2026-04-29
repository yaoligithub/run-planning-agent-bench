from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app import models
from app.planner import compute_target_volume, generate_sessions


def next_monday(d: date) -> date:
    delta = (7 - d.weekday()) % 7
    delta = 7 if delta == 0 else delta
    return d + timedelta(days=delta)


def should_autoplan_now(now_utc: datetime, tz_name: str = "America/Los_Angeles") -> tuple[bool, date]:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/Los_Angeles")
    local_now = now_utc.astimezone(tz)
    # Sunday 20:00+ in target timezone
    return (local_now.weekday() == 6 and local_now.time() >= time(20, 0), local_now.date())


def _derive_inputs_from_recent_4w(db: Session, user_id, weekly_days: int, week_start: date):
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
    weekly_km = round(max(total_km_4w / 4, 1.0), 1)

    runs_per_week = len(activities) / 4
    compliance = round(min(1.0, runs_per_week / max(weekly_days, 1)), 2)

    last7_start = end_dt - timedelta(days=7)
    last7_km = sum((a.distance_m or 0) for a in activities if a.started_at >= last7_start) / 1000
    ratio = (last7_km / weekly_km) if weekly_km > 0 else 1.0

    if ratio >= 1.4:
        fatigue = 7
    elif ratio >= 1.2:
        fatigue = 5
    else:
        fatigue = 3

    return weekly_km, compliance, fatigue


def ensure_next_week_plan_for_goal(db: Session, goal: models.TrainingGoal, week_start: date) -> bool:
    exists = (
        db.query(models.TrainingPlan)
        .filter(models.TrainingPlan.user_id == goal.user_id, models.TrainingPlan.week_start == week_start)
        .first()
    )
    if exists:
        return False

    derived = _derive_inputs_from_recent_4w(db, goal.user_id, goal.weekly_days, week_start)
    if derived:
        base_volume_km, compliance, fatigue_score = derived
        source_text = "auto-scheduled from last 4w"
        weekly_elev_cap_m = None
    else:
        base_volume_km, compliance, fatigue_score = 30.0, 0.8, 3
        source_text = "auto-scheduled default inputs"
        weekly_elev_cap_m = None

    target_volume, reason = compute_target_volume(base_volume_km, compliance, fatigue_score)
    reason = f"{reason} | {source_text}"

    weeks_to_race = None
    if goal.target_date:
        delta_days = (goal.target_date - week_start).days
        weeks_to_race = max(0, delta_days // 7)

    plan = models.TrainingPlan(
        user_id=goal.user_id,
        goal_id=goal.id,
        week_start=week_start,
        week_end=week_start + timedelta(days=6),
        planned_volume_km=target_volume,
        rationale=reason,
    )
    db.add(plan)
    db.flush()

    sessions = generate_sessions(
        week_start,
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
    return True


def run_sunday_autoplan(db: Session, today_local: date) -> int:
    week_start = next_monday(today_local)
    goals = (
        db.query(models.TrainingGoal)
        .filter(models.TrainingGoal.status == "active")
        .order_by(models.TrainingGoal.user_id, models.TrainingGoal.target_date.desc().nullslast())
        .all()
    )

    created = 0
    seen_users = set()
    for g in goals:
        if g.user_id in seen_users:
            continue
        seen_users.add(g.user_id)
        if ensure_next_week_plan_for_goal(db, g, week_start):
            created += 1

    return created

from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.ai_decision import generate_coach_chat_reply, generate_coach_decision
from app.coach_engine import build_weekly_review
from app.db import get_db

router = APIRouter(prefix="/coach", tags=["coach"])


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    idx = (len(ordered) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    frac = idx - lo
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * frac)


def _pick_checkin_for_date(db: Session, user_id: UUID, d: date):
    rows = (
        db.query(models.DailyCheckIn)
        .filter(models.DailyCheckIn.user_id == user_id, models.DailyCheckIn.checkin_date == d)
        .order_by(models.DailyCheckIn.created_at.desc())
        .all()
    )
    if not rows:
        return None
    post = next((x for x in rows if x.checkin_phase == "post_run"), None)
    morning = next((x for x in rows if x.checkin_phase == "morning"), None)
    return post or morning or rows[0]


def _adapt_plan_for_date(
    db: Session,
    user_id: UUID,
    target_date: date,
    decision: dict,
    source_date: date,
    source_phase: str,
):
    session = (
        db.query(models.PlannedSession)
        .join(models.TrainingPlan, models.PlannedSession.plan_id == models.TrainingPlan.id)
        .filter(
            models.TrainingPlan.user_id == user_id,
            models.PlannedSession.session_date == target_date,
        )
        .order_by(models.TrainingPlan.week_start.desc(), models.TrainingPlan.created_at.desc())
        .first()
    )
    if not session:
        return None

    hard_types = {"tempo", "interval", "threshold", "quality", "long"}
    is_hard_today = (session.session_type or "").lower() in hard_types

    target = (decision.get("tomorrow_session") or "easy").lower()
    # Morning check only force-adjusts when unrecovered and today is hard workout.
    if source_phase == "morning" and not is_hard_today and target in {"quality", "long", "easy"}:
        return None

    prev_type = session.session_type

    if target == "rest":
        session.session_type = "rest"
        session.target_distance_km = None
        session.target_hr_zone = "-"
    elif target == "recovery":
        session.session_type = "recovery"
        if session.target_distance_km is None:
            session.target_distance_km = 6.0
        else:
            session.target_distance_km = round(float(session.target_distance_km) * 0.6, 1)
        session.target_hr_zone = "Z1"
    elif target == "easy":
        session.session_type = "easy"
        if session.target_distance_km is None:
            session.target_distance_km = 8.0
        session.target_hr_zone = "Z2"
    elif target == "quality":
        session.session_type = "tempo"
        if session.target_distance_km is None:
            session.target_distance_km = 10.0
        session.target_hr_zone = "Z3"
    elif target == "long":
        session.session_type = "long"
        if session.target_distance_km is None:
            session.target_distance_km = 18.0
        session.target_hr_zone = "Z2"

    reason = " | ".join(decision.get("rationale") or [])
    session.notes = (
        f"[ADAPTED {source_date} {source_phase}] {prev_type} -> {session.session_type}; {reason}"
    )
    db.commit()

    return {
        "date": str(target_date),
        "from": prev_type,
        "to": session.session_type,
        "distance_km": float(session.target_distance_km) if session.target_distance_km is not None else None,
        "hr_zone": session.target_hr_zone,
    }


@router.post("/profile", response_model=schemas.RunnerProfileOut)
def upsert_profile(payload: schemas.RunnerProfileUpsert, db: Session = Depends(get_db)):
    user = db.get(models.User, payload.user_id)
    if not user:
        user = models.User(id=payload.user_id, display_name="runner")
        db.add(user)
        db.flush()

    profile = db.query(models.RunnerProfile).filter(models.RunnerProfile.user_id == payload.user_id).first()
    if not profile:
        profile = models.RunnerProfile(**payload.model_dump())
        db.add(profile)
    else:
        for k, v in payload.model_dump().items():
            setattr(profile, k, v)

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile/{user_id}", response_model=schemas.RunnerProfileOut)
def get_profile(user_id: UUID, db: Session = Depends(get_db)):
    profile = db.query(models.RunnerProfile).filter(models.RunnerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "runner profile not found")
    return profile


@router.post("/profile/autofill")
def autofill_profile_from_strava(
    user_id: UUID,
    days: int = Query(default=90, ge=28, le=180),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        user = models.User(id=user_id, display_name="runner")
        db.add(user)
        db.flush()

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)
    rows = (
        db.query(models.Activity)
        .filter(
            models.Activity.user_id == user_id,
            models.Activity.provider == "strava",
            models.Activity.started_at >= start_dt,
            models.Activity.started_at < end_dt,
            models.Activity.distance_m >= 3000,
        )
        .order_by(models.Activity.started_at.desc())
        .all()
    )

    if not rows:
        raise HTTPException(404, "近3个月没有可用跑步数据，请先 Strava 同步")

    paces = [float(r.avg_pace_sec_per_km) for r in rows if r.avg_pace_sec_per_km is not None]
    hrs = [int(r.avg_hr) for r in rows if r.avg_hr is not None]

    if not paces:
        raise HTTPException(400, "Strava 数据缺少可用配速，无法估算阈值")

    easy_pace_min = round(_percentile(paces, 0.35) or 280)
    easy_pace_max = round(_percentile(paces, 0.75) or 340)
    threshold_pace = round(_percentile(paces, 0.18) or 240)
    marathon_pace = round(_percentile(paces, 0.28) or 255)

    easy_hr_max = int(round(_percentile([float(h) for h in hrs], 0.60) or 145)) if hrs else 145
    threshold_hr_max = int(round(_percentile([float(h) for h in hrs], 0.90) or 170)) if hrs else 170
    marathon_hr_max = int(round(_percentile([float(h) for h in hrs], 0.78) or 162)) if hrs else 162

    easy_hr_max = max(130, min(easy_hr_max, 155))
    marathon_hr_max = max(easy_hr_max + 8, min(marathon_hr_max, 170))
    threshold_hr_max = max(marathon_hr_max + 3, min(threshold_hr_max, 185))

    profile = db.query(models.RunnerProfile).filter(models.RunnerProfile.user_id == user_id).first()
    if not profile:
        profile = models.RunnerProfile(user_id=user_id)
        db.add(profile)

    profile.goal = "sub3_marathon"
    profile.easy_pace_min = easy_pace_min
    profile.easy_pace_max = easy_pace_max
    profile.marathon_pace = marathon_pace
    profile.threshold_pace = threshold_pace
    profile.easy_hr_max = easy_hr_max
    profile.marathon_hr_max = marathon_hr_max
    profile.threshold_hr_max = threshold_hr_max
    profile.cadence_easy_min = profile.cadence_easy_min or 170
    profile.cadence_easy_max = profile.cadence_easy_max or 178
    profile.cadence_quality_min = profile.cadence_quality_min or 180

    db.commit()
    db.refresh(profile)

    return {
        "ok": True,
        "source": "strava_last_3_months",
        "runs_used": len(rows),
        "days": days,
        "notes": "基于最近3个月已同步Strava跑步记录估算，可手工微调",
        "profile": {
            "user_id": str(user_id),
            "goal": profile.goal,
            "easy_hr_max": profile.easy_hr_max,
            "marathon_hr_max": profile.marathon_hr_max,
            "threshold_hr_max": profile.threshold_hr_max,
            "easy_pace_min": float(profile.easy_pace_min) if profile.easy_pace_min is not None else None,
            "easy_pace_max": float(profile.easy_pace_max) if profile.easy_pace_max is not None else None,
            "marathon_pace": float(profile.marathon_pace) if profile.marathon_pace is not None else None,
            "threshold_pace": float(profile.threshold_pace) if profile.threshold_pace is not None else None,
            "cadence_easy_min": profile.cadence_easy_min,
            "cadence_easy_max": profile.cadence_easy_max,
            "cadence_quality_min": profile.cadence_quality_min,
        },
    }


@router.post("/feedback")
def upsert_feedback(
    payload: schemas.CheckinFeedbackUpsert,
    adapt_next_day: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, payload.user_id)
    if not user:
        user = models.User(id=payload.user_id, display_name="runner")
        db.add(user)
        db.flush()

    checkin = (
        db.query(models.DailyCheckIn)
        .filter(
            models.DailyCheckIn.user_id == payload.user_id,
            models.DailyCheckIn.checkin_date == payload.checkin_date,
            models.DailyCheckIn.checkin_phase == payload.checkin_phase,
        )
        .first()
    )

    if not checkin:
        checkin = models.DailyCheckIn(
            user_id=payload.user_id,
            checkin_date=payload.checkin_date,
            checkin_phase=payload.checkin_phase,
            fatigue_score=payload.fatigue_score if payload.fatigue_score is not None else 5,
            soreness_level=payload.soreness_level if payload.soreness_level is not None else 0,
            soreness_area=payload.soreness_area,
            sleep_note=payload.sleep_note,
        )
        db.add(checkin)
    else:
        if payload.fatigue_score is not None:
            checkin.fatigue_score = payload.fatigue_score
        if payload.soreness_level is not None:
            checkin.soreness_level = payload.soreness_level
        if payload.soreness_area is not None:
            checkin.soreness_area = payload.soreness_area or None
        if payload.sleep_note is not None:
            checkin.sleep_note = payload.sleep_note or None

    db.commit()
    db.refresh(checkin)

    adaptation = None
    if adapt_next_day:
        profile = db.query(models.RunnerProfile).filter(models.RunnerProfile.user_id == payload.user_id).first()
        if profile:
            decision = generate_coach_decision(db, payload.user_id, profile, checkin)
            checkin.fatigue_status = decision["fatigue_status"]
            checkin.injury_risk = decision["injury_risk"]
            checkin.tomorrow_session = decision["tomorrow_session"]
            checkin.hr_cap = decision.get("hr_cap")
            checkin.pace_hint = decision.get("pace_hint")
            checkin.cadence_hint = decision.get("cadence_hint")
            checkin.decision_rationale = " | ".join(decision.get("rationale") or [])
            checkin.coach_message = decision.get("coach_feedback")
            db.commit()
            if payload.checkin_phase == "post_run":
                adaptation = _adapt_plan_for_date(
                    db,
                    payload.user_id,
                    payload.checkin_date + timedelta(days=1),
                    decision,
                    payload.checkin_date,
                    payload.checkin_phase,
                )
            else:
                adaptation = _adapt_plan_for_date(
                    db,
                    payload.user_id,
                    payload.checkin_date,
                    decision,
                    payload.checkin_date,
                    payload.checkin_phase,
                )

    return {
        "ok": True,
        "date": str(checkin.checkin_date),
        "checkin_phase": checkin.checkin_phase,
        "fatigue_score": checkin.fatigue_score,
        "soreness_level": checkin.soreness_level,
        "soreness_area": checkin.soreness_area,
        "sleep_note": checkin.sleep_note,
        "tomorrow_session": checkin.tomorrow_session,
        "coach_feedback": checkin.coach_message,
        "adaptation": adaptation,
    }


@router.post("/daily-checkin", response_model=schemas.DailyCoachDecisionOut)
def daily_checkin(payload: schemas.DailyCheckInIn, db: Session = Depends(get_db)):
    data = payload.model_dump()
    # Morning check-in should be subjective only; clear run metrics to avoid stale carry-over.
    if data.get("checkin_phase") == "morning":
        data["distance_km"] = None
        data["pace_sec_per_km"] = None
        data["avg_hr"] = None
        data["cadence_spm"] = None
        data["elevation_gain_m"] = None
        data["actual_session_type"] = "rest"
    user = db.get(models.User, payload.user_id)
    if not user:
        user = models.User(id=payload.user_id, display_name="runner")
        db.add(user)
        db.flush()

    profile = db.query(models.RunnerProfile).filter(models.RunnerProfile.user_id == payload.user_id).first()
    if not profile:
        profile = models.RunnerProfile(
            user_id=payload.user_id,
            goal="sub3_marathon",
            easy_hr_max=145,
            marathon_hr_max=162,
            threshold_hr_max=170,
            cadence_easy_min=170,
            cadence_easy_max=178,
            cadence_quality_min=180,
        )
        db.add(profile)
        db.flush()

    checkin = (
        db.query(models.DailyCheckIn)
        .filter(
            models.DailyCheckIn.user_id == payload.user_id,
            models.DailyCheckIn.checkin_date == payload.checkin_date,
            models.DailyCheckIn.checkin_phase == payload.checkin_phase,
        )
        .first()
    )

    if not checkin:
        checkin = models.DailyCheckIn(**data)
        db.add(checkin)
    else:
        for k, v in data.items():
            setattr(checkin, k, v)

    db.commit()
    db.refresh(checkin)

    decision = generate_coach_decision(db, payload.user_id, profile, checkin)
    checkin.fatigue_status = decision["fatigue_status"]
    checkin.injury_risk = decision["injury_risk"]
    checkin.tomorrow_session = decision["tomorrow_session"]
    checkin.hr_cap = decision.get("hr_cap")
    checkin.pace_hint = decision.get("pace_hint")
    checkin.cadence_hint = decision.get("cadence_hint")
    checkin.decision_rationale = " | ".join(decision.get("rationale") or [])
    checkin.coach_message = decision.get("coach_feedback")
    db.commit()

    if payload.checkin_phase == "post_run":
        _adapt_plan_for_date(
            db,
            payload.user_id,
            payload.checkin_date + timedelta(days=1),
            decision,
            payload.checkin_date,
            payload.checkin_phase,
        )
    else:
        _adapt_plan_for_date(
            db,
            payload.user_id,
            payload.checkin_date,
            decision,
            payload.checkin_date,
            payload.checkin_phase,
        )

    return decision


@router.get("/autofill-today")
def autofill_today(
    user_id: UUID,
    checkin_date: date,
    tz: str = Query(default="Asia/Shanghai"),
    allow_nearest: bool = Query(default=False),
    max_days_back: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    try:
        tzinfo = ZoneInfo(tz)
    except Exception:
        tzinfo = ZoneInfo("Asia/Shanghai")
        tz = "Asia/Shanghai"

    start_dt = datetime.combine(checkin_date, datetime.min.time(), tzinfo=tzinfo).astimezone(timezone.utc)
    end_dt = (datetime.combine(checkin_date, datetime.min.time(), tzinfo=tzinfo) + timedelta(days=1)).astimezone(
        timezone.utc
    )

    rows = (
        db.query(models.Activity)
        .filter(
            models.Activity.user_id == user_id,
            models.Activity.provider == "strava",
            models.Activity.started_at >= start_dt,
            models.Activity.started_at < end_dt,
        )
        .order_by(models.Activity.started_at.desc())
        .all()
    )

    used_date = checkin_date
    used_nearest = False

    if not rows and allow_nearest:
        nearest_start = start_dt - timedelta(days=max_days_back)
        nearest_rows = (
            db.query(models.Activity)
            .filter(
                models.Activity.user_id == user_id,
                models.Activity.provider == "strava",
                models.Activity.started_at >= nearest_start,
                models.Activity.started_at < end_dt,
            )
            .order_by(models.Activity.started_at.desc())
            .all()
        )
        if nearest_rows:
            rows = nearest_rows
            used_nearest = True
            used_date = rows[0].started_at.astimezone(tzinfo).date()

    if not rows:
        has_any_synced = (
            db.query(models.Activity)
            .filter(models.Activity.user_id == user_id, models.Activity.provider == "strava")
            .first()
            is not None
        )
        if has_any_synced:
            raise HTTPException(404, "该日期附近没有跑步记录，请换日期或先去 Strava 完成训练同步")
        raise HTTPException(404, "还没有同步到任何 Strava 跑步记录，请先执行 /auth/strava/sync")

    activity = rows[0]

    planned_type = None
    current_plan = (
        db.query(models.TrainingPlan)
        .options(joinedload(models.TrainingPlan.sessions))
        .filter(models.TrainingPlan.user_id == user_id)
        .order_by(models.TrainingPlan.week_start.desc(), models.TrainingPlan.created_at.desc())
        .first()
    )
    if current_plan:
        for s in current_plan.sessions:
            if s.session_date == checkin_date:
                planned_type = s.session_type
                break

    distance_km = round((activity.distance_m or 0) / 1000.0, 2)
    pace = float(activity.avg_pace_sec_per_km) if activity.avg_pace_sec_per_km is not None else None

    actual_type = "easy"
    if distance_km >= 24:
        actual_type = "long"
    elif activity.avg_hr and activity.avg_hr >= 165:
        actual_type = "quality"

    summary = f"{used_date} 已拉取 1 条训练：{distance_km}km, 爬升 {activity.elevation_gain_m or 0}m, HR {activity.avg_hr or '-'}"
    if used_nearest:
        summary += f"（未找到 {checkin_date} 当日记录，已自动回退到最近一次）"

    return {
        "ok": True,
        "source": "strava_synced_activity",
        "timezone": tz,
        "started_at": activity.started_at,
        "distance_km": distance_km,
        "avg_hr": activity.avg_hr,
        "pace_sec_per_km": pace,
        "cadence_spm": activity.cadence_spm,
        "elevation_gain_m": activity.elevation_gain_m,
        "actual_session_type": actual_type,
        "planned_session_type": planned_type,
        "used_date": str(used_date),
        "used_nearest": used_nearest,
        "summary": summary,
    }


@router.post("/chat", response_model=schemas.CoachChatOut)
def coach_chat(payload: schemas.CoachChatIn, db: Session = Depends(get_db)):
    target_date = payload.checkin_date or date.today()
    target_checkin = _pick_checkin_for_date(db, payload.user_id, target_date)

    latest_checkin = (
        db.query(models.DailyCheckIn)
        .filter(models.DailyCheckIn.user_id == payload.user_id, models.DailyCheckIn.checkin_date <= target_date)
        .order_by(models.DailyCheckIn.checkin_date.desc(), models.DailyCheckIn.created_at.desc())
        .first()
    )

    profile = db.query(models.RunnerProfile).filter(models.RunnerProfile.user_id == payload.user_id).first()

    recent_activities = (
        db.query(models.Activity)
        .filter(models.Activity.user_id == payload.user_id, models.Activity.provider == "strava")
        .order_by(models.Activity.started_at.desc())
        .limit(10)
        .all()
    )

    planned_tomorrow = (
        db.query(models.PlannedSession)
        .join(models.TrainingPlan, models.PlannedSession.plan_id == models.TrainingPlan.id)
        .filter(
            models.TrainingPlan.user_id == payload.user_id,
            models.PlannedSession.session_date == (target_date + timedelta(days=1)),
        )
        .order_by(models.TrainingPlan.week_start.desc(), models.TrainingPlan.created_at.desc())
        .first()
    )

    history = payload.conversation_history or []
    history = [
        {"role": str(x.get("role", ""))[:20], "text": str(x.get("text", ""))[:300]}
        for x in history
        if isinstance(x, dict)
    ][-8:]

    # Source of truth: if selected date has saved check-in, prioritize DB snapshot
    # so history/calendar edits and coach page stay consistent.
    input_today = {
        "fatigue_score": target_checkin.fatigue_score if target_checkin else payload.fatigue_score,
        "soreness_level": target_checkin.soreness_level if target_checkin else payload.soreness_level,
        "soreness_area": target_checkin.soreness_area if target_checkin else payload.soreness_area,
        "sleep_note": target_checkin.sleep_note if target_checkin else payload.sleep_note,
        "distance_km": (float(target_checkin.distance_km) if target_checkin and target_checkin.distance_km is not None else payload.distance_km),
        "avg_hr": target_checkin.avg_hr if target_checkin else payload.avg_hr,
        "elevation_gain_m": target_checkin.elevation_gain_m if target_checkin else payload.elevation_gain_m,
        "actual_session_type": target_checkin.actual_session_type if target_checkin else payload.actual_session_type,
    }

    context = {
        "checkin_date": str(target_date),
        "input_today": input_today,
        "latest_checkin": {
            "date": str(latest_checkin.checkin_date) if latest_checkin else None,
            "fatigue_score": latest_checkin.fatigue_score if latest_checkin else None,
            "soreness_level": latest_checkin.soreness_level if latest_checkin else None,
            "tomorrow_session": latest_checkin.tomorrow_session if latest_checkin else None,
            "coach_message": latest_checkin.coach_message if latest_checkin else None,
        },
        "tomorrow_plan": {
            "date": str(target_date + timedelta(days=1)),
            "session_type": planned_tomorrow.session_type if planned_tomorrow else None,
            "target_distance_km": float(planned_tomorrow.target_distance_km) if planned_tomorrow and planned_tomorrow.target_distance_km is not None else None,
            "target_hr_zone": planned_tomorrow.target_hr_zone if planned_tomorrow else None,
        },
        "profile": {
            "easy_hr_max": profile.easy_hr_max if profile else None,
            "threshold_hr_max": profile.threshold_hr_max if profile else None,
            "easy_pace_min": float(profile.easy_pace_min) if profile and profile.easy_pace_min is not None else None,
            "easy_pace_max": float(profile.easy_pace_max) if profile and profile.easy_pace_max is not None else None,
        },
        "conversation_history": history,
        "recent_runs": [
            {
                "date": str(a.started_at.date()),
                "distance_km": round((a.distance_m or 0) / 1000.0, 2),
                "avg_hr": a.avg_hr,
                "pace_sec_per_km": float(a.avg_pace_sec_per_km) if a.avg_pace_sec_per_km is not None else None,
                "elevation_gain_m": a.elevation_gain_m,
            }
            for a in recent_activities
        ],
    }

    return generate_coach_chat_reply(payload.message, context)


@router.get("/checkin-snapshot")
def checkin_snapshot(user_id: UUID, checkin_date: date, db: Session = Depends(get_db)):
    checkin = _pick_checkin_for_date(db, user_id, checkin_date)
    if not checkin:
        return {"ok": True, "exists": False, "checkin_date": str(checkin_date)}

    return {
        "ok": True,
        "exists": True,
        "checkin_date": str(checkin_date),
        "checkin_phase": checkin.checkin_phase,
        "fatigue_score": checkin.fatigue_score,
        "soreness_level": checkin.soreness_level,
        "soreness_area": checkin.soreness_area,
        "sleep_note": checkin.sleep_note,
        "distance_km": float(checkin.distance_km) if checkin.distance_km is not None else None,
        "avg_hr": checkin.avg_hr,
        "elevation_gain_m": checkin.elevation_gain_m,
        "actual_session_type": checkin.actual_session_type,
        "planned_session_type": checkin.planned_session_type,
    }


@router.post("/chat/apply", response_model=schemas.CoachChatApplyOut)
def coach_chat_apply(payload: schemas.CoachChatApplyIn, db: Session = Depends(get_db)):
    target_date = payload.checkin_date or date.today()
    apply_date = target_date if payload.apply_to == "today" else (target_date + timedelta(days=1))

    session = (
        db.query(models.PlannedSession)
        .join(models.TrainingPlan, models.PlannedSession.plan_id == models.TrainingPlan.id)
        .filter(
            models.TrainingPlan.user_id == payload.user_id,
            models.PlannedSession.session_date == apply_date,
        )
        .order_by(models.TrainingPlan.week_start.desc(), models.TrainingPlan.created_at.desc())
        .first()
    )

    if not session:
        raise HTTPException(404, "未找到明天计划，无法应用")

    old_type = session.session_type
    old_dist = float(session.target_distance_km) if session.target_distance_km is not None else None

    new_type = payload.suggested_tomorrow_session
    session.session_type = "tempo" if new_type == "quality" else new_type

    base_dist = old_dist if old_dist is not None else (
        8.0 if session.session_type == "easy" else 6.0 if session.session_type == "recovery" else 18.0 if session.session_type == "long" else None
    )

    if payload.suggested_distance_km is not None:
        session.target_distance_km = max(0.0, round(float(payload.suggested_distance_km), 1))
        delta = None if old_dist is None else round(float(session.target_distance_km) - old_dist, 1)
    else:
        delta = payload.suggested_delta_km
        if delta is not None and base_dist is not None:
            next_dist = max(0.0, round(base_dist + float(delta), 1))
            session.target_distance_km = next_dist
        elif base_dist is not None and session.target_distance_km is None:
            session.target_distance_km = round(base_dist, 1)

    if session.session_type == "rest":
        session.target_distance_km = None
        session.target_hr_zone = "-"
    elif session.session_type == "recovery":
        session.target_hr_zone = "Z1"
    elif session.session_type in {"easy", "long"}:
        session.target_hr_zone = "Z2"
    elif session.session_type == "tempo":
        session.target_hr_zone = "Z3"

    note = f"[CHAT_APPLY {date.today()}] {old_type} -> {session.session_type}; delta_km={delta}"
    session.notes = f"{(session.notes + ' | ') if session.notes else ''}{note}"[:1000]

    db.commit()
    db.refresh(session)

    return {
        "ok": True,
        "date": apply_date,
        "from_session_type": old_type,
        "to_session_type": session.session_type,
        "from_distance_km": old_dist,
        "to_distance_km": float(session.target_distance_km) if session.target_distance_km is not None else None,
        "note": note,
    }


@router.post("/agent/propose", response_model=schemas.CoachAgentProposeOut)
def coach_agent_propose(payload: schemas.CoachChatIn, db: Session = Depends(get_db)):
    target_date = payload.checkin_date or date.today()
    apply_date = target_date if payload.apply_to == "today" else (target_date + timedelta(days=1))

    profile = db.query(models.RunnerProfile).filter(models.RunnerProfile.user_id == payload.user_id).first()
    easy_hr_cap = profile.easy_hr_max if profile and profile.easy_hr_max else 150

    planned = (
        db.query(models.PlannedSession)
        .join(models.TrainingPlan, models.PlannedSession.plan_id == models.TrainingPlan.id)
        .filter(models.TrainingPlan.user_id == payload.user_id, models.PlannedSession.session_date == apply_date)
        .order_by(models.TrainingPlan.week_start.desc(), models.TrainingPlan.created_at.desc())
        .first()
    )

    base_type = (planned.session_type if planned else "easy") or "easy"
    base_dist = float(planned.target_distance_km) if planned and planned.target_distance_km is not None else (8.0 if base_type in {"easy", "recovery"} else 10.0)

    fatigue = payload.fatigue_score if payload.fatigue_score is not None else 5
    soreness = payload.soreness_level if payload.soreness_level is not None else 0

    opt_a_type = "recovery" if (fatigue >= 6 or soreness >= 4) else ("easy" if base_type in {"tempo", "quality", "long"} else base_type)
    opt_a_dist = max(4.0, min(10.0, round(base_dist * 0.8, 1))) if opt_a_type in {"recovery", "easy"} else base_dist

    allow_b = fatigue < 6 and soreness < 4
    if allow_b:
        opt_b_type = "easy" if base_type in {"recovery", "easy"} else base_type
        opt_b_dist = round(min(base_dist + 2.0, base_dist * 1.15), 1)
        opt_b_risk = "medium"
        opt_b_reason = "状态可控，允许小幅加量（上限+2km），维持有氧强度。"
    else:
        opt_b_type = "recovery"
        opt_b_dist = max(5.0, min(8.0, round(base_dist * 0.75, 1)))
        opt_b_risk = "high"
        opt_b_reason = "疲劳/酸痛偏高，禁加量；B降级为恢复方案以控制风险。"

    options = [
        schemas.CoachAgentOption(
            code="A",
            label="保守恢复",
            tomorrow_session=opt_a_type if opt_a_type in {"rest","recovery","easy","quality","long"} else "easy",
            distance_km=opt_a_dist,
            hr_cap=easy_hr_cap,
            pace_hint="轻松可对话配速",
            risk="low",
            reason="优先恢复，降低次日累积疲劳。",
        ),
        schemas.CoachAgentOption(
            code="B",
            label="积极推进",
            tomorrow_session=opt_b_type if opt_b_type in {"rest","recovery","easy","quality","long"} else "easy",
            distance_km=opt_b_dist,
            hr_cap=easy_hr_cap,
            pace_hint="全程Z2，不冲配速",
            risk=opt_b_risk,
            reason=opt_b_reason,
        ),
    ]

    return {"ok": True, "date": apply_date, "options": options}


@router.post("/agent/apply", response_model=schemas.CoachChatApplyOut)
def coach_agent_apply(payload: schemas.CoachAgentApplyIn, db: Session = Depends(get_db)):
    propose = coach_agent_propose(
        schemas.CoachChatIn(user_id=payload.user_id, message="apply", checkin_date=payload.checkin_date, apply_to=payload.apply_to),
        db,
    )
    options = propose.get("options", []) if isinstance(propose, dict) else []

    def _code(x):
        return x.get("code") if isinstance(x, dict) else getattr(x, "code", None)

    def _session(x):
        return x.get("tomorrow_session") if isinstance(x, dict) else getattr(x, "tomorrow_session", None)

    picked = next((x for x in options if _code(x) == payload.option_code), None)
    if not picked:
        raise HTTPException(400, "invalid option")

    picked_dist = picked.get("distance_km") if isinstance(picked, dict) else getattr(picked, "distance_km", None)

    return coach_chat_apply(
        schemas.CoachChatApplyIn(
            user_id=payload.user_id,
            checkin_date=payload.checkin_date,
            apply_to=payload.apply_to,
            suggested_tomorrow_session=_session(picked),
            suggested_delta_km=None,
            suggested_distance_km=float(picked_dist) if isinstance(picked_dist, (int, float)) else None,
        ),
        db,
    )


@router.get("/calendar")
def coach_calendar(
    user_id: UUID,
    days: int = Query(default=90, ge=7, le=365),
    tz: str = Query(default="Asia/Shanghai"),
    db: Session = Depends(get_db),
):
    try:
        tzinfo = ZoneInfo(tz)
    except Exception:
        tzinfo = ZoneInfo("Asia/Shanghai")
        tz = "Asia/Shanghai"

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)

    activities = (
        db.query(models.Activity)
        .filter(
            models.Activity.user_id == user_id,
            models.Activity.provider == "strava",
            models.Activity.started_at >= start_dt,
            models.Activity.started_at < end_dt,
        )
        .all()
    )

    checkins = (
        db.query(models.DailyCheckIn)
        .filter(
            models.DailyCheckIn.user_id == user_id,
            models.DailyCheckIn.checkin_date >= (date.today() - timedelta(days=days)),
        )
        .all()
    )

    start_date = (date.today() - timedelta(days=days))
    planned_rows = (
        db.query(models.PlannedSession, models.TrainingPlan.week_start, models.TrainingPlan.created_at)
        .join(models.TrainingPlan, models.PlannedSession.plan_id == models.TrainingPlan.id)
        .filter(
            models.TrainingPlan.user_id == user_id,
            models.PlannedSession.session_date >= start_date,
            models.PlannedSession.session_date <= date.today() + timedelta(days=21),
        )
        .order_by(models.TrainingPlan.week_start.desc(), models.TrainingPlan.created_at.desc())
        .all()
    )

    activity_map: dict[str, dict] = {}
    for a in activities:
        local_day = a.started_at.astimezone(tzinfo).date().isoformat()
        if local_day not in activity_map:
            activity_map[local_day] = {
                "runs": 0,
                "distance_km": 0.0,
                "avg_hr_values": [],
                "cadence_values": [],
                "elevation_gain_m": 0.0,
            }
        activity_map[local_day]["runs"] += 1
        activity_map[local_day]["distance_km"] += (a.distance_m or 0) / 1000.0
        if a.avg_hr is not None:
            activity_map[local_day]["avg_hr_values"].append(a.avg_hr)
        if a.cadence_spm is not None:
            activity_map[local_day]["cadence_values"].append(a.cadence_spm)
        activity_map[local_day]["elevation_gain_m"] += float(a.elevation_gain_m or 0)

    checkin_map: dict[str, models.DailyCheckIn] = {}
    phase_flags: dict[str, dict] = {}
    for c in checkins:
        d = c.checkin_date.isoformat()
        if d not in phase_flags:
            phase_flags[d] = {"morning": False, "post_run": False}
        phase_flags[d][c.checkin_phase or "post_run"] = True

        existing = checkin_map.get(d)
        if not existing:
            checkin_map[d] = c
        elif (c.checkin_phase or "post_run") == "post_run":
            checkin_map[d] = c

    best_key_by_day: dict[str, tuple] = {}
    plan_map: dict[str, list] = {}
    seen_keys: dict[str, set] = {}
    adapted_best_key: dict[str, tuple] = {}
    adapted_map: dict[str, list] = {}
    adapted_seen: dict[str, set] = {}

    for s, week_start, created_at in planned_rows:
        d = s.session_date.isoformat()
        current_key = (week_start, created_at, str(s.plan_id))
        distance = float(s.target_distance_km) if s.target_distance_km is not None else None
        elev = float(s.target_elevation_gain_m) if s.target_elevation_gain_m is not None else None
        notes_text = s.notes or ""
        adapted = bool(("[ADAPTED" in notes_text) or ("[CHAT_APPLY" in notes_text))
        session_key = (s.session_type, round(distance or 0.0, 1), round(elev or 0.0, 1), s.target_hr_zone or "", adapted)
        session_obj = {
            "session_type": s.session_type,
            "target_distance_km": distance,
            "target_elevation_gain_m": elev,
            "target_hr_zone": s.target_hr_zone,
            "notes": s.notes,
            "adapted": adapted,
        }

        # Keep the latest adapted version for the day (even if it is not from the currently selected base plan).
        if adapted:
            best_adapt = adapted_best_key.get(d)
            if best_adapt is None or current_key > best_adapt:
                adapted_best_key[d] = current_key
                adapted_map[d] = []
                adapted_seen[d] = set()
            if adapted_best_key[d] == current_key and session_key not in adapted_seen[d]:
                adapted_seen[d].add(session_key)
                adapted_map[d].append(session_obj)

        best = best_key_by_day.get(d)
        if best is None:
            best_key_by_day[d] = current_key
            plan_map[d] = []
            seen_keys[d] = set()
        elif current_key < best:
            continue
        elif current_key > best:
            best_key_by_day[d] = current_key
            plan_map[d] = []
            seen_keys[d] = set()

        if session_key in seen_keys[d]:
            continue
        seen_keys[d].add(session_key)
        plan_map[d].append(session_obj)

    for d, adapted_sessions in adapted_map.items():
        if adapted_sessions:
            plan_map[d] = adapted_sessions

    all_days = sorted(set(activity_map.keys()) | set(checkin_map.keys()) | set(plan_map.keys()), reverse=True)

    items = []
    for d in all_days:
        act = activity_map.get(d, {})
        c = checkin_map.get(d)
        avg_hr = None
        if act.get("avg_hr_values"):
            avg_hr = round(sum(act["avg_hr_values"]) / len(act["avg_hr_values"]))
        cadence = None
        if act.get("cadence_values"):
            cadence = round(sum(act["cadence_values"]) / len(act["cadence_values"]))

        day_plans = plan_map.get(d, [])
        planned_total_km = round(
            sum((p.get("target_distance_km") or 0.0) for p in day_plans), 2
        ) if day_plans else 0.0

        items.append(
            {
                "date": d,
                "runs": act.get("runs", 0),
                "distance_km": round(act.get("distance_km", 0.0), 2),
                "avg_hr": avg_hr,
                "cadence_spm": cadence,
                "elevation_gain_m": round(act.get("elevation_gain_m", 0.0), 1),
                "planned_sessions": day_plans,
                "planned_session_type": day_plans[0]["session_type"] if day_plans else None,
                "planned_total_km": planned_total_km,
                "planned_adapted": any(p.get("adapted") for p in day_plans),
                "morning_checked": phase_flags.get(d, {}).get("morning", False),
                "post_run_checked": phase_flags.get(d, {}).get("post_run", False),
                "fatigue_score": c.fatigue_score if c else None,
                "soreness_level": c.soreness_level if c else None,
                "soreness_area": c.soreness_area if c else None,
                "sleep_note": c.sleep_note if c else None,
                "fatigue_status": c.fatigue_status if c else None,
                "injury_risk": c.injury_risk if c else None,
                "tomorrow_session": c.tomorrow_session if c else None,
                "hr_cap": c.hr_cap if c else None,
                "pace_hint": c.pace_hint if c else None,
                "cadence_hint": c.cadence_hint if c else None,
                "decision_rationale": c.decision_rationale if c else None,
                "coach_message": c.coach_message if c else None,
            }
        )

    return {"ok": True, "timezone": tz, "days": days, "items": items}


@router.get("/weekly-review", response_model=schemas.WeeklyReviewOut)
def weekly_review(
    user_id: UUID,
    weeks: int = Query(default=1, ge=1, le=12),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "user not found")

    report = build_weekly_review(db, user_id, weeks)
    return {
        "user_id": str(user_id),
        "weeks": weeks,
        **report,
    }

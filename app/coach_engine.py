from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models

QUALITY_TYPES = {"tempo", "interval", "threshold", "hill", "quality"}


def _load_recent_checkins(db: Session, user_id, days: int = 14):
    start_date = date.today() - timedelta(days=days - 1)
    rows = (
        db.query(models.DailyCheckIn)
        .filter(models.DailyCheckIn.user_id == user_id, models.DailyCheckIn.checkin_date >= start_date)
        .order_by(models.DailyCheckIn.checkin_date.asc())
        .all()
    )

    by_day: dict[date, models.DailyCheckIn] = {}
    for r in rows:
        existing = by_day.get(r.checkin_date)
        if not existing:
            by_day[r.checkin_date] = r
            continue
        if (r.checkin_phase or "post_run") == "post_run":
            by_day[r.checkin_date] = r

    return [by_day[d] for d in sorted(by_day.keys())]


def evaluate_daily_decision(db: Session, user_id, profile: models.RunnerProfile, today: models.DailyCheckIn):
    recent = _load_recent_checkins(db, user_id, days=21)
    fatigue_avg_7d = sum(c.fatigue_score for c in recent[-7:]) / max(len(recent[-7:]), 1)

    prev3 = recent[-6:-3]
    last3 = recent[-3:]
    fatigue_trend_up = False
    if prev3 and last3:
        prev_avg = sum(c.fatigue_score for c in prev3) / len(prev3)
        last_avg = sum(c.fatigue_score for c in last3) / len(last3)
        fatigue_trend_up = (last_avg - prev_avg) >= 1.0

    end_dt = datetime.now(timezone.utc)
    start_28 = end_dt - timedelta(days=28)
    start_7 = end_dt - timedelta(days=7)
    activities_28 = (
        db.query(models.Activity)
        .filter(
            models.Activity.user_id == user_id,
            models.Activity.started_at >= start_28,
            models.Activity.started_at < end_dt,
        )
        .all()
    )
    last7_km = sum((a.distance_m or 0) for a in activities_28 if a.started_at >= start_7) / 1000.0
    base_week_km = max(sum((a.distance_m or 0) for a in activities_28) / 4000.0, 1.0)
    load_ratio = last7_km / base_week_km

    fatigue_status = "low"
    if today.fatigue_score >= 8 or fatigue_avg_7d >= 7 or load_ratio >= 1.35:
        fatigue_status = "high"
    elif today.fatigue_score >= 5 or fatigue_avg_7d >= 5 or load_ratio >= 1.15:
        fatigue_status = "medium"

    soreness_streak = 0
    for c in reversed(recent[-7:]):
        if c.soreness_level >= 3:
            soreness_streak += 1
        else:
            break

    injury_risk = "none"
    if today.soreness_level >= 7 or soreness_streak >= 3:
        injury_risk = "high"
    elif today.soreness_level >= 3 or (today.soreness_area and today.soreness_area.strip()):
        injury_risk = "mild"

    quality_count = sum(1 for c in recent if (c.actual_session_type or "").lower() in QUALITY_TYPES)
    quality_ratio = quality_count / max(len(recent), 1)

    yesterday = recent[-2] if len(recent) >= 2 else None
    yesterday_hard = bool(yesterday and (yesterday.actual_session_type or "").lower() in QUALITY_TYPES)

    long_today = (today.actual_session_type or "").lower() == "long"

    rule_checks = {
        "rule_80_20": quality_ratio <= 0.2,
        "rule_no_back_to_back_hard": not yesterday_hard,
        "rule_long_run_controlled": not long_today or today.fatigue_score <= 6,
        "rule_injury_override": injury_risk == "none",
        "rule_load_safe": load_ratio <= 1.2,
    }

    rationale: list[str] = [
        f"近7天疲劳均值 {round(fatigue_avg_7d,1)}，负荷比(7d/28d基线) {round(load_ratio,2)}",
    ]

    if injury_risk == "high":
        tomorrow_session = "rest"
        rationale.append("连续不适或高伤病风险：自动降级为休息")
    elif injury_risk == "mild" or fatigue_status == "high" or load_ratio >= 1.35:
        tomorrow_session = "recovery"
        rationale.append("轻微不适/高疲劳/高负荷：安排恢复跑")
    elif yesterday_hard or not rule_checks["rule_80_20"] or fatigue_trend_up:
        tomorrow_session = "easy"
        rationale.append("避免连续高强度，并抑制疲劳上升趋势：安排轻松跑")
    else:
        tomorrow_session = "quality"
        rationale.append("状态允许，可安排受控质量训练")

    hr_cap = profile.easy_hr_max or 145
    pace_hint = "easy pace"
    cadence_hint = "保持自然步频"

    if tomorrow_session == "quality":
        hr_cap = profile.threshold_hr_max or profile.marathon_hr_max or 165
        if profile.threshold_pace:
            pace_hint = f"阈值段约 {profile.threshold_pace} sec/km，含充分热身与冷身"
        else:
            pace_hint = "短间歇或阈值段，避免过量"
        if profile.cadence_quality_min:
            cadence_hint = f"质量段步频 ≥ {profile.cadence_quality_min} spm"
    elif tomorrow_session in {"easy", "recovery"}:
        if profile.easy_pace_min and profile.easy_pace_max:
            pace_hint = f"easy配速 {profile.easy_pace_min}-{profile.easy_pace_max} sec/km"
        if profile.cadence_easy_min and profile.cadence_easy_max:
            cadence_hint = f"步频 {profile.cadence_easy_min}-{profile.cadence_easy_max} spm"

    if injury_risk != "none":
        rationale.append("出现不适：禁止 interval / downhill workout")
    if not rule_checks["rule_80_20"]:
        rationale.append("近期强度占比偏高，优先恢复有氧")

    return {
        "fatigue_status": fatigue_status,
        "injury_risk": injury_risk,
        "tomorrow_session": tomorrow_session,
        "hr_cap": hr_cap,
        "pace_hint": pace_hint,
        "cadence_hint": cadence_hint,
        "rationale": rationale,
        "rule_checks": rule_checks,
    }


def build_weekly_review(db: Session, user_id, weeks: int = 1):
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=7 * weeks)

    activities = (
        db.query(models.Activity)
        .filter(
            models.Activity.user_id == user_id,
            models.Activity.started_at >= start_dt,
            models.Activity.started_at < end_dt,
        )
        .all()
    )

    checkins = (
        db.query(models.DailyCheckIn)
        .filter(models.DailyCheckIn.user_id == user_id, models.DailyCheckIn.checkin_date >= start_dt.date())
        .all()
    )

    total_distance_km = round(sum((a.distance_m or 0) for a in activities) / 1000.0, 1)
    total_runs = len(activities)

    quality_count = sum(1 for c in checkins if (c.actual_session_type or "").lower() in QUALITY_TYPES)
    quality_ratio = round(quality_count / max(len(checkins), 1), 2)

    fatigue_values = [c.fatigue_score for c in checkins]
    fatigue_trend = "stable"
    if len(fatigue_values) >= 6:
        first = sum(fatigue_values[: len(fatigue_values) // 2]) / max(len(fatigue_values) // 2, 1)
        last = sum(fatigue_values[len(fatigue_values) // 2 :]) / max(len(fatigue_values) - len(fatigue_values) // 2, 1)
        if last - first >= 1.0:
            fatigue_trend = "up"
        elif first - last >= 1.0:
            fatigue_trend = "down"

    injury_signals = sum(1 for c in checkins if c.soreness_level >= 3)
    overload_risk = quality_ratio > 0.2 or fatigue_trend == "up" or injury_signals >= 2
    recommend_cutback = overload_risk

    structure = [
        "Mon: Recovery/Rest",
        "Tue: Controlled Quality (short)",
        "Wed: Easy",
        "Thu: Easy or light tempo",
        "Fri: Easy",
        "Sat: Long run (70% easy + 30% MP max)",
        "Sun: Easy",
    ]
    if recommend_cutback:
        structure = [
            "Cutback week: 总量下调 15-25%",
            "保留 1 次短质量，其余 easy/recovery",
            "长跑仅 easy，不加阈值",
        ]

    return {
        "total_runs": total_runs,
        "total_distance_km": total_distance_km,
        "quality_ratio": quality_ratio,
        "fatigue_trend": fatigue_trend,
        "injury_signals": injury_signals,
        "overload_risk": overload_risk,
        "recommend_cutback": recommend_cutback,
        "next_week_structure": structure,
    }

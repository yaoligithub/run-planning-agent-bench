from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models
from app.db import get_db

router = APIRouter(prefix="/activities", tags=["activities"])


def _meters_to_unit(distance_m: int | None, unit: Literal["km", "mi"]) -> float:
    meters = float(distance_m or 0)
    km = meters / 1000.0
    if unit == "mi":
        return round(km * 0.621371, 2)
    return round(km, 2)


def _elev_to_unit(elev_m: int | None, unit: Literal["km", "mi"]) -> float:
    meters = float(elev_m or 0)
    if unit == "mi":
        return round(meters * 3.28084, 1)  # feet
    return round(meters, 1)


@router.get("/recent")
def recent_activities(
    user_id: UUID,
    weeks: int = Query(default=4, ge=1, le=12),
    unit: Literal["km", "mi"] = Query(default="km"),
    provider: str = Query(default="strava"),
    tz: str = Query(default="Asia/Shanghai"),
    db: Session = Depends(get_db),
):
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=7 * weeks)

    rows = (
        db.query(models.Activity)
        .filter(
            models.Activity.user_id == user_id,
            models.Activity.provider == provider,
            models.Activity.started_at >= start_dt,
            models.Activity.started_at < end_dt,
        )
        .order_by(models.Activity.started_at.desc())
        .all()
    )

    try:
        tzinfo = ZoneInfo(tz)
    except Exception:
        tzinfo = ZoneInfo("Asia/Shanghai")
        tz = "Asia/Shanghai"

    total_distance = round(sum(_meters_to_unit(r.distance_m, unit) for r in rows), 2)
    total_elevation = round(sum(_elev_to_unit(r.elevation_gain_m, unit) for r in rows), 1)
    activities = []
    for r in rows:
        local_dt = r.started_at.astimezone(tzinfo)
        activities.append(
            {
                "id": str(r.id),
                "started_at": r.started_at,
                "started_at_local": local_dt.isoformat(),
                "date": local_dt.date().isoformat(),
                "distance": _meters_to_unit(r.distance_m, unit),
                "duration_min": round((r.duration_sec or 0) / 60, 1),
                "avg_hr": r.avg_hr,
                "cadence_spm": r.cadence_spm,
                "type": r.activity_type,
                "elevation_gain": _elev_to_unit(r.elevation_gain_m, unit),
                "provider": r.provider,
            }
        )

    daily_map: dict[str, dict] = {}
    for item in activities:
        day = item["date"]
        if day not in daily_map:
            daily_map[day] = {"date": day, "runs": 0, "distance": 0.0, "elevation_gain": 0.0}
        daily_map[day]["runs"] += 1
        daily_map[day]["distance"] = round(daily_map[day]["distance"] + item["distance"], 2)
        daily_map[day]["elevation_gain"] = round(daily_map[day]["elevation_gain"] + (item.get("elevation_gain") or 0.0), 1)

    daily = sorted(daily_map.values(), key=lambda d: d["date"], reverse=True)

    return {
        "ok": True,
        "weeks": weeks,
        "unit": unit,
        "provider": provider,
        "timezone": tz,
        "summary": {
            "runs": len(rows),
            "total_distance": total_distance,
            "avg_weekly_distance": round(total_distance / weeks, 2),
            "total_elevation_gain": total_elevation,
            "avg_weekly_elevation_gain": round(total_elevation / weeks, 1),
            "elevation_unit": "ft" if unit == "mi" else "m",
        },
        "daily": daily,
        "activities": activities,
    }

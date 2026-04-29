import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db import get_db

router = APIRouter(prefix="/auth/strava", tags=["strava"])

STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
RUN_TYPES = {"Run", "TrailRun", "VirtualRun"}


def _normalize_run_cadence(raw_value) -> int | None:
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None

    if value <= 0:
        return None

    # Some sources expose running cadence as strides/min (~80-100), convert to steps/min.
    if value < 130:
        value *= 2

    cadence = int(round(value))
    if cadence < 120 or cadence > 230:
        return None
    return cadence


def _require_strava_config():
    if not settings.STRAVA_CLIENT_ID or not settings.STRAVA_CLIENT_SECRET or not settings.STRAVA_REDIRECT_URI:
        raise HTTPException(500, "missing STRAVA_CLIENT_ID/STRAVA_CLIENT_SECRET/STRAVA_REDIRECT_URI")


def _to_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_user_id_from_state(state: str | None) -> UUID | None:
    if not state:
        return None

    candidate = state.strip().strip('"').strip("'")
    try:
        return UUID(candidate)
    except ValueError:
        pass

    match = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        candidate,
    )
    if not match:
        return None

    try:
        return UUID(match.group(0))
    except ValueError:
        return None


def _upsert_account(
    db: Session,
    user_id: UUID,
    athlete_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: int,
):
    account = (
        db.query(models.ConnectedAccount)
        .filter(
            models.ConnectedAccount.user_id == user_id,
            models.ConnectedAccount.provider == "strava",
        )
        .first()
    )

    expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)
    if not account:
        account = models.ConnectedAccount(
            user_id=user_id,
            provider="strava",
            provider_athlete_id=str(athlete_id),
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_dt,
        )
        db.add(account)
    else:
        account.provider_athlete_id = str(athlete_id)
        account.access_token = access_token
        account.refresh_token = refresh_token
        account.token_expires_at = expires_dt

    db.commit()
    db.refresh(account)
    return account


def _refresh_if_needed(db: Session, account: models.ConnectedAccount) -> str:
    _require_strava_config()
    now = datetime.now(timezone.utc)
    if account.token_expires_at > now:
        return account.access_token

    payload = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "client_secret": settings.STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": account.refresh_token,
    }

    with httpx.Client(timeout=20) as client:
        resp = client.post(STRAVA_TOKEN_URL, json=payload)

    if resp.status_code != 200:
        raise HTTPException(400, f"strava refresh failed: {resp.text}")

    data = resp.json()
    account.access_token = data["access_token"]
    account.refresh_token = data["refresh_token"]
    account.token_expires_at = datetime.fromtimestamp(data["expires_at"], tz=timezone.utc)
    db.commit()
    db.refresh(account)
    return account.access_token


def _build_authorize_url(user_id: UUID) -> str:
    redirect_uri = settings.STRAVA_REDIRECT_URI or ""
    params = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "auto",
        "scope": "read,activity:read_all",
        "state": str(user_id),
    }
    return f"{STRAVA_AUTHORIZE_URL}?{urlencode(params)}"


@router.get("/connect")
def strava_connect(user_id: UUID):
    _require_strava_config()
    return {"authorize_url": _build_authorize_url(user_id)}


@router.get("/connect/start")
def strava_connect_start(user_id: UUID):
    _require_strava_config()
    return RedirectResponse(_build_authorize_url(user_id), status_code=307)


@router.get("/callback")
def strava_callback(
    code: str | None = None,
    state: str | None = None,
    user_id: UUID | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    _require_strava_config()

    if error:
        return HTMLResponse(f"<h3>Strava 授权失败</h3><p>{error}</p><p>请返回 App 重试连接。</p>", status_code=400)

    resolved_user_id = _parse_user_id_from_state(state) or user_id
    if not resolved_user_id:
        raise HTTPException(400, "invalid state user_id")
    if not code:
        raise HTTPException(400, "missing code")

    payload = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "client_secret": settings.STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }

    with httpx.Client(timeout=20) as client:
        resp = client.post(STRAVA_TOKEN_URL, json=payload)

    if resp.status_code != 200:
        raise HTTPException(400, f"strava token exchange failed: {resp.text}")

    data = resp.json()
    athlete_id = data.get("athlete", {}).get("id")
    if not athlete_id:
        raise HTTPException(400, "strava response missing athlete id")

    account = _upsert_account(
        db=db,
        user_id=resolved_user_id,
        athlete_id=str(athlete_id),
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=data["expires_at"],
    )

    return HTMLResponse(
        f"<h3>Strava 连接成功</h3><p>user_id: {resolved_user_id}</p><p>athlete_id: {account.provider_athlete_id}</p><p>请回到 App 点击“先同步 Strava”。</p>"
    )


@router.get("/status")
def strava_status(user_id: UUID, db: Session = Depends(get_db)):
    account = (
        db.query(models.ConnectedAccount)
        .filter(models.ConnectedAccount.user_id == user_id, models.ConnectedAccount.provider == "strava")
        .first()
    )
    return {
        "ok": True,
        "connected": account is not None,
        "provider_athlete_id": account.provider_athlete_id if account else None,
        "token_expires_at": account.token_expires_at.isoformat() if account else None,
    }


@router.post("/sync")
def strava_sync(
    user_id: UUID,
    page_size: int = Query(default=100, ge=1, le=200),
    max_pages: int = Query(default=3, ge=1, le=20),
    db: Session = Depends(get_db),
):
    account = (
        db.query(models.ConnectedAccount)
        .filter(
            models.ConnectedAccount.user_id == user_id,
            models.ConnectedAccount.provider == "strava",
        )
        .first()
    )
    if not account:
        raise HTTPException(404, "strava account not connected")

    token = _refresh_if_needed(db, account)

    created = 0
    updated = 0
    skipped = 0

    with httpx.Client(timeout=20) as client:
        for page in range(1, max_pages + 1):
            resp = client.get(
                STRAVA_ACTIVITIES_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"per_page": page_size, "page": page},
            )
            if resp.status_code != 200:
                raise HTTPException(400, f"strava activities fetch failed: {resp.text}")

            activities = resp.json()
            if not activities:
                break

            for item in activities:
                if item.get("type") not in RUN_TYPES:
                    skipped += 1
                    continue

                provider_activity_id = str(item["id"])
                moving_time = int(item.get("moving_time") or 0)
                distance_m = int(item.get("distance") or 0)

                avg_pace = None
                if distance_m >= 200 and moving_time > 0:
                    raw_pace = moving_time / (distance_m / 1000)
                    # guard against sensor glitches / near-zero distances
                    if 120 <= raw_pace <= 2000:
                        avg_pace = round(raw_pace, 2)

                cadence_spm = _normalize_run_cadence(item.get("average_cadence"))

                existing = (
                    db.query(models.Activity)
                    .filter(
                        models.Activity.provider == "strava",
                        models.Activity.provider_activity_id == provider_activity_id,
                    )
                    .first()
                )

                if not existing:
                    db.add(
                        models.Activity(
                            user_id=user_id,
                            provider="strava",
                            provider_activity_id=provider_activity_id,
                            activity_type=str(item.get("type") or "Run").lower(),
                            started_at=_to_datetime(item["start_date"]),
                            duration_sec=moving_time,
                            distance_m=distance_m,
                            avg_pace_sec_per_km=avg_pace,
                            avg_hr=int(item["average_heartrate"]) if item.get("average_heartrate") else None,
                            cadence_spm=cadence_spm,
                            max_hr=int(item["max_heartrate"]) if item.get("max_heartrate") else None,
                            elevation_gain_m=int(item["total_elevation_gain"]) if item.get("total_elevation_gain") else None,
                        )
                    )
                    created += 1
                else:
                    existing.activity_type = str(item.get("type") or "Run").lower()
                    existing.started_at = _to_datetime(item["start_date"])
                    existing.duration_sec = moving_time
                    existing.distance_m = distance_m
                    existing.avg_pace_sec_per_km = avg_pace
                    existing.avg_hr = int(item["average_heartrate"]) if item.get("average_heartrate") else None
                    existing.cadence_spm = cadence_spm
                    existing.max_hr = int(item["max_heartrate"]) if item.get("max_heartrate") else None
                    existing.elevation_gain_m = (
                        int(item["total_elevation_gain"]) if item.get("total_elevation_gain") else None
                    )
                    updated += 1

    db.commit()

    total_runs = (
        db.query(models.Activity)
        .filter(models.Activity.user_id == user_id, models.Activity.provider == "strava")
        .count()
    )

    return {
        "ok": True,
        "created": created,
        "updated": updated,
        "skipped_non_run": skipped,
        "total_strava_runs": total_runs,
    }

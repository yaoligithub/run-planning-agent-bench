import asyncio
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlalchemy import text

from app.autoplan import run_sunday_autoplan, should_autoplan_now
from app.coach_ui import render_coach_ui
from app.db import Base, SessionLocal, engine
from app.history_ui import render_history_ui
from app.routers.activities import router as activities_router
from app.routers.coach import router as coach_router
from app.routers.executions import router as executions_router
from app.routers.goals import router as goals_router
from app.routers.plans import router as plans_router
from app.routers.strava import router as strava_router
from app.routers.users import router as users_router
from app.simple_ui import render_simple_ui

Base.metadata.create_all(bind=engine)

with engine.begin() as conn:
    conn.execute(text("ALTER TABLE activities ADD COLUMN IF NOT EXISTS cadence_spm INTEGER"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS checkin_phase VARCHAR(20)"))
    conn.execute(text("UPDATE daily_checkins SET checkin_phase = 'post_run' WHERE checkin_phase IS NULL"))
    conn.execute(text("ALTER TABLE daily_checkins DROP CONSTRAINT IF EXISTS daily_checkins_user_id_checkin_date_key"))
    conn.execute(text("ALTER TABLE daily_checkins DROP CONSTRAINT IF EXISTS uq_daily_checkins_user_date_phase"))
    conn.execute(text("ALTER TABLE daily_checkins ADD CONSTRAINT uq_daily_checkins_user_date_phase UNIQUE (user_id, checkin_date, checkin_phase)"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS fatigue_status VARCHAR(12)"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS injury_risk VARCHAR(12)"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS tomorrow_session VARCHAR(20)"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS hr_cap INTEGER"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS pace_hint VARCHAR(120)"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS elevation_gain_m INTEGER"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS cadence_hint VARCHAR(120)"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS decision_rationale TEXT"))
    conn.execute(text("ALTER TABLE daily_checkins ADD COLUMN IF NOT EXISTS coach_message TEXT"))
    conn.execute(text("ALTER TABLE training_goals ADD COLUMN IF NOT EXISTS race_elevation_gain_m INTEGER"))
    conn.execute(text("ALTER TABLE planned_sessions ADD COLUMN IF NOT EXISTS target_elevation_gain_m INTEGER"))
    conn.execute(text("ALTER TABLE training_plans ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()"))
    conn.execute(text("UPDATE training_plans SET created_at = now() WHERE created_at IS NULL"))

app = FastAPI(title="Running Planner API")


async def _autoplan_loop():
    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            ok, local_date = should_autoplan_now(now_utc, "America/Los_Angeles")
            if ok:
                db = SessionLocal()
                try:
                    run_sunday_autoplan(db, local_date)
                finally:
                    db.close()
        except Exception:
            # keep loop alive
            pass
        await asyncio.sleep(900)  # every 15 min


@app.on_event("startup")
async def start_autoplan_worker():
    asyncio.create_task(_autoplan_loop())


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def home():
    return render_simple_ui()


@app.get("/history-analysis")
def history_analysis():
    return render_history_ui()


@app.get("/coach")
def coach_page():
    return render_coach_ui()


app.include_router(users_router)
app.include_router(goals_router)
app.include_router(plans_router)
app.include_router(strava_router)
app.include_router(activities_router)
app.include_router(executions_router)
app.include_router(coach_router)

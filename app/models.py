import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunnerProfile(Base):
    __tablename__ = "runner_profiles"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    goal: Mapped[str] = mapped_column(String(50), nullable=False, default="sub3_marathon")
    easy_pace_min: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    easy_pace_max: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    marathon_pace: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    threshold_pace: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    interval_pace: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    easy_hr_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marathon_hr_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    threshold_hr_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence_easy_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence_easy_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence_quality_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_weekly_volume_km: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TrainingGoal(Base):
    __tablename__ = "training_goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    goal_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_time_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekly_days: Mapped[int] = mapped_column(Integer, nullable=False)
    long_run_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    race_elevation_gain_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_goals.id"), nullable=True
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    planned_volume_km: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions = relationship("PlannedSession", back_populates="plan", cascade="all, delete-orphan")


class PlannedSession(Base):
    __tablename__ = "planned_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("training_plans.id"), nullable=False
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_distance_km: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    target_hr_zone: Mapped[str | None] = mapped_column(String(10), nullable=True)
    target_elevation_gain_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan = relationship("TrainingPlan", back_populates="sessions")


class SessionExecution(Base):
    __tablename__ = "session_executions"
    __table_args__ = (UniqueConstraint("user_id", "planned_session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    planned_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planned_sessions.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="done")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_distance_km: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"
    __table_args__ = (UniqueConstraint("user_id", "checkin_date", "checkin_phase"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    checkin_phase: Mapped[str] = mapped_column(String(20), nullable=False, default="post_run")
    distance_km: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    pace_sec_per_km: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence_spm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elevation_gain_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fatigue_score: Mapped[int] = mapped_column(Integer, nullable=False)
    soreness_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    soreness_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sleep_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned_session_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actual_session_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fatigue_status: Mapped[str | None] = mapped_column(String(12), nullable=True)
    injury_risk: Mapped[str | None] = mapped_column(String(12), nullable=True)
    tomorrow_session: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hr_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pace_hint: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cadence_hint: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    coach_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"
    __table_args__ = (UniqueConstraint("provider", "provider_athlete_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_athlete_id: Mapped[str] = mapped_column(String(64), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (UniqueConstraint("provider", "provider_activity_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_activity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False, default="run")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_pace_sec_per_km: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cadence_spm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elevation_gain_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

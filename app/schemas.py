from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    display_name: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    display_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoalCreate(BaseModel):
    user_id: UUID
    goal_type: str
    target_date: Optional[date] = None
    target_time_sec: Optional[int] = None
    weekly_days: int
    long_run_day: Optional[int] = None
    race_elevation_gain_m: Optional[int] = None


class GoalOut(GoalCreate):
    id: UUID
    status: str

    model_config = ConfigDict(from_attributes=True)


class PlanGenerateIn(BaseModel):
    user_id: UUID
    goal_id: UUID
    week_start: date
    base_volume_km: Optional[float] = None
    compliance: Optional[float] = None
    fatigue_score: Optional[int] = None
    auto_derive_inputs: bool = True
    distance_unit: Literal["km", "mi"] = "km"


class SessionOut(BaseModel):
    session_date: date
    session_type: str
    target_distance_km: Optional[float] = None
    target_distance: Optional[float] = None
    distance_unit: Literal["km", "mi"] = "km"
    target_hr_zone: Optional[str] = None
    target_elevation_gain_m: Optional[int] = None
    target_elevation_gain: Optional[float] = None
    elevation_unit: Optional[Literal["m", "ft"]] = None
    notes: Optional[str] = None


class PlanOut(BaseModel):
    id: UUID
    user_id: UUID
    goal_id: Optional[UUID]
    week_start: date
    week_end: date
    planned_volume_km: float
    planned_volume: float
    volume_unit: Literal["km", "mi"] = "km"
    rationale: Optional[str]
    sessions: list[SessionOut] = []


class SessionExecutionUpsert(BaseModel):
    user_id: UUID
    planned_session_id: UUID
    status: Literal["done", "skipped", "missed"] = "done"
    completed_distance_km: Optional[float] = None
    duration_sec: Optional[int] = None
    rpe: Optional[int] = None
    notes: Optional[str] = None


class SessionExecutionOut(BaseModel):
    id: UUID
    user_id: UUID
    planned_session_id: UUID
    status: Literal["done", "skipped", "missed"]
    executed_at: datetime
    completed_distance_km: Optional[float] = None
    duration_sec: Optional[int] = None
    rpe: Optional[int] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RunnerProfileUpsert(BaseModel):
    user_id: UUID
    goal: str = "sub3_marathon"
    easy_pace_min: Optional[float] = None
    easy_pace_max: Optional[float] = None
    marathon_pace: Optional[float] = None
    threshold_pace: Optional[float] = None
    interval_pace: Optional[float] = None
    easy_hr_max: Optional[int] = None
    marathon_hr_max: Optional[int] = None
    threshold_hr_max: Optional[int] = None
    cadence_easy_min: Optional[int] = None
    cadence_easy_max: Optional[int] = None
    cadence_quality_min: Optional[int] = None
    max_weekly_volume_km: Optional[float] = None


class RunnerProfileOut(RunnerProfileUpsert):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyCheckInIn(BaseModel):
    user_id: UUID
    checkin_date: date
    checkin_phase: Literal["morning", "post_run"] = "post_run"
    distance_km: Optional[float] = None
    pace_sec_per_km: Optional[float] = None
    avg_hr: Optional[int] = None
    cadence_spm: Optional[int] = None
    elevation_gain_m: Optional[int] = None
    fatigue_score: int
    soreness_area: Optional[str] = None
    soreness_level: int = 0
    sleep_note: Optional[str] = None
    planned_session_type: Optional[str] = None
    actual_session_type: Optional[str] = None


class DailyCoachDecisionOut(BaseModel):
    fatigue_status: Literal["low", "medium", "high"]
    injury_risk: Literal["none", "mild", "high"]
    tomorrow_session: Literal["rest", "recovery", "easy", "quality", "long"]
    hr_cap: Optional[int] = None
    pace_hint: Optional[str] = None
    cadence_hint: Optional[str] = None
    rationale: list[str]
    rule_checks: dict[str, bool]
    decision_source: Optional[str] = None
    model_used: Optional[str] = None
    coach_feedback: Optional[str] = None


class WeeklyReviewOut(BaseModel):
    user_id: UUID
    weeks: int
    total_runs: int
    total_distance_km: float
    quality_ratio: float
    fatigue_trend: str
    injury_signals: int
    overload_risk: bool
    recommend_cutback: bool
    next_week_structure: list[str]


class CoachChatIn(BaseModel):
    user_id: UUID
    message: str
    checkin_date: Optional[date] = None
    apply_to: Literal["today", "tomorrow"] = "tomorrow"
    fatigue_score: Optional[int] = None
    soreness_level: Optional[int] = None
    soreness_area: Optional[str] = None
    sleep_note: Optional[str] = None
    distance_km: Optional[float] = None
    avg_hr: Optional[int] = None
    elevation_gain_m: Optional[int] = None
    actual_session_type: Optional[str] = None
    conversation_history: Optional[list[dict[str, str]]] = None


class CoachChatOut(BaseModel):
    ok: bool = True
    reply: str
    suggested_tomorrow_session: Optional[Literal["rest", "recovery", "easy", "quality", "long"]] = None
    suggested_delta_km: Optional[float] = None
    caution: Optional[str] = None
    source: Literal["ai", "fallback"] = "fallback"


class CoachChatApplyIn(BaseModel):
    user_id: UUID
    checkin_date: Optional[date] = None
    apply_to: Literal["today", "tomorrow"] = "tomorrow"
    suggested_tomorrow_session: Literal["rest", "recovery", "easy", "quality", "long"]
    suggested_delta_km: Optional[float] = None
    suggested_distance_km: Optional[float] = None


class CoachChatApplyOut(BaseModel):
    ok: bool = True
    date: date
    from_session_type: Optional[str] = None
    to_session_type: str
    from_distance_km: Optional[float] = None
    to_distance_km: Optional[float] = None
    note: Optional[str] = None


class CoachAgentOption(BaseModel):
    code: Literal["A", "B"]
    label: str
    tomorrow_session: Literal["rest", "recovery", "easy", "quality", "long"]
    distance_km: Optional[float] = None
    hr_cap: Optional[int] = None
    pace_hint: Optional[str] = None
    risk: Literal["low", "medium", "high"] = "low"
    reason: str


class CoachAgentProposeOut(BaseModel):
    ok: bool = True
    date: date
    options: list[CoachAgentOption]


class CoachAgentApplyIn(BaseModel):
    user_id: UUID
    checkin_date: Optional[date] = None
    apply_to: Literal["today", "tomorrow"] = "tomorrow"
    option_code: Literal["A", "B"]


class CheckinFeedbackUpsert(BaseModel):
    user_id: UUID
    checkin_date: date
    checkin_phase: Literal["morning", "post_run"] = "morning"
    fatigue_score: Optional[int] = None
    soreness_level: Optional[int] = None
    soreness_area: Optional[str] = None
    sleep_note: Optional[str] = None

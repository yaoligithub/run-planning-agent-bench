from datetime import timedelta


def compute_target_volume(base_volume_km: float, compliance: float, fatigue_score: int):
    if fatigue_score >= 7:
        return round(base_volume_km * 0.85, 1), "疲劳偏高，下周降载 15%"
    if compliance >= 0.8:
        return round(base_volume_km * 1.05, 1), "完成率良好，下周小幅进阶 5%"
    return round(base_volume_km, 1), "维持当前训练负荷"


def _long_run_elev_pct_range(weeks_to_race: int | None, goal_type: str | None) -> tuple[float, float]:
    gt = (goal_type or "").lower()
    trail = gt in {"50k", "50mi", "100k", "100mi"}

    if trail:
        if weeks_to_race is None:
            return 0.30, 0.50
        if weeks_to_race > 20:
            return 0.20, 0.35
        if weeks_to_race > 12:
            return 0.25, 0.40
        if weeks_to_race > 6:
            return 0.35, 0.55
        if weeks_to_race > 2:
            return 0.45, 0.65
        return 0.25, 0.45

    # road-focused goals: flatter and more conservative climb targets
    if weeks_to_race is None:
        return 0.12, 0.25
    if weeks_to_race > 20:
        return 0.08, 0.15
    if weeks_to_race > 12:
        return 0.10, 0.20
    if weeks_to_race > 6:
        return 0.12, 0.25
    if weeks_to_race > 2:
        return 0.15, 0.30
    return 0.08, 0.18


def generate_sessions(
    week_start,
    weekly_days: int,
    target_volume: float,
    long_run_day: int | None,
    race_elevation_gain_m: int | None = None,
    weeks_to_race: int | None = None,
    weekly_elev_cap_m: int | None = None,
    goal_type: str | None = None,
):
    sessions = []
    long_km = round(min(target_volume * 0.35, 18), 1)
    quality_km = round(target_volume * 0.2, 1)
    easy_left = max(round(target_volume - long_km - quality_km, 1), 0)

    lr_day = long_run_day if long_run_day else 7
    long_day_idx = max(0, min(6, lr_day - 1))
    quality_day_idx = 2  # 周三

    long_elev_low = None
    long_elev_high = None
    hill_elev_low = None
    hill_elev_high = None

    if race_elevation_gain_m and race_elevation_gain_m > 0:
        low_pct, high_pct = _long_run_elev_pct_range(weeks_to_race, goal_type)
        long_elev_low = int(round(race_elevation_gain_m * low_pct))
        long_elev_high = int(round(race_elevation_gain_m * high_pct))
        gt = (goal_type or "").lower()
        trail = gt in {"50k", "50mi", "100k", "100mi"}
        hill_low_pct, hill_high_pct = ((0.10, 0.18) if trail else (0.04, 0.10))
        hill_elev_low = int(round(race_elevation_gain_m * hill_low_pct))
        hill_elev_high = int(round(race_elevation_gain_m * hill_high_pct))

        if weekly_elev_cap_m and weekly_elev_cap_m > 0:
            # keep weekly climb progressive, avoid sudden spike
            long_elev_high = min(long_elev_high, int(round(weekly_elev_cap_m * 0.7)))
            hill_elev_high = min(hill_elev_high, int(round(weekly_elev_cap_m * 0.35)))
            long_elev_low = min(long_elev_low, long_elev_high)
            hill_elev_low = min(hill_elev_low, hill_elev_high)

    long_note = "Long run, easy effort"
    if long_elev_low is not None and long_elev_high is not None:
        long_note = f"Long run, easy effort; elevation target ~{long_elev_low}-{long_elev_high}m"

    sessions.append(
        {
            "session_date": week_start + timedelta(days=long_day_idx),
            "session_type": "long",
            "target_distance_km": long_km,
            "target_hr_zone": "Z2",
            "target_elevation_gain_m": long_elev_high,
            "notes": long_note,
        }
    )

    hill_note = "Hill workout: 6-10x uphill repeats"
    if hill_elev_low is not None and hill_elev_high is not None:
        hill_note += f"; elevation target ~{hill_elev_low}-{hill_elev_high}m"

    sessions.append(
        {
            "session_date": week_start + timedelta(days=quality_day_idx),
            "session_type": "hill",
            "target_distance_km": round(max(quality_km * 0.85, 5.0), 1),
            "target_hr_zone": "Z3",
            "target_elevation_gain_m": hill_elev_high,
            "notes": hill_note,
        }
    )

    easy_runs = max(weekly_days - 2, 0)
    per_easy = round(easy_left / easy_runs, 1) if easy_runs else 0

    reserved = {long_day_idx, quality_day_idx}
    preferred_days = [0, 2, 4, 6, 1, 3, 5]
    easy_day_candidates = [d for d in preferred_days if d not in reserved]
    easy_day_indexes = easy_day_candidates[:easy_runs]

    for day_idx in easy_day_indexes:
        sessions.append(
            {
                "session_date": week_start + timedelta(days=day_idx),
                "session_type": "easy",
                "target_distance_km": per_easy,
                "target_hr_zone": "Z2",
                "target_elevation_gain_m": None,
                "notes": "Easy aerobic run",
            }
        )

    sessions.sort(key=lambda s: s["session_date"])
    return sessions

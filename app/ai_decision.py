import json
from datetime import timedelta
from statistics import mean
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.coach_engine import evaluate_daily_decision


def _load_research_text() -> str:
    try:
        with open(settings.AI_RESEARCH_FILE, "r", encoding="utf-8") as f:
            return f.read()[:20000]
    except Exception:
        return ""


def _safe_json(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    return None


def _coach_message_fallback(decision: dict[str, Any]) -> str:
    tone = "今天整体不错，继续稳住节奏。"
    if decision.get("injury_risk") == "high":
        tone = "今天先把恢复放在第一位，别硬扛。"
    elif decision.get("injury_risk") == "mild":
        tone = "身体有一点预警，今天要保守执行。"

    return (
        f"{tone}\n"
        f"- 疲劳状态：{decision.get('fatigue_status')}，伤病风险：{decision.get('injury_risk')}\n"
        f"- 明日建议：{decision.get('tomorrow_session')}，HR上限 {decision.get('hr_cap', '-')}\n"
        f"- 重点：{decision.get('pace_hint', '-') }；{decision.get('cadence_hint', '-') }"
    )


def _enforce_guardrails(base: dict[str, Any], ai: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)

    out["fatigue_status"] = str(ai.get("fatigue_status") or base["fatigue_status"]).lower()
    if out["fatigue_status"] not in {"low", "medium", "high"}:
        out["fatigue_status"] = base["fatigue_status"]

    out["injury_risk"] = str(ai.get("injury_risk") or base["injury_risk"]).lower()
    if out["injury_risk"] not in {"none", "mild", "high"}:
        out["injury_risk"] = base["injury_risk"]

    suggest = str(ai.get("tomorrow_session") or base["tomorrow_session"]).lower()
    if suggest not in {"rest", "recovery", "easy", "quality", "long"}:
        suggest = base["tomorrow_session"]

    # Hard guardrails (rule engine has final authority)
    if base["injury_risk"] == "high":
        suggest = "rest"
    elif base["injury_risk"] == "mild" and suggest in {"quality", "long"}:
        suggest = "recovery"
    elif not base.get("rule_checks", {}).get("rule_80_20", True) and suggest == "quality":
        suggest = "easy"
    elif not base.get("rule_checks", {}).get("rule_no_back_to_back_hard", True) and suggest == "quality":
        suggest = "easy"

    out["tomorrow_session"] = suggest

    ai_hr = ai.get("hr_cap")
    if isinstance(ai_hr, (int, float)) and 100 <= int(ai_hr) <= 210:
        out["hr_cap"] = int(ai_hr)

    if ai.get("pace_hint"):
        out["pace_hint"] = str(ai["pace_hint"])[:200]
    if ai.get("cadence_hint"):
        out["cadence_hint"] = str(ai["cadence_hint"])[:200]

    rationale = ai.get("rationale")
    if isinstance(rationale, list) and rationale:
        out["rationale"] = [str(x)[:220] for x in rationale][:6]

    coach_msg = ai.get("coach_feedback")
    if coach_msg:
        out["coach_feedback"] = str(coach_msg)[:1200]

    out["decision_source"] = "ai+rules"
    out["model_used"] = settings.AI_MODEL
    if not out.get("coach_feedback"):
        out["coach_feedback"] = _coach_message_fallback(out)
    return out


def _build_context(db: Session, user_id, today: models.DailyCheckIn) -> dict[str, Any]:
    recent = (
        db.query(models.DailyCheckIn)
        .filter(
            models.DailyCheckIn.user_id == user_id,
            models.DailyCheckIn.checkin_date >= (today.checkin_date - timedelta(days=6)),
        )
        .order_by(models.DailyCheckIn.checkin_date.asc())
        .all()
    )

    return {
        "today": {
            "date": str(today.checkin_date),
            "phase": today.checkin_phase,
            "distance_km": float(today.distance_km) if today.distance_km is not None else None,
            "pace_sec_per_km": float(today.pace_sec_per_km) if today.pace_sec_per_km is not None else None,
            "avg_hr": today.avg_hr,
            "cadence_spm": today.cadence_spm,
            "fatigue_score": today.fatigue_score,
            "soreness_level": today.soreness_level,
            "soreness_area": today.soreness_area,
            "sleep_note": today.sleep_note,
            "actual_session_type": today.actual_session_type,
        },
        "recent_7d": [
            {
                "date": str(x.checkin_date),
                "fatigue": x.fatigue_score,
                "soreness": x.soreness_level,
                "session": x.actual_session_type,
            }
            for x in recent
        ],
    }


def _call_ai(base_decision: dict[str, Any], context: dict[str, Any], research: str) -> dict[str, Any] | None:
    if not settings.AI_DECISION_ENABLED or not settings.AI_API_KEY:
        return None

    sys_prompt = (
        "你是跑步训练决策助手。你可以参考研究材料，但必须遵守规则引擎安全约束。"
        "请只输出JSON对象，字段: fatigue_status, injury_risk, tomorrow_session, hr_cap, pace_hint, cadence_hint, rationale(list), coach_feedback。"
        "tomorrow_session只能是 rest/recovery/easy/quality/long。"
        "coach_feedback请写成真人教练口吻，简短、具体、可执行（3-5行）。"
    )
    user_payload = {
        "rule_engine_output": base_decision,
        "runner_context": context,
        "research": research,
    }

    payload = {
        "model": settings.AI_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=settings.AI_TIMEOUT_SEC) as client:
        resp = client.post(f"{settings.AI_API_BASE_URL}/chat/completions", headers=headers, json=payload)

    if resp.status_code != 200:
        return None

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = _safe_json(content)
    return parsed


def _today_volume_line(context: dict[str, Any]) -> str:
    today = context.get("input_today") or {}
    fatigue = today.get("fatigue_score")
    soreness = today.get("soreness_level")
    if isinstance(fatigue, (int, float)) and isinstance(soreness, (int, float)) and (fatigue >= 6 or soreness >= 4):
        return "今天建议：0-5 km 恢复慢跑（不痛再跑），或直接休息。"
    return "今天建议：5-8 km 轻松跑，心率控制在 Z1-Z2。"


def _build_chat_metrics(context: dict[str, Any]) -> dict[str, Any]:
    runs = context.get("recent_runs") or []
    dists = [float(x.get("distance_km")) for x in runs if isinstance(x.get("distance_km"), (int, float))]
    hrs = [int(x.get("avg_hr")) for x in runs if isinstance(x.get("avg_hr"), int)]

    weekly_km = round(sum(dists[:7]), 1) if dists else None
    avg_dist = round(mean(dists), 1) if dists else None
    avg_hr = round(mean(hrs)) if hrs else None

    fatigue = context.get("input_today", {}).get("fatigue_score")
    soreness = context.get("input_today", {}).get("soreness_level")

    risk_level = "low"
    if isinstance(fatigue, (int, float)) and isinstance(soreness, (int, float)):
        if fatigue >= 7 or soreness >= 5:
            risk_level = "high"
        elif fatigue >= 6 or soreness >= 4:
            risk_level = "medium"

    return {
        "weekly_km_est": weekly_km,
        "avg_run_km": avg_dist,
        "avg_hr_recent": avg_hr,
        "risk_level": risk_level,
    }


def _intent_hint(msg: str) -> str:
    m = (msg or "").lower()
    if any(k in m for k in ["这周", "本周", "周量", "周跑量", "总量"]):
        return "weekly_volume"
    if any(k in m for k in ["加量", "增加", "多跑", "加公里"]):
        return "volume_increase"
    if any(k in m for k in ["减量", "太累", "跑不动", "恢复"]):
        return "reduce_or_recover"
    if any(k in m for k in ["配速", "pace", "心率", "hr", "步频"]):
        return "intensity_control"
    if any(k in m for k in ["明天", "课程", "改课", "计划"]):
        return "plan_adjustment"
    return "general"


def _maybe_add_distance_guidance(msg: str, context: dict[str, Any], session: str | None, delta: float | None, reply: str) -> str:
    ask_distance = any(k in (msg or "") for k in ["跑多少", "多少公里", "几公里", "跑多长", "多远"])
    if not ask_distance:
        return reply

    # If user asks for "today", avoid forcing a "tomorrow" answer.
    ask_today = ("今天" in (msg or "")) and ("明天" not in (msg or ""))
    today = context.get("input_today") or {}
    fatigue = today.get("fatigue_score")
    soreness = today.get("soreness_level")
    if ask_today:
        if isinstance(fatigue, (int, float)) and isinstance(soreness, (int, float)) and (fatigue >= 6 or soreness >= 4):
            line = "今天建议跑量：0-5 km 恢复慢跑（或直接休息），以无痛为前提。"
        else:
            line = "今天建议跑量：5-8 km 轻松跑，心率控制在Z1-Z2。"
        return reply if line in reply else f"{reply}\n{line}"

    tp = context.get("tomorrow_plan") or {}
    base = tp.get("target_distance_km")
    if isinstance(base, (int, float)):
        target = float(base) + (float(delta) if isinstance(delta, (int, float)) else 0.0)
    else:
        if session == "recovery":
            target = 6.0
        elif session == "easy":
            target = 8.0
        elif session == "long":
            target = 18.0
        elif session == "rest":
            target = 0.0
        else:
            target = 7.0

    if session == "recovery":
        target = min(target, 8.0)
    elif session == "easy":
        target = min(target, 16.0)

    target = max(0.0, round(target, 1))
    if session == "rest" or target == 0:
        line = "明天建议：休息，不跑。"
    else:
        lo = max(0.0, round(target - 1.0, 1))
        hi = round(target + 1.0, 1)
        line = f"明天建议跑量：{target} km（可在 {lo}-{hi} km 浮动）。"

    if line in reply:
        return reply
    return f"{reply}\n{line}"


def generate_coach_chat_reply(message: str, context: dict[str, Any]) -> dict[str, Any]:
    msg = (message or "").strip()
    if not msg:
        return {
            "ok": True,
            "reply": "你可以直接问：明天能不能加量？加多少更稳妥？",
            "suggested_tomorrow_session": None,
            "suggested_delta_km": None,
            "caution": None,
            "source": "fallback",
        }

    today = context.get("input_today") or {}
    fatigue = today.get("fatigue_score")
    soreness = today.get("soreness_level")
    ask_today = ("今天" in msg) and ("明天" not in msg)
    metrics = _build_chat_metrics(context)
    intent = _intent_hint(msg)

    # Coach follow-up mode: ask one key question first when critical inputs are missing.
    missing = []
    if fatigue is None:
        missing.append("疲劳评分")
    if soreness is None:
        missing.append("不适程度")
    if not (context.get("tomorrow_plan") or {}).get("session_type"):
        missing.append("明天原计划类型")
    if intent in {"volume_increase", "plan_adjustment", "intensity_control"} and missing:
        ask = "；".join(missing[:2])
        q = f"我先确认1个关键信息：请补充{ask}（例如 疲劳6/10、不适3/10、原计划easy），我再给你精确建议。"
        return {
            "ok": True,
            "reply": q,
            "suggested_tomorrow_session": None,
            "suggested_delta_km": None,
            "caution": "信息不足时先不改课、不加量。",
            "source": "fallback",
        }

    if isinstance(fatigue, (int, float)) and isinstance(soreness, (int, float)) and (fatigue >= 6 or soreness >= 4):
        fallback_reply = "结论：先不加量。原因：你今天疲劳/酸痛偏高。执行：明天改 recovery 或 easy 短距离，HR 控制在 Z1-Z2。"
        fallback_session = "recovery"
        fallback_delta = 0.0
        fallback_caution = "若疼痛持续或加重，请休息并取消强度课。"
    elif intent == "weekly_volume":
        wk = metrics.get("weekly_km_est")
        if isinstance(wk, (int, float)):
            lo = max(0.0, round(float(wk) * 0.9, 1))
            hi = round(float(wk) * 1.05, 1)
            fallback_reply = f"结论：本周先稳住总量。原因：当前疲劳/酸痛风险不低。执行：本周总量控制在 {lo}-{hi} km，更关注恢复质量。"
        else:
            fallback_reply = "结论：本周先保守。原因：当前状态不适合冲量。执行：按 easy/recovery 为主，周总量先不要高于上周。"
        fallback_session = None
        fallback_delta = None
        fallback_caution = "若疼痛加重，本周立即减量20%-40%。"
    elif intent == "volume_increase":
        fallback_reply = "结论：可以小幅加量。原因：当前主观状态可控。执行：仅加 1km，强度维持 easy，跑后观察腿部反馈。"
        fallback_session = "easy"
        fallback_delta = 1.0
        fallback_caution = "任何刺痛或疲劳突增，立刻停止加量。"
    elif intent == "intensity_control":
        fallback_reply = "结论：优先控强度。原因：先守住有氧区间更稳。执行：明天按 easy/recovery，HR 不超过计划上限。"
        fallback_session = "easy"
        fallback_delta = 0.0
        fallback_caution = "不要同时加配速和加里程。"
    else:
        fallback_reply = "结论：先按计划稳妥执行。原因：当前信息未显示必须大改。执行：若体感良好可微调 +1km，保持 easy。"
        fallback_session = "easy"
        fallback_delta = 1.0
        fallback_caution = "若疲劳≥7或疼痛≥4，不要加量。"

    if not settings.AI_DECISION_ENABLED or not settings.AI_API_KEY:
        return {
            "ok": True,
            "reply": _maybe_add_distance_guidance(msg, context, fallback_session, fallback_delta, fallback_reply),
            "suggested_tomorrow_session": fallback_session,
            "suggested_delta_km": fallback_delta,
            "caution": fallback_caution,
            "source": "fallback",
        }

    sys_prompt = (
        "你是资深马拉松教练。用户会问是否加量、是否改课表。"
        "请先判断用户问的是今天还是明天；若问今天，必须给今天可执行建议，不能答成明天。"
        "请基于 context 里的 input_today、tomorrow_plan、recent_runs、conversation_history、metrics、intent_hint 给出明确 YES/NO 结论和替代方案。"
        "严格保守：fatigue>=6 或 soreness>=4 时，禁止加量，优先 recovery/easy；fatigue>=7 或 soreness>=5 时优先 rest/recovery。"
        "输出必须是JSON对象，字段: reply, suggested_tomorrow_session, suggested_delta_km, caution。"
        "suggested_tomorrow_session只能是 rest/recovery/easy/quality/long 或 null。"
        "suggested_delta_km 为数字，可为负数；若不建议调整则为0或null。"
        "reply要求包含：结论 + 原因 + 执行要点（今天或明天需与用户问题一致）；限制180字内。"
        "若信息不足以安全决策，请先只问1个最关键追问（写在reply里），并将 suggested_tomorrow_session 设为 null、suggested_delta_km 设为 null。"
        "若 conversation_history 提到具体伤痛部位/目标（如膝盖外侧痛、周末长距离），需在本轮回复里显式承接。"
    )

    payload = {
        "model": settings.AI_MODEL,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {"message": msg, "context": context, "metrics": metrics, "intent_hint": intent},
                    ensure_ascii=False,
                ),
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=settings.AI_TIMEOUT_SEC) as client:
            resp = client.post(f"{settings.AI_API_BASE_URL}/chat/completions", headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError("ai status error")
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = _safe_json(content) or {}
    except Exception:
        return {
            "ok": True,
            "reply": _maybe_add_distance_guidance(msg, context, fallback_session, fallback_delta, fallback_reply),
            "suggested_tomorrow_session": fallback_session,
            "suggested_delta_km": fallback_delta,
            "caution": fallback_caution,
            "source": "fallback",
        }

    session = parsed.get("suggested_tomorrow_session")
    if session not in {"rest", "recovery", "easy", "quality", "long", None}:
        session = None

    delta = parsed.get("suggested_delta_km")
    if isinstance(delta, (int, float)):
        delta = max(-10.0, min(10.0, round(float(delta), 1)))
    else:
        delta = None

    # Final safety override from latest form snapshot
    if isinstance(fatigue, (int, float)) and isinstance(soreness, (int, float)) and (fatigue >= 6 or soreness >= 4):
        if session in {"quality", "long", "easy"}:
            session = "recovery"
        if delta is not None and delta > 0:
            delta = 0.0

    if isinstance(fatigue, (int, float)) and isinstance(soreness, (int, float)) and (fatigue >= 7 or soreness >= 5):
        session = "rest" if session in {"quality", "long", "easy", "recovery", None} else session
        if delta is not None and delta > 0:
            delta = 0.0

    final_reply = str(parsed.get("reply") or fallback_reply)[:220]
    final_reply = _maybe_add_distance_guidance(msg, context, session, delta, final_reply)

    # Hard override for "today" questions to prevent tomorrow-loop replies.
    if ask_today:
        final_reply = f"{str(parsed.get('reply') or fallback_reply)[:180]}\n{_today_volume_line(context)}"
        session = None
        delta = None

    # Weekly question should not force tomorrow plan fields.
    if intent == "weekly_volume":
        session = None
        delta = None

    # De-loop: if highly similar to last assistant reply, output concise alternative.
    hist = context.get("conversation_history") or []
    last_ai = None
    for h in reversed(hist):
        if isinstance(h, dict) and h.get("role") == "assistant":
            last_ai = str(h.get("text") or "")
            break
    if last_ai and final_reply[:80] and final_reply[:80] in last_ai:
        alt = "换个更直接的说法：今天保守跑或休息；本周别加量，先把酸痛降到3/10以下再考虑推进。"
        final_reply = alt

    return {
        "ok": True,
        "reply": final_reply[:300],
        "suggested_tomorrow_session": session,
        "suggested_delta_km": delta,
        "caution": str(parsed.get("caution") or fallback_caution)[:120] or None,
        "source": "ai",
    }


def generate_coach_decision(db: Session, user_id, profile: models.RunnerProfile, today: models.DailyCheckIn):
    base = evaluate_daily_decision(db, user_id, profile, today)
    base["decision_source"] = "rule_engine"
    base["model_used"] = None
    base["coach_feedback"] = _coach_message_fallback(base)

    context = _build_context(db, user_id, today)
    research = _load_research_text()
    ai = _call_ai(base, context, research)
    if not ai:
        return base

    return _enforce_guardrails(base, ai)

# Run Planning Agent Bench

A long-horizon agent benchmark for adaptive running plan generation under real-world disruptions.

## 1) Overview

`run-planning-agent-bench` evaluates whether an agent can maintain and adapt a multi-week running plan when conditions change (e.g., injury, weather, schedule conflicts).

This project is built from a production-style running planner app and is being extended into a **research-engineering benchmark** focused on:
- long-horizon consistency
- interruption recovery
- decision quality under uncertainty
- robustness across scenarios

## 2) Why this project

Many agents perform well on short, static tasks but degrade when:
- goals evolve over time
- context is partially missing
- interruptions require re-planning

This benchmark aims to measure **real capability**, not just one-shot output quality.

## 3) Environment Design

Each episode simulates a runner with:
- profile: level, weekly mileage tolerance, goal race distance
- constraints: available training days, time budget, injury history
- dynamic events: minor injury, missed session, weather disruption, schedule change

### Task objective
Generate and iteratively update a training plan that remains:
1. feasible
2. goal-aligned
3. safety-aware (injury-aware)
4. stable across updates

## 4) Current System (Implemented)

- FastAPI + PostgreSQL backend
- Goal creation (`/goals`)
- Weekly plan generation (`/plans/generate`)
- Current plan retrieval (`/plans/current`)
- Distance unit support (km/mi)
- User model + execution records (`/users`, `/executions`)
- Strava OAuth + activity sync (`/auth/strava/*`)
- AI coach module (`/coach`) with guardrail-constrained recommendations

## 5) Benchmark Tasks (v0.1 target)

- Base plan creation (8-week / 12-week blocks)
- Missed-week recovery
- Load reduction after fatigue signal
- Rain/heat adaptation
- Taper adjustment
- Mid-cycle goal change (e.g., 10k -> Half Marathon)

## 6) Evaluation Protocol

Primary metrics:
- **Task Success Rate**: scenarios that satisfy feasibility + goal constraints
- **Recovery Score**: quality of re-plan after interruptions
- **Plan Stability**: minimal unnecessary churn between revisions
- **Step Efficiency**: number of agent interactions/actions to resolve scenario
- **Safety Violations**: overtraining / unsafe weekly jumps

See `docs/evaluation_protocol.md` for detailed metric definitions and run protocol.

## 7) Quickstart

```bash
cp .env.example .env
docker compose up --build
```

Entry points:
- UI: `http://localhost:8000/`
- Coach UI: `http://localhost:8000/coach`
- History analysis: `http://localhost:8000/history-analysis`
- API docs: `http://localhost:8000/docs`

## 8) Repository Structure

```text
run-planning-agent-bench/
  README.md
  app/
  docs/
    evaluation_protocol.md
  docker-compose.yml
  Dockerfile
  requirements.txt
```

## 9) Limitations

- Current scenarios are still semi-synthetic
- No biomechanical model yet
- LLM quality depends on model/prompting configuration

## 10) Roadmap

- [ ] Add deterministic scenario suite (10+ -> 25+)
- [ ] Add baseline comparison runners (rule-based vs LLM)
- [ ] Add ablation study (memory / interruption handling)
- [ ] Add reproducible eval scripts + result tables
- [ ] Publish short technical report

## 11) Disclaimer

This project is for research/benchmarking and personal training planning support only, and is **not medical advice**.

## 12) License

MIT (to be added)

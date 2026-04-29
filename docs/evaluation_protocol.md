# Evaluation Protocol (v0.1)

## 1) Goal

Measure whether a planning agent can produce and maintain safe, feasible, goal-aligned running plans under interruptions and evolving constraints.

## 2) Scenario Format

Each scenario includes:
- runner profile (experience, baseline weekly volume, target race)
- constraints (days/week, available time, injury history)
- event timeline (missed run, fatigue spike, weather block, schedule change)
- expected constraints for success

## 3) Primary Metrics

### 3.1 Task Success Rate
A scenario is successful if all required constraints are satisfied:
- plan remains feasible for available days/time
- plan remains aligned to target race goal
- no hard safety constraint violations

`task_success_rate = successful_scenarios / total_scenarios`

### 3.2 Recovery Score
How well the agent adapts after interruption events.

Per event score (0-1):
- 0.4: feasibility preserved
- 0.3: safety preserved
- 0.3: goal alignment preserved

Scenario recovery score = mean(event scores)

### 3.3 Plan Stability
Penalizes unnecessary churn between consecutive plan revisions.

Example proxy:
- count changed sessions beyond required adaptation window
- normalize by total planned sessions

Lower churn with preserved success = better stability.

### 3.4 Step Efficiency
Number of agent actions/interactions required to resolve scenario.

Lower is better if success and safety are maintained.

### 3.5 Safety Violations
Count of violations such as:
- excessive weekly volume jump
- high-intensity stacking without recovery
- no recovery day after high strain signals

## 4) Run Protocol

- Use fixed random seeds for reproducibility
- Evaluate across the same scenario set per baseline
- Run multiple seeds (recommended >= 3)
- Report mean and standard deviation

## 5) Baselines

Minimum baselines:
1. Rule-based planner
2. LLM-based planner

Optional:
3. Hybrid planner (rules + LLM critique)

## 6) Reporting Template

For each baseline, report:
- task success rate
- recovery score
- plan stability
- step efficiency
- safety violations

Also provide:
- per-scenario breakdown
- representative failure cases
- qualitative error categories

## 7) Known Threats to Validity

- Synthetic scenario bias
- Metric gaming risk
- Prompt sensitivity for LLM baseline
- Potential mismatch with real coaching decisions

## 8) Next Iteration (v0.2)

- richer long-horizon scenario graph
- hidden evaluation set
- stronger anti-gaming checks
- confidence intervals and significance tests

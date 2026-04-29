# Running Planner

给自己用的跑步计划 App（MVP）。

## 当前范围
- FastAPI + PostgreSQL 后端骨架
- 目标创建（/goals）
- 周计划生成（/plans/generate）
- 查看当前计划（/plans/current）
- 支持距离单位 km/mi（输入与输出）
- 每日 sessions 按日期排序输出
- Strava OAuth 连接 + token refresh + 跑步活动同步（MVP）
- 生成计划支持自动读取最近4周活动推导输入（跑量/完成率/疲劳）
- 最近4周 Strava 活动可视化（首页 + `/activities/recent`）
- 目标支持超马选项（50k/50mi/100k/100mi）+ 赛事模板快捷选择（含 UTMB）
- 首页表单与最近计划本地缓存（刷新后不丢）
- 用户模型（/users）与训练执行记录（/executions）
- AI 自教练模块（`/coach`）：
  - 个体参数化（配速/HR/cadence）
  - 每日 check-in（疲劳/不适/睡眠，支持晨起/跑后双次）
  - Injury-aware 次日建议（遵守 80/20、避免连续高强度）
  - 每周复盘与 cutback 建议
  - 可选接入 LLM 决策（规则引擎做最终安全约束）

## 快速启动
```bash
cp .env.example .env
docker compose up --build
```

## 访问入口
- 计划页（推荐手机）：`http://localhost:8000/`
- 历史智能分析页：`http://localhost:8000/history-analysis`
- AI 教练页（v1.0）：`http://localhost:8000/coach`
- API 文档（Swagger）：`http://localhost:8000/docs`

## Strava 快速接入
1. 在 `.env` 配置：
   - `STRAVA_CLIENT_ID`
   - `STRAVA_CLIENT_SECRET`
   - `STRAVA_REDIRECT_URI`（例如 `http://<你的IP>:8000/auth/strava/callback`）
2. 打开：`GET /auth/strava/connect?user_id=<uuid>` 拿到 `authorize_url`
3. 浏览器访问 `authorize_url` 完成授权
4. 授权回调成功后执行：`POST /auth/strava/sync?user_id=<uuid>` 同步活动

## AI 决策模型（可选开启）
在 `.env` 增加：
- `AI_DECISION_ENABLED=true`
- `AI_API_KEY=<你的key>`
- `AI_API_BASE_URL=https://api.openai.com/v1`（可替换兼容服务）
- `AI_MODEL=gpt-4o-mini`
- `AI_RESEARCH_FILE=/root/second-brain/02_projects/running-planner/coach_research.md`

说明：模型会参考规则引擎输出 + research 文档生成建议，但最终会经过 guardrails 约束。

## 下一步
1. 把 `/auth/strava/sync` 改为异步任务（RQ/Celery）
2. 将 `/coach/daily-checkin` 与 `/plans/adapt` 打通（按风险自动重排本周课表）
3. 新增 taper/peak 模块（赛前 3 周）

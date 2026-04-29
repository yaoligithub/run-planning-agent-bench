from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#0b1020" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="Run Planner" />
  <title>Running Planner</title>
  <style>
    :root {
      --bg: #0b1020;
      --card: #141b32;
      --muted: #9fb0db;
      --text: #e8eeff;
      --line: #2b365f;
      --primary: #4f8cff;
      --green: #22c55e;
      --orange: #fb923c;
      --purple: #a78bfa;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', sans-serif;
      background: radial-gradient(1200px 600px at 20% -10%, #1d2d62 0%, var(--bg) 50%);
      color: var(--text);
      padding: env(safe-area-inset-top) 0 env(safe-area-inset-bottom);
    }

    .app {
      max-width: 760px;
      margin: 0 auto;
      padding: 14px;
    }

    .hero {
      background: linear-gradient(135deg, #2952c6, #6d7bff);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, .25);
      margin-bottom: 12px;
    }

    .hero h1 { margin: 0; font-size: 22px; }
    .hero p { margin: 6px 0 0; color: #e7edff; font-size: 13px; opacity: .95; }
    .hero-actions { display: flex; gap: 8px; margin-top: 10px; }
    .mini-btn {
      border: 1px solid rgba(255,255,255,.35);
      background: rgba(13, 22, 46, .25);
      color: #fff;
      border-radius: 999px;
      padding: 7px 12px;
      font-size: 12px;
      font-weight: 700;
    }

    .card {
      background: color-mix(in oklab, var(--card) 92%, black);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      margin-bottom: 10px;
    }

    .title { margin: 0 0 10px; font-size: 16px; }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .field label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }

    .field input, .field select {
      width: 100%;
      border-radius: 10px;
      border: 1px solid #384777;
      background: #0f1730;
      color: #fff;
      padding: 10px;
      font-size: 14px;
    }

    .actions { display: flex; gap: 8px; margin-top: 10px; }
    .btn {
      flex: 1;
      border: 0;
      border-radius: 11px;
      padding: 11px;
      color: white;
      font-weight: 700;
      font-size: 14px;
    }
    .btn.primary { background: var(--primary); }
    .btn.secondary { background: #334155; }

    .chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    .chip {
      font-size: 12px;
      border-radius: 999px;
      padding: 6px 10px;
      border: 1px solid #3c4e85;
      color: #dfe7ff;
      background: #121a34;
    }

    .sessions {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 10px;
    }

    .session {
      border: 1px solid #33467e;
      border-left-width: 5px;
      border-radius: 12px;
      background: #101830;
      padding: 10px;
    }
    .session.long { border-left-color: var(--orange); }
    .session.tempo { border-left-color: var(--purple); }
    .session.easy { border-left-color: var(--green); }

    .session-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 6px;
    }

    .session .date { font-weight: 700; font-size: 14px; }
    .session .type {
      font-size: 12px;
      border: 1px solid #3d4e86;
      padding: 3px 8px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: .4px;
    }

    .session .meta { color: #d2ddff; font-size: 14px; }
    .session .note { color: var(--muted); font-size: 12px; margin-top: 4px; }

    details {
      margin-top: 10px;
      border-top: 1px dashed #33467e;
      padding-top: 8px;
    }
    summary { color: var(--muted); font-size: 12px; cursor: pointer; }
    pre {
      margin-top: 8px;
      white-space: pre-wrap;
      word-break: break-word;
      background: #0d142a;
      border: 1px solid #2b3a6e;
      border-radius: 10px;
      padding: 10px;
      color: #cdd9ff;
      font-size: 12px;
      max-height: 280px;
      overflow: auto;
    }

    .muted { color: var(--muted); font-size: 13px; }
    .status { margin-top: 6px; color: #b6c8ff; font-size: 12px; }

    .activity-list { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; }
    .activity-item {
      border: 1px solid #33467e;
      border-radius: 12px;
      background: #101830;
      padding: 10px;
      display: flex;
      justify-content: space-between;
      gap: 10px;
    }
    .activity-main { font-size: 13px; }
    .activity-sub { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .bars { margin-top: 10px; display: flex; flex-direction: column; gap: 6px; }
    .bar-row { display: grid; grid-template-columns: 72px 1fr 70px; gap: 8px; align-items: center; }
    .bar-track { height: 8px; border-radius: 999px; background: #1b274b; overflow: hidden; }
    .bar-fill { height: 100%; background: linear-gradient(90deg, #3b82f6, #22c55e); }
    .small { font-size: 12px; color: var(--muted); }

    @media (max-width: 640px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="app">
    <section class="hero">
      <h1>🏃 Running Planner</h1>
      <p>像 App 一样生成你的周跑步计划（支持 km / miles）</p>
      <div class="hero-actions">
        <button class="mini-btn" onclick="getCurrentPlan()">刷新计划</button>
        <button class="mini-btn" onclick="go('/history-analysis')">历史智能分析</button>
        <button class="mini-btn" onclick="go('/coach')">AI教练v1.0</button>
        <button class="mini-btn" onclick="hardRefresh()">刷新页面</button>
      </div>
    </section>

    <section class="card">
      <h2 class="title">参数</h2>
      <div class="grid">
        <div class="field">
          <label>用户名</label>
          <input id="display_name" value="我的跑步账号" />
          <input id="user_id" type="hidden" value="11111111-1111-1111-1111-111111111111" />
        </div>
        <div class="field">
          <label>目标类型</label>
          <select id="goal_type">
            <option value="5k">5k</option>
            <option value="10k" selected>10k</option>
            <option value="hm">half marathon</option>
            <option value="fm">marathon</option>
            <option value="50k">ultra 50k</option>
            <option value="50mi">ultra 50mi</option>
            <option value="100k">ultra 100k</option>
            <option value="100mi">ultra 100mi</option>
          </select>
        </div>
        <div class="field">
          <label>赛事模板（可选）</label>
          <select id="race_preset" onchange="applyRacePreset()">
            <option value="">不选赛事（仅按目标类型）</option>
          </select>
        </div>
        <div class="field">
          <label>目标日期</label>
          <input id="target_date" value="2026-09-20" />
        </div>
        <div class="field">
          <label id="race_elev_label">比赛总爬升 (ft)</label>
          <input id="race_elevation_gain" type="number" value="1000" />
        </div>
        <div class="field">
          <label>周起始日期（建议填下周一）</label>
          <input id="week_start" value="2026-05-04" />
        </div>
        <div class="field">
          <label>每周训练天数</label>
          <input id="weekly_days" type="number" value="4" />
        </div>
        <div class="field">
          <label>长跑日（1=Mon, 7=Sun）</label>
          <input id="long_run_day" type="number" value="7" />
        </div>
        <div class="field">
          <label>自动从最近4周活动推导输入</label>
          <select id="auto_inputs" onchange="toggleManualInputs()">
            <option value="on" selected>开启（推荐）</option>
            <option value="off">关闭（手动）</option>
          </select>
        </div>
        <div class="field">
          <label>基准周跑量（手动模式）</label>
          <input id="base_volume" type="number" step="0.1" value="30" disabled />
        </div>
        <div class="field">
          <label>单位</label>
          <select id="distance_unit">
            <option value="mi" selected>miles (mi)</option>
            <option value="km">kilometers (km)</option>
          </select>
        </div>
        <div class="field">
          <label>完成率 (0-1，手动模式)</label>
          <input id="compliance" type="number" step="0.01" value="0.85" disabled />
        </div>
        <div class="field">
          <label>疲劳分 (1-10，手动模式)</label>
          <input id="fatigue_score" type="number" min="1" max="10" value="3" disabled />
        </div>
      </div>

      <div class="actions">
        <button class="btn primary" onclick="generatePlan()">生成下周计划</button>
        <button class="btn secondary" onclick="getCurrentPlan()">查看当前计划</button>
      </div>
      <div class="grid" style="margin-top:8px">
        <div class="field">
          <label>查看计划范围</label>
          <select id="view_week_scope" onchange="getCurrentPlan()">
            <option value="last_week">上周（完成情况）</option>
            <option value="this_week">本周</option>
            <option value="next_week" selected>下周</option>
            <option value="latest">最近一版</option>
          </select>
        </div>
      </div>
    </section>

    <section class="card" id="planCard">
      <h2 class="title" id="plan_title">下周计划</h2>
      <div id="summary" class="muted">还没有计划，点击上方按钮开始。</div>
      <div id="status" class="status">状态：等待操作</div>
      <div id="sessions" class="sessions"></div>
      <div id="plan_totals" class="muted" style="margin-top:10px"></div>

      <details>
        <summary>查看原始 JSON</summary>
        <pre id="raw">{}</pre>
      </details>
    </section>

  </div>

<script>
const summaryEl = document.getElementById('summary');
const statusEl = document.getElementById('status');
const sessionsEl = document.getElementById('sessions');
const rawEl = document.getElementById('raw');
const planTitleEl = document.getElementById('plan_title');
const planTotalsEl = document.getElementById('plan_totals');
const STORAGE_KEY = 'running_planner_form_v1';
const LAST_PLAN_KEY = 'running_planner_last_plan_v1';
const GLOBAL_UNIT_KEY = 'running_planner_unit_v1';
let prevUnit = 'mi';

const RACE_PRESETS = [
  { key: 'shanghai-marathon-2026', label: '上海马拉松 2026', goal_type: 'fm', target_date: '2026-11-29', weekly_days: 5, race_elevation_gain_m: 180 },
  { key: 'beijing-marathon-2026', label: '北京马拉松 2026', goal_type: 'fm', target_date: '2026-10-25', weekly_days: 5, race_elevation_gain_m: 220 },
  { key: 'xiamen-marathon-2027', label: '厦门马拉松 2027', goal_type: 'fm', target_date: '2027-01-03', weekly_days: 5, race_elevation_gain_m: 160 },
  { key: 'utmb-occ-2026', label: 'UTMB OCC 2026 (55K)', goal_type: '50k', target_date: '2026-08-27', weekly_days: 5, race_elevation_gain_m: 3500 },
  { key: 'utmb-ccc-2026', label: 'UTMB CCC 2026 (100K)', goal_type: '100k', target_date: '2026-08-28', weekly_days: 6, race_elevation_gain_m: 6100 },
  { key: 'utmb-main-2026', label: 'UTMB 2026 (100M)', goal_type: '100mi', target_date: '2026-08-29', weekly_days: 6, race_elevation_gain_m: 10000 },
  { key: 'utmb-ptl-2026', label: 'UTMB PTL 2026 (~300K team)', goal_type: '100mi', target_date: '2026-08-24', weekly_days: 6, race_elevation_gain_m: 25000 },
  { key: 'ultra-50k-generic', label: '超马 50K（通用）', goal_type: '50k', target_date: '2026-10-01', weekly_days: 5, race_elevation_gain_m: 2000 },
  { key: 'ultra-50mi-generic', label: '超马 50mi（通用）', goal_type: '50mi', target_date: '2026-10-01', weekly_days: 5, race_elevation_gain_m: 3500 },
  { key: 'ultra-100k-generic', label: '超马 100K（通用）', goal_type: '100k', target_date: '2026-11-01', weekly_days: 6, race_elevation_gain_m: 5000 },
  { key: 'ultra-100mi-generic', label: '超马 100mi（通用）', goal_type: '100mi', target_date: '2026-11-01', weekly_days: 6, race_elevation_gain_m: 8000 },
];

function uiValue(id) { return document.getElementById(id).value.trim(); }
function unit() { return uiValue('distance_unit') === 'mi' ? 'mi' : 'km'; }
function unitFromUrl(){
  const q = new URLSearchParams(window.location.search || '');
  const u = q.get('unit');
  return (u === 'km' || u === 'mi') ? u : null;
}
function loadGlobalUnit(){
  const fromUrl = unitFromUrl();
  if(fromUrl) return fromUrl;
  const u = localStorage.getItem(GLOBAL_UNIT_KEY);
  return (u === 'km' || u === 'mi') ? u : 'mi';
}
function saveGlobalUnit(u){
  const v = (u === 'km' || u === 'mi') ? u : 'mi';
  localStorage.setItem(GLOBAL_UNIT_KEY, v);
}
function go(path){
  window.location.href = `${path}?unit=${encodeURIComponent(unit())}`;
}
function autoInputsOn() { return uiValue('auto_inputs') === 'on'; }
function elevationUnit(){ return unit()==='mi' ? 'ft' : 'm'; }
function elevToMeters(v){ const n=Number(v); if(Number.isNaN(n)) return null; return unit()==='mi' ? Math.round(n/3.28084) : Math.round(n); }
function elevFromMeters(v){ const n=Number(v); if(Number.isNaN(n)) return ''; return unit()==='mi' ? Math.round(n*3.28084) : Math.round(n); }
function refreshElevLabel(){ document.getElementById('race_elev_label').textContent = `比赛总爬升 (${elevationUnit()})`; }
function setStatus(msg) { statusEl.textContent = `状态：${msg}`; }
function scopeText(scope){
  if(scope === 'last_week') return '上周';
  if(scope === 'this_week') return '本周';
  if(scope === 'next_week') return '下周';
  return '最近一版';
}
function refreshPlanTitle(){
  if(!planTitleEl) return;
  const scope = uiValue('view_week_scope') || 'next_week';
  planTitleEl.textContent = `${scopeText(scope)}计划`;
}
function nowText() { return new Date().toLocaleTimeString('zh-CN', { hour12: false }); }
function hardRefresh() { window.location.reload(); }
function nextMondayISO(){
  const d = new Date();
  d.setHours(0,0,0,0);
  const day = d.getDay(); // 0=Sun
  const delta = ((8 - day) % 7) || 7; // always next Monday
  d.setDate(d.getDate() + delta);
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const dd = String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${dd}`;
}
function toggleManualInputs() {
  const disabled = autoInputsOn();
  document.getElementById('base_volume').disabled = disabled;
  document.getElementById('compliance').disabled = disabled;
  document.getElementById('fatigue_score').disabled = disabled;
}

function initRacePresets() {
  const sel = document.getElementById('race_preset');
  RACE_PRESETS.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.key;
    opt.textContent = p.label;
    sel.appendChild(opt);
  });
}

function applyRacePreset() {
  const key = uiValue('race_preset');
  if (!key) return;
  const preset = RACE_PRESETS.find(p => p.key === key);
  if (!preset) return;
  document.getElementById('goal_type').value = preset.goal_type;
  document.getElementById('target_date').value = preset.target_date;
  document.getElementById('weekly_days').value = String(preset.weekly_days);
  if (preset.race_elevation_gain_m != null) {
    document.getElementById('race_elevation_gain').value = String(elevFromMeters(preset.race_elevation_gain_m));
  }
  saveFormState();
}

function formFieldIds() {
  return [
    'user_id', 'display_name', 'goal_type', 'race_preset', 'target_date', 'race_elevation_gain', 'week_start',
    'weekly_days', 'long_run_day', 'auto_inputs', 'base_volume',
    'distance_unit', 'compliance', 'fatigue_score', 'view_week_scope'
  ];
}

function saveFormState() {
  const state = {};
  formFieldIds().forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    state[id] = el.value;
  });
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  saveGlobalUnit(state.distance_unit);
}

function loadFormState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;
  try {
    const state = JSON.parse(raw);
    formFieldIds().forEach(id => {
      const el = document.getElementById(id);
      if (!el || state[id] === undefined || state[id] === null) return;
      el.value = state[id];
    });
  } catch (_) {
    // ignore bad localStorage payload
  }
}

function bindAutosave() {
  formFieldIds().forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('change', saveFormState);
    el.addEventListener('input', saveFormState);
  });
}

function fmtDate(d) {
  const value = (d && d.includes && d.includes('T')) ? d : `${d}T00:00:00`;
  const dt = new Date(value);
  return dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}
function kmToUnit(km, u){
  if(km===null || km===undefined) return null;
  const n = Number(km);
  if(Number.isNaN(n)) return null;
  return u === 'mi' ? (n * 0.621371) : n;
}
function mToElevUnit(m, u){
  if(m===null || m===undefined) return null;
  const n = Number(m);
  if(Number.isNaN(n)) return null;
  return u === 'mi' ? (n * 3.28084) : n;
}
async function loadActualsForPlan(plan){
  if(!plan || !plan.week_start || !plan.week_end) return {};
  try{
    const user_id = uiValue('user_id');
    const tz = encodeURIComponent(Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/Los_Angeles');
    const res = await fetch(`/coach/calendar?user_id=${encodeURIComponent(user_id)}&days=60&tz=${tz}`);
    const data = await res.json();
    if(!res.ok || !data.ok) return {};
    const start = String(plan.week_start);
    const end = String(plan.week_end);
    const out = {};
    (data.items || []).forEach(it=>{
      const d = String(it.date || '');
      if(d >= start && d <= end){
        out[d] = it;
      }
    });
    return out;
  }catch(_){ return {}; }
}

function render(plan, actualByDate = {}) {
  rawEl.textContent = JSON.stringify(plan, null, 2);
  sessionsEl.innerHTML = '';
  if(planTotalsEl) planTotalsEl.textContent = '';
  setStatus(`已刷新 ${nowText()}`);

  if (plan && plan.sessions) {
    localStorage.setItem(LAST_PLAN_KEY, JSON.stringify(plan));
  }

  if (!plan || !plan.sessions) {
    summaryEl.textContent = '暂无计划';
    return;
  }

  summaryEl.innerHTML = `
    <div class="chips">
      <span class="chip">Week: ${plan.week_start} → ${plan.week_end}</span>
      <span class="chip">Volume: ${plan.planned_volume} ${plan.volume_unit}</span>
      <span class="chip">Rationale: ${plan.rationale || '-'}</span>
    </div>
  `;

  let totalDistance = 0;
  let totalElevation = 0;
  let doneDistance = 0;
  let doneElevation = 0;
  plan.sessions.forEach(s => {
    if(s.target_distance != null) totalDistance += Number(s.target_distance || 0);
    if(s.target_elevation_gain != null) totalElevation += Number(s.target_elevation_gain || 0);
    const actual = actualByDate[String(s.session_date)] || null;
    const actDist = kmToUnit(actual ? actual.distance_km : null, (s.distance_unit || plan.volume_unit || 'km'));
    const actElev = mToElevUnit(actual ? actual.elevation_gain_m : null, (s.distance_unit || plan.volume_unit || 'km'));
    if(actDist != null) doneDistance += Number(actDist || 0);
    if(actElev != null) doneElevation += Number(actElev || 0);
    const card = document.createElement('div');
    card.className = `session ${s.session_type || ''}`;
    card.innerHTML = `
      <div class="session-top">
        <div class="date">${fmtDate(s.session_date)}</div>
        <div class="type">${s.session_type || 'run'}</div>
      </div>
      <div class="meta">计划：${s.target_distance ?? '-'} ${s.distance_unit || ''} · ${s.target_hr_zone || '-'} · Elev ${s.target_elevation_gain ?? '-'} ${s.elevation_unit || ''}</div>
      <div class="activity-sub">实际：${actDist!=null ? actDist.toFixed(1) : '-'} ${s.distance_unit || ''} · Elev ${actElev!=null ? Math.round(actElev) : '-'} ${s.elevation_unit || ''}</div>
      <div class="note">${s.notes || ''}</div>
    `;
    sessionsEl.appendChild(card);
  });

  if(planTotalsEl){
    const dUnit = (plan.sessions[0] && plan.sessions[0].distance_unit) || plan.volume_unit || '';
    const eUnit = (plan.sessions[0] && plan.sessions[0].elevation_unit) || (dUnit === 'mi' ? 'ft' : 'm');
    planTotalsEl.textContent = `目标合计：${totalDistance.toFixed(1)} ${dUnit} · 爬升 ${Math.round(totalElevation)} ${eUnit} ｜ 已完成：${doneDistance.toFixed(1)} ${dUnit} · 爬升 ${Math.round(doneElevation)} ${eUnit}`;
  }
}

async function showPlan(plan){
  const actuals = await loadActualsForPlan(plan);
  render(plan, actuals);
}

async function generatePlan() {
  try {
    const user_id = uiValue('user_id');
    const forcedNextWeek = nextMondayISO();
    document.getElementById('week_start').value = forcedNextWeek;
    saveFormState();
    setStatus(`正在创建下周计划（${forcedNextWeek}）...`);

    const goalRes = await fetch('/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id,
        goal_type: uiValue('goal_type'),
        target_date: uiValue('target_date'),
        target_time_sec: 3000,
        weekly_days: Number(uiValue('weekly_days')),
        long_run_day: Number(uiValue('long_run_day')),
        race_elevation_gain_m: elevToMeters(uiValue('race_elevation_gain')),
      })
    });
    const goal = await goalRes.json();
    if (!goalRes.ok) return render(goal);

    setStatus('正在生成计划...');
    const planRes = await fetch('/plans/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id,
        goal_id: goal.id,
        week_start: forcedNextWeek,
        auto_derive_inputs: autoInputsOn(),
        base_volume_km: autoInputsOn() ? null : Number(uiValue('base_volume')),
        distance_unit: unit(),
        compliance: autoInputsOn() ? null : Number(uiValue('compliance')),
        fatigue_score: autoInputsOn() ? null : Number(uiValue('fatigue_score')),
      })
    });
    const plan = await planRes.json();
    await showPlan(plan);
  } catch (e) {
    setStatus('生成失败');
    render({ error: String(e) });
  }
}

function loadLastPlanCache() {
  const raw = localStorage.getItem(LAST_PLAN_KEY);
  if (!raw) return;
  try {
    const cached = JSON.parse(raw);
    if (cached && cached.sessions) {
      showPlan(cached);
      setStatus(`已加载缓存 ${nowText()}`);
    }
  } catch (_) {
    // ignore
  }
}

async function getCurrentPlan() {
  try {
    const user_id = uiValue('user_id');
    const scope = uiValue('view_week_scope') || 'next_week';
    const st = scopeText(scope);
    refreshPlanTitle();
    setStatus(`正在刷新${st}计划...`);
    const res = await fetch(`/plans/current?user_id=${encodeURIComponent(user_id)}&distance_unit=${unit()}&week_scope=${encodeURIComponent(scope)}`);
    const data = await res.json();
    if(!res.ok){
      if(String(data.detail||'').includes('no plan')){
        const tip = scope === 'next_week'
          ? '请先点“生成下周计划”或切到“最近一版”。'
          : '请切到其他范围或查看“最近一版”。';
        summaryEl.textContent = `${st}暂无计划，${tip}`;
        sessionsEl.innerHTML = '';
        rawEl.textContent = JSON.stringify(data, null, 2);
        setStatus(`${st}暂无计划`);
        return;
      }
      throw new Error(data.detail || '请求失败');
    }
    await showPlan(data);
  } catch (e) {
    setStatus('刷新失败');
    render({ error: String(e) });
  }
}

window.addEventListener('load', () => {
  initRacePresets();
  loadFormState();
  document.getElementById('distance_unit').value = loadGlobalUnit();
  prevUnit = unit();
  const nextMon = nextMondayISO();
  document.getElementById('week_start').value = nextMon;
  refreshElevLabel();
  bindAutosave();
  document.getElementById('view_week_scope').addEventListener('change', refreshPlanTitle);
  document.getElementById('distance_unit').addEventListener('change', ()=> {
    const input = document.getElementById('race_elevation_gain');
    const raw = Number(input.value);
    if(!Number.isNaN(raw)){
      const meters = prevUnit === 'mi' ? (raw / 3.28084) : raw;
      const next = unit() === 'mi' ? Math.round(meters * 3.28084) : Math.round(meters);
      input.value = String(next);
    }
    prevUnit = unit();
    saveGlobalUnit(unit());
    refreshElevLabel();
  });
  toggleManualInputs();
  loadLastPlanCache();
  refreshPlanTitle();
  getCurrentPlan();
});
</script>
</body>
</html>
"""


def render_simple_ui() -> HTMLResponse:
    return HTMLResponse(content=HTML)

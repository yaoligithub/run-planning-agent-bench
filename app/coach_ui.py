from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>AI Marathon Coach v1.1</title>
  <style>
    :root{--bg:#0b1020;--card:#141b32;--line:#2b365f;--muted:#9fb0db;--text:#e8eeff;--primary:#4f8cff;--ok:#22c55e;--warn:#fb923c;--bad:#ef4444}
    *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif}
    .app{max-width:760px;margin:0 auto;padding:14px}
    .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin-bottom:10px}
    .title{margin:0 0 8px}.muted{color:var(--muted);font-size:12px}
    .grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
    .field label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}
    input,select,textarea,button{width:100%;border-radius:10px;border:1px solid #384777;background:#0f1730;color:#fff;padding:10px;font-size:14px}
    button{background:var(--primary);border:0;font-weight:700}
    .row{display:flex;gap:8px}.chip{display:inline-block;padding:4px 8px;border-radius:999px;border:1px solid #3c4e85;font-size:12px}
    .ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}
    .result{line-height:1.7;font-size:14px}.result ul{margin:6px 0 0 16px;padding:0}
    .mini{background:#334155}
    @media (max-width:640px){.grid{grid-template-columns:1fr}}
  </style>
</head>
<body>
<div class="app">
  <div class="card">
    <h2 class="title">🧠 AI 马拉松教练（简化版）</h2>
    <div class="muted">先填“个人阈值”一次；每天只填下半部分，点一次就给明日建议。</div>
    <div style="margin-top:8px"><button class="mini" onclick="location.href='/?unit=' + encodeURIComponent(distanceUnit())">返回计划页</button></div>
  </div>

  <div class="card">
    <h3 class="title">1) 个人阈值（一次设置）</h3>
    <div class="grid">
      <div class="field"><label>用户名</label><input id="display_name" value="我的跑步账号" /><input id="user_id" type="hidden" value="11111111-1111-1111-1111-111111111111" /></div>
      <div class="field"><label>目标</label><select id="goal"><option value="sub3_marathon" selected>Sub-3 Marathon</option></select></div>
      <div class="field"><label>Easy HR 上限</label><input id="easy_hr_max" type="number" value="145" /></div>
      <div class="field"><label>Threshold HR 上限</label><input id="threshold_hr_max" type="number" value="170" /></div>
      <div class="field"><label>配速显示</label><select id="pace_display_unit"><option value="sec_km">秒/公里 (sec/km)</option><option value="mmss_km">分:秒/公里 (mm:ss/km)</option><option value="mmss_mi">分:秒/英里 (mm:ss/mi)</option></select></div>
      <div class="field"><label>距离单位</label><select id="distance_unit"><option value="mi" selected>miles (mi)</option><option value="km">kilometers (km)</option></select></div>
      <div class="field"><label id="label_easy_pace_min">Easy 配速下限 (sec/km)</label><input id="easy_pace_min" type="text" value="280" /></div>
      <div class="field"><label id="label_easy_pace_max">Easy 配速上限 (sec/km)</label><input id="easy_pace_max" type="text" value="340" /></div>
      <div class="field"><label id="label_threshold_pace">Threshold 配速 (sec/km)</label><input id="threshold_pace" type="text" value="240" /></div>
      <div class="field"><label>质量课步频下限</label><input id="cadence_quality_min" type="number" value="180" /></div>
    </div>
    <div class="row" style="margin-top:8px">
      <button class="mini" onclick="autofillProfileFromStrava()">从 Strava 估算近3个月阈值</button>
      <button onclick="saveProfile()">保存个人阈值</button>
    </div>
  </div>

  <div class="card">
    <h3 class="title">2) 今日输入（每天填）</h3>
    <div class="row" style="margin-bottom:8px">
      <button class="mini" onclick="connectStrava()">连接 Strava</button>
      <button class="mini" onclick="syncStravaNow()">先同步 Strava</button>
      <button class="mini" onclick="autofillFromStrava()">从 Strava 自动填充今天训练</button>
    </div>
    <div class="grid">
      <div class="field"><label>日期</label><input id="checkin_date" value="2026-04-27" /></div>
      <div class="field"><label>打卡时段</label><select id="checkin_phase"><option value="morning">晨起30分钟内</option><option value="post_run" selected>跑后</option></select></div>
      <div class="field"><label>训练类型（实际）</label><select id="actual_session_type"><option>easy</option><option>quality</option><option>long</option><option>recovery</option><option>rest</option></select></div>
      <div class="field"><label id="label_distance">距离 (mi)</label><input id="distance_km" type="number" step="0.1" value="11.2" /></div>
      <div class="field"><label>平均心率</label><input id="avg_hr" type="number" value="152" /></div>
      <div class="field"><label id="label_daily_pace">配速 (sec/km)</label><input id="pace_sec_per_km" type="text" value="295" /></div>
      <div class="field"><label>步频 (spm)</label><input id="cadence_spm" type="number" value="176" /></div>
      <div class="field"><label id="label_elevation">爬升 (ft)</label><input id="elevation_gain_m" type="number" value="0" /></div>
      <div class="field"><label>疲劳 (1-10)</label><input id="fatigue_score" type="number" min="1" max="10" value="6" /></div>
      <div class="field"><label>不适程度 (0-10)</label><input id="soreness_level" type="number" min="0" max="10" value="3" /></div>
      <div class="field"><label>不适部位</label><input id="soreness_area" value="右小腿" /></div>
      <div class="field"><label>原计划类型</label><select id="planned_session_type"><option>easy</option><option>quality</option><option>long</option><option>recovery</option><option>rest</option></select></div>
    </div>
    <div class="field" style="margin-top:8px"><label>睡眠备注</label><textarea id="sleep_note" rows="2">睡眠一般</textarea></div>
    <div style="margin-top:8px"><button onclick="dailyCheckin()">提交并生成“明天建议”</button></div>
  </div>

  <div class="card">
    <h3 class="title">3) AI 输出</h3>
    <div id="result" class="result muted">还没有结果，先点上面的按钮。</div>
    <details style="margin-top:8px"><summary class="muted">查看原始 JSON</summary><pre id="raw" style="white-space:pre-wrap">{}</pre></details>
  </div>

  <div class="card">
    <h3 class="title">4) 和 AI 教练对话（试验）</h3>
    <div id="chat_log" class="result muted" style="max-height:240px;overflow:auto;margin-bottom:8px">你可以问：明天能不能加一点量？</div>
    <div class="row" style="margin-bottom:8px">
      <input id="chat_input" placeholder="例如：我今天感觉不错，明天能否在easy跑上加2km？" />
      <button id="chat_send_btn" style="max-width:120px" onclick="askCoach()">发送</button>
    </div>
    <div class="row" style="margin-bottom:6px">
      <div class="field" style="max-width:220px">
        <label>应用到</label>
        <select id="apply_to"><option value="tomorrow" selected>次日课表</option><option value="today">当天课表</option></select>
      </div>
      <div id="apply_target_hint" class="muted" style="display:flex;align-items:flex-end;padding-bottom:8px"></div>
    </div>
    <div class="row">
      <button id="agent_propose_btn" class="mini" onclick="proposeABPlans()">生成 A/B 方案</button>
      <button id="agent_apply_a_btn" class="mini" onclick="applyOptionA()" disabled>应用方案A</button>
      <button id="agent_apply_b_btn" class="mini" onclick="applyOptionB()" disabled>应用方案B</button>
      <button id="chat_apply_btn" class="mini" onclick="applyChatSuggestion()" disabled>先发消息获取建议</button>
      <button id="chat_reset_btn" class="mini" onclick="resetChatContext()">重置对话上下文</button>
    </div>
    <div class="muted" style="margin-top:6px">说明：先点“生成 A/B 方案”，再应用。应用成功后请到“查看当前计划”刷新确认。</div>
    <div id="ab_preview" class="muted" style="margin-top:6px"></div>
  </div>
</div>
<script>
const KEY='coach_ui_v2';
const GLOBAL_UNIT_KEY = 'running_planner_unit_v1';
const KM_PER_MI = 1.60934;
let currentPaceMode = 'sec_km';
let lastChatSuggestion = null;
let lastABOptions = null;
let chatHistory = [];

function fmtDate(d){
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const day = String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${day}`;
}
function getApplyDate(){
  const raw = v('checkin_date') || todayLocalISO();
  const dt = new Date(raw + 'T00:00:00');
  if((v('apply_to') || 'tomorrow') === 'tomorrow') dt.setDate(dt.getDate()+1);
  return fmtDate(dt);
}
function refreshApplyTargetHint(){
  const el = document.getElementById('apply_target_hint');
  if(!el) return;
  el.textContent = `将修改日期：${getApplyDate()}`;
}
function setABButtonsEnabled(enabled){
  const a = document.getElementById('agent_apply_a_btn');
  const b = document.getElementById('agent_apply_b_btn');
  if(a) a.disabled = !enabled;
  if(b) b.disabled = !enabled;
}

function refreshAgreeApplyBtn(){
  const btn = document.getElementById('chat_apply_btn');
  if(!btn) return;
  const ok = !!(lastChatSuggestion && lastChatSuggestion.suggested_tomorrow_session);
  btn.disabled = !ok;
  btn.textContent = ok ? `应用本条建议到${(v('apply_to')||'tomorrow')==='today'?'当天':'次日'}` : '先发消息获取建议';
}

function v(id){return document.getElementById(id).value.trim()}
function n(id){const x=v(id); return x===''?null:Number(x)}
function todayLocalISO(){
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const day = String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${day}`;
}
function paceMode(){ return v('pace_display_unit') || 'sec_km'; }
function distanceUnit(){ return (v('distance_unit') === 'km') ? 'km' : 'mi'; }
function unitFromUrl(){ const q = new URLSearchParams(window.location.search || ''); const u=q.get('unit'); return (u==='km'||u==='mi')?u:null; }
function loadGlobalUnit(){ const u = unitFromUrl() || localStorage.getItem(GLOBAL_UNIT_KEY); return (u==='km'||u==='mi')?u:'mi'; }
function saveGlobalUnit(u){ localStorage.setItem(GLOBAL_UNIT_KEY, (u==='km'||u==='mi')?u:'mi'); }
function toKmDistance(vNum){ if(vNum===null || vNum===undefined || Number.isNaN(Number(vNum))) return null; const n=Number(vNum); return distanceUnit()==='mi' ? (n*KM_PER_MI) : n; }
function fromKmDistance(kmNum){ if(kmNum===null || kmNum===undefined || Number.isNaN(Number(kmNum))) return null; const n=Number(kmNum); return distanceUnit()==='mi' ? (n/KM_PER_MI) : n; }
function toMetersElev(vNum){ if(vNum===null || vNum===undefined || Number.isNaN(Number(vNum))) return null; const n=Number(vNum); return Math.round(distanceUnit()==='mi' ? (n/3.28084) : n); }
function fromMetersElev(mNum){ if(mNum===null || mNum===undefined || Number.isNaN(Number(mNum))) return null; const n=Number(mNum); return distanceUnit()==='mi' ? Math.round(n*3.28084) : Math.round(n); }
function formatDistanceKm(kmNum){ const v = fromKmDistance(kmNum); if(v===null) return '-'; return `${(Math.round(v*10)/10)} ${distanceUnit()}`; }
function refreshDistanceLabel(){
  const el=document.getElementById('label_distance');
  if(el) el.textContent = `距离 (${distanceUnit()})`;
  const ee=document.getElementById('label_elevation');
  if(ee) ee.textContent = `爬升 (${distanceUnit()==='mi'?'ft':'m'})`;
}
function onDistanceUnitChange(){
  const oldUnit = document.getElementById('distance_unit').dataset.prev || 'mi';
  const newUnit = distanceUnit();
  const input = document.getElementById('distance_km');
  const raw = Number(input.value);
  if(!Number.isNaN(raw) && raw>0){
    const km = (oldUnit==='mi') ? raw*KM_PER_MI : raw;
    const next = (newUnit==='mi') ? km/KM_PER_MI : km;
    input.value = (Math.round(next*10)/10).toString();
  }
  document.getElementById('distance_unit').dataset.prev = newUnit;
  refreshDistanceLabel();
  saveGlobalUnit(newUnit);
}
function paceFieldIds(){ return ['easy_pace_min','easy_pace_max','threshold_pace','pace_sec_per_km']; }

function parsePaceWithMode(raw, mode){
  if(raw === null || raw === undefined) return null;
  const t = String(raw).trim();
  if(!t) return null;

  let sec = null;
  if(t.includes(':')){
    const parts = t.split(':');
    if(parts.length !== 2) return null;
    const mm = Number(parts[0]);
    const ss = Number(parts[1]);
    if(Number.isNaN(mm) || Number.isNaN(ss)) return null;
    sec = mm * 60 + ss;
  } else {
    const x = Number(t);
    if(Number.isNaN(x)) return null;
    sec = x;
  }

  if(mode === 'mmss_mi') return sec / KM_PER_MI;
  return sec;
}

function formatPaceFromSecKm(secKm, mode){
  if(secKm === null || secKm === undefined || Number.isNaN(Number(secKm))) return '';
  const base = Number(secKm);
  if(mode === 'sec_km') return String(Math.round(base));

  let sec = base;
  if(mode === 'mmss_mi') sec = base * KM_PER_MI;
  sec = Math.round(sec);
  const mm = Math.floor(sec / 60);
  const ss = sec % 60;
  return `${mm}:${String(ss).padStart(2,'0')}`;
}

function convertPaceFields(fromMode, toMode){
  paceFieldIds().forEach(id => {
    const oldRaw = v(id);
    const secKm = parsePaceWithMode(oldRaw, fromMode);
    if(secKm === null) return;
    document.getElementById(id).value = formatPaceFromSecKm(secKm, toMode);
  });
}

function updatePaceLabels(){
  const mode = paceMode();
  const suffix = mode === 'mmss_mi' ? 'mm:ss/mi' : (mode === 'mmss_km' ? 'mm:ss/km' : 'sec/km');
  document.getElementById('label_easy_pace_min').textContent = `Easy 配速下限 (${suffix})`;
  document.getElementById('label_easy_pace_max').textContent = `Easy 配速上限 (${suffix})`;
  document.getElementById('label_threshold_pace').textContent = `Threshold 配速 (${suffix})`;
  document.getElementById('label_daily_pace').textContent = `配速 (${suffix})`;
}

function onPaceModeChange(){
  const nextMode = paceMode();
  if(nextMode !== currentPaceMode){
    convertPaceFields(currentPaceMode, nextMode);
    currentPaceMode = nextMode;
  }
  updatePaceLabels();
  save();
}

function paceSecKm(id){ return parsePaceWithMode(v(id), paceMode()); }

function save(){
  const ids=['user_id','display_name','goal','pace_display_unit','distance_unit','easy_hr_max','threshold_hr_max','easy_pace_min','easy_pace_max','threshold_pace','cadence_quality_min','checkin_date','checkin_phase','actual_session_type','distance_km','avg_hr','pace_sec_per_km','cadence_spm','elevation_gain_m','fatigue_score','soreness_level','soreness_area','planned_session_type','sleep_note','apply_to'];
  const s={}; ids.forEach(id=>s[id]=v(id)); localStorage.setItem(KEY, JSON.stringify(s));
}
function load(){
  try{const s=JSON.parse(localStorage.getItem(KEY)||'{}'); Object.keys(s).forEach(id=>{const el=document.getElementById(id); if(el) el.value=s[id];});}catch(_){ }
}
function setRaw(x){document.getElementById('raw').textContent=JSON.stringify(x,null,2)}
function classText(val){ if(['none','low'].includes(val)) return 'ok'; if(['mild','medium'].includes(val)) return 'warn'; return 'bad'; }
function nl2br(s){ return String(s || '').split('\\n').join('<br/>'); }
function nv(v, fallback){ return (v === null || v === undefined) ? fallback : v; }
function renderDecision(data){
  setRaw(data);
  if(!data || data.detail){
    const detail = (data && data.detail) ? data.detail : '未知错误';
    document.getElementById('result').innerHTML = `<span class='bad'>请求失败：</span>${detail}`;
    return;
  }
  const rules = data.rule_checks || {};
  const ruleRows = Object.keys(rules).map(k=>`<li>${rules[k]?'✅':'❌'} ${k}</li>`).join('');
  document.getElementById('result').innerHTML = `
    <div>疲劳状态：<span class='chip ${classText(data.fatigue_status)}'>${data.fatigue_status}</span></div>
    <div>伤病风险：<span class='chip ${classText(data.injury_risk)}'>${data.injury_risk}</span></div>
    <div>明日建议：<b>${data.tomorrow_session}</b></div>
    <div>HR 上限：<b>${nv(data.hr_cap, '-')}</b></div>
    <div>配速建议：${data.pace_hint || '-'}</div>
    <div>步频建议：${data.cadence_hint || '-'}</div>
    <div style='margin-top:6px'><b>教练反馈：</b><br/>${nl2br(data.coach_feedback || '无')}</div>
    <div style='margin-top:6px'>原因：</div>
    <ul>${(data.rationale||[]).map(x=>`<li>${x}</li>`).join('')}</ul>
    <div style='margin-top:6px'>规则检查：</div>
    <ul>${ruleRows}</ul>
  `;
}
function appendChat(role, text){
  const box = document.getElementById('chat_log');
  if(!box){
    document.getElementById('result').innerHTML = `<span class='bad'>聊天区域未找到</span>`;
    return;
  }
  const who = role === 'user' ? '你' : '教练';
  const cls = role === 'user' ? 'muted' : 'ok';
  const line = `<div style='margin:6px 0'><span class='${cls}'><b>${who}：</b></span>${String(text||'').replace(/\\\\n/g,'<br/>')}</div>`;
  if(box.classList.contains('muted') && box.textContent.includes('你可以问')) box.innerHTML = '';
  box.innerHTML += line;
  box.scrollTop = box.scrollHeight;

  const normRole = role === 'assistant' ? 'assistant' : 'user';
  chatHistory.push({ role: normRole, text: String(text || '') });
  if(chatHistory.length > 12) chatHistory = chatHistory.slice(-12);
}

async function askCoach(){
  const q = v('chat_input');
  if(!q) return;
  await syncCheckinFromServer();
  const sendBtn = document.getElementById('chat_send_btn');
  if(sendBtn){ sendBtn.disabled = true; sendBtn.textContent = '思考中...'; }
  appendChat('user', q);
  document.getElementById('chat_input').value = '';
  try {
    const body = {
      user_id: v('user_id'),
      message: q,
      checkin_date: v('checkin_date') || null,
      fatigue_score: n('fatigue_score'),
      soreness_level: n('soreness_level'),
      soreness_area: v('soreness_area') || null,
      sleep_note: v('sleep_note') || null,
      distance_km: toKmDistance(n('distance_km')),
      avg_hr: n('avg_hr'),
      elevation_gain_m: toMetersElev(n('elevation_gain_m')),
      actual_session_type: v('actual_session_type') || null,
      conversation_history: chatHistory.slice(-8)
    };
    const r = await fetch('/coach/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    const data = await r.json();
    setRaw(data);
    if(!r.ok){
      appendChat('assistant', `请求失败：${data.detail || '未知错误'}`);
      return;
    }
    const isTodayQuestion = q.includes('今天') && !q.includes('明天');
    let tail = '';
    if(!isTodayQuestion && data.suggested_tomorrow_session) tail += `\n建议课表：${data.suggested_tomorrow_session}`;
    if(!isTodayQuestion && data.suggested_delta_km != null) tail += `\n建议增减量：${data.suggested_delta_km > 0 ? '+' : ''}${data.suggested_delta_km} km`;
    if(data.caution) tail += `\n注意：${data.caution}`;
    appendChat('assistant', `${data.reply || '已收到。'}${tail}`);
    lastChatSuggestion = {
      suggested_tomorrow_session: data.suggested_tomorrow_session,
      suggested_delta_km: data.suggested_delta_km
    };
    refreshAgreeApplyBtn();
  } catch(e){
    appendChat('assistant', `异常：${String(e)}`);
  } finally {
    if(sendBtn){ sendBtn.disabled = false; sendBtn.textContent = '发送'; }
  }
}
async function proposeABPlans(){
  setABButtonsEnabled(false);
  const preview = document.getElementById('ab_preview');
  if(preview) preview.textContent = '正在生成 A/B 方案...';
  try {
    const body = {
      user_id: v('user_id'),
      message: 'propose',
      checkin_date: v('checkin_date') || null,
      apply_to: v('apply_to') || 'tomorrow',
      fatigue_score: n('fatigue_score'),
      soreness_level: n('soreness_level')
    };
    const r = await fetch('/coach/agent/propose', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    const data = await r.json();
    setRaw(data);
    if(!r.ok){ appendChat('assistant', `生成方案失败：${data.detail || '未知错误'}`); if(preview) preview.textContent=''; return; }
    lastABOptions = data.options || [];
     const a = lastABOptions.find(x=>x.code==='A');
     const b = lastABOptions.find(x=>x.code==='B');
    setABButtonsEnabled(!!a && !!b);
    if(preview) preview.innerHTML = `A：${a?.tomorrow_session||'-'} ${formatDistanceKm(a?.distance_km)}（风险${a?.risk||'-'}）<br/>B：${b?.tomorrow_session||'-'} ${formatDistanceKm(b?.distance_km)}（风险${b?.risk||'-'}）`;
    appendChat('assistant', `A(${a?.label||'-'}): ${a?.tomorrow_session||'-'} ${formatDistanceKm(a?.distance_km)} 风险${a?.risk||'-'}\nB(${b?.label||'-'}): ${b?.tomorrow_session||'-'} ${formatDistanceKm(b?.distance_km)} 风险${b?.risk||'-'}`);
  } catch(e){ appendChat('assistant', `生成方案异常：${String(e)}`); }
}

async function applyOptionA(){
  try {
    const r = await fetch('/coach/agent/apply', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ user_id: v('user_id'), checkin_date: v('checkin_date') || null, apply_to: v('apply_to') || 'tomorrow', option_code: 'A' })
    });
    const data = await r.json();
    setRaw(data);
    if(!r.ok){ appendChat('assistant', `应用方案A失败：${data.detail || '未知错误'}`); return; }
    appendChat('assistant', `方案A已应用到 ${data.date}：${data.from_session_type || '-'} -> ${data.to_session_type}，${formatDistanceKm(data.from_distance_km)} -> ${formatDistanceKm(data.to_distance_km)}`);
  } catch(e){ appendChat('assistant', `应用方案A异常：${String(e)}`); }
}

async function applyOptionB(){
  try {
    const r = await fetch('/coach/agent/apply', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ user_id: v('user_id'), checkin_date: v('checkin_date') || null, apply_to: v('apply_to') || 'tomorrow', option_code: 'B' })
    });
    const data = await r.json();
    setRaw(data);
    if(!r.ok){ appendChat('assistant', `应用方案B失败：${data.detail || '未知错误'}`); return; }
    appendChat('assistant', `方案B已应用到 ${data.date}：${data.from_session_type || '-'} -> ${data.to_session_type}，${formatDistanceKm(data.from_distance_km)} -> ${formatDistanceKm(data.to_distance_km)}`);
  } catch(e){ appendChat('assistant', `应用方案B异常：${String(e)}`); }
}

function resetChatContext(){
  chatHistory = [];
  lastChatSuggestion = null;
  refreshAgreeApplyBtn();
  const box = document.getElementById('chat_log');
  if(box){
    box.innerHTML = '你可以问：明天能不能加一点量？';
    box.scrollTop = box.scrollHeight;
  }
  appendChat('assistant', '已重置对话上下文。接下来我会按你最新输入重新判断。');
}

async function applyChatSuggestion(){
  if(!lastChatSuggestion || !lastChatSuggestion.suggested_tomorrow_session){
    appendChat('assistant', '还没有可应用的建议。先问一句并拿到建议课表后再点。');
    return;
  }
  try {
    const body = {
      user_id: v('user_id'),
      checkin_date: v('checkin_date') || null,
      apply_to: v('apply_to') || 'tomorrow',
      suggested_tomorrow_session: lastChatSuggestion.suggested_tomorrow_session,
      suggested_delta_km: lastChatSuggestion.suggested_delta_km
    };
    const r = await fetch('/coach/chat/apply', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
    const data = await r.json();
    setRaw(data);
    if(!r.ok){
      appendChat('assistant', `应用失败：${data.detail || '未知错误'}`);
      return;
    }
    appendChat('assistant', `已应用到 ${data.date}：${data.from_session_type || '-'} -> ${data.to_session_type}，距离 ${formatDistanceKm(data.from_distance_km)} -> ${formatDistanceKm(data.to_distance_km)}`);
  } catch(e){
    appendChat('assistant', `应用异常：${String(e)}`);
  } finally {
    refreshAgreeApplyBtn();
  }
}

async function autofillProfileFromStrava(){
  try {
    save();
    const userId = encodeURIComponent(v('user_id'));
    const r = await fetch(`/coach/profile/autofill?user_id=${userId}&days=90`, { method: 'POST' });
    const data = await r.json();
    setRaw(data);
    if(!r.ok){
      document.getElementById('result').innerHTML = `<span class='bad'>自动估算失败：</span>${data.detail || '请先同步Strava'}`;
      return;
    }
    const p = data.profile || {};
    if(p.easy_hr_max != null) document.getElementById('easy_hr_max').value = p.easy_hr_max;
    if(p.threshold_hr_max != null) document.getElementById('threshold_hr_max').value = p.threshold_hr_max;
    if(p.easy_pace_min != null) document.getElementById('easy_pace_min').value = formatPaceFromSecKm(p.easy_pace_min, paceMode());
    if(p.easy_pace_max != null) document.getElementById('easy_pace_max').value = formatPaceFromSecKm(p.easy_pace_max, paceMode());
    if(p.threshold_pace != null) document.getElementById('threshold_pace').value = formatPaceFromSecKm(p.threshold_pace, paceMode());
    if(p.cadence_quality_min != null) document.getElementById('cadence_quality_min').value = p.cadence_quality_min;
    save();
    document.getElementById('result').innerHTML = `<span class='ok'>已自动估算并写入阈值：</span>使用 ${data.runs_used || 0} 条近3个月记录。你可再微调后保存。`;
  } catch(e){
    document.getElementById('result').innerHTML = `<span class='bad'>自动估算异常：</span>${String(e)}`;
  }
}

async function saveProfile(){
  save();
  const body={
    user_id:v('user_id'),goal:v('goal'),
    easy_hr_max:n('easy_hr_max'),threshold_hr_max:n('threshold_hr_max'),
    easy_pace_min:paceSecKm('easy_pace_min'),easy_pace_max:paceSecKm('easy_pace_max'),
    threshold_pace:paceSecKm('threshold_pace'),cadence_quality_min:n('cadence_quality_min')
  };
  const r=await fetch('/coach/profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await r.json();
  if(data.detail){ renderDecision(data); return; }
  renderDecision({fatigue_status:'low',injury_risk:'none',tomorrow_session:'easy',hr_cap:body.easy_hr_max,pace_hint:'参数已保存',cadence_hint:'明天可直接打卡',rationale:['个人阈值已保存'],rule_checks:{saved_profile:true}})
}
function connectStrava(){
  save();
  const userId = encodeURIComponent(v('user_id'));
  const jump = `/auth/strava/connect/start?user_id=${userId}`;
  document.getElementById('result').innerHTML = `<span class='ok'>正在打开 Strava 授权页...</span><br/><a href='${jump}' style='color:#93c5fd'>若未自动跳转，点这里继续</a>`;
  window.location.href = jump;
}

async function syncStravaNow(){
  try {
    const userId = encodeURIComponent(v('user_id'));
    const r = await fetch(`/auth/strava/sync?user_id=${userId}`, { method: 'POST' });
    const data = await r.json();
    setRaw(data);
    if(!r.ok){
      const detail = data.detail || '请先完成Strava授权';
      if(String(detail).includes('not connected')){
        document.getElementById('result').innerHTML = `<span class='bad'>还没绑定 Strava：</span>请先点“连接 Strava”完成授权。`;
      } else {
        document.getElementById('result').innerHTML = `<span class='bad'>Strava 同步失败：</span>${detail}`;
      }
      return;
    }
    document.getElementById('result').innerHTML = `<span class='ok'>同步完成：</span>新增 ${nv(data.created, 0)}，更新 ${nv(data.updated, 0)}。现在可以点“自动填充”。`;
  } catch(e){
    document.getElementById('result').innerHTML = `<span class='bad'>同步异常：</span>${String(e)}`;
  }
}

async function autofillFromStrava(){
  try {
    save();
    const tz = encodeURIComponent(Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai');
    const url = `/coach/autofill-today?user_id=${encodeURIComponent(v('user_id'))}&checkin_date=${encodeURIComponent(v('checkin_date'))}&tz=${tz}&allow_nearest=false`;
    const r = await fetch(url);
    const data = await r.json();
    setRaw(data);
    if(!r.ok){
      document.getElementById('result').innerHTML = `<span class='bad'>Strava 自动填充失败：</span>${data.detail || '请先完成Strava同步'}。可先点“先同步 Strava”。`;
      return;
    }
    document.getElementById('checkin_phase').value = 'post_run';
    if(data.distance_km!=null) document.getElementById('distance_km').value = (Math.round(fromKmDistance(data.distance_km)*10)/10);
    if(data.avg_hr!=null) document.getElementById('avg_hr').value = data.avg_hr;
    if(data.pace_sec_per_km!=null) document.getElementById('pace_sec_per_km').value = formatPaceFromSecKm(data.pace_sec_per_km, paceMode());
    document.getElementById('cadence_spm').value = (data.cadence_spm!=null ? data.cadence_spm : '');
    document.getElementById('elevation_gain_m').value = (data.elevation_gain_m!=null ? fromMetersElev(data.elevation_gain_m) : '');
    if(data.actual_session_type) document.getElementById('actual_session_type').value = data.actual_session_type;
    if(data.planned_session_type) document.getElementById('planned_session_type').value = data.planned_session_type;
    const cadenceHint = data.cadence_spm==null ? '（本次Strava未返回步频）' : '';
    document.getElementById('result').innerHTML = `<span class='ok'>已自动填充：</span>${data.summary || '已从Strava读取今天训练'}${cadenceHint}。你只需要补主观疲劳/不适/睡眠。`;
    save();
  } catch(e){
    document.getElementById('result').innerHTML = `<span class='bad'>自动填充异常：</span>${String(e)}`;
  }
}
function clearRunMetrics(){
  ['distance_km','avg_hr','pace_sec_per_km','cadence_spm','elevation_gain_m'].forEach(id=>{ const el=document.getElementById(id); if(el) el.value=''; });
  const t = document.getElementById('actual_session_type');
  if(t) t.value = 'rest';
}

async function syncCheckinFromServer(){
  try {
    const user = v('user_id');
    const d = v('checkin_date');
    if(!user || !d) return;
    const r = await fetch(`/coach/checkin-snapshot?user_id=${encodeURIComponent(user)}&checkin_date=${encodeURIComponent(d)}`);
    const data = await r.json();
    if(!r.ok || !data.ok){
      return;
    }

    if(!data.exists){
      if(v('checkin_phase') === 'morning') clearRunMetrics();
      save();
      return;
    }

    if(data.checkin_phase) document.getElementById('checkin_phase').value = data.checkin_phase;
    if(data.fatigue_score != null) document.getElementById('fatigue_score').value = data.fatigue_score;
    if(data.soreness_level != null) document.getElementById('soreness_level').value = data.soreness_level;
    if(data.soreness_area != null) document.getElementById('soreness_area').value = data.soreness_area;
    if(data.sleep_note != null) document.getElementById('sleep_note').value = data.sleep_note;

    if(data.checkin_phase === 'morning'){
      clearRunMetrics();
    } else {
      document.getElementById('distance_km').value = (data.distance_km != null ? (Math.round(fromKmDistance(data.distance_km)*10)/10) : '');
      document.getElementById('avg_hr').value = (data.avg_hr != null ? data.avg_hr : '');
      document.getElementById('elevation_gain_m').value = (data.elevation_gain_m != null ? fromMetersElev(data.elevation_gain_m) : '');
      if(data.actual_session_type) document.getElementById('actual_session_type').value = data.actual_session_type;
    }

    if(data.planned_session_type) document.getElementById('planned_session_type').value = data.planned_session_type;
    save();
  } catch(e){
    // silent: keep UX smooth
  }
}

async function dailyCheckin(){
  save();
  const body={
    user_id:v('user_id'),checkin_date:v('checkin_date'),checkin_phase:v('checkin_phase')||'post_run',distance_km:toKmDistance(n('distance_km')),pace_sec_per_km:paceSecKm('pace_sec_per_km'),avg_hr:n('avg_hr'),cadence_spm:n('cadence_spm'),elevation_gain_m:toMetersElev(n('elevation_gain_m')),fatigue_score:Number(v('fatigue_score')),soreness_area:v('soreness_area')||null,soreness_level:Number(v('soreness_level')),sleep_note:v('sleep_note')||null,planned_session_type:v('planned_session_type')||null,actual_session_type:v('actual_session_type')||null
  };
  const r=await fetch('/coach/daily-checkin',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  renderDecision(await r.json());
}
window.addEventListener('load',()=>{
  load();
  document.getElementById('distance_unit').value = loadGlobalUnit();
  document.getElementById('distance_unit').dataset.prev = distanceUnit();
  refreshDistanceLabel();
  const dateEl = document.getElementById('checkin_date');
  if(dateEl && (!dateEl.value || dateEl.value === '2026-04-27')){
    dateEl.value = todayLocalISO();
  }
  currentPaceMode = paceMode();
  updatePaceLabels();
  document.getElementById('pace_display_unit').addEventListener('change', onPaceModeChange);
  document.getElementById('distance_unit').addEventListener('change', ()=>{ onDistanceUnitChange(); save(); });
  document.querySelectorAll('input,select,textarea').forEach(el=>el.addEventListener('change',save));
  document.getElementById('checkin_date').addEventListener('change', ()=>{ save(); syncCheckinFromServer(); refreshApplyTargetHint(); setABButtonsEnabled(false); });
  document.getElementById('apply_to').addEventListener('change', ()=>{ save(); refreshApplyTargetHint(); refreshAgreeApplyBtn(); setABButtonsEnabled(false); });
  document.getElementById('user_id').addEventListener('change', ()=>{ save(); syncCheckinFromServer(); setABButtonsEnabled(false); });
  document.getElementById('checkin_phase').addEventListener('change', ()=>{
    if(v('checkin_phase') === 'morning') clearRunMetrics();
    save();
  });

  const chatInput = document.getElementById('chat_input');
  if(chatInput){
    chatInput.addEventListener('keydown', (e)=>{
      if(e.key === 'Enter'){
        e.preventDefault();
        askCoach();
      }
    });
  }
  refreshAgreeApplyBtn();
  refreshApplyTargetHint();
  setABButtonsEnabled(false);
  syncCheckinFromServer();
});
</script>
</body>
</html>
"""


def render_coach_ui() -> HTMLResponse:
    return HTMLResponse(content=HTML)

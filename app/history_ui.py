from fastapi.responses import HTMLResponse


HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#0b1020" />
  <title>历史智能分析</title>
  <style>
    :root { --bg:#0b1020; --card:#141b32; --muted:#9fb0db; --text:#e8eeff; --line:#2b365f; --green:#22c55e; --orange:#fb923c; --red:#ef4444; }
    *{box-sizing:border-box}
    body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text',sans-serif;background:radial-gradient(1200px 600px at 20% -10%, #1d2d62 0%, var(--bg) 50%);color:var(--text);overflow-x:hidden}
    .app{max-width:760px;margin:0 auto;padding:14px}
    .hero{background:linear-gradient(135deg,#2952c6,#6d7bff);border-radius:18px;padding:16px;margin-bottom:12px}
    .hero h1{margin:0;font-size:22px}.hero p{margin:6px 0 0;color:#e7edff;font-size:13px}
    .hero-actions{display:flex;gap:8px;margin-top:10px}
    .mini-btn{border:1px solid rgba(255,255,255,.35);background:rgba(13,22,46,.25);color:#fff;border-radius:999px;padding:7px 12px;font-size:12px;font-weight:700}
    .card{background:#141b32;border:1px solid var(--line);border-radius:14px;padding:12px;margin-bottom:10px;overflow:hidden}
    .title{margin:0 0 10px;font-size:16px}
    .grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
    .field label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}
    .field input,.field select{width:100%;border-radius:10px;border:1px solid #384777;background:#0f1730;color:#fff;padding:10px;font-size:14px}
    .chips{display:flex;gap:8px;flex-wrap:wrap}.chip{font-size:12px;border-radius:999px;padding:6px 10px;border:1px solid #3c4e85;color:#dfe7ff;background:#121a34;max-width:100%;word-break:break-word}
    .status,.activity-sub{color:var(--muted);font-size:12px}
    .bars{margin-top:10px;display:flex;flex-direction:column;gap:6px}
    .bar-row{display:grid;grid-template-columns:80px 1fr 80px;gap:8px;align-items:center}
    .bar-track{height:8px;border-radius:999px;background:#1b274b;overflow:hidden}
    .bar-fill{height:100%;background:linear-gradient(90deg,#3b82f6,#22c55e)}
    .activity-list{display:flex;flex-direction:column;gap:8px;margin-top:10px}
    .activity-item{border:1px solid #33467e;border-radius:12px;background:#101830;padding:10px;display:flex;justify-content:space-between;gap:10px}
    .activity-main{font-size:13px}
    .cal-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}
    .cal-btn{border:1px solid #3c4e85;background:#101830;color:#fff;border-radius:8px;padding:6px 10px;font-size:12px}
    .weekdays,.month-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}
    .trend-card{margin-top:10px;border:1px solid #33467e;border-radius:12px;background:#101830;padding:10px}
    .trend-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px}
    .trend-tabs{display:flex;gap:8px}
    .trend-tab{border:1px solid #3c4e85;background:#0f1730;color:#dfe7ff;border-radius:999px;padding:4px 10px;font-size:12px;cursor:pointer}
    .trend-tab.active{background:#1f3b7a;color:#fff}
    .trend-svg{width:100%;height:170px;display:block}
    .weekdays div{text-align:center;color:var(--muted);font-size:11px}
    .day{min-height:74px;width:100%;min-width:0;border:1px solid #2f3c69;border-radius:10px;background:#101830;padding:6px;font-size:12px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden}
    .day .n{font-weight:700}.day .m{font-size:10px;color:var(--muted);line-height:1.25;word-break:break-word}
    .day.muted{opacity:.35}.day.selected{outline:2px solid #7ea7ff}.has-run .n::after{content:'•';color:var(--green);margin-left:4px}
    .risk-mild{border-color:var(--orange)}.risk-high{border-color:var(--red)}
    @media (max-width:640px){.grid{grid-template-columns:1fr}}
  </style>
</head>
<body>
<div class="app">
  <section class="hero">
    <h1>📈 历史智能分析</h1>
    <p>查看最近训练趋势、负荷和关键统计（含每日反馈日历）</p>
    <div class="hero-actions">
      <button class="mini-btn" onclick="goHome()">返回计划页</button>
      <button class="mini-btn" onclick="refreshAll()">刷新分析</button>
    </div>
  </section>

  <section class="card">
    <h2 class="title">筛选</h2>
    <div class="grid">
      <div class="field"><label>用户名</label><input id="display_name" value="我的跑步账号" /><input id="user_id" type="hidden" value="11111111-1111-1111-1111-111111111111" /></div>
      <div class="field"><label>周数</label><select id="weeks"><option value="4" selected>最近4周</option><option value="8">最近8周</option><option value="12">最近12周</option></select></div>
      <div class="field"><label>单位</label><select id="unit"><option value="mi" selected>miles</option><option value="km">kilometers</option></select></div>
    </div>
    <div class="status" id="status">状态：等待加载</div>
  </section>

  <section class="card"><h2 class="title">总览</h2><div class="chips" id="summary"></div><div id="insights"></div></section>

  <section class="card">
    <h2 class="title">训练反馈月历</h2>
    <div class="cal-head">
      <button class="cal-btn" onclick="shiftMonth(-1)">← 上月</button>
      <div id="calTitle">-</div>
      <button class="cal-btn" onclick="shiftMonth(1)">下月 →</button>
    </div>
    <div class="weekdays"><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div><div>Sun</div></div>
    <div class="month-grid" id="monthGrid"></div>
    <div style="margin-top:10px" class="activity-sub">说明：A=实际跑量，P=计划；绿点=有跑步；橙/红边框=轻微/高风险；*=已自动改课。</div>
  </section>

  <section class="card">
    <h2 class="title">选中日期详情</h2>
    <div id="dayDetail">点击上方某一天查看反馈与建议</div>
    <div class="grid" style="margin-top:10px">
      <div class="field"><label>打卡时段</label><select id="fbPhase"><option value="morning">晨起30分钟内</option><option value="post_run">跑后</option></select></div>
      <div class="field"><label>疲劳(1-10)</label><select id="fbFatigue"></select></div>
      <div class="field"><label>酸痛(0-10)</label><select id="fbSoreness"></select></div>
      <div class="field"><label>酸痛部位</label><input id="fbArea" placeholder="如：右小腿" /></div>
      <div class="field"><label>睡眠备注</label><input id="fbSleep" placeholder="如：睡眠一般" /></div>
    </div>
    <div style="margin-top:8px; display:flex; gap:8px; align-items:center;">
      <button class="mini-btn" onclick="saveDayFeedback()">保存当日体感</button>
      <div id="fbStatus" class="activity-sub"></div>
    </div>
  </section>

  <section class="card"><h2 class="title">按天跑量</h2><div class="bars" id="bars"></div></section>
  <section class="card">
    <h2 class="title">过去三个月趋势</h2>
    <div class="trend-card">
      <div class="trend-head">
        <div class="activity-sub">按周汇总（近12周）</div>
        <div class="trend-tabs">
          <button id="trend_dist_btn" class="trend-tab active" onclick="setTrendMetric('distance')">跑量</button>
          <button id="trend_elev_btn" class="trend-tab" onclick="setTrendMetric('elevation')">爬升</button>
        </div>
      </div>
      <svg id="trendSvg" class="trend-svg" viewBox="0 0 700 170" preserveAspectRatio="none"></svg>
    </div>
  </section>
  <section class="card"><h2 class="title">最近活动</h2><div class="activity-list" id="list"></div></section>
</div>

<script>
var summaryEl = document.getElementById('summary');
var insightsEl = document.getElementById('insights');
var barsEl = document.getElementById('bars');
var listEl = document.getElementById('list');
var statusEl = document.getElementById('status');
var monthGridEl = document.getElementById('monthGrid');
var calTitleEl = document.getElementById('calTitle');
var dayDetailEl = document.getElementById('dayDetail');
var trendMetric = 'distance';
var lastActivities = [];
var lastUnit = 'mi';

const GLOBAL_UNIT_KEY = 'running_planner_unit_v1';
var calendarMap = {};
var selectedDate = null;
var currentMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
var inited = false;

function v(id){ var el=document.getElementById(id); return el ? (el.value||'').trim() : ''; }
function unitFromUrl(){ var q=new URLSearchParams(window.location.search||''); var u=q.get('unit'); return (u==='km'||u==='mi')?u:null; }
function loadGlobalUnit(){ var u=unitFromUrl() || localStorage.getItem(GLOBAL_UNIT_KEY); return (u==='km'||u==='mi')?u:'mi'; }
function saveGlobalUnit(u){ localStorage.setItem(GLOBAL_UNIT_KEY, (u==='km'||u==='mi')?u:'mi'); }
function goHome(){ window.location.href='/?unit='+encodeURIComponent(v('unit')||'mi'); }
function displayUnit(){ return (v('unit')==='km') ? 'km' : 'mi'; }
function fromKm(km){ if(km===null||km===undefined||km==='') return null; var n=Number(km); if(Number.isNaN(n)) return null; return displayUnit()==='mi' ? (n/1.60934) : n; }
function fmtDist(km, digits){ var v=fromKm(km); if(v===null) return '-'; var d=(digits===undefined?1:digits); return v.toFixed(d) + ' ' + displayUnit(); }
function fmtShort(km){ var v=fromKm(km); if(v===null) return '0'+displayUnit(); return (Math.round(v*10)/10) + displayUnit(); }
function fmtElev(m){ var n=Number(m||0); if(displayUnit()==='mi') return Math.round(n*3.28084)+'ft'; return Math.round(n)+'m'; }
function nv(v,f){ return (v===null || v===undefined) ? f : v; }
function setStatus(s){ statusEl.textContent = '状态：' + s; }
function nl2br(s){ return String(s||'').split('\\n').join('<br/>'); }
function two(n){ n=String(n); return n.length<2 ? ('0'+n) : n; }
function isoDate(dt){ return dt.toISOString().slice(0,10); }
function fmtDate(v){ var d=new Date(v||''); return d.toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric'}); }

function getJSON(url, ok, err){
  var xhr=new XMLHttpRequest();
  xhr.open('GET', url, true);
  xhr.onreadystatechange=function(){
    if(xhr.readyState!==4) return;
    var obj={};
    try{ obj=JSON.parse(xhr.responseText||'{}'); }catch(e){ err({detail:'json parse'}); return; }
    if(xhr.status>=200 && xhr.status<300) ok(obj); else err(obj);
  };
  xhr.onerror=function(){ err({detail:'network'}); };
  xhr.send();
}

function startOfWeekMonday(dt){ var d=new Date(dt); var w=(d.getDay()+6)%7; d.setDate(d.getDate()-w); d.setHours(0,0,0,0); return d; }
function setTrendMetric(metric){
  trendMetric = metric === 'elevation' ? 'elevation' : 'distance';
  var db=document.getElementById('trend_dist_btn'); var eb=document.getElementById('trend_elev_btn');
  if(db) db.classList.toggle('active', trendMetric==='distance');
  if(eb) eb.classList.toggle('active', trendMetric==='elevation');
  renderTrend();
}
function setTrendActivities(acts, unit){
  lastActivities = acts || [];
  if(unit) lastUnit = unit;
  renderTrend();
}
function renderTrend(){
  var svg=document.getElementById('trendSvg'); if(!svg) return;
  var weeks={};
  for(var i=0;i<lastActivities.length;i++){
    var a=lastActivities[i];
    var dt=new Date(a.started_at_local || a.started_at);
    var wk=startOfWeekMonday(dt);
    var key=wk.toISOString().slice(0,10);
    if(!weeks[key]) weeks[key]={k:key, distance:0, elevation:0};
    weeks[key].distance += Number(a.distance||0);
    weeks[key].elevation += Number(a.elevation_gain||0);
  }

  // Build continuous 12-week window ending this week, so missing weeks are shown as 0.
  var nowWk=startOfWeekMonday(new Date());
  var keys=[];
  for(var w=11; w>=0; w--){
    var d=new Date(nowWk); d.setDate(d.getDate()-7*w);
    keys.push(d.toISOString().slice(0,10));
    if(!weeks[keys[keys.length-1]]) weeks[keys[keys.length-1]]={k:keys[keys.length-1], distance:0, elevation:0};
  }

  var vals = keys.map(k=>trendMetric==='distance'?weeks[k].distance:weeks[k].elevation);
  var max=Math.max.apply(null, vals); if(max<=0) max=1;
  var yMax = Math.ceil(max / 4) * 4;
  if(trendMetric==='elevation') yMax = Math.ceil(max / 200) * 200;
  if(yMax<=0) yMax = max;

  var left=40, right=680, top=20, bottom=150;
  var pts=[], circles=[], xLabels=[];
  for(var j=0;j<vals.length;j++){
    var x=left + ((right-left)*(j/(Math.max(1,vals.length-1))));
    var y=bottom - ((bottom-top)*(vals[j]/yMax));
    pts.push(x.toFixed(1)+','+y.toFixed(1));
    circles.push(`<circle cx='${x.toFixed(1)}' cy='${y.toFixed(1)}' r='3.5' fill='#93c5fd' stroke='#1e3a8a' stroke-width='1'/>`);
    if(j%4===0 || j===vals.length-1){
      var mm = keys[j].slice(5,7);
      xLabels.push(`<text x='${x.toFixed(1)}' y='166' fill='#9fb0db' font-size='11' text-anchor='middle'>${mm}</text>`);
    }
  }
  var fill=pts.slice(); fill.push(right+','+bottom); fill.push(left+','+bottom);
  var unitTxt = trendMetric==='distance' ? lastUnit : (lastUnit==='mi' ? 'ft' : 'm');

  var yTicks='';
  for(var t=0;t<=4;t++){
    var y=bottom - ((bottom-top)*(t/4));
    var v=(yMax*(t/4));
    yTicks += `<line x1='${left}' y1='${y.toFixed(1)}' x2='${right}' y2='${y.toFixed(1)}' stroke='#24345f' stroke-width='1'/>`;
    yTicks += `<text x='${(right+8)}' y='${(y+4).toFixed(1)}' fill='#9fb0db' font-size='11'>${v.toFixed(0)}</text>`;
  }

  svg.innerHTML = `${yTicks}<line x1='${left}' y1='${bottom}' x2='${right}' y2='${bottom}' stroke='#33467e' stroke-width='1'/><polyline points='${fill.join(' ')}' fill='rgba(59,130,246,0.18)' stroke='none'/><polyline points='${pts.join(' ')}' fill='none' stroke='#60a5fa' stroke-width='3'/>${circles.join('')}${xLabels.join('')}<text x='${right}' y='12' fill='#9fb0db' font-size='12' text-anchor='end'>${trendMetric==='distance'?'跑量':'爬升'}（${unitTxt}）</text>`;
}

function renderSummary(data){
  summaryEl.innerHTML=''; insightsEl.innerHTML=''; barsEl.innerHTML=''; listEl.innerHTML='';
  if(!data || !data.ok){ setStatus('加载失败'); return; }
  setStatus('已刷新 (' + data.timezone + ')');

  var s=data.summary||{};
  var elevUnit = s.elevation_unit || (data.unit==='mi' ? 'ft' : 'm');
  var chips=['Runs: '+nv(s.runs,0),'Total: '+nv(s.total_distance,0)+' '+data.unit,'Avg/Week: '+nv(s.avg_weekly_distance,0)+' '+data.unit,'Elev: '+nv(s.total_elevation_gain,0)+' '+elevUnit,'Weeks: '+data.weeks];
  for(var i=0;i<chips.length;i++){ var c=document.createElement('span'); c.className='chip'; c.textContent=chips[i]; summaryEl.appendChild(c); }

  var acts=data.activities||[]; lastUnit=data.unit||'mi'; var longest=null; var totalMin=0; var hr=[];
  for(var j=0;j<acts.length;j++){ if(!longest || acts[j].distance>(longest.distance||0)) longest=acts[j]; totalMin+=(acts[j].duration_min||0); if(acts[j].avg_hr) hr.push(acts[j].avg_hr); }
  var avgHr='-'; if(hr.length){ var sum=0; for(var h=0;h<hr.length;h++) sum+=hr[h]; avgHr=Math.round(sum/hr.length); }
  insightsEl.innerHTML='<div>• 最长单次：'+(longest?longest.distance:0)+' '+data.unit+'（'+(longest?longest.date:'-')+'）</div><div>• 平均心率：'+avgHr+'</div><div>• 总爬升：'+nv(s.total_elevation_gain,0)+' '+elevUnit+'</div><div>• 总训练时长：'+Math.round(totalMin)+' 分钟</div>';

  var daily=data.daily||[]; var max=1; for(var d=0;d<daily.length;d++){ if((daily[d].distance||0)>max) max=daily[d].distance; }
  for(var q=0;q<Math.min(14,daily.length);q++){
    var it=daily[q]; var w=Math.round(((it.distance||0)/max)*100); var row=document.createElement('div'); row.className='bar-row';
    row.innerHTML='<div class="activity-sub">'+it.date.slice(5)+'</div><div class="bar-track"><div class="bar-fill" style="width:'+w+'%"></div></div><div class="activity-sub">'+it.distance+' '+data.unit+'</div>';
    barsEl.appendChild(row);
  }

  for(var a=0;a<Math.min(20,acts.length);a++){
    var x=acts[a]; var item=document.createElement('div'); item.className='activity-item';
    item.innerHTML='<div><div class="activity-main">'+fmtDate(x.started_at_local)+' · '+x.type+'</div><div class="activity-sub">'+x.duration_min+' min · HR '+(x.avg_hr||'-')+' · Cad '+(x.cadence_spm||'-')+' · Elev '+(x.elevation_gain||0)+' '+elevUnit+'</div></div><div class="activity-main">'+x.distance+' '+data.unit+'</div>';
    listEl.appendChild(item);
  }
}

function initSelectors(){
  var f=document.getElementById('fbFatigue'); var s=document.getElementById('fbSoreness');
  f.innerHTML=''; s.innerHTML='';
  for(var i=1;i<=10;i++){ var o=document.createElement('option'); o.value=String(i); o.textContent=String(i); f.appendChild(o); }
  for(var j=0;j<=10;j++){ var p=document.createElement('option'); p.value=String(j); p.textContent=String(j); s.appendChild(p); }
}

function renderDayDetail(dateStr){
  var it=calendarMap[dateStr];
  if(!it){
    dayDetailEl.innerHTML='日期 '+dateStr+'：无记录';
    document.getElementById('fbPhase').value='morning'; document.getElementById('fbFatigue').value='5'; document.getElementById('fbSoreness').value='0'; document.getElementById('fbArea').value=''; document.getElementById('fbSleep').value='';
    return;
  }
  var plans=it.planned_sessions||[]; var parts=[];
  for(var i=0;i<plans.length;i++){
    var p=plans[i];
    var pe=(p && p.target_elevation_gain_m!=null) ? (' ↑'+fmtElev(p.target_elevation_gain_m)) : '';
    parts.push(p.session_type + (p.target_distance_km?(' '+fmtShort(p.target_distance_km)):'') + pe + (p.adapted?' (adapted)':''));
  }
  var plannedTxt=parts.join(' / '); var plannedTotal=(it.planned_total_km!==null && it.planned_total_km!==undefined)?fmtShort(it.planned_total_km):'-';
  var rationale='<li>无</li>'; if(it.decision_rationale){ var arr=String(it.decision_rationale).split(' | '); rationale=''; for(var r=0;r<arr.length;r++) rationale+='<li>'+arr[r]+'</li>'; }

  dayDetailEl.innerHTML='<div><b>'+dateStr+'</b> · 跑步 '+(it.runs||0)+' 次 · '+fmtDist(it.distance_km,2)+'</div><div>计划：'+(plannedTxt||'-')+'（合计 '+plannedTotal+'）</div><div>客观：HR '+(it.avg_hr||'-')+' · Cad '+(it.cadence_spm||'-')+' · Elev '+fmtElev(it.elevation_gain_m||0)+'</div><div>主观：疲劳 '+nv(it.fatigue_score,'-')+' · 不适 '+nv(it.soreness_level,'-')+' '+(it.soreness_area||'')+'</div><div>打卡：晨起 '+(it.morning_checked?'✅':'—')+' · 跑后 '+(it.post_run_checked?'✅':'—')+'</div><div>AI建议（次日）：'+(it.tomorrow_session||'-')+' · 风险 '+(it.injury_risk||'-')+' · 疲劳状态 '+(it.fatigue_status||'-')+'</div><div>建议约束：HR上限 '+(it.hr_cap||'-')+'，配速 '+(it.pace_hint||'-')+'，步频 '+(it.cadence_hint||'-')+'</div><div>教练反馈：'+nl2br(it.coach_message||'-')+'</div><div style="margin-top:4px">建议依据：</div><ul>'+rationale+'</ul>';

  document.getElementById('fbPhase').value = it.post_run_checked ? 'post_run' : 'morning';
  document.getElementById('fbFatigue').value = String(nv(it.fatigue_score,5));
  document.getElementById('fbSoreness').value = String(nv(it.soreness_level,0));
  document.getElementById('fbArea').value = it.soreness_area || '';
  document.getElementById('fbSleep').value = it.sleep_note || '';
}

function saveDayFeedback(){
  if(!selectedDate){ document.getElementById('fbStatus').textContent='请先选一个日期'; return; }
  var body={ user_id:v('user_id'), checkin_date:selectedDate, checkin_phase:document.getElementById('fbPhase').value, fatigue_score:Number(document.getElementById('fbFatigue').value), soreness_level:Number(document.getElementById('fbSoreness').value), soreness_area:document.getElementById('fbArea').value.trim()||null, sleep_note:document.getElementById('fbSleep').value.trim()||null };
  document.getElementById('fbStatus').textContent='保存中...';
  var xhr=new XMLHttpRequest(); xhr.open('POST','/coach/feedback',true); xhr.setRequestHeader('Content-Type','application/json');
  xhr.onreadystatechange=function(){ if(xhr.readyState!==4) return; if(xhr.status>=200 && xhr.status<300){ document.getElementById('fbStatus').textContent='已保存'; refreshAll(); } else { document.getElementById('fbStatus').textContent='保存失败'; } };
  xhr.onerror=function(){ document.getElementById('fbStatus').textContent='保存异常'; };
  xhr.send(JSON.stringify(body));
}

function renderMonthGrid(){
  monthGridEl.innerHTML='';
  var y=currentMonth.getFullYear(); var m=currentMonth.getMonth(); calTitleEl.textContent=y+'-'+two(m+1);
  var first=new Date(y,m,1); var start=new Date(first); var monOffset=(first.getDay()+6)%7; start.setDate(first.getDate()-monOffset);
  for(var i=0;i<42;i++){
    var d=new Date(start); d.setDate(start.getDate()+i); var iso=isoDate(d); var inMonth=(d.getMonth()===m); var data=calendarMap[iso];
    var cell=document.createElement('button'); cell.className='day'; if(!inMonth) cell.className+=' muted'; if(data && (data.runs||0)>0) cell.className+=' has-run'; if(data&&data.injury_risk==='mild') cell.className+=' risk-mild'; if(data&&data.injury_risk==='high') cell.className+=' risk-high'; if(selectedDate===iso) cell.className+=' selected';
    var runKm=(data&&data.distance_km!=null)?fmtShort(data.distance_km):('0'+displayUnit()); var elev=(data&&data.elevation_gain_m!=null)?fmtElev(data.elevation_gain_m):fmtElev(0); var fatigue='F'+nv(data?data.fatigue_score:null,'-'); var pType=(data&&data.planned_session_type)?data.planned_session_type:'-'; var pKm=(data&&data.planned_total_km!=null)?fmtShort(data.planned_total_km):'-'; var ad=(data&&data.planned_adapted)?' *':''; var meta=data?('A:'+runKm+' '+elev+' '+fatigue+'<br/>P:'+pType+' '+pKm+ad):'';
    cell.innerHTML='<div class="n">'+d.getDate()+'</div><div class="m">'+meta+'</div>';
    cell.onclick=(function(x){ return function(){ selectedDate=x; renderMonthGrid(); renderDayDetail(x); }; })(iso);
    monthGridEl.appendChild(cell);
  }
}

function shiftMonth(step){ currentMonth=new Date(currentMonth.getFullYear(), currentMonth.getMonth()+step, 1); renderMonthGrid(); }

function renderCalendarData(data){
  calendarMap={}; if(!data||!data.ok) return; var items=data.items||[]; for(var i=0;i<items.length;i++) calendarMap[items[i].date]=items[i];
  if(!selectedDate){ var keys=Object.keys(calendarMap).sort().reverse(); selectedDate=keys.length?keys[0]:isoDate(new Date()); }
  var sd=new Date(selectedDate+'T00:00:00'); currentMonth=new Date(sd.getFullYear(), sd.getMonth(), 1); renderMonthGrid(); renderDayDetail(selectedDate);
}

function refreshAll(){
  setStatus('加载中...');
  var tz='Asia/Shanghai'; try{ tz=Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai'; }catch(e){}
  var user=encodeURIComponent(v('user_id')); var weeks=Number(v('weeks')); var unit=v('unit');
  var url1='/activities/recent?user_id='+user+'&weeks='+weeks+'&unit='+unit+'&provider=strava&tz='+encodeURIComponent(tz);
  var urlTrend='/activities/recent?user_id='+user+'&weeks=12&unit='+unit+'&provider=strava&tz='+encodeURIComponent(tz);
  var url2='/coach/calendar?user_id='+user+'&days=180&tz='+encodeURIComponent(tz);
  getJSON(url1, function(d1){
    renderSummary(d1);
    getJSON(urlTrend, function(dt){ setTrendActivities(dt.activities||[], unit); }, function(){ setTrendActivities([], unit); });
    getJSON(url2, function(d2){ renderCalendarData(d2); }, function(){ setStatus('日历加载失败'); });
  }, function(){ setStatus('活动加载失败'); });
}

function boot(){
  if(!inited){
    initSelectors();
    document.getElementById('unit').value = loadGlobalUnit();
    document.getElementById('unit').addEventListener('change', function(){ saveGlobalUnit(v('unit')); refreshAll(); });
    inited=true;
  }
  refreshAll();
}
window.addEventListener('load', boot);
window.addEventListener('pageshow', boot);
window.onerror = function(msg){ setStatus('前端脚本异常: ' + msg); };
</script>
</body>
</html>
"""


def render_history_ui() -> HTMLResponse:
    return HTMLResponse(content=HTML)

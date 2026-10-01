# -*- coding: utf-8 -*-
"""由题库 bank.json 生成单文件自测页（多套卷、自动判分）。

用法：
    python build.py            # 读 bank.json 生成 自测.html
    python build.py --out X.html
"""
import argparse
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

CSS = """
  :root { --ok:#2e9e5b; --bad:#d9534f; --warn:#c98a00; }
  #wrap { color: var(--foreground); font-size: 14px; line-height: 1.7; }
  .hdr { font-size: 16px; font-weight: 600; }
  .sub { color: var(--muted-foreground); font-size: 12.5px; }
  .tabs { display:flex; flex-wrap:wrap; gap:6px; margin:10px 0 2px; }
  .tab { font:inherit; color:var(--foreground); background:var(--card); border:1px solid var(--border);
         border-radius:6px; padding:3px 12px; cursor:pointer; }
  .tab.on { border-color: var(--accent); font-weight:600; }
  .tab .sc { color: var(--muted-foreground); font-size:12px; }
  .bar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:8px 0 4px; }
  button { font:inherit; color: var(--foreground); background: var(--card); border:1px solid var(--border);
           border-radius:6px; padding:4px 10px; cursor:pointer; }
  button:hover { border-color: var(--accent); }
  button.primary { border-color: var(--accent); font-weight:600; }
  button.mini { font-size:12px; padding:1px 7px; border-radius:5px; }
  #clock { font-variant-numeric: tabular-nums; font-weight:600; }
  .sec { margin-top:16px; border-top:1px solid var(--border); padding-top:10px; }
  .secTitle { font-weight:600; }
  .q { margin:12px 0 14px; }
  .qno { font-weight:600; }
  .pts { color: var(--muted-foreground); font-size:12px; }
  .tag { font-size:11.5px; border:1px solid var(--border); border-radius:4px; padding:0 5px; color: var(--muted-foreground); }
  .src { font-size:11.5px; color: var(--muted-foreground); border-bottom:1px dotted var(--border); }
  .opts { margin:4px 0 0 2px; }
  .opt { display:block; margin:1px 0; cursor:pointer; }
  .opt input { margin-right:6px; }
  input.ans { font: inherit; background: transparent; color: var(--foreground); border:1px solid var(--border);
              border-radius:5px; padding:2px 8px; min-width:170px; }
  textarea.work { width:100%; box-sizing:border-box; min-height:64px; font:13px/1.6 inherit; background:transparent;
                  color: var(--foreground); border:1px solid var(--border); border-radius:6px; padding:6px 8px; margin-top:6px; }
  .rubric { margin:6px 0 0; }
  .rubric label { display:block; font-size:13px; }
  .feedback { margin-top:6px; font-size:13px; }
  .mark-ok { color: var(--ok); font-weight:600; }
  .mark-bad { color: var(--bad); font-weight:600; }
  .mark-part { color: var(--warn); font-weight:600; }
  .sol { margin-top:4px; border-left:2px solid var(--border); padding:2px 0 2px 10px; color: var(--muted-foreground); font-size:13px; }
  .sol b { color: var(--foreground); }
  .hidden { display:none; }
  #report { margin:12px 0 0; }
  .card { border:1px solid var(--border); border-radius:8px; padding:10px 12px; background: var(--card); }
  .big { font-size:26px; font-weight:700; }
  table { border-collapse: collapse; font-size:13px; margin-top:6px; }
  th, td { border:1px solid var(--border); padding:3px 9px; text-align:left; }
  th { color: var(--muted-foreground); font-weight:600; }
  .hint { color: var(--muted-foreground); font-size:12.5px; }
  a.jump { color: var(--accent); }
"""

JS = r"""
var CH = {'1':'第 1 章 函数与极限','2':'第 2 章 导数与微分','3':'第 3 章 中值定理与导数应用','4':'第 4 章 不定积分'};
var LET = 'ABCDEFGH';
var PS = {};        /* 每套卷的状态 */
function st(id){
  if(!PS[id]) PS[id] = {picked:{},text:{},rubric:{},over:{},graded:false,left:90*60,timer:null,showAll:false,done:false};
  return PS[id];
}
var cur = PAPERS[0].id;

/* ---------- 判分工具 ---------- */
function norm(s){
  return String(s).toLowerCase()
    .replace(/[\s　]/g,'')
    .replace(/[·＊*×]/g,'')
    .replace(/\^/g,'')
    .replace(/[{}\[\]]/g,'')
    .replace(/²/g,'2').replace(/³/g,'3')
    .replace(/pi/g,'π')
    .replace(/[−–—－]/g,'-')
    .replace(/＋/g,'+').replace(/＝/g,'=')
    .replace(/，/g,',').replace(/；/g,';')
    .replace(/（/g,'(').replace(/）/g,')')
    .replace(/\+c$/,'').replace(/-c$/,'')
    .replace(/^y=/,'').replace(/^k=/,'');
}
function num(s){
  var t = norm(s).replace(/(\d)π/g,'$1*π').replace(/π/g,String(Math.PI)).replace(/(\d)\(/g,'$1*(');
  if(!/^[0-9+\-*/().]+$/.test(t)) return null;
  try { var v = Function('"use strict";return ('+t+')')(); return (typeof v === 'number' && isFinite(v)) ? v : null; }
  catch(e){ return null; }
}
function matchAnswer(q, raw){
  if(!raw || !raw.trim()) return false;
  var u = norm(raw);
  for(var i=0;i<q.accept.length;i++){
    var a = q.accept[i];
    if(norm(a) === u || String(a).toLowerCase().trim() === raw.toLowerCase().trim()) return true;
    var nu = num(u), na = num(a);
    if(nu !== null && na !== null && Math.abs(nu-na) <= 1e-4*Math.max(1,Math.abs(na))) return true;
  }
  return false;
}
function paperById(id){ for(var i=0;i<PAPERS.length;i++){ if(PAPERS[i].id===id) return PAPERS[i]; } return PAPERS[0]; }
function fmt(s){ s=Math.max(0,s); var m=Math.floor(s/60), r=s%60; return (m<10?'0':'')+m+':'+(r<10?'0':'')+r; }
function el(id){ return document.getElementById(id); }
function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }

/* ---------- 渲染一套卷 ---------- */
var TITLES = {choice:'一、选择题', fill:'二、填空题', calc:'三、计算题', proof:'四、证明题'};
function secHead(t, qs){
  var n = 0, pts = 0;
  qs.forEach(function(q){ if(q.t===t){ n++; pts += q.pts; } });
  return '<div class="sec"><div class="secTitle">'+TITLES[t]+'（共 '+n+' 题，'+pts+' 分）</div></div>';
}
function renderPaper(){
  var P = paperById(cur), s = st(cur), html = '', sec = '';
  el('pname').textContent = P.name + ' · ' + (P.note||'');
  el('clock').textContent = fmt(s.left);
  el('btnStart').textContent = s.timer ? '暂停' : (s.left < 90*60 ? '继续计时' : '开始计时');
  P.qs.forEach(function(q){
    if(q.t !== sec){ sec = q.t; html += secHead(sec, P.qs); }
    html += '<div class="q" id="q'+q.n+'" data-n="'+q.n+'">'
         +  '<div><span class="qno">'+q.n+'.</span> '+q.stem+' <span class="pts">（'+q.pts+' 分）</span> '
         +  (q.src ? '<span class="src">'+q.src+'</span> ' : '')
         +  '<span class="tag">'+CH[q.ch]+'</span></div>';
    if(q.t === 'choice'){
      html += '<div class="opts">';
      q.opts.forEach(function(o,i){
        html += '<label class="opt"><input type="radio" name="c'+(cur+'_'+q.n)+'" value="'+i+'"'
             +  ' data-q="'+q.n+'" data-kind="choice"'+(s.picked[q.n]===i?' checked':'')+'>'
             +  LET[i]+'. '+o+'</label>';
      });
      html += '</div>';
    } else {
      if(q.t === 'calc') html += '<textarea class="work" data-q="'+q.n+'" data-kind="work" placeholder="在此写过程（不判分，留痕用）">'+esc(s.text['w'+q.n]||'')+'</textarea>';
      if(q.t === 'proof') html += '<textarea class="work" data-q="'+q.n+'" data-kind="work" placeholder="在此写证明过程（不判分）">'+esc(s.text['w'+q.n]||'')+'</textarea>';
      if(q.accept) html += '<div style="margin-top:5px">答：<input class="ans" type="text" data-q="'+q.n+'" data-kind="text"'
           +  ' value="'+String(s.text[q.n]||'').replace(/"/g,'&quot;')+'" placeholder="填最终结果"></div>';
      if(q.points){
        html += '<div class="rubric">';
        q.points.forEach(function(pt,i){
          html += '<label><input type="checkbox" data-q="'+q.n+'" data-kind="rub" data-i="'+i+'"'
               +  ((s.rubric[q.n]&&s.rubric[q.n][i])?' checked':'')+'> '+pt.t+' <span class="pts">('+pt.p+' 分)</span></label>';
        });
        html += '</div>';
      }
    }
    html += '<div class="feedback" id="fb'+q.n+'"></div>'
         +  '<div class="sol'+(s.showAll?'':' hidden')+'" id="sol'+q.n+'"><b>解析：</b>'+q.sol+'</div>'
         +  (q.ref ? '<div class="hint" style="margin-top:3px">参考解答：'+q.ref+'</div>' : '')
         +  '</div>';
  });
  el('qs').innerHTML = html;
  el('btnAll').textContent = s.showAll ? '收起解析' : '显示全部解析';
  el('report').innerHTML = '';
  if(s.graded) grade(true);
  renderTabs();
}
function renderTabs(){
  var html = '';
  PAPERS.forEach(function(P){
    var s = st(P.id);
    html += '<button class="tab'+(P.id===cur?' on':'')+'" data-pid="'+P.id+'">'+P.name
         +  (s.graded ? ' <span class="sc">'+s.total+'/100</span>' : '') + '</button>';
  });
  var done = PAPERS.filter(function(P){ return st(P.id).graded; });
  el('tabs').innerHTML = html;
  el('sum').textContent = done.length ? '已完成 '+done.length+'/'+PAPERS.length+' 套：'
      + done.map(function(P){ return P.name+' '+st(P.id).total+' 分'; }).join('，') : '';
}
function renderAllQuestionsButKeepScroll(){ renderPaper(); }

/* ---------- 事件 ---------- */
document.addEventListener('click', function(e){
  var t = e.target;
  if(t.dataset && t.dataset.pid){
    var s = st(cur);
    if(s.timer){ clearInterval(s.timer); s.timer = null; }   /* 切换时停表 */
    cur = t.dataset.pid; renderPaper(); return;
  }
  if(t.dataset && t.dataset.over){
    var parts = t.dataset.over.split(':');
    st(cur).over[parts[0]] = parts[1];
    grade(); return;
  }
  if(t.dataset && t.dataset.showone){ el('sol'+t.dataset.showone).classList.toggle('hidden'); return; }
  if(t.id === 'btnSend'){
    var P = paperById(cur), s = st(cur);
    var txt = '微积分（上）期中自测 · ' + P.name + '：总分 ' + s.total + '/100，错题：第 ' + s.wrongs.join('、') + ' 题。'
            + '请把这几个考点整理成一份复习笔记（考点、我的错因推测、易混淆点、2 道同类练习题带答案）。';
    if(window.hermes && window.hermes.send){ window.hermes.send(txt); return; }
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(txt).then(function(){ t.textContent = '已复制，粘贴给你的 AI 助手即可'; },
                                             function(){ t.dataset.copy = txt; t.textContent = '复制失败，请手动选中下方文字'; });
    } else { t.dataset.copy = txt; t.textContent = '请手动复制：' + txt; }
    return;
  }
});
document.addEventListener('change', function(e){
  var el0 = e.target, n = el0.dataset.q, kind = el0.dataset.kind, s = st(cur);
  if(kind === 'choice') s.picked[n] = +el0.value;
  if(kind === 'rub'){ s.rubric[n] = s.rubric[n] || {}; s.rubric[n][el0.dataset.i] = el0.checked; }
  if(s.graded) grade();
});
document.addEventListener('input', function(e){
  var el0 = e.target, s = st(cur);
  if(el0.dataset.kind === 'text') s.text[el0.dataset.q] = el0.value;
  if(el0.dataset.kind === 'work') s.text['w'+el0.dataset.q] = el0.value;
});
document.addEventListener('click', function(e){
  if(e.target.id === 'btnStart'){
    var s = st(cur);
    if(s.timer){ clearInterval(s.timer); s.timer = null; e.target.textContent = '继续计时'; }
    else { s.timer = setInterval(function(){ tick(cur); }, 1000); e.target.textContent = '暂停'; }
  }
  if(e.target.id === 'btnSubmit'){ var s2 = st(cur); if(s2.timer){ clearInterval(s2.timer); s2.timer=null; } grade(); }
  if(e.target.id === 'btnReset'){
    var s3 = st(cur);
    if(s3.timer){ clearInterval(s3.timer); s3.timer = null; }
    PS[cur] = {picked:{},text:{},rubric:{},over:{},graded:false,left:90*60,timer:null,showAll:false,done:false};
    renderPaper();
  }
  if(e.target.id === 'btnAll'){
    var s4 = st(cur);
    s4.showAll = !s4.showAll;
    renderPaper();
  }
});
function tick(id){
  var s = st(id);
  if(s.left <= 0) return;
  s.left--;
  if(id === cur) el('clock').textContent = fmt(s.left);
  if(s.left === 0){ clearInterval(s.timer); s.timer = null; el('status').textContent = '　时间到，本套已自动判分。'; grade(); }
}

/* ---------- 判分 ---------- */
function qScore(q, s){
  if(s.over[q.n] === 'right') return {s:q.pts, st:'ok', why:'（已手动改判为正确）'};
  if(s.over[q.n] === 'wrong') return {s:0, st:'bad', why:'（已手动改判为错误）'};
  if(q.t === 'choice'){
    var p = s.picked[q.n];
    if(p === undefined) return {s:0, st:'bad', why:'未作答'};
    return p === q.a ? {s:q.pts, st:'ok', why:''} : {s:0, st:'bad', why:'选了 '+LET[p]};
  }
  if(q.accept){
    var raw = s.text[q.n];
    if(!raw || !raw.trim()) return {s:0, st:'bad', why:'未作答'};
    return matchAnswer(q, raw) ? {s:q.pts, st:'ok', why:''} : {s:0, st:'bad', why:'与参考答案不一致'};
  }
  var rb = s.rubric[q.n] || {}, got = 0;
  q.points.forEach(function(pt,i){ if(rb[i]) got += pt.p; });
  return {s:got, st:(got===q.pts?'ok':(got>0?'part':'bad')), why:'你按得分点自评 '+got+' 分', self:true};
}
function grade(silent){
  var P = paperById(cur), s = st(cur), total = 0, byCh = {}, wrongs = [];
  s.graded = true;
  P.qs.forEach(function(q){
    var r = qScore(q, s);
    total += r.s;
    byCh[q.ch] = byCh[q.ch] || {s:0, full:0};
    byCh[q.ch].s += r.s; byCh[q.ch].full += q.pts;
    var fb = el('fb'+q.n);
    var mark = r.st==='ok' ? '<span class="mark-ok">✔ 得 '+r.s+'/'+q.pts+' 分</span>'
             : (r.st==='part' ? '<span class="mark-part">◐ 得 '+r.s+'/'+q.pts+' 分</span>'
                              : '<span class="mark-bad">✘ 得 0/'+q.pts+' 分</span>');
    var over = '';
    if(q.t !== 'proof' && q.accept){
      over = (r.st==='ok') ? ' <button class="mini" data-over="'+q.n+':wrong">其实答错了</button>'
                           : ' <button class="mini" data-over="'+q.n+':right">我答对了，改判</button>';
    }
    fb.innerHTML = mark + (r.why ? ' <span class="hint">'+r.why+'</span>' : '') + over;
    var solEl = el('sol'+q.n);
    if(solEl) solEl.classList.toggle('hidden', !(s.showAll || r.s < q.pts));
    if(r.s < q.pts) wrongs.push(q.n);
  });
  s.total = total; s.wrongs = wrongs; s.byCh = byCh;
  if(!silent) el('report').innerHTML = reportHTML(P, s);
  renderTabs();
}
function reportHTML(P, s){
  var used = 90*60 - s.left, nRight = P.qs.length - s.wrongs.length;
  var srcs = {};
  P.qs.forEach(function(q){ if(q.src) srcs[q.src] = (srcs[q.src]||0)+1; });
  var html = '<div class="card"><div><span class="big">'+s.total+'</span> / 100 分'
           + '<span class="hint">　全对 '+nRight+'/'+P.qs.length+' 题　用时 '+fmt(used)+'</span></div>'
           + '<div class="hint">选择、填空、计算题按标准答案自动判分；证明题是你按得分点自评的结果。</div>';
  html += s.wrongs.length
        ? '<div style="margin-top:6px">错题：'+s.wrongs.map(function(n){ return '<a class="jump" href="#q'+n+'">第 '+n+' 题</a>'; }).join('、')+'（解析已展开）</div>'
        : '<div style="margin-top:6px" class="mark-ok">全对。</div>';
  html += '<table><tr><th>章节</th><th>得分</th><th>满分</th><th>掌握度</th></tr>';
  ['1','2','3','4'].forEach(function(k){
    var b = s.byCh[k]; if(!b) return;
    var rate = b.s/b.full, cls = rate>=0.85?'mark-ok':(rate>=0.6?'mark-part':'mark-bad');
    html += '<tr><td>'+CH[k]+'</td><td>'+b.s+'</td><td>'+b.full+'</td><td class="'+cls+'">'+Math.round(rate*100)+'%</td></tr>';
  });
  html += '</table>';
  html += '<div class="hint" style="margin-top:6px">本套题目来源：'+Object.keys(srcs).map(function(k){ return k+'（'+srcs[k]+' 题）'; }).join('；')+'</div>';
  if(s.wrongs.length) html += '<div style="margin-top:8px"><button class="mini" id="btnSend">复制错题清单（交给 AI 助手整理成复习笔记）</button></div>';
  html += '</div>';
  return html;
}
renderPaper();
"""

HTML_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
<div id="wrap">
  <div class="hdr">{title}</div>
  <div class="sub">{sub}</div>
  <div class="sub">范围：{scope}</div>

  <div class="tabs" id="tabs"></div>
  <div class="hint" id="sum"></div>

  <div class="bar">
    <button id="btnStart" class="primary">开始计时</button>
    <span>剩余 <span id="clock">90:00</span></span>
    <button id="btnSubmit" class="primary">提交并判分</button>
    <button id="btnReset">重做本套</button>
    <button id="btnAll">显示全部解析</button>
  </div>
  <div class="sub" id="pname"></div>
  <div class="hint">答案格式：分数写 1/2，幂写 e^2 或 e²，不定积分的 +C 可省略；大小写与空格不敏感。判分与你的写法不一致时，点该题的“改判”。<span id="status"></span></div>

  <div id="report"></div>
  <div id="qs"></div>
  <div id="notes">{footer}</div>
</div>
<script>
var PAPERS = {papers};
{js}
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default=str(HERE / "bank.json"))
    ap.add_argument("--out", default=str(HERE / "自测.html"))
    a = ap.parse_args()
    bank = json.loads(pathlib.Path(a.bank).read_text(encoding="utf-8"))
    meta = bank["meta"]
    footer = ""
    if meta.get("notes"):
        footer += '<div class="sec"><div class="secTitle">说明</div>' + "".join(
            '<div class="hint">· ' + s + '</div>' for s in meta["notes"]) + "</div>"
    if meta.get("sources"):
        footer += '<div class="sec"><div class="secTitle">题目来源与核对</div>' + "".join(
            '<div class="hint">· ' + s + '</div>' for s in meta["sources"]) + "</div>"
    js_papers = json.dumps(bank["papers"], ensure_ascii=False).replace("<", "\\u003c")
    html = (HTML_TMPL
            .replace("{title}", meta["title"])
            .replace("{sub}", meta["sub"])
            .replace("{scope}", meta["scope"])
            .replace("{footer}", footer)
            .replace("{css}", CSS)
            .replace("{js}", JS)
            .replace("{papers}", js_papers))
    out = pathlib.Path(a.out)
    out.write_text(html, encoding="utf-8")
    print("wrote", out, len(html), "bytes,", len(bank["papers"]), "papers")


if __name__ == "__main__":
    main()

"""把 复习讲义.md 渲染成自包含的 复习讲义.html（目录 + 各考点可折叠 + 搜索）。

用法：
    python build_notes.py                # 读同目录的 复习讲义.md / bank.json / notes_map.json
    python build_notes.py --check        # 只做一致性检查后渲染（等同先跑 check_notes.py）

附录 A「逐题索引」由本脚本从 bank.json + notes_map.json 生成并注入
md 里的 <!-- BEGIN:INDEX --> ... <!-- END:INDEX --> 之间，保证与自测页题库永远同步。
"""
import html as _html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
MD = HERE / "复习讲义.md"
BANK = HERE / "bank.json"
MAP = HERE / "notes_map.json"
METHODS = HERE / "methods.json"
OUT = HERE / "复习讲义.html"

LET = "ABCDEFGH"


def load():
    bank = json.loads(BANK.read_text(encoding="utf-8"))
    nmap = json.loads(MAP.read_text(encoding="utf-8"))
    md = MD.read_text(encoding="utf-8")
    return bank, nmap, md


def q_index(bank):
    """{(paper_no, q_no): (question, paper)}"""
    out = {}
    for i, P in enumerate(bank["papers"], 1):
        for q in P["qs"]:
            out[(i, q["n"])] = (q, P)
    return out


def answer_text(q):
    if q.get("key"):
        return q["key"]
    if q.get("t") == "proof":
        return "证明题：按得分点自评"
    pts = q.get("points") or []
    if pts:
        return "按得分点自评（%d 个得分点）" % len(pts)
    return "见解析"


def build_index(bank, nmap):
    """生成附录 A 的 markdown 表格。"""
    idx = q_index(bank)
    where = {}          # (i,n) -> 考点 id
    for t in nmap["topics"]:
        for ref in t["qs"]:
            m = re.fullmatch(r"p(\d+):(\d+)", ref)
            where[(int(m.group(1)), int(m.group(2)))] = t["id"]
    tname = {t["id"]: t["name"] for t in nmap["topics"]}
    rows = ["| 题号 | 出处 | 考点 | 参考答案 / 判分方式 |", "|---|---|---|---|"]
    stats = {"n": 0, "miss": []}
    for i, P in enumerate(bank["papers"], 1):
        for q in sorted(P["qs"], key=lambda x: x["n"]):
            tid = where.get((i, q["n"]))
            if tid is None:
                stats["miss"].append("套%d 第%d题" % (i, q["n"]))
                tid_txt = "—"
            else:
                tid_txt = "%s %s" % (tid, tname[tid])
            ans = answer_text(q).replace("|", "／")
            src = (q.get("src") or "").replace("|", "／")
            rows.append("| 套%d 第%d题 | %s | %s | %s |" % (i, q["n"], src, tid_txt, ans))
            stats["n"] += 1
    head = "把答案遮起来自测一遍，再回看对应考点讲解。四套卷的作答入口：[自测.html](自测.html)（同目录）。\n\n"
    return head + "\n".join(rows), stats


def inject_index(md, table):
    begin = "<!-- BEGIN:INDEX -->"
    end = "<!-- END:INDEX -->"
    if begin not in md or end not in md:
        raise SystemExit("复习讲义.md 缺少 %s / %s 标记" % (begin, end))
    pre, rest = md.split(begin, 1)
    _, post = rest.split(end, 1)
    return pre + begin + "\n\n" + table + "\n\n" + end + post


def build_methods_table(nmap):
    """生成附录 D 的名师方法索引表（读合并后的 methods.json）。"""
    data = json.loads(METHODS.read_text(encoding="utf-8"))["topics"]
    tname = {t["id"]: t["name"] for t in nmap["topics"]}
    rows = ["| 考点 | 老师 | 招牌方法 | 关键要点 | 出处 |", "|---|---|---|---|---|"]
    n = 0
    for t in nmap["topics"]:
        tid = t["id"]
        for m in data.get(tid, []):
            n += 1
            pts = "；".join(m["p"][:2])
            pts = pts.replace("|", "／")
            host = re.sub(r"^https?://([^/]+).*$", r"\1", m["s"])
            rows.append("| %s %s | %s | %s | %s | [%s](%s) |"
                        % (tid, tname.get(tid, ""), m["t"], m["m"].replace("|", "／"),
                           pts, host, m["s"]))
    head = ("下面的表格按考点编号排列，列出本讲义引用的全部名师方法及其出处链接。"
            "方法名按公开讲义、题解里的通行叫法书写；出处逐条可打开，便于自行核对。\n\n")
    return head + "\n".join(rows), n


def inject_methods(md, table):
    begin = "<!-- BEGIN:METHODS -->"
    end = "<!-- END:METHODS -->"
    if begin not in md or end not in md:
        raise SystemExit("复习讲义.md 缺少 %s / %s 标记" % (begin, end))
    pre, rest = md.split(begin, 1)
    _, post = rest.split(end, 1)
    return pre + begin + "\n\n" + table + "\n\n" + end + post


# ----------------------------------------------------------------- 渲染后的结构整理
H_RE = re.compile(r'^<h([12]) id="([^"]*)"[^>]*>(.*)</h\1>$')


def _strip(text):
    return re.sub(r"<[^>]+>", "", text).strip()


def restructure(html):
    """把渲染结果整理成「章 → 考点」两级结构，返回 (toc_html, body_html, stats)。"""
    lines = html.split("\n")
    # 逐行分组：遇到 h1 开新章，遇到 h2 开新考点，其余按归属追加
    doc_head, chapters = [], []
    cur_ch = None
    cur_tp = None
    h1_seen = 0
    for ln in lines:
        m = H_RE.match(ln.strip())
        if m and m.group(1) == "1":
            h1_seen += 1
            title = _strip(m.group(3))
            hid = m.group(2)
            if h1_seen == 1:                       # 文档标题 → 前言
                doc_head.append(("h1", hid, title))
                cur_ch = {"id": hid, "title": title, "kind": "head", "raw": [], "topics": [], "body": []}
                chapters.append(cur_ch)
            else:
                cur_ch = {"id": hid, "title": title, "kind": "chapter", "raw": [], "topics": [], "body": []}
                chapters.append(cur_ch)
            cur_tp = None
            continue
        if m and m.group(1) == "2":
            tid_raw = _strip(m.group(3))
            mm = re.match(r"^([0-9]+\.[0-9]+)\s*(.*)$", tid_raw)
            tid = mm.group(1) if mm else ""
            tname = mm.group(2) if mm else tid_raw
            cur_tp = {"id": m.group(2), "tid": tid, "name": tname, "body": []}
            if cur_ch is None:
                cur_ch = {"id": "pre", "title": "开篇", "kind": "head", "raw": [], "topics": [], "body": []}
                chapters.append(cur_ch)
            cur_ch["topics"].append(cur_tp)
            continue
        if cur_tp is not None:
            cur_tp["body"].append(ln)
        elif cur_ch is not None:
            cur_ch["body"].append(ln)
        else:
            doc_head.append(("raw", "", ln))

    toc, body = [], []
    n_topics = 0
    for ci, ch in enumerate(chapters):
        anchor = ch["id"]
        topics_txt = "".join(
            ('<a class="ti" href="#%s">%s %s</a>' % (t["id"], t["tid"], _html.escape(t["name"])))
            if t["tid"] else
            ('<a class="ti" href="#%s">%s</a>' % (t["id"], _html.escape(t["name"])))
            for t in ch["topics"])
        toc.append('<div class="tc"><a class="tt" href="#%s">%s</a>%s</div>'
                   % (anchor, _html.escape(ch["title"]), topics_txt))
        parts = ['<section class="chapter" data-ch="%s">' % _html.escape(ch["title"])]
        parts.append('<h1 id="%s" class="chead">%s<span class="chev">▾</span></h1>'
                     % (anchor, _html.escape(ch["title"])))
        parts.append('<div class="cbody">')
        parts.append("\n".join(ch["body"]))
        for t in ch["topics"]:
            if t["tid"]:
                n_topics += 1
            parts.append('<div class="topic closed" data-tid="%s">' % t["tid"])
            parts.append('<h2 id="%s" class="thead"><span class="tid">%s</span> '
                         '<span class="tname">%s</span><span class="chev">▾</span></h2>'
                         % (t["id"], t["tid"], _html.escape(t["name"])))
            parts.append('<div class="tbody">')
            parts.append("\n".join(t["body"]))
            parts.append('</div></div>')
        parts.append("</div></section>")
        body.append("\n".join(parts))
    return "".join(toc), "\n".join(body), {"chapters": len(chapters), "topics": n_topics}


CSS = """
  :root { --ok:#2e9e5b; --bad:#d9534f; }
  #wrap { color: var(--foreground); font-size: 14px; line-height: 1.75; max-width: 900px; }
  h1.chead { font-size: 17px; margin: 18px 0 6px; padding-top: 10px; border-top: 1px solid var(--border);
             cursor: pointer; }
  h1.chead .chev { color: var(--muted-foreground); float: right; font-size: 13px; }
  section.chapter.shut .cbody { display: none; }
  h2.thead { font-size: 14.5px; margin: 8px 0 4px; padding: 5px 8px; border: 1px solid var(--border);
             border-radius: 6px; background: var(--card); cursor: pointer; font-weight: 600; }
  h2.thead .tid { color: var(--accent); margin-right: 6px; }
  h2.thead .chev { color: var(--muted-foreground); float: right; font-size: 12px; }
  .topic.closed .tbody { display: none; }
  .tbody { padding: 2px 4px 8px 14px; border-left: 2px solid var(--border); margin-left: 4px; }
  .topic.hide, section.chapter.hide { display: none; }
  .tb { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 8px 0; }
  input#q { font: inherit; background: transparent; color: var(--foreground); border: 1px solid var(--border);
            border-radius: 6px; padding: 3px 8px; min-width: 220px; }
  button { font: inherit; color: var(--foreground); background: var(--card); border: 1px solid var(--border);
           border-radius: 6px; padding: 3px 10px; cursor: pointer; }
  button:hover { border-color: var(--accent); }
  #toc { border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; background: var(--card);
         margin: 10px 0 4px; }
  #toc.shut { display: none; }
  .tc { margin: 2px 0; }
  .tt { color: var(--foreground); font-weight: 600; text-decoration: none; }
  .ti { color: var(--muted-foreground); font-size: 12.5px; text-decoration: none; margin: 0 8px 0 0;
        white-space: nowrap; }
  .ti:hover, .tt:hover { color: var(--accent); }
  a { color: var(--accent); }
  table { border-collapse: collapse; font-size: 12.5px; margin-top: 6px; }
  th, td { border: 1px solid var(--border); padding: 3px 8px; text-align: left; vertical-align: top; }
  th { color: var(--muted-foreground); font-weight: 600; }
  blockquote { margin: 8px 0; padding: 2px 0 2px 12px; border-left: 2px solid var(--accent);
               color: var(--muted-foreground); }
  code { background: var(--card); border: 1px solid var(--border); border-radius: 4px; padding: 0 3px;
         font-size: 12.5px; }
  .hint { color: var(--muted-foreground); font-size: 12.5px; }
  strong { color: var(--foreground); }
"""

JS = r"""
var chapters = [].slice.call(document.querySelectorAll('section.chapter'));
function shutChapter(sec, s){ sec.classList.toggle('shut', s); }
function closeTopic(tp, s){ tp.classList.toggle('closed', s); }
document.querySelectorAll('h1.chead').forEach(function(h){
  h.addEventListener('click', function(){
    var sec = h.parentNode; shutChapter(sec, !sec.classList.contains('shut'));
  });
});
document.querySelectorAll('h2.thead').forEach(function(h){
  h.addEventListener('click', function(){
    var tp = h.parentNode; closeTopic(tp, !tp.classList.contains('closed'));
  });
});
function topics(){ return [].slice.call(document.querySelectorAll('.topic')); }
function realTopics(){ return topics().filter(function(t){ return t.getAttribute('data-tid'); }); }
document.getElementById('bOpen').addEventListener('click', function(){
  topics().forEach(function(t){ closeTopic(t, false); });
  chapters.forEach(function(s){ shutChapter(s, false); });
  document.getElementById('toc').classList.remove('shut');
});
document.getElementById('bShut').addEventListener('click', function(){
  topics().forEach(function(t){ closeTopic(t, true); });
  chapters.forEach(function(s){ shutChapter(s, false); });
  document.getElementById('toc').classList.remove('shut');
});
document.getElementById('bToc').addEventListener('click', function(){
  document.getElementById('toc').classList.toggle('shut');
});
function applyFilter(){
  var s = document.getElementById('q').value.trim().toLowerCase();
  var hits = 0;
  chapters.forEach(function(sec){
    var vis = 0;
    [].slice.call(sec.querySelectorAll('.topic')).forEach(function(tp){
      var ok = !s || tp.textContent.toLowerCase().indexOf(s) >= 0;
      tp.classList.toggle('hide', !ok);
      if(ok) vis++;
    });
    if(s){ /* 搜索时自动展开命中的章与考点 */
      [].slice.call(sec.querySelectorAll('.topic')).forEach(function(tp){
        if(!tp.classList.contains('hide')) closeTopic(tp, false);
      });
      shutChapter(sec, vis === 0 && sec.textContent.toLowerCase().indexOf(s) < 0);
    } else {
      shutChapter(sec, false);
    }
    if(sec.classList.contains('hide')) /* noop */;
    sec.classList.toggle('hide', s && vis === 0 && sec.textContent.toLowerCase().indexOf(s) < 0);
    [].slice.call(sec.querySelectorAll('.topic')).forEach(function(tp){
      if(!tp.classList.contains('hide') && tp.getAttribute('data-tid')) hits++;
    });
  });
  document.getElementById('cnt').textContent = s ? ('匹配考点 ' + hits + ' 个')
                                                  : ('共 ' + realTopics().length + ' 个考点');
}
document.getElementById('q').addEventListener('input', applyFilter);
document.getElementById('cnt').textContent = '共 ' + realTopics().length + ' 个考点';
"""

TPL = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>微积分（上）期中复习讲义</title>
<style>{css}</style></head>
<body><div id="wrap">
<div class="tb">
  <input id="q" placeholder="搜索考点 / 知识点（如：罗尔、分部积分、间断点）">
  <button id="bOpen">展开全部</button>
  <button id="bShut">收起考点</button>
  <button id="bToc">目录</button>
  <span class="hint" id="cnt"></span>
</div>
<div id="toc">{toc}</div>
{body}
<div class="hint" style="margin-top:14px">讲义由 复习讲义.md 生成 · 题目取自《微积分（上）期中自测》四套卷 · 答案均由 sympy/mpmath 独立复算</div>
</div>
<script>{js}</script></body></html>
"""


def main():
    bank, nmap, md = load()
    table, stats = build_index(bank, nmap)
    if stats["miss"]:
        print("警告：题库里有未被讲义归入考点的题：%s" % "、".join(stats["miss"]))
    md2 = inject_index(md, table)
    mtable, n_meth = build_methods_table(nmap)
    md2 = inject_methods(md2, mtable)
    if md2 != md:                     # 把两张自动生成的表也写回 md，让仓库里的 .md 自带索引
        MD.write_text(md2, encoding="utf-8")
    try:
        import markdown
    except ImportError:
        raise SystemExit("需要 markdown 库：<项目 python> -m pip install markdown")
    body_html = markdown.markdown(
        md2, extensions=["tables", "fenced_code", "toc", "attr_list", "sane_lists"])
    toc, body, st = restructure(body_html)
    # 前言那一节不需要折叠标记
    out = TPL.format(css=CSS, js=JS, toc=toc, body=body)
    OUT.write_text(out, encoding="utf-8")
    print("已生成 %s（%.1f KB）｜章 %d 个、考点 %d 个、索引 %d 行、名师方法 %d 条"
          % (OUT.name, OUT.stat().st_size / 1024, st["chapters"], st["topics"], stats["n"], n_meth))
    if st["topics"] != len(nmap["topics"]):
        print("警告：讲义考点数 %d ≠ notes_map 里的 %d" % (st["topics"], len(nmap["topics"])))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

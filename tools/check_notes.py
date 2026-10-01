"""复习讲义与题库的一致性自检（讲义 ↔ notes_map ↔ bank 三方对账）。

用法：  python check_notes.py
退出码 0 = 全部通过；非 0 = 有一致性问题（输出里逐条列明）。

检查项：
  [1] 讲义里的 ### 考点编号集合 == notes_map 的考点集合，名称一致
  [2] 每个考点段落引用的「套i 第n题」== notes_map 里该考点的题号（集合相等）
  [3] 题库 80 道题每道恰好归入一个考点（无遗漏、无重复、无越界引用）
  [4] 每个考点段落都有「本卷真题 / 小练 / 答案」三件套
  [5] 「考点地图」表里的编号与题号列表和 notes_map 一致
  [6] 附录 A 的自动生成标记存在
  [7] methods.json 覆盖全部考点，老师在白名单内、出处为 http(s) 链接
  [8] 每条方法的出处 URL 必须出现在该考点段落的「出处」清单里（正文与索引不脱节）
  [9] 每个考点段落都有 原理 / 名师方法 / 出处 / 例题 四个注入块，且标记成对
  [10] 附录 D 标记存在，且表格里的方法行数 == methods.json 的方法总数
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
MD = HERE / "复习讲义.md"
BANK = HERE / "bank.json"
MAP = HERE / "notes_map.json"
METHODS = HERE / "methods.json"
DEEPEN = HERE / "deepen.json"

TEACHERS = {"张宇", "武忠祥", "汤家凤", "杨超", "余丙森", "李永乐", "通用技巧"}

fails, warns = [], []


def fail(m):
    fails.append(m)


def warn(m):
    warns.append(m)


md = MD.read_text(encoding="utf-8")
bank = json.loads(BANK.read_text(encoding="utf-8"))
nmap = json.loads(MAP.read_text(encoding="utf-8"))
methods = json.loads(METHODS.read_text(encoding="utf-8"))["topics"]
deepen = json.loads(DEEPEN.read_text(encoding="utf-8"))["topics"]

# ---- 讲义里的考点段落： '## 1.2 标题' 到下一个 '#'/'## ' 之前
secs = {}
order = []
cur = None
for ln in md.split("\n"):
    m = re.match(r"^##\s+([0-9]+\.[0-9]+)\s+(.*)$", ln.strip())
    if m:
        cur = m.group(1)
        secs[cur] = {"name": m.group(2).strip(), "lines": []}
        order.append(cur)
        continue
    if re.match(r"^#{1,2}\s", ln.strip()):      # 换到非考点的标题 → 段落结束
        cur = None
    if cur:
        secs[cur]["lines"].append(ln)

map_t = {t["id"]: t for t in nmap["topics"]}

# [1] 编号与名称
if set(secs) != set(map_t):
    fail("[1] 考点编号不一致：仅在讲义 %s；仅在 notes_map %s"
         % (sorted(set(secs) - set(map_t)), sorted(set(map_t) - set(secs))))
for tid in sorted(set(secs) & set(map_t)):
    a = secs[tid]["name"].strip()
    b = map_t[tid]["name"].strip()
    if a != b:
        fail("[1] %s 名称不一致：讲义「%s」/ notes_map「%s」" % (tid, a, b))

# [2] 段落里引用的题号
seen = {}
for tid, sec in secs.items():
    refs = re.findall(r"套\s*(\d+)\s*第\s*(\d+)\s*题", "\n".join(sec["lines"]))
    got = ["p%s:%s" % (a, b) for a, b in refs]
    if len(got) != len(set(got)):
        fail("[2] %s 段落里同一道题被引用多次：%s"
             % (tid, [r for r in set(got) if got.count(r) > 1]))
    want = map_t.get(tid, {}).get("qs", [])
    if sorted(set(got)) != sorted(set(want)):
        fail("[2] %s 题号不一致：讲义 %s / notes_map %s" % (tid, sorted(set(got)), sorted(want)))
    for r in set(got):
        if r in seen:
            fail("[3] %s 被两个考点同时引用（%s、%s）" % (r, seen[r], tid))
        seen[r] = tid

# [3] 题库覆盖
allq = ["p%d:%d" % (i, q["n"]) for i, P in enumerate(bank["papers"], 1) for q in P["qs"]]
missing = [r for r in allq if r not in seen]
extra = [r for r in seen if r not in allq]
if missing:
    fail("[3] 题库里这些题没有归入任何考点：%s" % missing)
if extra:
    fail("[3] 讲义引用了题库里不存在的题：%s" % extra)
if len(allq) != len(set(allq)):
    fail("[3] 题库自身有重复题号")

# [4] 段落三件套
for tid, sec in secs.items():
    txt = "\n".join(sec["lines"])
    for key in ("本卷真题", "小练", "答案"):
        if key not in txt:
            fail("[4] %s 段落缺少「%s」" % (tid, key))
    if "TODO" in txt or "待补" in txt:
        fail("[4] %s 段落里有未完成的占位" % tid)

# [5] 考点地图表
geo = re.findall(r"^\|\s*([0-9]+\.[0-9]+)\s*\|([^|]*)\|([^|]*)\|", md, re.M)
geo_ids = [g[0] for g in geo]
if len(geo_ids) != len(set(geo_ids)):
    fail("[5] 考点地图里有重复编号")
if set(geo_ids) != set(map_t):
    fail("[5] 考点地图编号与 notes_map 不一致：地图 %s / map %s"
         % (sorted(set(geo_ids) - set(map_t)), sorted(set(map_t) - set(geo_ids))))
for tid, name, qlist in geo:
    if tid not in map_t:
        continue
    if name.strip() != map_t[tid]["name"].strip():
        fail("[5] 考点地图 %s 名称不一致：地图「%s」/ notes_map「%s」"
             % (tid, name.strip(), map_t[tid]["name"]))
    refs = ["p%s:%s" % (a, b) for a, b in re.findall(r"套\s*(\d+)-(\d+)", qlist)]
    if sorted(set(refs)) != sorted(set(map_t[tid]["qs"])):
        fail("[5] 考点地图 %s 题号不一致：地图 %s / notes_map %s"
             % (tid, sorted(set(refs)), sorted(map_t[tid]["qs"])))

# [6] 附录标记
for mark in ("<!-- BEGIN:INDEX -->", "<!-- END:INDEX -->"):
    if mark not in md:
        fail("[6] 复习讲义.md 缺少 %s" % mark)

# [7] methods.json 的覆盖与来源合法性
if set(methods) != set(map_t):
    fail("[7] 名师方法覆盖不全：缺 %s；多 %s"
         % (sorted(set(map_t) - set(methods)), sorted(set(methods) - set(map_t))))
n_meth = 0
for tid, lst in methods.items():
    if not lst:
        fail("[7] %s 考点没有任何名师方法" % tid)
    names = [m["m"] for m in lst]
    if len(names) != len(set(names)):
        fail("[7] %s 考点有重名方法：%s" % (tid, [n for n in set(names) if names.count(n) > 1]))
    for m in lst:
        n_meth += 1
        if m["t"] not in TEACHERS:
            fail("[7] %s 出现白名单外的老师「%s」" % (tid, m["t"]))
        if not m["s"].startswith("http"):
            fail("[7] %s「%s」的出处不是 http(s) 链接：%s" % (tid, m["m"], m["s"]))
        if not m.get("p"):
            fail("[7] %s「%s」没有要点" % (tid, m["m"]))

# [8] 每条方法的出处必须出现在该考点段落的「出处」清单里
for tid, lst in methods.items():
    txt = "\n".join(secs.get(tid, {}).get("lines", []))
    for m in lst:
        if m["s"] not in txt:
            fail("[8] %s「%s」的出处没在该考点段落里列出：%s" % (tid, m["m"], m["s"]))

# [9] 注入块 + 标记成对
for tid in map_t:
    txt = "\n".join(secs.get(tid, {}).get("lines", []))
    for key, label in (("why", "原理"), ("meth", "名师方法"), ("ex", "例题")):
        open_m = "<!-- DEEP:%s:%s -->" % (key, tid)
        close_m = "<!-- /DEEP:%s:%s -->" % (key, tid)
        if open_m not in txt:
            fail("[9] %s 缺少 %s 块" % (tid, label))
        elif close_m not in txt:
            fail("[9] %s 的 %s 块没有闭合标记" % (tid, label))
    if "**出处**" not in txt:
        fail("[9] %s 段落缺少「出处」清单" % tid)
    if tid not in deepen:
        fail("[9] %s 在 deepen.json 里没有原理/例题" % tid)

# [10] 附录 D 标记与行数
miss_mark = [m for m in ("<!-- BEGIN:METHODS -->", "<!-- END:METHODS -->") if m not in md]
if miss_mark:
    fail("[10] 复习讲义.md 缺少 %s" % "、".join(miss_mark))
else:
    body = md.split("<!-- BEGIN:METHODS -->", 1)[1].split("<!-- END:METHODS -->", 1)[0]
    rows = [ln for ln in body.split("\n") if ln.startswith("|") and "---" not in ln]
    if not rows:
        warn("[10] 附录 D 还没生成（先跑 build_notes.py）")
    elif len(rows) - 1 != n_meth:
        fail("[10] 附录 D 方法行数 %d ≠ methods.json 的 %d 条" % (len(rows) - 1, n_meth))

# ---- 报告
print("考点 %d 个（notes_map %d 个）；题库 %d 道；已归类 %d 道；名师方法 %d 条"
      % (len(secs), len(map_t), len(allq), len(seen), n_meth))
for w in warns:
    print("  提醒：" + w)
if fails:
    print("失败 %d 项：" % len(fails))
    for f in fails:
        print("  ✗ " + f)
    sys.exit(1)
print("全部通过：讲义、考点地图、notes_map、题库、名师方法五方一致。")
sys.exit(0)

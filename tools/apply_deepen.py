"""把 methods/*.json（名师方法）与 deepen/*.json（原理、例题）注入 复习讲义.md。

用法：
    python apply_deepen.py            # 合并数据文件 → methods.json / deepen.json → 改写 复习讲义.md
    python apply_deepen.py --dry      # 只合并数据、打印统计，不改写 md

设计要点：
  * 数据文件按章拆成小文件（methods/01.json ...），本脚本合并成单一的
    methods.json / deepen.json，构建与校验只读合并结果，避免多处真源。
  * 注入靠标记对（<!-- DEEP:why:1.1 --> ... <!-- /DEEP:why:1.1 -->），
    每次重跑先删除旧块再写入，因此可反复运行而不会重复堆叠。
  * 注入内容里不允许出现「套N 第M题」这种真题引用格式——那是 本卷真题 小节的
    专属写法，check_notes.py 会按段落统计引用数并对账。
"""
import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
MD = HERE / "复习讲义.md"
OUT_METHODS = HERE / "methods.json"
OUT_DEEPEN = HERE / "deepen.json"

TOPIC_RE = re.compile(r"^##\s+([0-9]+\.[0-9]+)\s+(.*)$")

MARK_KINDS = ("why", "meth", "ex")


def merge(pattern, note):
    files = sorted(HERE.glob(pattern))
    if not files:
        raise SystemExit("没有找到数据文件：%s" % pattern)
    topics = {}
    for fp in files:
        data = json.loads(fp.read_text(encoding="utf-8"))
        for tid, val in data.get("topics", {}).items():
            if tid in topics:
                raise SystemExit("考点 %s 在多个数据文件里重复定义（%s）" % (tid, fp.name))
            topics[tid] = val
    return {"_note": note, "topics": topics}, [f.name for f in files]


def drop_old(md, tid):
    for kind in MARK_KINDS:
        md = re.sub(r"<!-- DEEP:%s:%s -->.*?<!-- /DEEP:%s:%s -->\n\n?" % (kind, tid, kind, tid),
                    "", md, flags=re.S)
    return md


def why_block(tid, why):
    return ("<!-- DEEP:why:%s -->\n**原理**（为什么这招成立）：%s\n<!-- /DEEP:why:%s -->\n"
            % (tid, why, tid))


def meth_block(tid, methods):
    lines = ["<!-- DEEP:meth:%s -->" % tid, "**名师方法**（公开讲义与题解的通行讲法，出处见下）", ""]
    for md_ in methods:
        pts = []
        for i, p in enumerate(md_["p"]):
            p = p.rstrip()
            while p.endswith("。") or p.endswith("；") or p.endswith("."):
                p = p[:-1]
            pts.append("%s %s" % (chr(0x2460 + i) if i < 20 else "·", p))
        line = "- **%s｜%s**：%s。" % (md_["t"], md_["m"], "；".join(pts))
        if md_.get("e"):
            line += "（例：%s）" % md_["e"]
        lines.append(line)
    seen, srcs = set(), []
    for md_ in methods:
        s = md_["s"]
        if s not in seen:
            seen.add(s)
            srcs.append(s)
    lines.append("")
    lines.append("**出处**")
    lines += ["- <%s>" % s for s in srcs]
    lines.append("<!-- /DEEP:meth:%s -->" % tid)
    return "\n".join(lines) + "\n"


def ex_block(tid, ex):
    return ("<!-- DEEP:ex:%s -->\n**例题**：%s\n<!-- /DEEP:ex:%s -->\n" % (tid, ex, tid))


def inject(md, methods, deepen):
    topics = [t for t in re.findall(r"^##\s+([0-9]+\.[0-9]+)", md, re.M)]
    for tid in topics:
        md = drop_old(md, tid)

    lines = md.split("\n")
    out, cur, i = [], None, 0
    while i < len(lines):
        ln = lines[i]
        m = TOPIC_RE.match(ln.strip())
        if m:
            cur = m.group(1)
        if ln.strip() == "**本卷真题**" and cur:
            if cur in deepen:
                out.append(why_block(cur, deepen[cur]["why"]).rstrip("\n"))
                out.append("")
            if cur in methods:
                out.append(meth_block(cur, methods[cur]).rstrip("\n"))
                out.append("")
        if ln.strip().startswith("**易错点**") and cur:
            if cur in deepen:
                out.append(ex_block(cur, deepen[cur]["ex"]).rstrip("\n"))
                out.append("")
        out.append(ln)
        i += 1
    return "\n".join(out)


def ensure_appendix(md):
    if "BEGIN:METHODS" in md:
        return md
    if not md.endswith("\n"):
        md += "\n"
    md += ("\n# 附录 D　名师方法索引（含出处）\n\n"
           "下面是本讲义各考点引用的全部名师方法，按考点编号排列，方便按「我想看某位老师的讲法」"
           "或「这个考点的所有招法」两种方式检索。方法名按公开讲义、题解里的通行叫法书写，"
           "出处逐条给出可打开的链接。\n\n"
           "<!-- BEGIN:METHODS -->\n\n<!-- END:METHODS -->\n")
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只合并数据并打印统计，不改写讲义")
    args = ap.parse_args()

    methods, mf = merge("methods/*.json", "由 methods/*.json 合并生成，勿直接手改；改分章文件后重跑 apply_deepen.py")
    deepen, df = merge("deepen/*.json", "由 deepen/*.json 合并生成，勿直接手改；改分章文件后重跑 apply_deepen.py")
    OUT_METHODS.write_text(json.dumps(methods, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_DEEPEN.write_text(json.dumps(deepen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    nmeth = sum(len(v) for v in methods["topics"].values())
    teachers = sorted({m["t"] for v in methods["topics"].values() for m in v})
    print("合并 %s → methods.json：%d 个考点、%d 条方法；老师 %s"
          % ("、".join(mf), len(methods["topics"]), nmeth, "、".join(teachers)))
    print("合并 %s → deepen.json：%d 个考点（原理+例题）" % ("、".join(df), len(deepen["topics"])))
    if args.dry:
        return 0

    md = MD.read_text(encoding="utf-8")
    md = ensure_appendix(md)
    md2 = inject(md, methods["topics"], deepen["topics"])
    if md2 != md:
        MD.write_text(md2, encoding="utf-8")
        print("已改写 %s（+%d 字符）" % (MD.name, len(md2) - len(md)))
    else:
        print("讲义内容已是最新，无需改写")
    # 注入后立即自检：每段该有的块必须齐
    missing = []
    for tid in deepen["topics"]:
        blk = re.search(r"^##\s+%s\s+.*?(?=^##\s|^#\s)" % re.escape(tid), md2, re.M | re.S)
        if not blk:
            missing.append(tid + "(段落没找到)")
            continue
        txt = blk.group(0)
        for kind in MARK_KINDS:
            if "<!-- DEEP:%s:%s -->" % (kind, tid) not in txt:
                missing.append("%s(%s)" % (tid, kind))
    if missing:
        print("警告：这些考点的注入块缺失：%s" % "、".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

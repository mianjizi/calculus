# -*- coding: utf-8 -*-
"""题库自检：分值合计、选项索引、参考答案与可接受写法是否自洽。

用法：python check.py [bank.json]
退出码非 0 表示有问题。
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent


def norm(s):
    s = str(s).lower()
    s = re.sub(r"[\s　]", "", s)
    s = re.sub(r"[·＊*×]", "", s)
    s = s.replace("^", "")
    s = re.sub(r"[{}\[\]]", "", s)
    s = s.replace("²", "2").replace("³", "3")
    s = s.replace("pi", "π")
    for ch in "−–—－":
        s = s.replace(ch, "-")
    s = s.replace("＋", "+").replace("＝", "=")
    s = s.replace("，", ",").replace("；", ";")
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"\+c$", "", s)
    s = re.sub(r"^y=", "", s)
    s = re.sub(r"^k=", "", s)
    return s


def num(s):
    t = norm(s).replace("π", repr(3.141592653589793))
    t = re.sub(r"(\d)\(", r"\1*(", t)
    if not re.fullmatch(r"[0-9+\-*/().]+", t):
        return None
    try:
        return float(eval(t, {"__builtins__": {}}, {}))
    except Exception:
        return None


def match(accept, key):
    u = norm(key)
    for a in accept:
        if norm(a) == u:
            return True
        nu, na = num(u), num(a)
        if nu is not None and na is not None and abs(nu - na) <= 1e-4 * max(1, abs(na)):
            return True
    return False


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "bank.json")
    bank = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    for P in bank["papers"]:
        qs = P["qs"]
        total = sum(q["pts"] for q in qs)
        seen = set()
        kinds = {}
        for q in qs:
            tag = "%s 第%s题" % (P["name"], q["n"])
            if q["n"] in seen:
                problems.append(tag + "：题号重复")
            seen.add(q["n"])
            kinds[q["t"]] = kinds.get(q["t"], 0) + 1
            if q["t"] not in ("choice", "fill", "calc", "proof"):
                problems.append(tag + "：未知题型 " + str(q["t"]))
            if q["ch"] not in ("1", "2", "3", "4"):
                problems.append(tag + "：章节标记异常 " + str(q["ch"]))
            if not q.get("stem"):
                problems.append(tag + "：缺题干")
            if not q.get("sol"):
                problems.append(tag + "：缺解析")
            if not q.get("src"):
                problems.append(tag + "：缺出处标注 src")
            if q["t"] == "choice":
                if not (0 <= q["a"] < len(q["opts"])):
                    problems.append(tag + "：正确选项索引越界")
                if len(set(q["opts"])) != len(q["opts"]):
                    problems.append(tag + "：选项有重复")
            if q["t"] in ("fill", "calc", "proof"):
                if not q.get("accept") and not q.get("points"):
                    problems.append(tag + "：既没有 accept 也没有 points，无法判分")
            if q.get("accept") and not q.get("key"):
                problems.append(tag + "：有 accept 但缺 key（check 无法核对）")
            if q.get("accept") and q.get("points"):
                problems.append(tag + "：同时给了 accept 和 points，判分口径不唯一")
            if q.get("accept") and not match(q["accept"], q["key"]):
                problems.append(tag + "：key「%s」不在 accept 里（判分时会判错）" % q["key"])
            if q.get("points"):
                ps = sum(p["p"] for p in q["points"])
                if abs(ps - q["pts"]) > 1e-9:
                    problems.append(tag + "：得分点合计 %s ≠ 分值 %s" % (ps, q["pts"]))
        print("%-6s %2d 题  合计 %3d 分  题型分布 %s" % (P["name"], len(qs), total, kinds))
        if total != 100:
            problems.append(P["name"] + "：总分 %d ≠ 100" % total)
    print("-" * 46)
    if problems:
        print("发现 %d 个问题：" % len(problems))
        for p in problems:
            print("  ✘", p)
        return 1
    print("题库自检通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

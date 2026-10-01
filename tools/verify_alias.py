# -*- coding: utf-8 -*-
"""核验每题 accept 列表里的每一种写法是否与 key 数学等价（sympy 符号化简 + 数值抽样）。

只检查同时带 accept 与 key 的题；多参数问答（key 里含 "="）、非表达式答案会标为 SKIP 并列出。
用法：python verify_alias.py [bank.json]
退出码非 0 表示发现不等价的写法。
"""
import json
import pathlib
import random
import re
import sys

import sympy as sp

HERE = pathlib.Path(__file__).resolve().parent
LOCAL = {"asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "arcsin": sp.asin,
         "arccos": sp.acos, "arctan": sp.atan, "ln": sp.log, "sqrt": sp.sqrt,
         "exp": sp.exp, "log": sp.log, "E": sp.E, "pi": sp.pi}


def to_expr(s):
    """把 Unicode 数学写法转成 sympy 能读的表达式。"""
    t = str(s).strip()
    t = re.sub(r"\+\s*[cC]\s*$", "", t)              # 去 +C
    for ch in "−–—－":
        t = t.replace(ch, "-")
    t = t.replace("＋", "+").replace("，", ",").replace("；", ";")
    t = t.replace("（", "(").replace("）", ")")
    t = t.replace("{", "(").replace("}", ")")
    t = t.replace("·", "*").replace("×", "*").replace("✕", "*")
    t = t.replace("²", "**2").replace("³", "**3")
    t = t.replace("^", "**")
    t = t.replace("π", "pi")
    t = re.sub(r"√\(([^()]*(?:\([^()]*\)[^()]*)*)\)", r"sqrt(\1)", t)   # √(...)
    t = re.sub(r"√([0-9]+(?:\.[0-9]+)?)", r"sqrt(\1)", t)              # √2 -> sqrt(2)
    t = re.sub(r"√([A-Za-z])", r"sqrt(\1)", t)                        # √e -> sqrt(e)
    t = t.replace("√", "sqrt")
    t = t.replace("arcsin", "asin").replace("arccos", "acos").replace("arctan", "atan")
    t = re.sub(r"(?<![A-Za-z_])e(?![A-Za-z_])", "E", t)               # 裸 e -> E
    t = re.sub(r"(?<=[A-Za-z0-9\)])e\*\*", "*E**", t)                 # xe**(-x) -> x*E**(-x)
    t = t.replace("ln", "log")
    t = re.sub(r"log\s*([0-9]+(?:\.[0-9]+)?)", r"log(\1)", t)         # log 2 / log2 -> log(2)
    # 隐式乘法
    t = re.sub(r"(?<=[0-9\)])\s*\(", "*(", t)                          # 2( .. ), )(
    t = re.sub(r"(?<![A-Za-z0-9_])([a-zA-Z])\(", r"\1*(", t)          # n( .. )、x( .. )
    t = re.sub(r"\)\s*(?=[A-Za-z0-9])", ")*", t)                      # )E , )x
    t = re.sub(r"(?<=[A-Za-z0-9])\s+(?=[A-Za-z0-9(])", "*", t)        # x asin -> x*asin
    t = re.sub(r"([0-9])([A-Za-z])", r"\1*\2", t)                     # 2x -> 2*x
    return _fix_func_sqrt(t)


def _fix_func_sqrt(t):
    """把「asin√(u)」这类写法补全成「asin(sqrt(u))」。"""
    pat = re.compile(r"(asin|acos|atan|log|sin|cos|tan|exp|sqrt)(sqrt\()")
    while True:
        m = pat.search(t)
        if not m:
            return t
        i0 = m.start(2)                     # "sqrt(" 的起点
        i = i0 + 4                          # sqrt 的 "("
        depth = 0
        j = -1
        for k in range(i, len(t)):
            if t[k] == "(":
                depth += 1
            elif t[k] == ")":
                depth -= 1
                if depth == 0:
                    j = k
                    break
        if j < 0:
            return t
        t = t[:m.start(1)] + m.group(1) + "(" + t[i0:j + 1] + ")" + t[j + 1:]


def _canon(s):
    """规范化后的字符串形式（去掉空白），用于识别「只是写法不同、公式一模一样」。"""
    return re.sub(r"\s+", "", to_expr(s))


def parse(s):
    t = to_expr(s)
    if "=" in t:
        raise ValueError("含等号（多参数问答），非单一表达式")
    expr = sp.sympify(t, locals=LOCAL, rational=True)
    return expr


def equivalent(k, a):
    """判定 k 与 a 是否等价：精确化简 → 数值近似（容差 0.2%）→ 抽样比对。

    返回 (True/False/None, 说明)；None 表示数值上无法判定（例如含 asin 的定义域限制）。
    """
    d = sp.simplify(k - a)
    if d == 0:
        return True, "符号化简为 0"
    if not d.free_symbols:
        try:
            av = complex(a.evalf())
            dv = abs(complex(d.evalf()))
        except Exception:
            return None, "无法数值化：%s" % d
        if dv <= 2e-3 * max(1.0, abs(av)):
            return True, "数值近似（差 %s，在容差内）" % dv
        return False, "常数差 = %s" % d
    syms = sorted(d.free_symbols, key=lambda z: z.name)
    n_ok = 0
    for _ in range(24):
        den = random.choice([1, 2, 3, 4, 5])
        num = random.choice([i for i in range(-7, 8) if i != 0])
        subs = {z: sp.Rational(num, den) for z in syms}
        try:
            v = complex(d.subs(subs).evalf(30))
        except Exception:
            continue
        if abs(v.imag) > 1e-9:
            continue                      # 落在定义域外（出现复数），不计入
        if abs(v.real) > 1e-6:            # 高精度求值下仍不相等才算真不等价
            return False, "抽样 %s 处差 = %s" % (subs, v.real)
        n_ok += 1
    if n_ok >= 3:
        return True, "抽样 %d 点一致（化简未归零）" % n_ok
    return None, "定义域限制，数值抽样不成立（%d 点）" % n_ok


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "bank.json")
    bank = json.loads(path.read_text(encoding="utf-8"))
    bad, skipped, n_pass = [], [], 0
    for P in bank["papers"]:
        for q in P["qs"]:
            if not (q.get("accept") and q.get("key")):
                continue
            tag = "%s 第%s题（%s）" % (P["name"], q["n"], q.get("src", ""))
            try:
                key = parse(q["key"])
            except Exception as exc:
                skipped.append("%s：key 非单一表达式（%s）" % (tag, exc))
                continue
            for a in q["accept"]:
                if _canon(a) == _canon(q["key"]):
                    n_pass += 1
                    continue
                try:
                    alias = parse(a)
                except Exception as exc:
                    skipped.append("%s：写法「%s」无法解析（%s）" % (tag, a, exc))
                    continue
                same, why = equivalent(key, alias)
                if same is True:
                    n_pass += 1
                elif same is False:
                    bad.append("%s：写法「%s」与 key「%s」不等价 —— %s" % (tag, a, q["key"], why))
                else:
                    skipped.append("%s：写法「%s」数值上无法判定（%s）" % (tag, a, why))
    print("=" * 60)
    print("写法等价性核验：通过 %d 条，不等价 %d 条，跳过 %d 条" % (n_pass, len(bad), len(skipped)))
    if max(len(bad), len(skipped)):
        print("-" * 60)
    for b in bad:
        print("  ✘ " + b)
    for s in skipped:
        print("  · 跳过 " + s)
    print("=" * 60)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

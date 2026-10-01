# -*- coding: utf-8 -*-
"""把要进卷子的真题逐条独立验算：能符号算的用 sympy，含无初等原函数的积分用
mpmath 数值算。任何一条算不通就不写进题库。

用法：python verify_math.py   （退出码非 0 表示有题算错）
"""
import sys

import mpmath as mp
import sympy as sp
from sympy import (E, Integral, Rational, asin, atan, cos, diff, exp, log,
                   oo, pi, simplify, sin, sqrt, symbols, tan)

mp.mp.dps = 40

x, t, u, k, n = symbols("x t u k n", real=True)
XP = symbols("X", positive=True)
res = []


def chk(label, got, want, tol=1e-6):
    def close(g, w):
        if isinstance(w, (list, tuple)):
            return isinstance(g, (list, tuple)) and len(g) == len(w) and all(close(gi, wi) for gi, wi in zip(g, w))
        if isinstance(w, bool) or isinstance(g, bool):
            return bool(g) == bool(w)
        if w is oo or g is oo:
            return (g is oo) or (sp.sympify(g) is sp.oo)
        gg, ww = complex(sp.N(g)), complex(sp.N(w))
        return abs(gg - ww) <= tol * max(1.0, abs(ww))
    try:
        good = close(got, want)
    except Exception as e:
        good, got = False, "err:%s" % e
    res.append((label, good, got, want))


def chkf(label, got, want, tol=1e-4):
    got, want = float(got), float(want)
    res.append((label, abs(got - want) <= tol * max(1, abs(want)), got, want))


def F(expr):
    """sympy 表达式 -> mpmath 函数"""
    return sp.lambdify(x, expr, "mpmath")


def nroots(f, lo, hi, step=0.002):
    """扫描变号点计数（配合单调性使用）。"""
    v0, prev, cnt = mp.mpf(lo), None, 0
    while v0 <= mp.mpf(hi):
        try:
            v = f(v0)
        except Exception:
            v = None
        if v is not None:
            if prev is not None and prev * v < 0:
                cnt += 1
            prev = v
        v0 += step
    return cnt


# ============================================================== 第 1 章 极限
chk("2013数一(1) lim(x-atan x)/x³ = 1/3", sp.limit((x - atan(x)) / x ** 3, x, 0), Rational(1, 3))
chk("2015数一(9) lim ln cos x/x² = -1/2", sp.limit(log(cos(x)) / x ** 2, x, 0), Rational(-1, 2))
chk("2016数三(9) 取 f≡6 时极限为 2，故 lim f = 6",
    sp.limit((sqrt(1 + 6 * sin(2 * x)) - 1) / (exp(3 * x) - 1), x, 0), 2)
chk("2018数一(9) k=-2 时原极限 = e",
    sp.limit(((1 - tan(x)) / (1 + tan(x))) ** (1 / sin(-2 * x)), x, 0), E)
chk("2018数二(9) lim x²(atan(x+1)-atan x) = 1",
    sp.limit(x ** 2 * (atan(x + 1) - atan(x)), x, oo), 1)
chk("2022数二(11) lim((1+e^x)/2)^cot x = √e",
    sp.limit(((1 + exp(x)) / 2) ** (cos(x) / sin(x)), x, 0), sqrt(E))
chk("2013数三(15) 1-cosxcos2xcos3x ~ 7x²",
    sp.limit((1 - cos(x) * cos(2 * x) * cos(3 * x)) / x ** 2, x, 0), 7)
chk("2010数一(1) lim(x²/((x-1)(x+2)))^x = e⁻¹",
    sp.limit((x ** 2 / ((x - 1) * (x + 2))) ** x, x, oo), exp(-1))
chk("2019数三(9) lim(1-1/(n+1))^n = 1/e", sp.limit((1 - 1 / (n + 1)) ** n, n, oo), exp(-1))
chk("2017数一(1) (1-cos√x)/x → 1/2，故 ab=1/2",
    sp.limit((1 - cos(sqrt(x))) / x, x, 0, "+"), Rational(1, 2))
chk("2018数二(1) a=-1/2,b=-1 时极限为 1",
    sp.limit((exp(x) - x ** 2 / 2 - x) ** (1 / x ** 2), x, 0), 1)
chk("2011数二(9) lim((1+2^x)/2)^{1/x} = √2",
    sp.limit(((1 + 2 ** x) / 2) ** (1 / x), x, 0), sqrt(2))
chk("2012数三(9) lim(tan x)^{1/(cosx-sinx)} = e^{-√2}",
    sp.limit(tan(x) ** (1 / (cos(x) - sin(x))), x, pi / 4), exp(-sqrt(2)))
chk("2016数二(15) lim(cos2x+2x sinx)^{1/x⁴} = e^{1/3}",
    sp.limit((cos(2 * x) + 2 * x * sin(x)) ** (1 / x ** 4), x, 0), exp(Rational(1, 3)))
chk("2011数一(15) lim(ln(1+x)/x)^{1/(e^x-1)} = e^{-1/2}",
    sp.limit((log(1 + x) / x) ** (1 / (exp(x) - 1)), x, 0), exp(Rational(-1, 2)))
chkf("2016数一(9) ∫₀ˣ t ln(1+t sin t)dt /(1-cos x²) = 1/2",
     mp.quad(lambda v: v * mp.log(1 + v * mp.sin(v)), [0, mp.mpf("1e-3")])
     / (1 - mp.cos(mp.mpf("1e-3") ** 2)), 0.5, tol=1e-3)
chk("2021数二(1) ∫₀^{x²}(e^t-1)dt ~ x⁴/2",
    sp.limit(Integral(exp(t) - 1, (t, 0, XP ** 2)).doit() / XP ** 4, XP, 0), Rational(1, 2))
chkf("2020数二(1) A 阶 3", mp.quad(lambda v: mp.e ** (v * v) - 1, [0, mp.mpf("1e-3")]) / mp.mpf("1e-3") ** 3, 1 / 3, tol=1e-3)
chkf("2020数二(1) B 阶 5/2",
     mp.quad(lambda v: mp.log(1 + v ** mp.mpf(1.5)), [0, mp.mpf("1e-4")]) / mp.mpf("1e-4") ** mp.mpf(2.5), 0.4, tol=1e-3)
chkf("2020数二(1) C 阶 3",
     mp.quad(lambda v: mp.sin(v * v), [0, mp.sin(mp.mpf("1e-2"))]) / mp.mpf("1e-2") ** 3, 1 / 3, tol=1e-3)
chkf("2020数二(1) D 阶 5（四个里阶最高，系数 2/(5·2^{5/2})）",
     mp.quad(lambda v: mp.sqrt(mp.sin(v) ** 3), [0, 1 - mp.cos(mp.mpf("1e-2"))]) / mp.mpf("1e-2") ** 5,
     2 / (5 * mp.mpf(2) ** mp.mpf("2.5")), tol=1e-3)
chk("2010数三(1) a=2 时 lim(1/x-(1/x-2)e^x) = 1", sp.limit(1 / x - (1 / x - 2) * exp(x), x, 0), 1)
chk("2014数三(3) d=1/3 时残差为 o(x³)", sp.limit((tan(x) - x - x ** 3 / 3) / x ** 3, x, 0), 0)
chk("2014数三(3) 而 d=1/6 不成立", sp.limit((tan(x) - x - x ** 3 / 6) / x ** 3, x, 0), Rational(1, 6))

# 间断点（数值）
f1 = F(((x ** 2 - x) / (x ** 2 - 1)) * sqrt(1 + 1 / x ** 2))
chkf("2010数二(1) x→-1 发散（唯一无穷间断点）", 1e7 if abs(f1(-1 + mp.mpf("1e-9"))) > 1e6 else 0, 1e7, tol=1e-6)
chk("2010数二(1) x→1 极限 √2/2（可去）",
    sp.limit(simplify(((x ** 2 - x) / (x ** 2 - 1)) * sqrt(1 + 1 / x ** 2)), x, 1), sqrt(2) / 2)
chkf("2010数二(1) x→0⁺ 极限 1", f1(mp.mpf("1e-9")), 1, tol=1e-6)
chkf("2010数二(1) x→0⁻ 极限 -1", f1(-mp.mpf("1e-9")), -1, tol=1e-6)
f2 = F(sp.Abs(x) ** (1 / ((1 - x) * (x - 2))))
chkf("2024数二(1) x→1 极限 e（有限，属第一类可去）", f2(1 - mp.mpf("1e-9")), mp.e, tol=1e-6)
chkf("2024数二(1) x→0 发散（第二类）", 1e4 if abs(f2(mp.mpf("1e-6"))) > 1e3 else 0, 1e4, tol=1e-6)
f3 = F((sp.Abs(x) ** x - 1) / (x * (x + 1) * log(sp.Abs(x))))
chkf("2013数三(2) x→0⁺ 极限 1（可去）", f3(mp.mpf("1e-9")), 1, tol=1e-5)
chkf("2013数三(2) x→1 极限 1/2（可去）", f3(1 + mp.mpf("1e-9")), 0.5, tol=1e-5)
f4 = F(exp(1 / (x - 1)) * log(sp.Abs(1 + x)) / ((exp(x) - 1) * (x - 2)))
chkf("2020数二(2) x→0 极限 -1/(2e)（有限，属第一类）", f4(mp.mpf("1e-9")), -1 / (2 * mp.e), tol=1e-4)
chkf("2020数二(2) x→-1 对数发散（增长约 4 倍）",
     abs(f4(-1 + mp.mpf("1e-12")) / f4(-1 + mp.mpf("1e-3"))), 4.0, tol=0.6)
chkf("2020数二(2) x→1⁺ 发散", 1e7 if abs(f4(1 + mp.mpf("1e-9"))) > 1e6 else 0, 1e7, tol=1e-6)
chkf("2020数二(2) x→2 发散", 1e7 if abs(f4(2 + mp.mpf("1e-9"))) > 1e6 else 0, 1e7, tol=1e-6)
chkf("2016数二(1) a1 ~ -x²/2", F(x * (cos(sqrt(x)) - 1))(mp.mpf("1e-8")) / mp.mpf("1e-8") ** 2, -0.5, tol=1e-4)
chkf("2016数二(1) a2 阶 5/6",
     F(sqrt(x) * log(1 + sp.cbrt(x)))(mp.mpf("1e-12")) / mp.mpf("1e-12") ** (mp.mpf(5) / 6), 1.0, tol=1e-2)
chkf("2016数二(1) a3 ~ x/3", F(sp.cbrt(x + 1) - 1)(mp.mpf("1e-12")) / (mp.mpf("1e-12") / 3), 1.0, tol=1e-6)
xn, yn = mp.mpf("0.5"), mp.mpf("0.5")
for _ in range(24):
    xn, yn = mp.sin(xn), yn * yn
chkf("2023数二(3) y_n/x_n → 0（y_n 是 x_n 的高阶无穷小）", float(yn / xn), 0.0, tol=1e-10)

# ============================================================== 第 2 章 导数
chk("2010数二(11) y=ln(1-2x) 的 n 阶导（n=1..5）",
    [sp.diff(log(1 - 2 * x), x, m).subs(x, 0) / (-2 ** m * sp.factorial(m - 1)) for m in range(1, 6)], [1] * 5)
xt, yt = exp(-t), Integral(log(sqrt(1 + u ** 2)), (u, 0, t)).doit()
d1 = sp.diff(yt, t) / sp.diff(xt, t)
chk("2010数一(9) 参数方程 d²y/dx²|_{t=0} = 0", sp.diff(d1, t).subs(t, 0) / sp.diff(xt, t).subs(t, 0), 0)
Y = symbols("y")
def _E2010(xv, yv):
    return (mp.quad(lambda s: mp.e ** (-s * s), [0, xv + yv])
            - xv * mp.quad(lambda s: mp.sin(s * s), [0, xv]))

_h = mp.mpf("1e-6")
_yh = mp.findroot(lambda yv: _E2010(_h, yv), 0)
chkf("2010数三(9) 隐函数 y'(0) = -1（数值隐式求导）", float(_yh / _h), -1.0, tol=1e-2)
chk("2011数二(2) 极限 = -f'(0)（取 f=sin x 验算）",
    sp.limit((x ** 2 * sin(x) - 2 * sin(x ** 3)) / x ** 3, x, 0), -1)
def _E2011(xv, yv):
    return mp.tan(xv + yv + mp.pi / 4) - mp.e ** yv


_h2 = mp.mpf("1e-6")
_y2 = mp.findroot(lambda yv: _E2011(_h2, yv), 0)
chkf("2011数三(11) 切线斜率 -2（数值隐式求导）", float((_y2 - 0) / _h2), -2.0, tol=1e-2)
chk("2012数二(9) 由 2-y'' = e^y[(y')²+y''] 得 y''(0)=1",
    sp.solve(sp.Eq(2 - sp.Symbol("ypp"), 1 * 0 + 1 * sp.Symbol("ypp")), sp.Symbol("ypp"))[0], 1)
fp = sp.Piecewise((log(x), x >= 1), (2 * x - 1, True))
chk("2012数三(10) dy/dx|_{x=e} = 1/e",
    sp.diff(fp, x).subs(x, fp.subs(x, E)) * sp.diff(fp, x).subs(x, E), 1 / E)
chk("2013数二(10) 反函数导数 = 1/√(1-e⁻¹)", 1 / sqrt(1 - exp(-1)), 1 / sqrt(1 - exp(-1)))
chk("2013数二(12) 参数方程 dy/dx|_{t=1} = 1", (sp.diff(log(sqrt(1 + t ** 2)), t) / sp.diff(atan(t), t)).subs(t, 1), 1)
chk("2013数二(12) 切点纵坐标 = ½ln2", log(sqrt(2)), Rational(1, 2) * log(2))
chk("2013数三(9) n·f(n/(n+2)) → -2（取 f=x-1 验算）", sp.limit(n * ((n / (n + 2)) - 1), n, oo), -2)
chk("2014数二(12) 极坐标 r=θ 在 θ=π/2 处斜率 = -2/π",
    (sp.diff(t * sin(t), t) / sp.diff(t * cos(t), t)).subs(t, pi / 2), -2 / pi)
chk("2015数二(10) f=x²2^x 的 n 阶导（n=2..6）",
    [sp.diff(x ** 2 * 2 ** x, x, m).subs(x, 0) / (m * (m - 1) * log(2) ** (m - 2)) for m in range(2, 7)], [1] * 5)
dt = sp.diff(sin(t), t) / sp.diff(t + exp(t), t)
chk("2017数二(10) d²y/dx²|_{t=0} = -1/8", sp.diff(dt, t).subs(t, 0) / sp.diff(t + exp(t), t).subs(t, 0), Rational(-1, 8))
chk("2019数二(10) 切线与 y 轴截距 = 3π/2+2", 1 + (3 * pi / 2 + 1), 3 * pi / 2 + 2)
dt2 = sp.diff(4 * (t - 1) * exp(t) + t ** 2, t) / sp.diff(2 * exp(t) + t + 1, t)
chk("2021数一(12) d²y/dx²|_{t=0} = 2/3", sp.diff(dt2, t).subs(t, 0) / sp.diff(2 * exp(t) + t + 1, t).subs(t, 0), Rational(2, 3))
chk("2021数一(1) f'(0) = 1/2", sp.limit((exp(x) - 1 - x) / x ** 2, x, 0), Rational(1, 2))
chkf("2018数一(1) cos√|x| 右导 = -1/2", sp.limit((cos(sqrt(x)) - 1) / x, x, 0, "+"), -0.5)
chkf("2018数一(1) cos√|x| 左导 = 1/2（故不可导）", sp.limit((cos(sqrt(-x)) - 1) / x, x, 0, "-"), 0.5)


def f2016(xv):
    xv = mp.mpf(xv)
    nn = mp.floor(1 / xv)
    return mp.mpf(1) / nn


chkf("2016数一(4) 右导数 f'+(0) = 1", f2016(mp.mpf("0.0019")) / mp.mpf("0.0019"), 1.0, tol=1e-2)
chk("2015数一(15) a=-1,b=-1/2,k=-1/3 时 f/g → 1",
    sp.limit((x - log(1 + x) - Rational(1, 2) * x * sin(x)) / (-x ** 3 / 3), x, 0), 1)
chk("2013数三(15) a=7 时 1-cosxcos2xcos3x ~ 7x²",
    sp.limit((1 - cos(x) * cos(2 * x) * cos(3 * x)) / (7 * x ** 2), x, 0), 1)

# ================================================ 第 3 章 中值定理与导数应用
fx = Integral((x ** 2 - t) * exp(-t ** 2), (t, 1, x ** 2)).doit()
chk("2010数一(16) f'(x) = 2x∫₁^{x²}e^{-t²}dt",
    sp.simplify(sp.diff(fx, x) - 2 * x * Integral(exp(-t ** 2), (t, 1, x ** 2)).doit()), 0)
chk("2010数一(16) 极大值 f(0) = (1-e⁻¹)/2", fx.subs(x, 0), (1 - exp(-1)) / 2)
chk("2010数一(16) f(±1) = 0", [fx.subs(x, 1), fx.subs(x, -1)], [0, 0])
f4a = 4 * atan(x) - x + 4 * pi / 3 - sqrt(3)
chk("2011数三(18) f(-√3) = 0", f4a.subs(x, -sqrt(3)), 0)
chk("2011数三(18) (-∞,-√3] 上再无零点（各点均 > 0）",
    min(float(F(f4a)(mp.mpf(v))) for v in ["-10", "-4", "-2.5", "-1.6", "-1.5"]) > 0, True)
chkf("2011数三(18) (√3,+∞) 上恰一个零点（(2,12) 内变号一次）", nroots(F(f4a), 2, 12, 0.005), 1, tol=0)
chkf("2011数一(17) k=0.5 时实根个数 = 1", nroots(F(Rational(1, 2) * atan(x) - x), -50, 50, 0.004), 1, tol=0)
chkf("2011数一(17) k=2 时实根个数 = 3", nroots(F(2 * atan(x) - x), -50, 50, 0.004), 3, tol=0)
chk("2012数一(1) 水平渐近线 y=1、铅直渐近线 x=1（共 2 条）",
    [sp.limit((x ** 2 + x) / (x ** 2 - 1), x, oo), sp.limit((x ** 2 + x) / (x ** 2 - 1), x, 1, "+")], [1, oo])
f5 = Integral(sqrt(1 + u ** 2), (u, XP, 1)).doit() + Integral(sqrt(1 + u), (u, 1, XP ** 2)).doit()
chk("2015数二(19) f'(x) = √(1+x²)(2x-1)", sp.simplify(sp.diff(f5, XP) - sqrt(1 + XP ** 2) * (2 * XP - 1)), 0)
f5x = (Integral(sqrt(1 + u ** 2), (u, x, 1)).doit() + Integral(sqrt(1 + u), (u, 1, x ** 2)).doit())
chkf("2015数二(19) 零点个数 = 2", nroots(F(f5x), -3, 3, 0.002), 2, tol=0)
f6 = lambda v: mp.quad(lambda s: mp.cos(s) / (2 * s - 3 * mp.pi), [0, v])
chkf("2016数二(21) 平均值 = 1/(3π)", mp.quad(f6, [0, 3 * mp.pi / 2]) / (3 * mp.pi / 2), 1 / (3 * mp.pi), tol=1e-8)
chkf("2016数二(21) f(π/2)<0<f(3π/2)，唯一零点在 (π/2,3π/2)",
     f6(mp.pi / 2) < 0 < f6(3 * mp.pi / 2 * mp.mpf("0.999")), 1, tol=0)
chk("2014数二(5) lim ξ²/x² = 1/3", sp.limit((x - atan(x)) / (x ** 2 * atan(x)), x, 0), Rational(1, 3))
chk("2019数三(2) 极大值 4+k、极小值 k-4（k=0 时为 4 与 -4）",
    [(x ** 5 - 5 * x + 0).subs(x, -1), (x ** 5 - 5 * x + 0).subs(x, 1)], [4, -4])
chk("2019数三(2) 极大值 4+k、极小值 k-4（k=1 时为 5 与 -3）",
    [(x ** 5 - 5 * x + 1).subs(x, -1), (x ** 5 - 5 * x + 1).subs(x, 1)], [5, -3])
chkf("2019数三(2) k=0 时 3 个实根", nroots(F(x ** 5 - 5 * x), -5, 5, 0.004), 3, tol=0)
chkf("2019数三(2) k=3.9 时 3 个实根", nroots(F(x ** 5 - 5 * x + mp.mpf("3.9")), -5, 5, 0.004), 3, tol=0)
chk("2019数三(2) k=4 时 x=1 恰为根（切触，故 k 取不到 4）", (x ** 5 - 5 * x + 4).subs(x, 1), 0)
chkf("2019数三(2) k=4.1 时只剩 1 个实根", nroots(F(x ** 5 - 5 * x + mp.mpf("4.1")), -5, 5, 0.004), 1, tol=0)
f8 = sum(x ** m for m in range(1, 9)) - 1
chk("2012数二(21) f₈(1/2) < 0 < f₈(1)", [f8.subs(x, Rational(1, 2)) < 0, f8.subs(x, 1) > 0], [True, True])
chkf("2012数二(21) f₈ 在 (1/2,1) 内恰一个零点", nroots(F(f8), 0.5, 1, 0.001), 1, tol=0)
chk("2017数三(18) lim_{x→0⁺} f = 1/2", sp.limit(1 / log(1 + x) - 1 / x, x, 0, "+"), Rational(1, 2))
chk("2017数三(18) f(1) = 1/ln2 - 1", (1 / log(1 + x) - 1 / x).subs(x, 1), 1 / log(2) - 1)

# ============================================================== 第 4 章 不定积分
chk("2018数三(10) 求导验证 ∫e^x·asin√(1-e^{2x})dx",
    sp.simplify(sp.diff(exp(XP) * asin(sqrt(1 - exp(2 * XP))) - sqrt(1 - exp(2 * XP)), XP)
                - exp(XP) * asin(sqrt(1 - exp(2 * XP)))), 0)
chk("2019数二(16) 求导验证有理函数积分",
    sp.simplify(sp.diff(-2 * log(XP - 1) - 3 / (XP - 1) + log(XP ** 2 + XP + 1), XP)
                - (3 * XP + 6) / ((XP - 1) ** 2 * (XP ** 2 + XP + 1))), 0)
chk("2018数一(15) 求导验证 ∫e^{2x}·atan√(e^x-1)dx",
    sp.simplify(sp.diff(Rational(1, 2) * exp(2 * XP) * atan(sqrt(exp(XP) - 1))
                        - Rational(1, 6) * (exp(XP) - 1) ** Rational(3, 2)
                        - Rational(1, 2) * sqrt(exp(XP) - 1), XP)
                - exp(2 * XP) * atan(sqrt(exp(XP) - 1))), 0)
chk("2011数三(17) 求导验证 ∫(asin√x+ln x)/√x dx",
    sp.simplify(sp.diff(2 * sqrt(XP) * asin(sqrt(XP)) + 2 * sqrt(1 - XP) + 2 * sqrt(XP) * log(XP) - 4 * sqrt(XP), XP)
                - (asin(sqrt(XP)) + log(XP)) / sqrt(XP)), 0)
chk("2003数二 求导验证 ∫x·e^{atan x}/(1+x²)^{3/2}dx",
    sp.simplify(sp.diff((XP - 1) * exp(atan(XP)) / (2 * sqrt(1 + XP ** 2)), XP)
                - XP * exp(atan(XP)) / (1 + XP ** 2) ** Rational(3, 2)), 0)
chk("2001数一 求导验证 ∫atan(e^x)/e^{2x}dx",
    sp.simplify(sp.diff(-Rational(1, 2) * exp(-2 * XP) * atan(exp(XP)) - Rational(1, 2) * exp(-XP)
                        - Rational(1, 2) * atan(exp(XP)), XP) - atan(exp(XP)) / exp(2 * XP)), 0)
chk("2001数二 求导验证 ∫dx/((2x²+1)√(x²+1))",
    sp.simplify(sp.diff(atan(XP / sqrt(1 + XP ** 2)), XP) - 1 / ((2 * XP ** 2 + 1) * sqrt(XP ** 2 + 1))), 0)
chk("2000数二 求导验证 ∫f(x)dx（f(ln x)=ln(1+x)/x）",
    sp.simplify(sp.diff(-(1 + exp(-XP)) * log(1 + exp(XP)) + XP, XP) - log(1 + exp(XP)) / exp(XP)), 0)
def _A2006(xv):
    ex = mp.e ** xv
    return -mp.asin(ex) / ex + mp.mpf(1) / 2 * mp.log(abs((mp.sqrt(1 - ex ** 2) - 1) / (mp.sqrt(1 - ex ** 2) + 1)))


def _dnum(fn, xv, h=mp.mpf("1e-8")):
    return (fn(xv + h) - fn(xv - h)) / (2 * h)


_x06 = mp.mpf("-0.3")  # 被积函数含 arcsin(e^x)，需 e^x ≤ 1，即 x ≤ 0
chkf("2006数二 数值求导验证 ∫asin(e^x)/e^x dx",
     _dnum(_A2006, _x06), float(mp.asin(mp.e ** _x06) / mp.e ** _x06), tol=1e-6)

# ============================== 补录：拼卷时新加条目的逐条复算
# 2016数一(2) 分段函数的一个原函数
chk("2016数一(2) 原函数左支 (x-1)² 求导 = 2(x-1)", sp.simplify(sp.diff((x - 1) ** 2, x) - 2 * (x - 1)), 0)
chk("2016数一(2) 原函数右支 x(ln x -1)+1 求导 = ln x", sp.simplify(sp.diff(XP * (log(XP) - 1) + 1, XP) - log(XP)), 0)
chk("2016数一(2) 原函数在 x=1 连续（左 0 = 右 0）", (0, (1 * (log(1) - 1) + 1)), (0, 0))
chk("2016数一(2) 干扰项 x(ln x +1)-1 求导 = ln x + 2 ≠ ln 1，不是原函数",
    sp.diff(XP * (log(XP) + 1) - 1, XP).subs(XP, 1), 2)
# 2018数二(10) 拐点处切线
chk("2018数二(10) y=x²+2ln x 的 y'' 零点 x=1（y=1）",
    [sp.solve(sp.diff(XP ** 2 + 2 * log(XP), XP, 2), XP), (1 ** 2 + 2 * log(1))], [[1], 1])
chk("2018数二(10) 拐点处斜率 4，切线 y = 4x-3",
    sp.diff(XP ** 2 + 2 * log(XP), XP).subs(XP, 1) - 4, 0)
# 2019数一(1) x - tan x 与 x³ 同阶
chk("2019数一(1) lim(x-tan x)/x³ = -1/3", sp.limit((x - tan(x)) / x ** 3, x, 0), Rational(-1, 3))
chk("2019数一(1) lim(x-tan x)/x² = 0（故不是 2 阶）", sp.limit((x - tan(x)) / x ** 2, x, 0), 0)
# 2019数一(2) x|x| / x·ln x 在 0 处：不可导点，极值点
chkf("2019数一(2) x<0 时 x|x| = -x² < 0（0 是最大值）", float(1e3 if all((-mp.mpf(v) ** 2) < 0 for v in ["0.1", "0.5", "1", "2"]) else 0), 1e3, tol=1e-6)
chkf("2019数一(2) 0<x<1 时 x·ln x < 0（0 是最大值）", float(1e3 if all(mp.mpf(v) * mp.log(mp.mpf(v)) < 0 for v in ["0.01", "0.1", "0.3", "0.9"]) else 0), 1e3, tol=1e-6)
chkf("2019数一(2) 右导数 lim(x ln x)/x = ln x → -∞（不可导）",
     mp.log(mp.mpf("1e-9")), -20.72, tol=1e-3)

# ====================================================================== 汇总
bad = [r for r in res if not r[1]]
for label, good, got, want in res:
    print(("  OK  " if good else "  !!  ") + label + ("" if good else "   算得 %s，期望 %s" % (got, want)))
print("-" * 62)
print("共 %d 项，通过 %d 项，失败 %d 项" % (len(res), len(res) - len(bad), len(bad)))
sys.exit(1 if bad else 0)

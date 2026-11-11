#!/usr/bin/env python3
"""Tolerance-aware EM-in-the-loop polish: start from emopt build values, minimise
0.3*nominal + 0.7*75th-percentile cost over fixed tolerance samples (C<5pF: +-0.05 pF 'W' grade; L: +-0.1 nH 'B' grade),
min capacitor 0.8 pF. Then snap to purchasable values and report MC.  Usage: python3 em_robust.py NAME"""
import os, sys, json
import numpy as np
from scipy.optimize import minimize
import filter_em as E, em_opt as O
F = E.F
name = sys.argv[1]
spec, types, f, s2 = O.make(name)
d = os.path.join(E.OUT, name)
x0 = np.array(json.load(open(os.path.join(d, "emopt_s1.json")))["vals_best"])
lo = np.array([0.8 if t == "C" else 0.5 for t in types]); hi = np.array([12.0 if t == "C" else 15.0 for t in types])
x0 = np.clip(x0, lo, hi)
rng = np.random.default_rng(3); NS = 12
P = [np.array([rng.uniform(-1, 1) for _ in types]) for _ in range(NS)]
def pert(x, p):
    y = x.copy()
    for i, t in enumerate(types):
        if t == "C": y[i] += 0.05 * p[i] if y[i] < 5 else y[i] * 0.02 * p[i]
        else: y[i] += 0.1 * p[i] if y[i] < 6 else y[i] * 0.02 * p[i]
    return y
cost = lambda x: E.mask_cost(spec, f, s2(x))
def rc(u):
    x = np.clip(10 ** u, lo, hi)
    cs = [cost(pert(x, p)) for p in P]
    return 0.3 * cost(x) + 0.7 * np.percentile(cs, 75)
r = minimize(rc, np.log10(x0), method="Nelder-Mead", options=dict(maxiter=2500, xatol=1e-4, fatol=1e-5, adaptive=True))
xc = np.clip(10 ** r.x, lo, hi)
xs = F.snap(spec["topo"], xc); xs = np.maximum(xs, lo)
best = rc(np.log10(xs))
for rnd in range(3):
    imp = False
    for i, t in enumerate(types):
        ser = F.L_SER if t == "L" else [c for c in F.C_SER if c >= 0.8]
        k = ser.index(min(ser, key=lambda q: abs(q - xs[i])))
        for kk in range(max(0, k - 2), min(len(ser), k + 3)):
            tr = xs.copy(); tr[i] = ser[kk]; c = rc(np.log10(tr))
            if c < best - 1e-9: best, xs, imp = c, tr, True
    if not imp: break
rng2 = np.random.default_rng(11); mcs = []
for _ in range(400):
    p = np.array([rng2.uniform(-1, 1) for _ in types]); mcs.append(E.mask_metrics(spec, f, s2(pert(xs, p))))
m = E.mask_metrics(spec, f, s2(xs))
L = [f"## {name}: tolerance-aware EM optimisation (W-grade caps +-0.05 pF, B-grade L +-0.1 nH)\n", "| El | build |", "|---|---|"]
L += [f"| {t}{i+1} | **{v:g} {'nH' if t == 'L' else 'pF'}** |" for i, (t, v) in enumerate(zip(types, xs))]
L.append("\n| Metric | EM build | MC 400 (5th pct worst) | MC median |\n|---|---|---|---|")
for k in m:
    v = np.array([q[k] for q in mcs]); w = np.percentile(v, 95) if k.startswith("IL") else np.percentile(v, 5)
    L.append(f"| {k} | {m[k]:.2f} | {w:.2f} | {np.median(v):.2f} |")
open(os.path.join(d, "EMROBUST.md"), "w").write("\n".join(L) + "\n")
S2 = s2(xs)
json.dump(dict(f=list(map(float, f)), s21_best=list(map(float, np.abs(S2[:, 1, 0]))), s11_best=list(map(float, np.abs(S2[:, 0, 0]))),
               vals_best=list(map(float, xs))), open(os.path.join(d, "emrobust.json"), "w"))
print("\n".join(L))

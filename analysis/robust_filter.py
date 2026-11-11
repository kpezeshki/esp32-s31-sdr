#!/usr/bin/env python3
"""Tolerance-aware polish of a lumped filter from filters.py: cost = mean over fixed tolerance samples.
Usage: python3 robust_filter.py NAME START_JSON [--if=30]"""
import sys, json, os
import numpy as np
from scipy.optimize import minimize
import filters as F

name, start = sys.argv[1], sys.argv[2]
spec = dict(F.FILTERS[name])
for a in sys.argv[3:]:
    if a.startswith("--if="):
        v = float(a.split("=")[1])
        spec["mask"] = [(k, lo, hi, (v if (k == "stop" and lo == 2.40e9) else lim)) for k, lo, hi, lim in spec["mask"]]
topo = spec["topo"]; ts = F.types_of(topo)
cost, _ = F.make_cost(spec)
rng = np.random.default_rng(11)
NS = 16
P = []
for _ in range(NS):
    P.append([(rng.uniform(-0.1, 0.1), rng.uniform(-0.03, 0.03)) if t == "L" else (rng.uniform(-0.05, 0.05), rng.uniform(-0.02, 0.02)) for t in ts])

def perturb(x, p):
    y = np.array(x, float)
    for i, t in enumerate(ts):
        a, r = p[i]
        if t == "L": y[i] += a if y[i] < 3.9 else y[i] * r
        else:        y[i] += a if y[i] < 5 else y[i] * r
    return y

def rcost(x):
    x = np.asarray(x)
    cs = [cost(perturb(x, p)) for p in P]
    return 0.3 * cost(x) + 0.7 * np.percentile(cs, 75)

x0 = np.array(json.load(open(start))["x"])
b = F.bounds_for(topo)
best = None
for trial in range(3):
    xs = x0 if trial == 0 else x0 * (1 + 0.05 * rng.standard_normal(len(x0)))
    r = minimize(lambda u: rcost(np.clip(10 ** u, [a for a, _ in b], [c for _, c in b])), np.log10(xs),
                 method="Nelder-Mead", options=dict(maxiter=6000, xatol=1e-5, fatol=1e-6, adaptive=True))
    xr = np.clip(10 ** r.x, [a for a, _ in b], [c for _, c in b])
    if best is None or r.fun < best[1]:
        best = (xr, r.fun)
x = best[0]
xs, _ = F.refine(topo, F.snap(topo, x), rcost, rounds=3)
xr = F.reduce_palette(topo, xs, rcost, max_penalty=1.1)
mc = F.monte_carlo(spec, xr, n=1000, seed=5)
m = F.metrics(spec, xr)
out = [f"# Robust (tolerance-aware) {name}, start {os.path.basename(start)}\n", "| # | Elem | Value |", "|---|---|---|"]
for i, (t, v) in enumerate(zip(ts, xr)):
    out.append(f"| {i+1} | {t} | {v:g} {'nH' if t=='L' else 'pF'} |")
out.append(f"\nUnique values: {len(set(zip(ts, xr)))}\n\n| Metric | Nominal | MC 5th pct worst | MC median |\n|---|---|---|---|")
for k in m:
    vals = np.array([d[k] for d in mc])
    w = np.percentile(vals, 95) if k.startswith("IL") else np.percentile(vals, 5)
    out.append(f"| {k} | {m[k]:.2f} | {w:.2f} | {np.median(vals):.2f} |")
tag = os.path.basename(start).replace("_opt.json", "")
open(os.path.join(F.EXP, f"{tag}_robust.md"), "w").write("\n".join(out) + "\n")
json.dump(dict(x=list(map(float, xr))), open(os.path.join(F.EXP, f"{tag}_robust.json"), "w"))
print("\n".join(out))

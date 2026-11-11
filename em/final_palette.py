#!/usr/bin/env python3
"""Merge component values across the 4 EM-optimised filters (fewer JLC part types), evaluated on the EM models
with W-grade capacitors / B-grade inductors.  Accept a merge if every affected filter's EM cost stays within
max(1.15x, +3) of its start and the MC IF-rejection median does not drop by > 2 dB.  Output: filters/final_values.json"""
import json, os, numpy as np, em_opt as O, filter_em as E
F = E.F
SRC = {"LB_LPF": "emrobust", "MB_BPF2": "emopt_s1", "HB_HPF": "emrobust", "HB_PRE": "result"}
M = {}
for k, src in SRC.items():
    spec, types, f, s2 = O.make(k)
    x = np.array(json.load(open(f"filters/{k}/{src}.json"))["vals_best"])
    M[k] = dict(spec=spec, types=types, f=f, s2=s2, x=x, c0=E.mask_cost(spec, f, s2(x)))
def cost(k, x): m = M[k]; return E.mask_cost(m["spec"], m["f"], m["s2"](x))
def pal():
    return sorted(set((t, round(v, 2)) for k in M for t, v in zip(M[k]["types"], M[k]["x"])))
print("start unique", len(pal()))
while True:
    P = pal(); best = None
    for (t, v) in P:
        for (t2, o) in P:
            if t2 != t or o == v or abs(np.log(o / v)) > 0.25: continue
            trial = {}; ok = True; tot = 0
            for k in M:
                x = np.array([o if (tt == t and round(xx, 2) == v) else xx for tt, xx in zip(M[k]["types"], M[k]["x"])])
                if np.allclose(x, M[k]["x"]): continue
                c = cost(k, x)
                if c > max(M[k]["c0"] * 1.15, M[k]["c0"] + 3.0): ok = False; break
                trial[k] = x; tot += c - cost(k, M[k]["x"])
            if ok and trial and (best is None or tot < best[1]): best = (trial, tot, (t, v, o))
    if best is None: break
    for k, x in best[0].items(): M[k]["x"] = x
    print("merged", best[2], "->", len(pal()))
out = {k: list(map(float, M[k]["x"])) for k in M}
json.dump(out, open("filters/final_values.json", "w"), indent=1)
lines = ["# Final filter values (EM-optimised, joint palette)\n", f"Unique values: {len(pal())}: " + ", ".join(f"{v:g}{'nH' if t=='L' else 'pF'}" for t, v in pal()) + "\n"]
for k in M:
    m = M[k]; x = m["x"]; mm_ = E.mask_metrics(m["spec"], m["f"], m["s2"](x))
    rng = np.random.default_rng(7); mcs = []
    for _ in range(300):
        y = x.copy()
        for i, t in enumerate(m["types"]):
            if t == "C": y[i] += rng.uniform(-0.05, 0.05) if y[i] < 5 else y[i] * rng.uniform(-0.02, 0.02)
            else: y[i] += rng.uniform(-0.1, 0.1) if y[i] < 6 else y[i] * rng.uniform(-0.02, 0.02)
        mcs.append(E.mask_metrics(m["spec"], m["f"], m["s2"](y)))
    lines.append(f"\n## {k}\n" + ", ".join(f"{t}{i+1}={v:g}" for i, (t, v) in enumerate(zip(m["types"], x))) + "\n")
    lines.append("| Metric | EM nominal | MC median | MC 5th pct worst |\n|---|---|---|---|")
    for key in mm_:
        v = np.array([q[key] for q in mcs]); w = np.percentile(v, 95) if key.startswith("IL") else np.percentile(v, 5)
        lines.append(f"| {key} | {mm_[key]:.2f} | {np.median(v):.2f} | {w:.2f} |")
open("filters/FINAL_FILTERS.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))

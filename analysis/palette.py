#!/usr/bin/env python3
"""Joint palette reduction across all band filters: merge 0402 values shared between filters
to minimize JLC part types, while each filter's (nominal) cost stays within a tolerance of its start.
Final check: Monte-Carlo per filter. Output: export/filter_palette.md, export/filter_palette.json"""
import json, os, itertools
import numpy as np
import filters as F

E = F.EXP
def load(p): return np.array(json.load(open(os.path.join(E, p)))["x"])
HB_BUILD = np.array([1.2, 2.2, 2.3, 0.7, 2.8, 1.2, 0.6, 1.6, 0.7])
FL = {
    "LB_LPF": load("filter_LB_LPF_s1_robust.json"),
    "MB_BPF2": load("filter_MB_BPF2_s2_robust.json"),
    "HB_HPF": HB_BUILD,
    "HB_PRE": np.array([1.6, 2.0, 1.6]),
}
SPEC = {k: F.FILTERS[k] for k in FL}
COST = {k: F.make_cost(SPEC[k])[0] for k in FL}
TS = {k: F.types_of(SPEC[k]["topo"]) for k in FL}
C0 = {k: COST[k](FL[k]) for k in FL}
SLACK = {k: max(C0[k] * 1.25, C0[k] + 8.0) for k in FL}

def palette(sol):
    return sorted(set((t, round(v, 2)) for k in sol for t, v in zip(TS[k], sol[k])))

def refine_in(k, x, pal):
    return F.refine(SPEC[k]["topo"], x, COST[k], palette=pal, rounds=3)

sol = {k: v.copy() for k, v in FL.items()}
print("start unique:", len(palette(sol)), {k: round(C0[k], 1) for k in FL})
while True:
    pal = palette(sol); best = None
    for (t, v) in pal:
        for (t2, o) in pal:
            if t2 != t or o == v or abs(np.log(o / v)) > 0.45:
                continue
            newpal = [p for p in pal if p != (t, v)]
            trial, ok, tot = {}, True, 0.0
            for k in sol:
                x = np.array([o if (tt == t and round(xv, 2) == v) else xv for tt, xv in zip(TS[k], sol[k])])
                if not np.allclose(x, sol[k]):
                    x, c = refine_in(k, x, newpal)
                else:
                    c = COST[k](x)
                if c > SLACK[k]:
                    ok = False; break
                trial[k] = x; tot += c / max(C0[k], 1.0)
            if ok and (best is None or tot < best[1]):
                best = (trial, tot, (t, v, o))
    if best is None:
        break
    sol = best[0]; print("merged", best[2], "-> unique", len(palette(sol)))

out = ["# Joint 0402 palette across band filters (analysis/palette.py)\n",
       f"Unique values: start {len(palette(FL))}, final **{len(palette(sol))}**\n",
       "Palette: " + ", ".join(f"{v:g} {'nH' if t=='L' else 'pF'}" for t, v in palette(sol)) + "\n"]
for k in sol:
    m = F.metrics(SPEC[k], sol[k]); mc = F.monte_carlo(SPEC[k], sol[k], n=600, seed=9)
    out.append(f"\n## {k}\nValues: " + ", ".join(f"{t}{i+1}={v:g}" for i, (t, v) in enumerate(zip(TS[k], sol[k]))) + "\n")
    out.append("| Metric | Nominal | MC 5th pct worst |\n|---|---|---|")
    for key in m:
        vals = np.array([d[key] for d in mc]); w = np.percentile(vals, 95) if key.startswith("IL") else np.percentile(vals, 5)
        out.append(f"| {key} | {m[key]:.2f} | {w:.2f} |")
open(os.path.join(E, "filter_palette.md"), "w").write("\n".join(out) + "\n")
json.dump({k: list(map(float, v)) for k, v in sol.items()}, open(os.path.join(E, "filter_palette.json"), "w"), indent=1)
print("\n".join(out))

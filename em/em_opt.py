#!/usr/bin/env python3
"""Continuous global optimization of filter component values against the Sonnet EM N-port of the layout
(vectorized co-simulation), then snap to purchasable values preferring the joint palette, then Monte-Carlo
on the EM model with real part tolerances (B: +-0.1 pF / +-0.1 nH; C: +-0.2 nH where the LQW15AN part is C-grade).
Usage: python3 em_opt.py NAME [--seed=N]"""
import os, sys, json
import numpy as np
from scipy.optimize import differential_evolution, minimize
import filter_em as E
F = E.F

def zparts(types, vals, w):
    out = []
    for t, v in zip(types, vals):
        out.append(E.z_part(t, v, w))
    return np.array(out)                       # (nparts, nf)

def make(name):
    spec = F.FILTERS[name]; types = F.types_of(spec["topo"])
    d = os.path.join(E.OUT, name); g = json.load(open(os.path.join(d, "geo.json")))
    npts, pm = g["nports"], [tuple(x) for x in g["portmap"]]
    f, S = E.read_touchstone(os.path.join(d, f"{name}.s{npts}p"), npts)
    keep = (f <= 8.0e9)
    keep &= (np.arange(len(f)) % 2 == 0) | ((f > 1.5e9) & (f < 3.3e9))   # thin the grid away from transition bands
    f, S = f[keep], S[keep]
    n = S.shape[1]; I = np.eye(n)
    Y0 = np.linalg.solve(np.transpose(I + S, (0, 2, 1)), np.transpose(I - S, (0, 2, 1)))
    Y0 = np.transpose(Y0, (0, 2, 1)) / 50.0                    # (nf, n, n)
    w = 2 * np.pi * f
    e = [0, 1]; ii = list(range(2, n))
    A = np.zeros((len(pm), n)); 
    for k, (ei, pa, pb) in enumerate(pm):
        A[k, pa - 1] = 1; A[k, pb - 1] = -1
    order = [ei for (ei, pa, pb) in pm]
    def s2(vals):
        y = 1 / zparts([types[o] for o in order], [vals[o] for o in order], w)   # (np, nf)
        Y = Y0 + np.einsum("kn,kf,km->fnm", A, y, A)
        Yee = Y[:, :2, :2]; Yei = Y[:, :2, 2:]; Yie = Y[:, 2:, :2]; Yii = Y[:, 2:, 2:]
        Yr = Yee - Yei @ np.linalg.solve(Yii, Yie)
        Zr = np.linalg.inv(Yr); I2 = np.eye(2) * 50.0
        return (Zr - I2) @ np.linalg.inv(Zr + I2)
    return spec, types, f, s2

def main():
    name = sys.argv[1]
    seed = int([a.split("=")[1] for a in sys.argv if a.startswith("--seed=")][0]) if any(a.startswith("--seed=") for a in sys.argv) else 1
    spec, types, f, s2 = make(name)
    cost = lambda v: E.mask_cost(spec, f, s2(v))
    b = F.bounds_for(spec["topo"])
    lb = [(np.log10(a), np.log10(c)) for a, c in b]
    lc = lambda u: cost(10 ** np.asarray(u))
    pal = json.load(open(os.path.join(E.HERE, "..", "analysis", "export", "filter_palette.json")))
    x0 = np.log10(np.clip(pal[name], [a for a, _ in b], [c for _, c in b]))
    r = differential_evolution(lc, lb, seed=seed, popsize=12, maxiter=(300 if name == "MB_BPF2" else 500), tol=1e-12, init="sobol", x0=x0,
                               mutation=(0.4, 1.0), recombination=0.9, polish=False)
    r2 = minimize(lc, r.x, method="Nelder-Mead", options=dict(maxiter=30000, xatol=1e-5, fatol=1e-8, adaptive=True))
    xc = 10 ** r2.x
    # snap: purchasable series, prefer palette values (small penalty for new values)
    palset = set(tuple(x) for k in pal for x in zip(F.types_of(F.FILTERS[k]["topo"]), np.round(pal[k], 2)))
    newpen = lambda v: sum(0.5 for t, x in zip(types, v) if (t, round(x, 2)) not in palset)
    xs = F.snap(spec["topo"], xc)
    best = cost(xs) + newpen(xs)
    for rnd in range(6):
        imp = False
        for i, t in enumerate(types):
            ser = F.L_SER if t == "L" else F.C_SER
            k = ser.index(min(ser, key=lambda q: abs(q - xs[i])))
            for kk in range(max(0, k - 3), min(len(ser), k + 4)):
                tr = xs.copy(); tr[i] = ser[kk]; c = cost(tr) + newpen(tr)
                if c < best - 1e-9: best, xs, imp = c, tr, True
        if not imp: break
    # Monte-Carlo with part tolerances
    tolC = {"L": {1.6: 0.2, 2.3: 0.2, 5.1: 0.2}}
    rng = np.random.default_rng(5); mcs = []
    for _ in range(300):
        t = xs.copy()
        for i, ty in enumerate(types):
            if ty == "L":
                tl = tolC["L"].get(round(t[i], 1), 0.1)
                t[i] += rng.uniform(-tl, tl) if t[i] < 6 else t[i] * rng.uniform(-0.02, 0.02)
            else:
                t[i] += rng.uniform(-0.1, 0.1) if t[i] < 5 else t[i] * rng.uniform(-0.05, 0.05)
        mcs.append(E.mask_metrics(spec, f, s2(t)))
    m_c, m_s = E.mask_metrics(spec, f, s2(xc)), E.mask_metrics(spec, f, s2(xs))
    lines = [f"## {name}: EM-in-the-loop optimization (seed {seed})\n", "| El | continuous | build |", "|---|---|---|"]
    for i, t in enumerate(types):
        u = "nH" if t == "L" else "pF"
        lines.append(f"| {t}{i+1} | {xc[i]:.2f} {u} | **{xs[i]:g} {u}**{'' if (t, round(xs[i],2)) in palset else ' (new)'} |")
    lines.append("\n| Metric | EM continuous | EM build values | EM build, MC 300 (5th pct worst) |\n|---|---|---|---|")
    for k in m_s:
        v = np.array([m[k] for m in mcs]); wv = np.percentile(v, 95) if k.startswith("IL") else np.percentile(v, 5)
        lines.append(f"| {k} | {m_c[k]:.2f} | {m_s[k]:.2f} | {wv:.2f} |")
    d = os.path.join(E.OUT, name)
    open(os.path.join(d, f"EMOPT_s{seed}.md"), "w").write("\n".join(lines) + "\n")
    S2 = s2(xs)
    json.dump(dict(f=list(map(float, f)), s21_best=list(map(float, np.abs(S2[:, 1, 0]))), s11_best=list(map(float, np.abs(S2[:, 0, 0]))),
                   vals_best=list(map(float, xs)), cost=float(cost(xs))), open(os.path.join(d, f"emopt_s{seed}.json"), "w"))
    print("\n".join(lines))

if __name__ == "__main__":
    main()

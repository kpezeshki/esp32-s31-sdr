#!/usr/bin/env python3
"""
Lumped 0402 band filters (post-LNA, 50 ohm both ends) with parasitic models, optimized by
differential evolution, snapped to purchasable values, palette-reduced (each unique value costs a
JLC loading fee, D8/D11), then Monte-Carlo on tolerances.

Filters (D13/D14):
  HB_HPF : pass 3.1-6.0 GHz; >=45 dB at 2.40-2.48 GHz (IF feedthrough); >=50 dB at <=1.9 GHz (HB image)
  MB_BPF : pass 1.75-2.15 GHz; >=40 dB <=1.55 GHz (1x3 inputs); >=50 dB 2.40-2.48 GHz (IF);
           >=50 dB 2.70-4.60 GHz (image 2.73-3.13, 1x3 3.31-4.51)
  HB_PRE : 2nd-order HPF before LNA_HB (series C, shunt L), fc ~2 GHz: keeps VHF/UHF/cellular off the LNA

Usage: python3 filters.py [HB_HPF|MB_BPF|HB_PRE|all] [--reopt]
Outputs: export/filter_<name>.md, export/auto_filter_<name>.png, export/filter_<name>_opt.json
"""
import os, sys, json
import numpy as np
from scipy.optimize import differential_evolution, minimize
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:          # remote compute venv has no matplotlib
    plt = None

HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.join(HERE, "export")
Z0 = 50.0
# ---- 0402 parasitics (ASSUMPTIONS; replace with Murata LQP15/LQW15 + GJM15 S-parameters before layout)
Q_L, CP_L = 35.0, 0.07e-12          # inductor Q, parallel C
ESL_C, ESR_C = 0.30e-9, 0.15        # capacitor ESL incl. pads, ESR
L_VIA = 0.25e-9                     # ground via(s) in every shunt branch
C_PAD = 0.05e-12                    # node pad capacitance

def zL(w, L):
    zs = w * L / Q_L + 1j * w * L
    return zs / (1 + 1j * w * CP_L * zs)

def zC(w, C):
    return 1 / (1j * w * C) + 1j * w * ESL_C + ESR_C

def branch_z(w, kind, v):
    if kind == "L":   return zL(w, v[0])
    if kind == "C":   return zC(w, v[0])
    if kind == "LCs": return zL(w, v[0]) + zC(w, v[1])
    if kind == "LCp": return 1 / (1 / zL(w, v[0]) + 1 / zC(w, v[1]))
    raise ValueError(kind)

NPAR = {"L": 1, "C": 1, "LCs": 2, "LCp": 2}
PTYPE = {"L": ["L"], "C": ["C"], "LCs": ["L", "C"], "LCp": ["L", "C"]}

def response(topo, x, f):
    """topo: list of (pos 's'|'p', kind). x: values in nH / pF order of topo."""
    w = 2 * np.pi * f
    A = np.ones_like(w, dtype=complex); B = np.zeros_like(A); C = np.zeros_like(A); D = np.ones_like(A)
    i = 0
    for pos, kind in topo:
        n = NPAR[kind]; vals = []
        for t, xv in zip(PTYPE[kind], x[i:i + n]):
            vals.append(xv * (1e-9 if t == "L" else 1e-12))
        i += n
        Z = branch_z(w, kind, vals)
        if pos == "s":
            A, B, C, D = A, A * Z + B, C, C * Z + D
            # node pad cap after each series element
            Y = 1j * w * C_PAD
            A, B, C, D = A + B * Y, B, C + D * Y, D
        else:
            Y = 1 / (Z + 1j * w * L_VIA)
            A, B, C, D = A + B * Y, B, C + D * Y, D
    den = A + B / Z0 + C * Z0 + D
    s21 = 2 / den
    s11 = (A + B / Z0 - C * Z0 - D) / den
    return 20 * np.log10(np.abs(s21) + 1e-15), 20 * np.log10(np.abs(s11) + 1e-15)

def types_of(topo):
    out = []
    for _, kind in topo:
        out += PTYPE[kind]
    return out

# ----------------------------------------------------------------------------- filter definitions
FILTERS = {
    "HB_HPF": dict(
        topo=[("s", "C"), ("p", "LCs"), ("s", "C"), ("p", "LCs"), ("s", "C"), ("p", "L"), ("s", "C")],
        mask=[("pass", 3.10e9, 6.0e9, 1.6), ("stop", 2.40e9, 2.48e9, 47), ("stop", 0.03e9, 1.9e9, 52)],
        rl=13.0, fmax=8e9),
    # MB band-pass = HPF section + LPF section, each optimized alone, then cascaded and polished jointly
    "MB_HP": dict(
        topo=[("s", "C"), ("p", "LCs"), ("s", "C"), ("p", "LCs"), ("s", "C"), ("p", "L"), ("s", "C")],
        mask=[("pass", 1.75e9, 2.5e9, 0.9), ("stop", 0.03e9, 1.55e9, 38)],
        rl=15.0, fmax=8e9),
    "MB_LP": dict(
        topo=[("s", "L"), ("p", "LCs"), ("s", "L"), ("p", "LCs"), ("s", "L"), ("p", "LCs"), ("s", "L")],
        mask=[("pass", 1.0e9, 2.15e9, 1.0), ("stop", 2.40e9, 2.48e9, 48), ("stop", 2.70e9, 3.15e9, 48),
              ("stop", 3.15e9, 4.6e9, 43), ("stop", 4.6e9, 7.0e9, 33)],
        rl=15.0, fmax=8e9),
    "MB_BPF2": dict(   # direct design, relaxed spec (IF feedthrough sits ~35 dB below conversion -> 35 dB at IF suffices)
        topo=[("s", "C"), ("p", "LCs"), ("s", "C"), ("p", "L"), ("s", "C"),
              ("p", "C"), ("s", "L"), ("p", "LCs"), ("s", "L"), ("p", "LCs"), ("s", "L")],
        mask=[("pass", 1.75e9, 2.15e9, 2.5), ("stop", 0.03e9, 1.50e9, 32), ("stop", 2.40e9, 2.48e9, 37),
              ("stop", 2.70e9, 3.15e9, 42), ("stop", 3.15e9, 4.6e9, 38), ("stop", 4.6e9, 7.0e9, 30)],
        rl=12.0, fmax=8e9, log=True),
    "MB_BPF": dict(
        topo=None, sections=["MB_HP", "MB_LP"],
        mask=[("pass", 1.75e9, 2.15e9, 2.5), ("stop", 0.03e9, 1.55e9, 35), ("stop", 2.40e9, 2.48e9, 45),
              ("stop", 2.70e9, 3.15e9, 45), ("stop", 3.15e9, 4.6e9, 40), ("stop", 4.6e9, 7.0e9, 30)],
        rl=12.0, fmax=8e9),
    "LB_LPF": dict(    # replaces LFCG-1700+ ($4.43): image 4.93-6.63 GHz, 1x3 inputs >= 5.0 GHz, IF feedthrough 2.44 GHz
        topo=[("s", "L"), ("p", "C"), ("s", "L"), ("p", "LCs"), ("s", "L"), ("p", "LCs"), ("s", "L")],
        mask=[("pass", 0.03e9, 1.75e9, 1.0), ("stop", 2.40e9, 2.48e9, 42), ("stop", 2.48e9, 4.8e9, 30),
              ("stop", 4.8e9, 7.6e9, 47)],
        rl=14.0, fmax=8e9, log=True),
    "HB_PRE": dict(
        topo=[("s", "C"), ("p", "L"), ("s", "C")],
        mask=[("pass", 3.10e9, 6.0e9, 0.35), ("stop", 0.03e9, 1.0e9, 15)],
        rl=15.0, fmax=8e9),
}

def grid(spec):
    f = []
    for kind, a, b, _ in spec["mask"]:
        f.append(np.linspace(a, b, 40))
    f.append(np.linspace(0.03e9, spec["fmax"], 120))
    return np.unique(np.concatenate(f))

def make_cost(spec):
    f = grid(spec); topo = spec["topo"]
    masks = [(k, (f >= a) & (f <= b), lim) for k, a, b, lim in spec["mask"]]
    passmask = np.zeros_like(f, dtype=bool)
    for k, m, _ in masks:
        if k == "pass": passmask |= m
    def cost(x):
        s21, s11 = response(topo, np.asarray(x), f)
        c = 0.0
        for k, m, lim in masks:
            if k == "pass":
                c += 20 * np.sum(np.clip(-s21[m] - lim, 0, None) ** 2)
            else:
                c += np.sum(np.clip(s21[m] + lim, 0, None) ** 2)
        c += 2 * np.sum(np.clip(s11[passmask] + spec["rl"], 0, None) ** 2)
        return c
    return cost, f

def metrics(spec, x):
    f = np.linspace(0.03e9, spec["fmax"], 4000)
    s21, s11 = response(spec["topo"], np.asarray(x), f)
    out = {}
    for k, a, b, lim in spec["mask"]:
        m = (f >= a) & (f <= b)
        if k == "pass":
            out[f"IL max {a/1e9:.2f}-{b/1e9:.2f} GHz (spec <= {lim})"] = -s21[m].min()
            out[f"RL min {a/1e9:.2f}-{b/1e9:.2f} GHz (spec >= {spec['rl']})"] = -s11[m].max()
        else:
            out[f"Rej min {a/1e9:.2f}-{b/1e9:.2f} GHz (spec >= {lim})"] = -s21[m].max()
    return out

L_SER = sorted(set([round(v, 1) for v in np.arange(0.6, 3.0, 0.1)] + [3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1, 10, 11, 12, 13, 15, 16, 18, 20, 22, 24, 27, 30, 33]))
C_SER = sorted(set([round(v, 1) for v in np.arange(0.2, 3.0, 0.1)] + [3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1, 10, 12, 15, 18, 22]))

def bounds_for(topo):
    b = []
    for t in types_of(topo):
        b.append((0.5, 15.0) if t == "L" else (0.2, 12.0))
    return b

SEED = 7
for _a in sys.argv:
    if _a.startswith("--seed="):
        SEED = int(_a.split("=")[1])

def snap(topo, x):
    return np.array([min(L_SER if t == "L" else C_SER, key=lambda v: abs(v - xi)) for xi, t in zip(x, types_of(topo))])

def refine(topo, x, cost, palette=None, rounds=5):
    """Coordinate search over purchasable values; if palette given, restrict to it."""
    ts = types_of(topo)
    def opts(i):
        base = L_SER if ts[i] == "L" else C_SER
        if palette is not None:
            base = sorted(set(v for (tt, v) in palette if tt == ts[i]))
        return base
    xs = np.array(x, float); best = cost(xs)
    for _ in range(rounds):
        imp = False
        for i in range(len(xs)):
            for v in opts(i):
                if v == xs[i]: continue
                t = xs.copy(); t[i] = v; c = cost(t)
                if c < best - 1e-9:
                    best, xs, imp = c, t, True
        if not imp: break
    return xs, best

def reduce_palette(topo, xs, cost, max_penalty=1.15):
    """Greedily merge unique values (same type) while cost stays within max_penalty x of start (+ small abs)."""
    ts = types_of(topo)
    cur = xs.copy(); c0 = cost(cur)
    while True:
        uniq = sorted(set(zip(ts, cur)))
        best_try = None
        for (t, v) in uniq:
            others = [u for u in uniq if u != (t, v) and u[0] == t]
            for o in others:
                trial = np.array([o[1] if (tt == t and xv == v) else xv for tt, xv in zip(ts, cur)])
                trial, c = refine(topo, trial, cost, palette=[u for u in uniq if u != (t, v)], rounds=2)
                if c <= max(c0 * max_penalty, c0 + 5.0) and (best_try is None or c < best_try[1]):
                    best_try = (trial, c)
        if best_try is None:
            return cur
        cur = best_try[0]

def monte_carlo(spec, x, n=1000, seed=1):
    rng = np.random.default_rng(seed); ts = types_of(spec["topo"]); out = []
    for _ in range(n):
        t = np.array(x, float)
        for i, tt in enumerate(ts):
            if tt == "L":
                t[i] += rng.uniform(-0.1, 0.1) if t[i] < 3.9 else t[i] * rng.uniform(-0.03, 0.03)
            else:
                t[i] += rng.uniform(-0.05, 0.05) if t[i] < 5 else t[i] * rng.uniform(-0.02, 0.02)
        out.append(metrics(spec, t))
    return out

def run(name, reopt=False):
    spec = FILTERS[name]
    init = None
    if spec.get("sections"):
        topo, init = [], []
        for sec in spec["sections"]:
            sc = os.path.join(EXP, f"filter_{sec}_opt.json")
            if not os.path.exists(sc) or reopt:
                run(sec, reopt)
            topo += FILTERS[sec]["topo"]; init += json.load(open(sc))["x"]
        spec["topo"] = topo
    topo = spec["topo"]
    cost, _ = make_cost(spec)
    tag = name if SEED == 7 else f"{name}_s{SEED}"
    cache = os.path.join(EXP, f"filter_{tag}_opt.json")
    if init is not None:
        b = bounds_for(topo)
        r2 = minimize(cost, np.array(init), method="Nelder-Mead", options=dict(maxiter=40000, xatol=1e-4, fatol=1e-7, adaptive=True))
        x = np.clip(r2.x, [a for a, _ in b], [c for _, c in b])
        json.dump(dict(x=list(map(float, x)), cost=float(cost(x))), open(cache, "w"))
    elif os.path.exists(cache) and not reopt:
        x = np.array(json.load(open(cache))["x"])
    else:
        b = bounds_for(topo)
        if spec.get("log"):
            lb_ = [(np.log10(a), np.log10(c)) for a, c in b]
            lc = lambda u: cost(10 ** np.asarray(u))
            r = differential_evolution(lc, lb_, seed=SEED, popsize=40, maxiter=3000, tol=1e-12, init="sobol",
                                       mutation=(0.4, 1.0), recombination=0.9, polish=False)
            r2 = minimize(lc, r.x, method="Nelder-Mead", options=dict(maxiter=40000, xatol=1e-5, fatol=1e-8, adaptive=True))
            x = np.clip(10 ** r2.x, [a for a, _ in b], [c for _, c in b])
        else:
            r = differential_evolution(cost, b, seed=SEED, popsize=30, maxiter=2000, tol=1e-10,
                                       mutation=(0.5, 1.0), recombination=0.8, polish=False)
            r2 = minimize(cost, r.x, method="Nelder-Mead", options=dict(maxiter=20000, xatol=1e-4, fatol=1e-7))
            x = np.clip(r2.x, [a for a, _ in b], [c for _, c in b])
        json.dump(dict(x=list(map(float, x)), cost=float(cost(x))), open(cache, "w"))
    xs, _ = refine(topo, snap(topo, x), cost)
    xr = reduce_palette(topo, xs, cost)
    ts = types_of(topo)
    m_c, m_s, m_r = metrics(spec, x), metrics(spec, xs), metrics(spec, xr)
    mc = monte_carlo(spec, xr)
    md = [f"# Filter {name} (auto-generated by analysis/filters.py)\n",
          f"Topology (from LNA side): {' - '.join(p + ':' + k for p, k in topo)}  (s = series, p = shunt to ground via {L_VIA*1e9:.2f} nH)\n",
          f"Parasitics: L Q={Q_L:.0f}, Cp={CP_L*1e12:.2f} pF; C ESL={ESL_C*1e9:.2f} nH, ESR={ESR_C} ohm; node pad {C_PAD*1e12:.2f} pF (assumptions).\n",
          "| # | Branch | Element | Continuous | Snapped | **Palette-reduced (build)** |", "|---|---|---|---|---|---|"]
    i = 0
    for bi, (pos, kind) in enumerate(topo):
        for t in PTYPE[kind]:
            u = "nH" if t == "L" else "pF"
            md.append(f"| {i+1} | {bi+1} {'series' if pos=='s' else 'shunt'} {kind} | {t} | {x[i]:.2f} {u} | {xs[i]:g} {u} | **{xr[i]:g} {u}** |")
            i += 1
    nu_s, nu_r = len(set(zip(ts, xs))), len(set(zip(ts, xr)))
    md.append(f"\nUnique values (JLC part types): snapped {nu_s}, palette-reduced **{nu_r}**.\n")
    keys = list(m_c.keys())
    md.append("| Metric | Continuous | Snapped | Reduced | Reduced, MC 1000 (5th pct worst) |\n|---|---|---|---|---|")
    for k in keys:
        vals = np.array([d[k] for d in mc])
        worst = np.percentile(vals, 95) if k.startswith("IL") else np.percentile(vals, 5)
        md.append(f"| {k} | {m_c[k]:.2f} | {m_s[k]:.2f} | {m_r[k]:.2f} | {worst:.2f} |")
    open(os.path.join(EXP, f"filter_{tag}.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    # plot
    f = np.linspace(0.03e9, spec["fmax"], 3000)
    fig, axs = plt.subplots(2, 1, figsize=(9.5, 6.6), dpi=130, sharex=True, gridspec_kw=dict(height_ratios=[2.2, 1]))
    rng = np.random.default_rng(3)
    for _ in range(25):
        t = np.array(xr, float)
        for j, tt in enumerate(ts):
            t[j] += (rng.uniform(-0.1, 0.1) if t[j] < 3.9 else t[j] * rng.uniform(-0.03, 0.03)) if tt == "L" else \
                    (rng.uniform(-0.05, 0.05) if t[j] < 5 else t[j] * rng.uniform(-0.02, 0.02))
        s21, _ = response(topo, t, f)
        axs[0].plot(f / 1e9, s21, color="#86b6ef", lw=0.6, alpha=0.6)
        axs[1].plot(f / 1e9, s21, color="#86b6ef", lw=0.6, alpha=0.6)
    s21, s11 = response(topo, xr, f)
    axs[0].plot(f / 1e9, s21, color="#2a78d6", lw=2, label="S21, build values")
    axs[0].plot(f / 1e9, s11, color="#777", lw=1.3, ls="--", label="S11")
    for k, a, b, lim in spec["mask"]:
        if k == "stop":
            axs[0].plot([a / 1e9, b / 1e9], [-lim, -lim], color="#eb6834", lw=3, alpha=0.5)
        else:
            axs[0].axvspan(a / 1e9, b / 1e9, color="#eef3fb", lw=0); axs[1].axvspan(a / 1e9, b / 1e9, color="#eef3fb", lw=0)
    axs[0].set_ylim(-90, 2); axs[0].set_ylabel("dB")
    axs[0].set_title(f"{name}: 0402 lumped filter with parasitics (orange = stopband spec, light = 25 tolerance runs)", fontsize=9.5, loc="left")
    axs[0].legend(fontsize=8, frameon=False, loc="lower right")
    axs[1].set_ylim(-4, 0.2); axs[1].set_ylabel("Passband IL (dB)"); axs[1].set_xlabel("Frequency (GHz)")
    for a in axs:
        a.spines[["top", "right"]].set_visible(False); a.grid(color="#ececec"); a.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(EXP, f"auto_filter_{tag}.png")); plt.close(fig)

if __name__ == "__main__":
    which = [a for a in sys.argv[1:] if not a.startswith("--")] or ["all"]
    names = list(FILTERS) if which == ["all"] else which
    for n in names:
        run(n, reopt="--reopt" in sys.argv)

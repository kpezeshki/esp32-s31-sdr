#!/usr/bin/env python3
"""
Antenna diplexer for the mixer path: LB arm (LPF, 30-1750 MHz) and HB arm (HPF, 2.95-6.0 GHz)
joined at the SMA node. Lumped 0402 elements with parasitics; ABCD cascade; optimized with
scipy differential evolution, snapped to purchasable values, then Monte-Carlo on tolerances.

Topology (common node = SMA side):
  LB: L1 - [T1: La+Ca to gnd] - L2 - [T2: Lb+Cb] - L3 - [T3: Lc+Cc] - L4 -> LNA_LB (50 ohm)
  HB: C1 - [S1: Ld+Cd to gnd] - C2 - [S2: Le+Ce] - C3 - [S3: Lf+Cf] - C4 -> LNA_HB (50 ohm)
  (elliptic-style ladders; every shunt branch is a series-LC trap; traps place transmission zeros
   at the IF (2.44 GHz), the LB image / 1x3 band (4.9-7.6 GHz) and the HB image band (<1.9 GHz))

Spec (from SIGNAL_CHAIN_ANALYSIS s.4):
  LB: IL <= ~1 dB 30-1750 MHz; >= 35 dB at IF 2.38-2.50 GHz; >= 50 dB 4.8-7.6 GHz
  HB: IL <= ~1.3 dB 2.95-6.0 GHz; >= 35 dB at 2.38-2.50 GHz; >= 50 dB 30-1900 MHz
  Common port RL >= 12 dB in both passbands.

Outputs: export/diplexer_values.md, export/auto_diplexer.png, export/auto_diplexer_mc.png
"""
import os, sys, json
import numpy as np
from scipy.optimize import differential_evolution, minimize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.join(HERE, "export")
Z0 = 50.0

# ---------------------------------------------------------------- parasitic models (0402)
Q_L = 35.0          # inductor Q (Murata LQW15AN/LQP15MN class, ~1-3 GHz)  ASSUMPTION
CP_L = 0.07e-12     # inductor parallel C -> SRF        ASSUMPTION
ESL_C = 0.30e-9     # capacitor ESL incl. pads          ASSUMPTION
ESR_C = 0.15        # ohm
L_VIA = 0.25e-9     # ground via(s) in every shunt branch ASSUMPTION (2 vias, 1.6 mm board, L1-L2 0.1 mm)
C_PAD = 0.05e-12    # pad/node capacitance to ground at each ladder node

def zL(w, L):
    R = w * L / Q_L
    zs = R + 1j * w * L
    return zs / (1 + 1j * w * CP_L * zs)

def zC(w, C):
    return 1 / (1j * w * C) + 1j * w * ESL_C + ESR_C

def ser(Z):
    o = np.ones_like(Z); z = np.zeros_like(Z)
    return np.array([[o, Z], [z, o]])

def sh(Y):
    o = np.ones_like(Y); z = np.zeros_like(Y)
    return np.array([[o, z], [Y, o]])

def mm(A, B):
    return np.einsum("ijf,jkf->ikf", A, B)

def arm_abcd(w, series, traps, kind):
    """series: 4 values (L for LP, C for HP); traps: 3 (L, C) pairs."""
    M = None
    for i in range(4):
        Zs = zL(w, series[i]) if kind == "LP" else zC(w, series[i])
        E = ser(Zs)
        M = E if M is None else mm(M, E)
        if i < 3:
            Lt, Ct = traps[i]
            Zt = zL(w, Lt) + zC(w, Ct) + 1j * w * L_VIA
            M = mm(M, sh(1 / Zt + 1j * w * C_PAD))
    return M

def unpack(x):
    # x in physical units: LP series L (nH) x4, LP traps (nH,pF) x3, HP series C (pF) x4, HP traps (nH,pF) x3
    lp_s = np.array(x[0:4]) * 1e-9
    lp_t = [(x[4 + 2 * i] * 1e-9, x[5 + 2 * i] * 1e-12) for i in range(3)]
    hp_s = np.array(x[10:14]) * 1e-12
    hp_t = [(x[14 + 2 * i] * 1e-9, x[15 + 2 * i] * 1e-12) for i in range(3)]
    return lp_s, lp_t, hp_s, hp_t

def response(x, f):
    w = 2 * np.pi * f
    lp_s, lp_t, hp_s, hp_t = unpack(x)
    A = arm_abcd(w, lp_s, lp_t, "LP"); B = arm_abcd(w, hp_s, hp_t, "HP")
    # input impedance of each arm terminated in Z0, plus node pad C
    zin = lambda M: (M[0, 0] * Z0 + M[0, 1]) / (M[1, 0] * Z0 + M[1, 1])
    Ylp, Yhp = 1 / zin(A), 1 / zin(B)
    Yn = Ylp + Yhp + 1j * w * C_PAD
    Zn = 1 / Yn
    s11 = (Zn - Z0) / (Zn + Z0)
    v1 = Zn / (Zn + Z0)                     # Vs = 1 -> available-power normalization: S21 = 2 V2 / Vs
    v2lp = v1 / (A[0, 0] + A[0, 1] / Z0)
    v2hp = v1 / (B[0, 0] + B[0, 1] / Z0)
    return 20 * np.log10(np.abs(s11)), 20 * np.log10(np.abs(2 * v2lp)), 20 * np.log10(np.abs(2 * v2hp))

# ---------------------------------------------------------------- objective
F = np.concatenate([np.linspace(30e6, 1750e6, 60), np.linspace(1750e6, 2950e6, 50),
                    np.linspace(2950e6, 6000e6, 60), np.linspace(6000e6, 7600e6, 25)])
LB_PASS = (F >= 30e6) & (F <= 1750e6)
HB_PASS = (F >= 2950e6) & (F <= 6000e6)
IFB = (F >= 2380e6) & (F <= 2500e6)
LB_STOP_HI = (F >= 4800e6) & (F <= 7600e6)
HB_STOP_LO = (F >= 30e6) & (F <= 1900e6)

def cost(x, verbose=False):
    s11, lp, hp = response(x, F)
    c = 0.0
    c += np.sum(np.clip(-lp[LB_PASS] - 0.9, 0, None) ** 2) * 20
    c += np.sum(np.clip(-hp[HB_PASS] - 1.2, 0, None) ** 2) * 20
    c += np.sum(np.clip(s11[LB_PASS | HB_PASS] + 13.0, 0, None) ** 2) * 2
    c += np.sum(np.clip(lp[IFB] + 38, 0, None) ** 2)
    c += np.sum(np.clip(hp[IFB] + 38, 0, None) ** 2)
    c += np.sum(np.clip(lp[LB_STOP_HI] + 52, 0, None) ** 2) * 0.5
    c += np.sum(np.clip(hp[HB_STOP_LO] + 52, 0, None) ** 2) * 0.5
    return c

# bounds: LP series L 1-20 nH; LP trap L 0.3-10 nH, C 0.2-10 pF; HP series C 0.3-10 pF; HP trap L 0.5-15 nH, C 0.3-15 pF
BOUNDS = ([(1, 20)] * 4 + [(0.3, 10), (0.2, 10)] * 3 + [(0.3, 10)] * 4 + [(0.5, 15), (0.3, 15)] * 3)

# ---------------------------------------------------------------- purchasable values
L_SERIES = sorted(set([round(v, 1) for v in np.arange(0.6, 3.0, 0.1)] +
                      [3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1, 10, 11, 12, 13, 15, 16, 18, 20]))
C_SERIES = sorted(set([round(v, 1) for v in np.arange(0.2, 3.0, 0.1)] +
                      [3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1, 10, 12, 15]))
IS_L = [True] * 4 + [True, False] * 3 + [False] * 4 + [True, False] * 3

def snap(x):
    return np.array([min(L_SERIES if isl else C_SERIES, key=lambda v: abs(v - xi)) for xi, isl in zip(x, IS_L)])

def snap_refine(x):
    """greedy coordinate search over neighbouring purchasable values."""
    xs = snap(x); best = cost(xs)
    for _ in range(4):
        improved = False
        for i in range(len(xs)):
            ser_ = L_SERIES if IS_L[i] else C_SERIES
            k = ser_.index(xs[i])
            for kk in (k - 2, k - 1, k + 1, k + 2):
                if 0 <= kk < len(ser_):
                    t = xs.copy(); t[i] = ser_[kk]; c = cost(t)
                    if c < best:
                        best, xs, improved = c, t, True
        if not improved:
            break
    return xs

def metrics(x):
    s11, lp, hp = response(x, F)
    return dict(lb_il_max=-lp[LB_PASS].min(), hb_il_max=-hp[HB_PASS].min(),
                rl_min=-s11[LB_PASS | HB_PASS].max(),
                lb_rej_if=-lp[IFB].max(), hb_rej_if=-hp[IFB].max(),
                lb_rej_hi=-lp[LB_STOP_HI].max(), hb_rej_lo=-hp[HB_STOP_LO].max())

def monte_carlo(x, n=2000, seed=1):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        t = np.array(x, dtype=float)
        for i, isl in enumerate(IS_L):
            if isl:   # LQP15/LQW15: +/-0.1 nH below 3.9 nH, +/-2-3% above
                t[i] += rng.uniform(-0.1, 0.1) if t[i] < 3.9 else t[i] * rng.uniform(-0.03, 0.03)
            else:     # C0G 0402: +/-0.05 pF below 5 pF, +/-2% above
                t[i] += rng.uniform(-0.05, 0.05) if t[i] < 5 else t[i] * rng.uniform(-0.02, 0.02)
        out.append(metrics(t))
    return out

def main():
    cache = os.path.join(EXP, "diplexer_opt.json")
    if os.path.exists(cache) and "--reopt" not in sys.argv:
        x = np.array(json.load(open(cache))["x"])
    else:
        r = differential_evolution(cost, BOUNDS, seed=3, popsize=25, maxiter=1500, tol=1e-9,
                                   mutation=(0.5, 1.0), recombination=0.8, polish=False, workers=1)
        x = r.x
        r2 = minimize(cost, x, method="Nelder-Mead", options=dict(maxiter=20000, xatol=1e-4, fatol=1e-6))
        x = np.clip(r2.x, [b[0] for b in BOUNDS], [b[1] for b in BOUNDS])
        json.dump(dict(x=list(x), cost=float(cost(x))), open(cache, "w"))
    xs = snap_refine(x)
    m_c, m_s = metrics(x), metrics(xs)
    mc = monte_carlo(xs)
    keys = list(m_s.keys())
    pct = {k: (np.percentile([d[k] for d in mc], 5 if "il" not in k else 95)) for k in keys}

    names = (["L1", "L2", "L3", "L4", "La", "Ca", "Lb", "Cb", "Lc", "Cc"] +
             ["C1", "C2", "C3", "C4", "Ld", "Cd", "Le", "Ce", "Lf", "Cf"])
    units = ["nH" if isl else "pF" for isl in IS_L]
    md = ["# Antenna diplexer: optimized & snapped values (auto-generated by analysis/diplexer.py)\n",
          f"Parasitics: inductor Q={Q_L:.0f}, Cp={CP_L*1e12:.2f} pF; capacitor ESL={ESL_C*1e9:.2f} nH, ESR={ESR_C} ohm; "
          f"shunt-branch via {L_VIA*1e9:.2f} nH; node pad C {C_PAD*1e12:.2f} pF (all assumptions -> replace with vendor S-parameters).\n",
          "| Ref | Role | Continuous | Snapped (buy) |", "|---|---|---|---|"]
    roles = (["LB series L"] * 4 + ["LB trap 1 L", "LB trap 1 C", "LB trap 2 L", "LB trap 2 C", "LB trap 3 L", "LB trap 3 C"] +
             ["HB series C"] * 4 + ["HB trap 1 L", "HB trap 1 C", "HB trap 2 L", "HB trap 2 C", "HB trap 3 L", "HB trap 3 C"])
    for n_, r_, a, b, u in zip(names, roles, x, xs, units):
        md.append(f"| {n_} | {r_} | {a:.2f} {u} | **{b:g} {u}** |")
    # trap resonances
    md.append("\nTrap (shunt series-LC incl. via + ESL) resonances, snapped values:\n")
    lp_s, lp_t, hp_s, hp_t = unpack(xs)
    for lab, (L, C) in zip(["LB T1", "LB T2", "LB T3", "HB S1", "HB S2", "HB S3"], lp_t + hp_t):
        f0 = 1 / (2 * np.pi * np.sqrt((L + L_VIA + ESL_C) * C))
        md.append(f"- {lab}: {f0/1e9:.2f} GHz")
    md.append("\n| Metric | Spec | Continuous | Snapped | Snapped, MC 2000 runs (95% worst) |\n|---|---|---|---|---|")
    spec = dict(lb_il_max="<= 1.0 dB", hb_il_max="<= 1.3 dB", rl_min=">= 12 dB", lb_rej_if=">= 35 dB",
                hb_rej_if=">= 35 dB", lb_rej_hi=">= 50 dB", hb_rej_lo=">= 50 dB")
    desc = dict(lb_il_max="LB max IL 30-1750 MHz", hb_il_max="HB max IL 2.95-6 GHz", rl_min="Common-port RL (both passbands)",
                lb_rej_if="LB rejection 2.38-2.50 GHz", hb_rej_if="HB rejection 2.38-2.50 GHz",
                lb_rej_hi="LB rejection 4.8-7.6 GHz", hb_rej_lo="HB rejection 30-1900 MHz")
    for k in keys:
        md.append(f"| {desc[k]} | {spec[k]} | {m_c[k]:.1f} | {m_s[k]:.1f} | {pct[k]:.1f} |")
    open(os.path.join(EXP, "diplexer_values.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))

    # plot
    ff = np.linspace(10e6, 8e9, 1600)
    s11, lp, hp = response(xs, ff)
    BLUE, ORANGE = "#2a78d6", "#eb6834"
    fig, axs = plt.subplots(2, 1, figsize=(9.5, 7.2), dpi=130, sharex=True, gridspec_kw=dict(height_ratios=[2.2, 1]))
    ax = axs[0]
    for xx in mc[:0]:
        pass
    ax.plot(ff / 1e9, lp, color=BLUE, lw=2, label="LB arm (to LNA_LB)")
    ax.plot(ff / 1e9, hp, color=ORANGE, lw=2, label="HB arm (to LNA_HB)")
    ax.plot(ff / 1e9, s11, color="#777", lw=1.4, ls="--", label="Common port S11")
    for (a, b, lvl) in [(2.38, 2.50, -35), (4.8, 7.6, -50)]:
        ax.plot([a, b], [lvl, lvl], color=BLUE, lw=3, alpha=0.35)
    for (a, b, lvl) in [(2.38, 2.50, -35), (0.03, 1.9, -50)]:
        ax.plot([a, b], [lvl - 1.5, lvl - 1.5], color=ORANGE, lw=3, alpha=0.35)
    ax.axvspan(2.40, 2.4835, color="#e6e6e6", lw=0); ax.text(2.2, -88, "IF", fontsize=7.5, color="#555")
    ax.set_ylim(-90, 2); ax.set_ylabel("dB")
    ax.set_title("Antenna diplexer, snapped 0402 values with parasitics (shaded bars = stopband specs)", fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False); ax.grid(color="#ececec"); ax.set_axisbelow(True)
    ax = axs[1]
    ax.plot(ff / 1e9, lp, color=BLUE, lw=2); ax.plot(ff / 1e9, hp, color=ORANGE, lw=2)
    ax.set_ylim(-3, 0.2); ax.set_ylabel("Passband IL (dB)"); ax.set_xlabel("Frequency (GHz)")
    ax.axvspan(0.03, 1.75, color="#eef3fb", lw=0); ax.axvspan(2.95, 6.0, color="#fdf0ea", lw=0)
    ax.spines[["top", "right"]].set_visible(False); ax.grid(color="#ececec"); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(os.path.join(EXP, "auto_diplexer.png")); plt.close(fig)

if __name__ == "__main__":
    main()

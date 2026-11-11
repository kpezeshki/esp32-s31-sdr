#!/usr/bin/env python3
"""EM report figures: final filters (EM co-simulation incl. MC envelope) vs ideal lumped models; RF line Z0."""
import json, os, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import em_opt as O, filter_em as E
F = E.F
fv = json.load(open("filters/final_values.json"))
os.makedirs("figs", exist_ok=True)
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#777777"
fig, axs = plt.subplots(2, 2, figsize=(12, 8), dpi=130)
for ax, name in zip(axs.flat, ["LB_LPF", "MB_BPF2", "HB_PRE", "HB_HPF"]):
    spec, types, f, s2 = O.make(name); x = np.array(fv[name])
    rng = np.random.default_rng(1)
    for _ in range(40):
        y = x.copy()
        for i, t in enumerate(types):
            if t == "C": y[i] += rng.uniform(-0.05, 0.05) if y[i] < 5 else y[i] * rng.uniform(-0.02, 0.02)
            else: y[i] += rng.uniform(-0.1, 0.1) if y[i] < 6 else y[i] * rng.uniform(-0.02, 0.02)
        ax.plot(f / 1e9, 20 * np.log10(np.abs(s2(y)[:, 1, 0])), color="#b7d3f6", lw=0.6)
    S = s2(x)
    ax.plot(f / 1e9, 20 * np.log10(np.abs(S[:, 1, 0])), color=BLUE, lw=2, label="S21 EM co-sim (build values)")
    ax.plot(f / 1e9, 20 * np.log10(np.abs(S[:, 0, 0])), color=GREY, lw=1.2, ls="--", label="S11 EM co-sim")
    s21l, _ = F.response(spec["topo"], x, f)
    ax.plot(f / 1e9, s21l, color=ORANGE, lw=1.2, ls=":", label="S21 lumped model (no layout)")
    for k, a, b, lim in spec["mask"]:
        if k == "stop": ax.plot([a / 1e9, b / 1e9], [-lim, -lim], color=ORANGE, lw=3, alpha=0.4)
        else: ax.axvspan(a / 1e9, b / 1e9, color="#eef3fb", lw=0)
    ax.axvspan(2.40, 2.48, color="#e6e6e6", lw=0)
    ax.set_ylim(-80, 2); ax.set_xlim(0, 8); ax.set_title(name + "  (light blue: 40 tolerance runs, W/B grade)", fontsize=9, loc="left")
    ax.set_xlabel("GHz"); ax.set_ylabel("dB"); ax.grid(color="#ececec"); ax.spines[["top", "right"]].set_visible(False)
axs[0, 0].legend(fontsize=7, frameon=False, loc="lower left")
fig.tight_layout(); fig.savefig("figs/filters_em.png"); print("figs/filters_em.png")

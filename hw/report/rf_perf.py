#!/usr/bin/env python3
"""Simulated RF performance for the report (two-board build, as laid out).
1) Band filters: Sonnet EM N-port of the routed filter geometry co-simulated with the final part values, plus a
   Monte-Carlo tolerance envelope (C +-0.05 pF W-grade, L +-0.1 nH B-grade, uniform, 300 draws).
2) Cascade NF / gain vs RF frequency: datasheet stage models from analysis/cascade_parts.py, with the filter loss taken
   from (1), trace loss from the measured RF trace lengths on board B x Sonnet line loss, the split-board IF tail
   (SAW -> 3 dB pad -> U.FL + 10 cm cable -> WROOM-1U), GVA-62+ gain block fitted.
3) Dynamic range: input-referred noise floor (40 MHz), 8-bit ADC clip, front-end P1dB and IIP3 vs frequency.
Writes PNGs + rf_perf.json into hw/report/."""
import os, sys, json
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path[:0] = [os.path.join(ROOT, "em"), os.path.join(ROOT, "analysis")]
import em_opt, cascade as C, cascade_parts as CP

# dataviz reference palette (light): categorical slots 1-3 + neutral ink
BLUE, ORANGE, AQUA, GRAY, INK, INK2 = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c9c8c2", "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.grid": True, "grid.color": "#ecebe7", "grid.linewidth": 0.8,
                     "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb", "lines.linewidth": 2})
VALS = json.load(open(os.path.join(ROOT, "em", "filters", "final_values.json")))
IF_BAND = (2.40, 2.48)
FILT = {"LB_LPF": ("Low band: LPF 50-1750 MHz", (0.05, 1.75)), "MB_BPF2": ("Mid band: BPF 1750-2150 MHz", (1.75, 2.15)),
        "HB_PRE": ("High band pre-LNA HPF (2nd order)", (3.1, 6.0)), "HB_HPF": ("High band: elliptic HPF 3.1-6 GHz", (3.1, 6.0))}

# ---------------------------------------------------------------------------- 1) filters
rng = np.random.default_rng(1)
filt = {}
for name, (title, pb) in FILT.items():
    spec, types, f, s2 = em_opt.make(name)
    nom = np.array(VALS[name], float)
    s21 = 20 * np.log10(np.abs(s2(nom)[:, 1, 0]) + 1e-12)
    s11 = 20 * np.log10(np.abs(s2(nom)[:, 0, 0]) + 1e-12)
    tol = np.array([0.1 if t == "L" else 0.05 for t in types])
    mc = np.array([20 * np.log10(np.abs(s2(np.maximum(nom + rng.uniform(-1, 1, len(nom)) * tol, 0.1))[:, 1, 0]) + 1e-12) for _ in range(300)])
    filt[name] = dict(f=f / 1e9, s21=s21, s11=s11, lo=np.percentile(mc, 5, axis=0), hi=np.percentile(mc, 95, axis=0))

fig, axs = plt.subplots(2, 2, figsize=(11, 7.2), sharex=True)
for ax, (name, (title, pb)) in zip(axs.flat, FILT.items()):
    d = filt[name]
    ax.axvspan(*pb, color=BLUE, alpha=0.07, lw=0); ax.axvspan(*IF_BAND, color=ORANGE, alpha=0.18, lw=0)
    ax.fill_between(d["f"], d["lo"], d["hi"], color=BLUE, alpha=0.22, lw=0, label="5-95 % with part tolerance")
    ax.plot(d["f"], d["s21"], color=BLUE, label="|S21| nominal (EM co-sim)")
    ax.plot(d["f"], d["s11"], color=GRAY, lw=1.2, ls="--", label="|S11| nominal")
    ax.set_ylim(-70, 2); ax.set_xlim(0, 7); ax.set_title(title, fontsize=10.5, color=INK, loc="left")
    ax.text(np.mean(IF_BAND), -66, "IF", ha="center", fontsize=8.5, color=ORANGE)
    pbm = (d["f"] >= pb[0]) & (d["f"] <= pb[1]); ifm = (d["f"] >= IF_BAND[0]) & (d["f"] <= IF_BAND[1])
    ax.text(0.98, 0.06, f"passband IL max {-d['s21'][pbm].min():.1f} dB\nIF rejection min {-d['s21'][ifm].max():.0f} dB",
            transform=ax.transAxes, ha="right", fontsize=8.5, color=INK2,
            bbox=dict(fc="#fcfcfb", ec="#e2e1dc", boxstyle="round,pad=0.3"))
for ax in axs[1]: ax.set_xlabel("Frequency (GHz)")
for ax in axs[:, 0]: ax.set_ylabel("dB")
axs[0, 0].legend(loc="lower left", fontsize=8, frameon=False)
fig.suptitle("Band filters: Sonnet EM model of the routed 0402 layout + final part values", x=0.01, ha="left", fontsize=12, color=INK)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "rf_filters.png"), dpi=150); plt.close(fig)

def il(name, fmhz):   # filter insertion loss (dB, positive) at f MHz from the EM co-sim
    d = filt[name]; return float(-np.interp(fmhz / 1e3, d["f"], d["s21"]))

# ---------------------------------------------------------------------------- 2) cascade
def a_line(fmhz):     # 0.19 mm microstrip loss, dB/mm: Sonnet 0.028 @ 6 GHz, split ~50/50 conductor (sqrt f) / dielectric (f)
    x = fmhz / 6000.0; return 0.014 * np.sqrt(x) + 0.014 * x
TR = dict(LB_pre=2.5 + 1.2 + 9.2 + 0.8, LB_post=1.4 + 16.2 + 11.2, MB_pre=2.5 + 1.2 + 9.2 + 0.8, MB_post=0.3 + 22.4 + 11.2,
          HB_pre=2.5 + 1.2 + 1.2 + 0.3 + 1.3, HB_post=1.5 + 0.6 + 6.3 + 11.2)   # mm, measured on board B (W50 nets)
P = C.passive
def tail(f, rffc):
    return [CP.gb(f, "gva62"), P("Balun H3-TCM2-63WX+", float(np.interp(f, [100, 1750, 3000, 5000, 6000], [0.9, 1.1, 1.5, 2.5, 2.5]))),
            rffc, P("SAW SAFEA2G45MC0", 2.5), P("3 dB pad (cal-burst protection)", 3.0),
            P("U.FL + 10 cm cable + U.FL", 0.5), C.esp32()]
def chain(band, f):
    sw = CP.sw3(f)
    if band in ("LB", "MB"):
        mb = band == "MB"
        g = float(np.interp(f, [1750, 2150], [15.5, 14.0])) if mb else float(np.interp(f, [100, 500, 1000, 1750], [22.0, 20.5, 18.4, 15.5]))
        nf = float(np.interp(f, [1750, 2150], [0.9, 1.0])) if mb else float(np.interp(f, [100, 1000, 1750], [0.9, 0.75, 0.9]))
        rffc = ("RFFC5072 + 4:1 balun", -5.0, 13.0, 22.0, 11.0)
        return [P("SMA + ESD", 0.2), P("trace to LNA", a_line(f) * TR[band + "_pre"]), P("SP3T in", sw, ip3=70, p1=34),
                ("LNA PSA4-5043+", g, nf, 33.5 - g, 21 - g + 1), P("filter (EM)", il("MB_BPF2" if mb else "LB_LPF", f)),
                P("trace", a_line(f) * TR[band + "_post"]), P("SP3T out", sw, ip3=70, p1=34)] + tail(f, rffc)
    if band == "HB":
        g = float(np.interp(f, [3000, 5500, 6000], [22.0, 21.6, 21.0])); nf = float(np.interp(f, [3000, 6000], [0.8, 1.0]))
        rffc = ("RFFC5072 + 4:1 balun", float(np.interp(f, [3000, 6000], [-6, -8])), float(np.interp(f, [3000, 6000], [14, 16])),
                float(np.interp(f, [3000, 6000], [20, 16])), float(np.interp(f, [3000, 6000], [8, 4])))
        return [P("SMA + ESD", 0.3), P("trace to LNA", a_line(f) * TR["HB_pre"]), P("SP3T in", sw, ip3=70, p1=34),
                P("pre-LNA HPF (EM)", il("HB_PRE", f)), ("LNA QPL9503", g, nf, 35.5 - g, 19 - g + 1),
                P("HPF (EM)", il("HB_HPF", f)), P("trace", a_line(f) * TR["HB_post"]), P("SP3T out", sw, ip3=70, p1=34)] + tail(f, rffc)
    return [P("antenna U.FL + cable", 0.5), C.esp32()]       # native path: Board A alone, antenna on the module U.FL

BANDS = {"LB": (np.arange(50, 1751, 10), BLUE, "Low band (mixer)"), "MB": (np.arange(1750, 2151, 10), ORANGE, "Mid band (mixer)"),
         "HB": (np.arange(3100, 6001, 20), AQUA, "High band (mixer)"), "NAT": (np.arange(2150, 2801, 10), GRAY, "Native ESP32 (Board A alone)")}
res = {}
for b, (fs, col, lab) in BANDS.items():
    rows = [C.summarize(chain(b, float(f))) for f in fs]
    res[b] = dict(f=fs.tolist(), nf=[r["nf"] for r in rows], G=[r["G"] for r in rows], n40=[r["n_in_bw"] for r in rows],
                  clip=[r["clip_in"] for r in rows], iip3=[r["iip3"] for r in rows], p1=[r["p1"] for r in rows])

fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 7.2), sharex=True, gridspec_kw=dict(height_ratios=[1.3, 1]))
for b, (fs, col, lab) in BANDS.items():
    ls = "--" if b == "NAT" else "-"
    a1.plot(fs / 1e3, res[b]["nf"], color=col, ls=ls); a2.plot(fs / 1e3, res[b]["G"], color=col, ls=ls)
    k = len(fs) // 2
    a1.annotate(lab, (fs[k] / 1e3, res[b]["nf"][k]), xytext=(0, 9 if b != "NAT" else -16), textcoords="offset points",
                ha="center", fontsize=8.5, color=INK2)
a1.axvspan(2.8, 3.1, color="#e2e1dc", alpha=0.6, lw=0); a1.text(2.95, 0.4, "gap", ha="center", fontsize=8, color=INK2)
a1.set_ylabel("System noise figure (dB)"); a1.set_ylim(0, 6.5)
a2.set_ylabel("Gain to ESP32 pin (dB)"); a2.set_xlabel("RF frequency (GHz)"); a2.set_xlim(0, 6.1)
a1.set_title("Noise figure and gain vs frequency (antenna SMA to ESP32 ADC; EM filter loss, measured trace lengths, ESP32 NF 5 dB assumed)",
             loc="left", fontsize=10.5, color=INK)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "rf_nf_gain.png"), dpi=150); plt.close(fig)

# ---------------------------------------------------------------------------- 3) dynamic range (input-referred levels)
fig, ax = plt.subplots(figsize=(11, 5.2))
first = True
for b in ("LB", "MB", "HB"):
    f = np.array(res[b]["f"]) / 1e3
    ax.fill_between(f, res[b]["n40"], res[b]["clip"], color=BLUE, alpha=0.10, lw=0, label="instantaneous DR (8-bit ADC, 40 MHz)" if first else None)
    ax.plot(f, res[b]["n40"], color=BLUE, label="noise floor, dBm in 40 MHz" if first else None)
    ax.plot(f, res[b]["clip"], color=ORANGE, label="ADC full scale (gain set: noise 6 dB over quantization)" if first else None)
    ax.plot(f, res[b]["p1"], color=AQUA, label="front-end input P1dB" if first else None)
    ax.plot(f, res[b]["iip3"], color=GRAY, ls="--", label="front-end input IP3" if first else None)
    first = False
ax.axvspan(2.15, 3.1, color="#e2e1dc", alpha=0.45, lw=0); ax.text(2.62, -10, "native path /\ngap", ha="center", fontsize=8, color=INK2)
ax.set_xlim(0, 6.1); ax.set_ylim(-110, 25); ax.set_xlabel("RF frequency (GHz)"); ax.set_ylabel("Level at antenna SMA (dBm)")
ax.legend(loc="center right", fontsize=8.5, frameon=False)
ax.set_title("Dynamic range, input-referred (mixer bands): ~44 dB instantaneous in 40 MHz, limited by the 8-bit ADC, not the analog chain",
             loc="left", fontsize=10.5, color=INK)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "rf_dynamic_range.png"), dpi=150); plt.close(fig)

# ---------------------------------------------------------------------------- summary numbers
def at(b, fm):
    i = int(np.argmin(np.abs(np.array(res[b]["f"]) - fm))); return {k: round(float(v[i]), 1) for k, v in res[b].items()}
pts = {f"{b} {fm} MHz": at(b, fm) for b, fm in [("LB", 100), ("LB", 433), ("LB", 1090), ("LB", 1700), ("MB", 1900), ("MB", 2100),
                                                   ("NAT", 2440), ("HB", 3500), ("HB", 5000), ("HB", 5800)]}
fsum = {n: dict(pb_il_max=round(float(-filt[n]["s21"][(filt[n]["f"] >= FILT[n][1][0]) & (filt[n]["f"] <= FILT[n][1][1])].min()), 2),
                if_rej_min=round(float(-filt[n]["s21"][(filt[n]["f"] >= 2.40) & (filt[n]["f"] <= 2.48)].max()), 1)) for n in FILT}
json.dump(dict(points=pts, filters=fsum), open(os.path.join(HERE, "rf_perf.json"), "w"), indent=1)
for k, v in pts.items(): print(k, v)
print(fsum)

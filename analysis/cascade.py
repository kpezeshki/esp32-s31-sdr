#!/usr/bin/env python3
"""
ESP32-S31 RX-only SDR - signal-chain cascade & node power levels.

Every stage is (name, gain_dB, NF_dB, IIP3_dBm, IP1dB_dBm).  Passive stages: NF = loss.
Numbers are ASSUMPTIONS unless tagged [DS] (datasheet). See SIGNAL_CHAIN_ANALYSIS.md section 2.

Outputs (analysis/export/):
  cascade_tables.md          per-band node tables + summary
  auto_nf_contrib.png        NF contribution per stage
  auto_levels_lb1090.png     node level diagram (noise / weak / strong) at 1090 MHz
"""
import math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, "export")
os.makedirs(EXP, exist_ok=True)

KT = -174.0          # dBm/Hz at 290 K
BW_CAP = 40e6        # ESP32-S31 continuous stream over GbE: 40 MS/s complex, 8 bit [ESP-SDR docs]
ADC_BITS = 8
INF = 99.0

def db2lin(x): return 10 ** (x / 10)
def lin2db(x): return 10 * math.log10(x)

def passive(name, loss, ip3=INF, p1=INF):
    return (name, -loss, loss, ip3, p1)

# ----------------------------------------------------------------------------- stage library
ESP_NF = 5.0  # ESP32-S31 RX NF, assumption. Datasheet sensitivity implies ~2.5-4.5 dB (see doc s.2.6)

def esp32(nf=None):
    # gain/linearity of ESP32 handled separately (internal AGC/manual gain + 8-bit ADC)
    return ("ESP32-S31 RX", 0.0, ESP_NF if nf is None else nf, INF, INF)

def gain_block(f_mhz):
    """Common wideband gain block after the band SPDT (50 MHz-6 GHz MMIC class). ASSUMPTION."""
    g = float(np.interp(f_mhz, [100, 2000, 6000], [16.0, 15.0, 12.0]))
    nf = float(np.interp(f_mhz, [100, 2000, 6000], [3.0, 3.5, 4.5]))
    oip3 = float(np.interp(f_mhz, [100, 2000, 6000], [32.0, 30.0, 25.0]))
    op1 = float(np.interp(f_mhz, [100, 2000, 6000], [18.0, 17.0, 14.0]))
    return ("Gain block (opt.)", g, nf, oip3 - g, op1 - g + 1)

def lb_chain(f_mhz, if_amp=False, gb=False):
    """Low band 50-1750 MHz, mixer path. LNA = SPF5189Z-class @5V/90mA."""
    # SPF5189Z [DS] table: 0.8G 19.6dB/0.52dB, 0.9G 18.7/0.55, 1.0G 17.9/0.79, 1.7G 13.8/0.75
    # below 800 MHz: extrapolated (gain rises; NF assumed 0.8 dB at 100 MHz) -> ASSUMPTION
    fpts = [100, 450, 800, 900, 1000, 1700, 1800]
    gpts = [23.0, 21.0, 19.6, 18.7, 17.9, 13.8, 13.5]
    npts = [0.8, 0.6, 0.52, 0.55, 0.79, 0.75, 0.81]
    g = float(np.interp(f_mhz, fpts, gpts)); nf = float(np.interp(f_mhz, fpts, npts))
    oip3, op1 = 38.5, 22.4                           # [DS] @0.9 GHz
    filt = float(np.interp(f_mhz, [100, 1000, 1700], [0.8, 1.1, 1.6]))  # post-LNA LPF 1.75G (lumped 0402 or LTCC)
    st = [
        passive("SMA + ESD + trace", 0.3),
        passive("SPDT_in (band select)", 0.4, ip3=60, p1=30),
        ("LNA_LB (SPF5189Z-cl.)", g, nf, oip3 - g, op1 - g + 1),
        passive("Post-LNA LPF 1.75G", filt),
        passive("SPDT_out", 0.4, ip3=60, p1=30),
    ] + ([gain_block(f_mhz)] if gb else []) + [
        passive("Input balun 1:2", 1.0),
        # RFFC5071/2 MIX_IDD=4..5 [DS @IF=100MHz]: Gc -3..-5 dB, NF 11-13, IIP3 ~+23..+25, IP1dB ~+11
        # derated for 2.44 GHz IF and incl. 4:1 IF LTCC balun -> ASSUMPTION
        ("RFFC507x mixer + 4:1 balun", -5.0, 13.0, 22.0, 11.0),
        passive("IF SAW/BAW 2.44G", 2.5, ip3=45, p1=30),
    ]
    if if_amp:
        st.append(("IF LNA 2.4G (opt.)", 14.0, 1.3, 25.0 - 14.0, 12.0 - 14.0 + 1))
    st += [passive("0R tee + ESP32 match", 0.4), esp32()]
    return st

def hb_chain(f_mhz, if_amp=False, gb=False):
    """High band 3.0-6.0 GHz, mixer path. LNA = generic 0.5-6 GHz MMIC LNA (MGA-665P8-class)."""
    g = float(np.interp(f_mhz, [3000, 6000], [18.0, 15.0]))
    nf = float(np.interp(f_mhz, [3000, 6000], [1.1, 1.5]))
    oip3, op1 = 25.0, 12.0                                   # ASSUMPTION (low-current LNA)
    filt = float(np.interp(f_mhz, [3000, 6000], [1.2, 1.6]))   # post-LNA HPF 2.95G (lumped 0402 or LTCC)
    sw = float(np.interp(f_mhz, [3000, 6000], [0.6, 0.9]))
    gm = float(np.interp(f_mhz, [3000, 6000], [-6.0, -8.0]))   # mixer derated vs DS (DS plots stop at 2 GHz)
    nfm = float(np.interp(f_mhz, [3000, 6000], [14.0, 16.0]))
    ip3m = float(np.interp(f_mhz, [3000, 6000], [20.0, 16.0]))
    st = [
        passive("SMA + ESD + trace", float(np.interp(f_mhz, [3000, 6000], [0.4, 0.6]))),
        passive("SPDT_in (band select)", sw, ip3=60, p1=30),
        passive("Pre-LNA HPF 2nd order", 0.3),
        ("LNA_HB (0.5-6G MMIC)", g, nf, oip3 - g, op1 - g + 1),
        passive("Post-LNA HPF 2.95G", filt),
        passive("SPDT_out", sw, ip3=60, p1=30),
    ] + ([gain_block(f_mhz)] if gb else []) + [
        passive("Input balun 1:2", float(np.interp(f_mhz, [3000, 6000], [1.2, 1.8]))),
        ("RFFC507x mixer + 4:1 balun", gm, nfm, ip3m, ip3m - 12),
        passive("IF SAW/BAW 2.44G", 2.5, ip3=45, p1=30),
    ]
    if if_amp:
        st.append(("IF LNA 2.4G (opt.)", 14.0, 1.3, 25.0 - 14.0, 12.0 - 14.0 + 1))
    st += [passive("0R tee + ESP32 match", 0.4), esp32()]
    return st

def native_chain(f_mhz=2441):
    return [passive("SMA + ESD + trace", 0.3), passive("0R tee + ESP32 match", 0.4), esp32()]

# ----------------------------------------------------------------------------- cascade math
def cascade(stages):
    """Return per-node cumulative (G, NF, IIP3_in, IP1_in) after each stage, input referred."""
    G = 0.0; F = 1.0; inv_ip3 = 0.0; p1_in = INF
    rows = []
    for (name, g, nf, ip3, p1) in stages:
        Glin_before = db2lin(G)
        F += (db2lin(nf) - 1) / Glin_before
        if ip3 < INF:
            inv_ip3 += 1.0 / (db2lin(ip3) / Glin_before)     # mW
        if p1 < INF:
            p1_in = min(p1_in, p1 - G)                       # first stage to compress (input ref.)
        G += g
        rows.append(dict(name=name, g=g, nf=nf, ip3=ip3, p1=p1, Gc=G, NFc=lin2db(F),
                         IIP3c=(lin2db(1 / inv_ip3) if inv_ip3 > 0 else INF), P1c=p1_in))
    return rows

def nf_contrib(stages):
    """Share of total (F-1) contributed by each stage, in dB-equivalent terms."""
    G = 0.0; parts = []
    for (name, g, nf, ip3, p1) in stages:
        parts.append((name, (db2lin(nf) - 1) / db2lin(G)))
        G += g
    return parts

# ----------------------------------------------------------------------------- report
def fmt(x, w=6, p=1):
    return " -- " if x >= INF - 1 else f"{x:{w}.{p}f}"

def node_table(title, stages, pin_list=(-100, -60, -30)):
    rows = cascade(stages)
    nfin = rows[-1]["NFc"]
    out = [f"### {title}\n",
           "| # | Stage | G | NF | IIP3 (stage) | Cum G | Cum NF | Cum IIP3 (in-ref) | Noise out dBm/Hz | Noise out dBm/40MHz | "
           + " | ".join(f"Pout @ Pin={p}" for p in pin_list) + " |",
           "|---|---|---|---|---|---|---|---|---|---|" + "---|" * len(pin_list)]
    for i, r in enumerate(rows):
        # output noise density at this node (input-referred cum NF to this node, times cum gain)
        n_hz = KT + r["NFc"] + r["Gc"]
        n_bw = n_hz + lin2db(BW_CAP)
        pouts = " | ".join(f"{p + r['Gc']:.1f}" for p in pin_list)
        out.append(f"| {i+1} | {r['name']} | {r['g']:+.1f} | {r['nf']:.1f} | {fmt(r['ip3'])} | {r['Gc']:+.1f} | "
                   f"{r['NFc']:.2f} | {fmt(r['IIP3c'])} | {n_hz:.1f} | {n_bw:.1f} | {pouts} |")
    G_pin = rows[-1]["Gc"]  # gain to ESP32 pin (ESP32 stage has 0 dB)
    iip3 = rows[-2]["IIP3c"]
    p1 = rows[-2]["P1c"]
    s = summarize(stages)
    out.append("")
    out.append(f"Gain to ESP32 pin **{G_pin:+.1f} dB**, system NF (incl. ESP32 {ESP_NF:.0f} dB) **{nfin:.2f} dB**, "
               f"front-end input IIP3 **{iip3:+.1f} dBm**, first-stage input P1dB **{p1:+.1f} dBm** (analog, excl. ESP32/ADC).  ")
    out.append(f"Noise floor at antenna: {s['n_in_hz']:.1f} dBm/Hz = {s['n_in_bw']:.1f} dBm in 40 MHz; "
               f"MDS(1 kHz, SNR 0 dB) {s['mds1k']:.1f} dBm; "
               f"8-bit ADC instantaneous DR ~{s['adc_dr']:.0f} dB in 40 MHz -> in-band clip ~**{s['clip_in']:.0f} dBm** at the antenna "
               f"(ESP32 gain set so noise sits {s['noise_over_q']:.0f} dB over quantization); "
               f"SFDR(analog, 10 kHz) {s['sfdr10k']:.0f} dB.\n")
    return "\n".join(out), rows

def summarize(stages, noise_over_q=6.0):
    rows = cascade(stages)
    nf = rows[-1]["NFc"]
    n_in_hz = KT + nf
    n_in_bw = n_in_hz + lin2db(BW_CAP)
    q_snr = 6.02 * ADC_BITS + 1.76          # full-scale sine vs quantization noise over Nyquist (complex BW)
    # analog noise placed noise_over_q dB above quantization noise -> sits at -(q_snr - noise_over_q) dBFS
    noise_dbfs = -(q_snr - noise_over_q)
    adc_dr = -noise_dbfs                    # FS sine to integrated noise
    clip_in = n_in_bw + adc_dr              # CW at antenna that reaches 0 dBFS (sine FS)
    iip3 = rows[-2]["IIP3c"]
    sfdr10k = 2 / 3 * (iip3 - (n_in_hz + 40)) if iip3 < INF - 1 else INF
    return dict(nf=nf, G=rows[-1]["Gc"], n_in_hz=n_in_hz, n_in_bw=n_in_bw, mds1k=n_in_hz + 30,
                adc_dr=adc_dr, clip_in=clip_in, iip3=iip3, p1=rows[-2]["P1c"], sfdr10k=sfdr10k,
                noise_over_q=noise_over_q)

def main():
    global ESP_NF
    md = ["# Cascade tables (auto-generated by analysis/cascade.py)\n",
          f"Assumptions: kT = {KT} dBm/Hz, capture BW = {BW_CAP/1e6:.0f} MHz complex, {ADC_BITS}-bit I/Q, ESP32 NF = {ESP_NF} dB.  ",
          "Pout columns = signal level at the *output* of each stage for the given antenna power (small-signal, ignores compression).  ",
          "'Noise out' = thermal + added noise density at each node.  ESP32 row = level at the ESP32 RF pin (before its internal gain).\n"]
    cases = [("LB 100 MHz", lb_chain(100)), ("LB 1090 MHz", lb_chain(1090)), ("LB 1600 MHz", lb_chain(1600)),
             ("HB 3500 MHz", hb_chain(3500)), ("HB 5800 MHz", hb_chain(5800)),
             ("LB 1090 MHz + optional IF LNA", lb_chain(1090, True)),
             ("HB 5800 MHz + optional IF LNA", hb_chain(5800, True)),
             ("LB 100 MHz + gain block", lb_chain(100, gb=True)),
             ("LB 1090 MHz + gain block", lb_chain(1090, gb=True)),
             ("LB 1600 MHz + gain block", lb_chain(1600, gb=True)),
             ("HB 3500 MHz + gain block", hb_chain(3500, gb=True)),
             ("HB 5800 MHz + gain block", hb_chain(5800, gb=True)),
             ("Native ESP32 path 2441 MHz", native_chain())]
    summ = ["| Case | Gain to ESP32 pin | NF | IIP3 in | P1dB in | Noise dBm/40MHz | MDS 1 kHz | ADC clip @ant. | SFDR 10 kHz |",
            "|---|---|---|---|---|---|---|---|---|"]
    for title, st in cases:
        t, rows = node_table(title, st)
        md.append(t)
        s = summarize(st)
        summ.append(f"| {title} | {s['G']:+.1f} | {s['nf']:.2f} | {fmt(s['iip3'])} | {fmt(s['p1'])} | {s['n_in_bw']:.1f} | "
                    f"{s['mds1k']:.1f} | {s['clip_in']:.0f} | {fmt(s['sfdr10k'],3,0)} |")
    md.insert(4, "## Summary\n\n" + "\n".join(summ) + "\n\n## Node tables\n")

    # ESP32 NF sensitivity
    sens = ["\n## Sensitivity of system NF to the (unknown) ESP32 NF\n",
            "| ESP32 NF | LB 1090 | LB 1090 +IF LNA | LB 1090 +gain blk | HB 5800 | HB 5800 +IF LNA | HB 5800 +gain blk | Native |", "|---|---|---|---|---|---|---|---|"]
    base = ESP_NF
    for e in [3, 5, 8, 10]:
        ESP_NF = e
        v = [summarize(lb_chain(1090))['nf'], summarize(lb_chain(1090, True))['nf'], summarize(lb_chain(1090, gb=True))['nf'],
             summarize(hb_chain(5800))['nf'], summarize(hb_chain(5800, True))['nf'], summarize(hb_chain(5800, gb=True))['nf'],
             summarize(native_chain())['nf']]
        sens.append(f"| {e} dB | " + " | ".join(f"{x:.2f}" for x in v) + " |")
    ESP_NF = base
    md += sens
    with open(os.path.join(EXP, "cascade_tables.md"), "w") as f:
        f.write("\n".join(md) + "\n")

    # ------------------------------------------------------------- plot 1: NF contribution (stacked share)
    BLUE, ORANGE, AQUA, YELLOW, MAG, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
    groups = {"Input loss (SMA/ESD/SPDT_in)": BLUE, "LNA": ORANGE, "Post-LNA loss (filter/SPDT/balun)": AQUA,
              "Mixer": YELLOW, "IF filter / match / IF amp": MAG, "ESP32 RX": GREEN}
    def grp(n):
        if n.startswith("SMA") or n.startswith("SPDT_in") or n.startswith("Pre-LNA"): return "Input loss (SMA/ESD/SPDT_in)"
        if n.startswith("LNA"): return "LNA"
        if n.startswith("Post-LNA") or n.startswith("SPDT_out") or n.startswith("Input balun"): return "Post-LNA loss (filter/SPDT/balun)"
        if "mixer" in n: return "Mixer"
        if n.startswith("ESP32"): return "ESP32 RX"
        return "IF filter / match / IF amp"
    pc = [("LB 100", lb_chain(100)), ("LB 1090", lb_chain(1090)), ("LB 1600", lb_chain(1600)),
          ("HB 3500", hb_chain(3500)), ("HB 5800", hb_chain(5800)),
          ("LB 1090\n+IF LNA", lb_chain(1090, True)), ("HB 5800\n+IF LNA", hb_chain(5800, True)),
          ("LB 1090\n+gain blk", lb_chain(1090, gb=True)), ("HB 5800\n+gain blk", hb_chain(5800, gb=True)),
          ("Native\n2441", native_chain())]
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=130)
    x = np.arange(len(pc))
    bottoms = np.zeros(len(pc))
    for gname, col in groups.items():
        vals = []
        for _, st in pc:
            parts = nf_contrib(st)
            Ftot = 1 + sum(p for _, p in parts)
            share = sum(p for n, p in parts if grp(n) == gname)
            vals.append(lin2db(Ftot) * share / (Ftot - 1))   # apportion total NF (dB) by share of F-1
        vals = np.array(vals)
        ax.bar(x, vals, 0.62, bottom=bottoms, color=col, label=gname, edgecolor="white", linewidth=1.5)
        bottoms += vals
    for i, b in enumerate(bottoms):
        ax.text(i, b + 0.12, f"{b:.1f} dB", ha="center", va="bottom", fontsize=8.5, color="#333")
    ax.set_xticks(x, [p[0] for p in pc], fontsize=8.5)
    ax.set_ylabel("System noise figure (dB), split by stage")
    ax.set_title("Where the noise figure comes from (ESP32 NF assumed 5 dB)", fontsize=10.5, loc="left")
    ax.spines[["top", "right"]].set_visible(False); ax.grid(axis="y", color="#e5e5e5"); ax.set_axisbelow(True)
    ax.legend(fontsize=7.5, frameon=False, ncol=3, loc="upper left")
    ax.set_ylim(0, max(bottoms) * 1.35)
    fig.tight_layout(); fig.savefig(os.path.join(EXP, "auto_nf_contrib.png")); plt.close(fig)

    # ------------------------------------------------------------- plot 2: level diagram LB 1090
    for tag, st in [("lb1090", lb_chain(1090, gb=True)), ("hb5800", hb_chain(5800, gb=True))]:
        rows = cascade(st)
        names = ["Antenna"] + [r["name"] for r in rows]
        G = [0.0] + [r["Gc"] for r in rows]
        NFc = [0.0] + [r["NFc"] for r in rows]
        noise40 = [KT + lin2db(BW_CAP) + n + g for n, g in zip(NFc, G)]
        noise1k = [KT + 30 + n + g for n, g in zip(NFc, G)]
        fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=130)
        xs = np.arange(len(names))
        for pin, col, lab in [(-30, ORANGE, "Strong signal, -30 dBm at antenna"),
                              (-100, BLUE, "Weak signal, -100 dBm at antenna")]:
            ax.plot(xs, [pin + g for g in G], "-o", color=col, lw=2, ms=5, label=lab)
        ax.plot(xs, noise40, "--", color="#666", lw=2, label="Noise in 40 MHz (whole capture)")
        ax.plot(xs, noise1k, ":", color="#666", lw=2, label="Noise in 1 kHz")
        p1o = [None] + [r["p1"] + r["g"] - 1 if r["p1"] < INF - 1 else None for r in rows]
        px = [i for i, v in enumerate(p1o) if v is not None]
        ax.scatter(px, [p1o[i] for i in px], marker="v", s=55, color="#c0392b", zorder=5, label="Stage output P1dB")
        ax.set_xticks(xs, names, rotation=28, ha="right", fontsize=7.8)
        ax.set_ylabel("Power at stage output (dBm)")
        ax.set_title(f"Node power levels, mixer path with gain block, {'LB 1090 MHz' if tag=='lb1090' else 'HB 5800 MHz'}", fontsize=10.5, loc="left")
        ax.spines[["top", "right"]].set_visible(False); ax.grid(color="#ececec"); ax.set_axisbelow(True)
        ax.legend(fontsize=7.5, frameon=False, loc="upper left", ncol=2)
        ax.set_ylim(-150, 35)
        fig.tight_layout(); fig.savefig(os.path.join(EXP, f"auto_levels_{tag}.png")); plt.close(fig)

    print("\n".join(summ))
    print("\n".join(sens))

if __name__ == "__main__":
    main()

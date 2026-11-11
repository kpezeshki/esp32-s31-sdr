#!/usr/bin/env python3
"""Cascade with the parts chosen in PART_SELECTION.md (rev 3, 2026-11-09: SP3T BGS13SN8, mid band, HB from 3.1 GHz).
Switch-first chain + 3 dB pad before ESP32 (R1). Compares GVA-63+ vs GVA-62+ gain block."""
import numpy as np
import cascade as c

def gb(f, which):
    if which == "gva63":   # [DS] 21.9/21.1/19.9/18.5/17.3/15.9 dB @0.05/0.8/2/3/4/6 GHz; NF 3.6-4.6; OIP3 ~+33.5..+35 (assume +30 @6G); OP1dB ~+19 (assume)
        g = np.interp(f, [50, 800, 2000, 3000, 4000, 6000], [21.9, 21.1, 19.9, 18.5, 17.3, 15.9])
        nf = np.interp(f, [50, 800, 2000, 3000, 4000, 6000], [3.6, 3.8, 3.7, 3.7, 4.0, 4.6])
        oip3 = np.interp(f, [50, 2000, 6000], [33.5, 34.8, 30.0]); op1 = 19.0
    else:                  # GVA-62+ [DS] 16.5/15.6/15.4/15.3/15.0/14.5 dB; NF 4.7-5.1; OIP3 +37.8/+37.5/+33.6/+30.4/+28.1/+2x
        g = np.interp(f, [50, 1000, 2000, 3000, 4000, 6000], [16.5, 15.6, 15.4, 15.3, 15.0, 14.5])
        nf = np.interp(f, [50, 1000, 2000, 6000], [4.7, 5.0, 5.1, 5.5])
        oip3 = np.interp(f, [50, 1000, 2000, 3000, 4000, 6000], [37.8, 37.5, 33.6, 30.4, 28.1, 26.0]); op1 = 18.0
    return ("Gain block " + which.upper(), float(g), float(nf), float(oip3 - g), float(op1 - g + 1))

def sw3(f):
    """BGS13SN8 SP3T [DS typ]: 0.22 (0.7-0.96G), 0.25 (1.4-2.0G), 0.28 (1.9-2.2G), 0.33 (2.2-2.7G), 0.65 (5.15-5.7G); 6 GHz extrapolated."""
    return float(np.interp(f, [100, 960, 1990, 2170, 2690, 5400, 6000], [0.22, 0.22, 0.25, 0.28, 0.33, 0.65, 0.75]))

def lb(f, gbw, mb=False):
    # PSA4-5043+ [DS] 18.4 dB/0.75 dB @1 GHz, NF 0.98 @2 GHz, OIP3 +33.5, OP1dB +21 @5V; <1 GHz gain extrapolated (ASSUMPTION)
    g = float(np.interp(f, [100, 500, 1000, 1750], [22.0, 20.5, 18.4, 15.5]))
    nf = float(np.interp(f, [100, 1000, 1750], [0.9, 0.75, 0.9]))
    if mb:   # mid band 1.75-2.15 GHz: PSA4 gain ~15-14 dB, NF ~0.95; lumped 0402 BPF with IF notch ~2.0 dB (ASSUMPTION)
        g = float(np.interp(f, [1750, 2150], [15.5, 14.0])); nf = float(np.interp(f, [1750, 2150], [0.9, 1.0]))
        filt, fname = 2.0, "BPF MB lumped 0402"
    else:
        filt, fname = float(np.interp(f, [100, 1700], [0.5, 0.9])), "LPF LFCG-1700+"   # [DS] 0.91 dB @1.7 GHz
    st = [c.passive("SMA + ESD + trace", 0.3), c.passive("SP3T_in BGS13SN8", sw3(f), ip3=70, p1=34),
          ("LNA_LB PSA4-5043+", g, nf, 33.5 - g, 21 - g + 1), c.passive(fname, filt),
          c.passive("SP3T_out BGS13SN8", sw3(f), ip3=70, p1=34)]
    if gbw: st.append(gb(f, gbw))
    st += [c.passive("Balun H3-TCM2-63WX+", float(np.interp(f, [100, 1750], [0.9, 1.1]))),
           ("RFFC5072 + 4:1 balun", -5.0, 13.0, 22.0, 11.0), c.passive("SAW SAFEA2G45MC0", 2.5),
           c.passive("0R tee", 0.1), c.passive("3 dB pad (R1)", 3.0), c.passive("ESP32 match", 0.3), c.esp32()]
    return st

def hb(f, gbw):
    sw = sw3(f)
    g = float(np.interp(f, [3000, 5500, 6000], [22.0, 21.6, 21.0])); nf = float(np.interp(f, [3000, 6000], [0.8, 1.0]))  # QPL9503 [DS @5.5G]
    st = [c.passive("SMA + ESD + trace", float(np.interp(f, [3000, 6000], [0.4, 0.6]))),
          c.passive("SP3T_in BGS13SN8", sw, ip3=70, p1=34), c.passive("Pre-LNA HPF 2nd order", 0.3),
          ("LNA_HB QPL9503", g, nf, 35.5 - g, 19 - g + 1),
          c.passive("HPF lumped 0402 (3.1G, IF notch)", float(np.interp(f, [3100, 3400, 6000], [2.0, 1.5, 1.5]))),
          c.passive("SP3T_out BGS13SN8", sw, ip3=70, p1=34)]
    if gbw: st.append(gb(f, gbw))
    st += [c.passive("Balun H3-TCM2-63WX+", float(np.interp(f, [3000, 5000, 6000], [1.5, 2.5, 2.5]))),
           ("RFFC5072 + 4:1 balun", float(np.interp(f, [3000, 6000], [-6, -8])), float(np.interp(f, [3000, 6000], [14, 16])),
            float(np.interp(f, [3000, 6000], [20, 16])), float(np.interp(f, [3000, 6000], [8, 4]))),
           c.passive("SAW SAFEA2G45MC0", 2.5), c.passive("0R tee", 0.1), c.passive("3 dB pad (R1)", 3.0),
           c.passive("ESP32 match", 0.3), c.esp32()]
    return st

if __name__ == "__main__":
    rows = ["| Case | Gain block | Gain to ESP32 pin | NF | IIP3 in | P1dB in | ADC clip @ant. |", "|---|---|---|---|---|---|---|"]
    for gbw in (None, "gva62", "gva63"):
        for lab, fn, f in [("LB 100", lb, 100), ("LB 1090", lb, 1090), ("LB 1700", lb, 1700),
                           ("MB 1800", lambda f, g: lb(f, g, mb=True), 1800), ("MB 2100", lambda f, g: lb(f, g, mb=True), 2100),
                           ("HB 3200", hb, 3200), ("HB 3500", hb, 3500), ("HB 5800", hb, 5800)]:
            s = c.summarize(fn(f, gbw))
            rows.append(f"| {lab} | {gbw or 'none'} | {s['G']:+.1f} | {s['nf']:.2f} | {s['iip3']:+.1f} | {s['p1']:+.1f} | {s['clip_in']:.0f} |")
    out = "\n".join(rows)
    open(c.os.path.join(c.EXP, "cascade_parts.md"), "w").write("# Cascade with selected parts (cascade_parts.py)\n\n" + out + "\n")
    print(out)

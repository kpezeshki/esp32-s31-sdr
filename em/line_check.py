#!/usr/bin/env python3
"""Z0 of the 0.19 mm RF trace on the JLC stack with coplanar ground pour (F.Cu GND, stitched to L2) at gap g.
Extract Z0 = sqrt(B/C) from the ABCD matrix of a 6 mm line (Sonnet, box-wall ports, de-embedded)."""
import os, numpy as np, filter_em as E
OUT = os.path.join(E.HERE, "lines"); os.makedirs(OUT, exist_ok=True)
L = 6.0; W = E.W50
def son(path, gap, width=W):
    H = 3.0; yc = H / 2
    rects = [(0.0, yc - width / 2, L, yc + width / 2)]
    vias = []
    if gap is not None:
        rects += [(0.0, 0.2, L, yc - width / 2 - gap), (0.0, yc + width / 2 + gap, L, H - 0.2)]
        for x in np.arange(0.5, L, 1.0):
            vias += [(x, (0.2 + yc - width / 2 - gap) / 2), (x, (yc + width / 2 + gap + H - 0.2) / 2)]
    um = lambda v: round(v / 0.01) * 10.0
    S = ["FTYP SONPROJ 1 ! Sonnet Project File", "VER 19.54", "HEADER", "END HEADER", "DIM", "FREQ GHZ", "IND NH", "LNG UM", "ANG DEG",
         "CON /OH", "CAP PF", "RES OH", "END DIM", "FREQ", "SWEEP 0.5 6.5 0.5", "END FREQ", "CONTROL", "STD", "OPTIONS  -d", "SPEED 0",
         "END CONTROL", "GEO", 'TMET "Lossless" 0 SUP 0 0 0 0', 'BMET "Lossless" 0 SUP 0 0 0 0', 'MET "Cu35" 1 NOR 5.8e7 0 35',
         "BOX 1 %.1f %.1f %d %d 20 0" % (L * 1000, H * 1000, int(L / 0.01), int(H / 0.01)),
         '      1000.0 1 1 0 0 0 0 "Air"', '      %.1f %.4f 1 %.4f 0 0 0 "PP3313"' % (E.H_PP * 1000, E.ER_PP, E.TAN_PP),
         "POR1 STD", "POLY 1 1", "3", "1 50 0 0 0 0.0 %.1f" % um(yc), "POR1 STD", "POLY 1 1", "1", "2 50 0 0 0 %.1f %.1f" % (L * 1000, um(yc))]
    polys = []
    for i, (x0, y0, x1, y1) in enumerate(rects):
        polys.append(["0 5 0 N %d 1 1 100 100 0 0 0 Y" % (i + 1)] + ["%.1f %.1f" % (um(a), um(b)) for a, b in [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]] + ["END"])
    for j, (x, y) in enumerate(vias):
        r = 0.15
        polys.append(["VIA POLYGON", "0 5 0 V %d 1 1 100 100 0 0 0 Y" % (100 + j), "TOLEVEL GND RING COVERS"] +
                     ["%.1f %.1f" % (um(a), um(b)) for a, b in [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r), (x - r, y - r)]] + ["END"])
    S += ["NUM %d" % len(polys)] + sum(polys, []) + ["END GEO", "FILEOUT", "TS D Y $BASENAME.s2p 15 S RI R 50.00000", "END FILEOUT"]
    open(path, "w").write("\n".join(S) + "\n")
res = []
for gap in [None, 0.4, 0.3, 0.2, 0.15]:
    for width in ([W, 0.17, 0.16] if gap in (0.2, 0.15) else [W]):
        tag = f"w{width:.2f}_g{'inf' if gap is None else gap}"
        p = os.path.join(OUT, tag + ".son"); son(p, gap, width); E.run_em(p)
        f, S = E.read_touchstone(os.path.join(OUT, tag + ".s2p"), 2)
        z0s = []
        for k in range(len(f)):
            s11, s21, s12, s22 = S[k, 0, 0], S[k, 1, 0], S[k, 0, 1], S[k, 1, 1]
            Bm = 50 * ((1 + s11) * (1 + s22) - s12 * s21) / (2 * s21); Cm = (1 / 50) * ((1 - s11) * (1 - s22) - s12 * s21) / (2 * s21)
            z0s.append(np.sqrt(Bm / Cm).real)
        il = -20 * np.log10(np.abs(S[:, 1, 0]))
        res.append((tag, np.median(z0s), il[np.argmin(abs(f - 6e9))] / L))
        print(f"{tag}: Z0 = {np.median(z0s):.1f} ohm, loss @6 GHz {il[np.argmin(abs(f - 6e9))] / L:.3f} dB/mm", flush=True)
open(os.path.join(OUT, "Z0_REPORT.md"), "w").write("# RF trace Z0 vs coplanar ground gap (Sonnet)\n\n| case | Z0 (ohm) | loss @ 6 GHz (dB/mm) |\n|---|---|---|\n" +
    "\n".join(f"| {t} | {z:.1f} | {l:.3f} |" for t, z, l in res) + "\n")

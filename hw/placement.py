"""Placement + scripted RF routing for build_pcb.py. Board coordinates in mm, origin top-left, y down."""
import pcbnew
import build_pcb as BP
from build_pcb import P

W = BP.W50

def conn(B, a, b, net, w=W, layer=pcbnew.F_Cu, corner="hv"):
    """Orthogonal 2-segment connection between points a and b ('hv': horizontal first)."""
    (x0, y0), (x1, y1) = a, b
    if abs(x0 - x1) < 1e-6 or abs(y0 - y1) < 1e-6:
        B.track(a, b, w, layer, net); return
    m = (x1, y0) if corner == "hv" else (x0, y1)
    B.track(a, m, w, layer, net); B.track(m, b, w, layer, net)

def pp(B, ref, num): return B.padxy(ref, num)

def series_h(B, ref, x, y):
    """0402 series part centred so pad1 is left at x and pad2 right; returns (pad1, pad2) centres."""
    B.place(ref, x + 0.48, y, 0)
    return (x, y), (x + 0.96, y)

def shunt_at(B, ref, x, y, down=True, gnd_via=True):
    """0402 shunt part with pad1 on the line point (x,y); pad2 (GND) away from the line + via."""
    B.place(ref, x, y + (0.48 if down else -0.48), -90 if down else 90)
    if gnd_via:
        yv = y + (0.96 + 0.55 if down else -(0.96 + 0.55))
        B.track((x, y + (0.96 if down else -0.96)), (x, yv), 0.3, net="GND"); B.via(x, yv)

def gnd_via_at(B, ref, num, dx=0.0, dy=0.7):
    x, y = pp(B, ref, num); B.track((x, y), (x + dx, y + dy), 0.3, net="GND"); B.via(x + dx, y + dy)

def place_all(B, D):
    # ================================================================ RF front end
    Y_IN = 13.5                     # SMA_MIX / SP3T_in centre line
    B.place("J1", 2.1, Y_IN, -90)   # edge SMA on left edge (PCB-edge line at origin + 2.1 along the connector axis)
    xin = pp(B, "J1", "1")
    x = xin[0] + 2.3
    shunt_at(B, "D301", x, Y_IN)                         # RF ESD
    p1, p2 = series_h(B, "C301", x + 0.7, Y_IN)          # DC block
    BP_line = lambda a, b, n: B.track(a, b, W, pcbnew.F_Cu, n)
    BP_line((xin[0] + 0.5, Y_IN), p1, "RF_IN_SMA")
    XS_IN = p2[0] + 1.6
    B.place("U20", XS_IN, Y_IN, 180)                     # SP3T_in: RFin ML, RF1 TL (LB), RF3 TM (HB), RF2 BL (MB)
    BP_line(p2, pp(B, "U20", "6"), "SW1_COM")
    B.place("C302", XS_IN + 1.75, Y_IN + 2.1, 0)          # VDD bypass (pin1 is BR after rotation)
    # rows
    Y_LB, Y_HB, Y_MB = 4.5, Y_IN - 1.3, 22.5
    XS_OUT, YS_OUT = 33.0, Y_HB - 1.3
    # ---- LB branch: RF1 (TL) up to LB row
    a = pp(B, "U20", "5"); B.track(a, (a[0], Y_LB), W, net="LB_IN")
    x = a[0]
    B.track((a[0], Y_LB), (x + 0.6, Y_LB), W, net="LB_IN")
    p1, p2 = series_h(B, "C310", x + 0.6, Y_LB)
    B.place("U21", p2[0] + 1.8, Y_LB + 0.65, 180)       # PSA4: RF-IN TL, RF-OUT BR
    conn(B, p2, pp(B, "U21", "3"), "LB_LNA_I")
    for g in ("2", "4"): gnd_via_at(B, "U21", g, 0, -0.7 if g == "2" else 0.7)
    o = pp(B, "U21", "1"); y_lbf = o[1]
    # bias: L310 vertical down from output node, L311 1uH, C311/C312
    B.place("L310", o[0] + 0.6, y_lbf + 1.1, -90); conn(B, o, pp(B, "L310", "1"), "LB_LNA_O", 0.2, corner="hv")
    B.place("L311", o[0] + 0.6, y_lbf + 3.6, -90)
    B.track(pp(B, "L310", "2"), pp(B, "L311", "1"), 0.25, net="LB_CHK")
    B.place("C311", o[0] - 0.6, y_lbf + 2.2, -90); B.track(pp(B, "C311", "1"), pp(B, "L310", "2"), 0.25, net="LB_CHK"); gnd_via_at(B, "C311", "2")
    p1, p2 = series_h(B, "C313", o[0] + 1.4, y_lbf)
    B.track(o, p1, W, net="LB_LNA_O")
    xe = BP.place_ladder(B, "FLB", "LB_LPF", p2[0], y_lbf, "LB_F_IN", "LB_OUT")
    # ---- HB branch: RF3 (TM) up 0.9 then right
    a = pp(B, "U20", "4"); B.track(a, (a[0], Y_HB), W, net="HB_IN")
    xe_hp = BP.place_ladder(B, "FHP", "HB_PRE", a[0], Y_HB, "HB_IN", "HB_PRE_O")
    p1, p2 = series_h(B, "C350", xe_hp, Y_HB)
    shunt_at(B, "C351", p2[0] + 0.35, Y_HB, down=True)
    B.place("U23", p2[0] + 2.3, Y_HB + 0.25, 0)          # QPL9503: pin2 in (-1,-0.25), pin7 out (1,-0.25)
    B.track(p2, pp(B, "U23", "2"), W, net="HB_LNA_I")
    ep = pp(B, "U23", "9")
    B.via(ep[0], ep[1] - 0.4, d=0.5, drill=0.2); B.via(ep[0], ep[1] + 0.4, d=0.5, drill=0.2)
    o = pp(B, "U23", "7")
    B.place("L350", o[0] + 1.0, Y_HB - 1.45, 90); conn(B, (o[0] + 1.0, o[1]), pp(B, "L350", "1"), "HB_LNA_O", 0.2, corner="vh")
    p1, p2 = series_h(B, "C355", o[0] + 1.5, Y_HB); B.track(o, p1, W, net="HB_LNA_O")
    xe = BP.place_ladder(B, "FHB", "HB_HPF", p2[0], Y_HB, "HB_F_IN", "HB_HPF_O")
    p1, p2 = series_h(B, "R352", xe + 0.3, Y_HB); B.track((xe - 0.28, Y_HB), p1, W, net="HB_HPF_O")
    # ---- MB branch: RF2 (BL) down to MB row
    a = pp(B, "U20", "7"); B.track(a, (a[0], Y_MB), W, net="MB_IN")
    x = a[0]
    B.track((a[0], Y_MB), (x + 0.6, Y_MB), W, net="MB_IN")
    p1m, p2m = series_h(B, "C330", x + 0.6, Y_MB)
    B.place("U22", p2m[0] + 1.8, Y_MB + 0.65, 180)
    conn(B, p2m, pp(B, "U22", "3"), "MB_LNA_I")
    for g in ("2", "4"): gnd_via_at(B, "U22", g, 0, -0.7 if g == "2" else 0.7)
    o = pp(B, "U22", "1"); y_mbf = o[1]
    B.place("L330", o[0] + 0.6, y_mbf + 1.1, -90); conn(B, o, pp(B, "L330", "1"), "MB_LNA_O", 0.2)
    B.place("L331", o[0] + 0.6, y_mbf + 3.6, -90); B.track(pp(B, "L330", "2"), pp(B, "L331", "1"), 0.25, net="MB_CHK")
    B.place("C331", o[0] - 0.6, y_mbf + 2.2, -90); B.track(pp(B, "C331", "1"), pp(B, "L330", "2"), 0.25, net="MB_CHK"); gnd_via_at(B, "C331", "2")
    xe_mb = BP.place_ladder(B, "FMB", "MB_BPF2", o[0] + 0.0, y_mbf, "MB_LNA_O", "MB_OUT", flip=True)
    # ---- SP3T_out (rot 0): RFin MR, RF2 TR <- LB, RF3 BM <- HB, RF1 BR <- MB  (LB_OUT=RF1 net, so ports are re-labelled in design)
    B.place("U24", XS_OUT, YS_OUT, 0)
    B.place("C360", XS_OUT - 1.3, YS_OUT - 1.2, 0)
    # branch outputs into SP3T_out
    t7, t4, t5, t6 = pp(B, "U24", "7"), pp(B, "U24", "4"), pp(B, "U24", "5"), pp(B, "U24", "6")
    lb_end = (max(xe for xe in [B.padxy("FLB9", "2")[0]]) , y_lbf)
    conn(B, (B.padxy("FLB9", "2")[0] + 0.3, y_lbf), t7, "LB_OUT")
    conn(B, B.padxy("R352", "2"), t4, "HB_OUT")
    mb_last = B.padxy("FMB14", "2")
    conn(B, mb_last, t5, "MB_OUT")
    g8 = pp(B, "U24", "8"); B.track(g8, (g8[0], g8[1] - 0.45), 0.2, net="GND"); B.track((g8[0], g8[1] - 0.45), (g8[0] - 0.45, g8[1] - 0.9), 0.2, net="GND"); B.via(g8[0] - 0.45, g8[1] - 0.9, d=0.45, drill=0.2)
    g8 = pp(B, "U20", "8"); B.track(g8, (g8[0], g8[1] + 0.45), 0.2, net="GND"); B.track((g8[0], g8[1] + 0.45), (g8[0] + 0.45, g8[1] + 0.9), 0.2, net="GND"); B.via(g8[0] + 0.45, g8[1] + 0.9, d=0.45, drill=0.2)
    # ================================================================ gain block (straight main line with DNP bypass R360)
    YG = 18.5
    o = (t6[0] + 1.0, t6[1]); B.track(t6, o, W, net="SW2_COM"); B.track(o, (o[0], YG), W, net="SW2_COM")
    xa = o[0] + 1.6; xb = xa + 3.0
    B.track((o[0], YG), (xa, YG), W, net="SW2_COM")
    B.place("R360", (xa + xb) / 2, YG, 0)
    B.track((xa, YG), B.padxy("R360", "1"), W, net="SW2_COM"); B.track(B.padxy("R360", "2"), (xb, YG), W, net="MIX_DRV")
    B.place("U25", (xa + xb) / 2, YG - 1.6 - 1.95, 90)     # GVA-62+: pin1 bottom-left, pin3 bottom-right, tab up
    B.place("C361", xa, YG - 0.48, 90)                      # pad1 on line (A), pad2 up toward pin1
    B.track(B.padxy("C361", "2"), B.padxy("U25", "1"), 0.3, net="GB_I")
    B.place("C364", xb, YG - 0.48, -90)                     # pad1 (GB_O) up, pad2 on line (B)
    B.track(B.padxy("C364", "1"), B.padxy("U25", "3"), 0.3, net="GB_O")
    tab = B.padxy("U25", "2")
    for dx in (-0.9, 0.0, 0.9): B.via(tab[0] + dx, tab[1] - 1.3)
    p3 = B.padxy("U25", "3")
    B.place("L360", p3[0] + 1.35, p3[1], 0); B.track(p3, B.padxy("L360", "1"), 0.25, net="GB_O")
    l2 = B.padxy("L360", "2")
    B.place("C362", l2[0] + 0.86, l2[1], 0); gnd_via_at(B, "C362", "2", 0.0, 0.65)
    B.place("L361", l2[0] + 0.1, l2[1] - 2.1, 90); B.track(l2, B.padxy("L361", "1"), 0.25, net="GB_CHK")
    # ================================================================ mixer: T1 balun, RFFC5072 (rot -90: MIX in at bottom, IF out right, LF top, REF left)
    XR, YR = xb + 4.6, YG - 8.4
    B.place("U3", XR, YR, -90)
    p23, p24 = B.padxy("U3", "23"), B.padxy("U3", "24")
    xm = (p23[0] + p24[0]) / 2
    B.place("T1", xm, YG - 1.59, 180)                         # pin3 (primary) bottom-left on the main line
    B.track((xb, YG), B.padxy("T1", "3"), W, net="MIX_DRV")
    for g in ("1", "2"): gnd_via_at(B, "T1", g, 0, 0.8)
    t4p, t6p = B.padxy("T1", "4"), B.padxy("T1", "6")
    yj = p23[1] + 1.0                                          # jog row just below the RFFC pins
    B.place("C370", t4p[0], t4p[1] - 1.05, 90); B.track(t4p, B.padxy("C370", "1"), 0.25, net="MIX_IN_P")
    c = B.padxy("C370", "2"); B.track(c, (c[0], yj), 0.2, net="MIX_IPP"); B.track((c[0], yj), (p23[0], yj), 0.2, net="MIX_IPP"); B.track((p23[0], yj), p23, 0.2, net="MIX_IPP")
    B.place("C371", t6p[0], t6p[1] - 1.05, 90); B.track(t6p, B.padxy("C371", "1"), 0.25, net="MIX_IN_N")
    c = B.padxy("C371", "2"); B.track(c, (c[0], yj), 0.2, net="MIX_IPN"); B.track((c[0], yj), (p24[0], yj), 0.2, net="MIX_IPN"); B.track((p24[0], yj), p24, 0.2, net="MIX_IPN")
    # IF: T2 balun right of RFFC
    p27, p28 = B.padxy("U3", "27"), B.padxy("U3", "28")
    B.place("T2", p28[0] + 1.75, (p27[1] + p28[1]) / 2, -90)
    B.track(p28, B.padxy("T2", "3"), 0.2, net="IF_OP_P"); B.track(p27, B.padxy("T2", "4"), 0.2, net="IF_OP_N")
    ct = B.padxy("T2", "1")
    B.place("C390", ct[0] + 0.1, ct[1] + 1.0, -90); B.track(ct, B.padxy("C390", "1"), 0.25, net="IF_CT"); gnd_via_at(B, "C390", "2")
    B.place("C391", ct[0] + 1.2, ct[1] + 1.4, -90); B.place("R390", ct[0] + 1.2, ct[1] + 3.2, -90)
    se = B.padxy("T2", "2")
    y_if = se[1]
    B.track(se, (se[0] + 0.85, y_if), W, net="IF_SE")
    shunt_at(B, "L390", se[0] + 0.85, y_if, down=False)
    B.place("U4", se[0] + 2.2, y_if, 0)                     # SAW: in (-0.5,0), out (0.5,-0.2875)
    B.track((se[0] + 0.85, y_if), B.padxy("U4", "1"), W, net="IF_SE")
    g2, g3 = B.padxy("U4", "2"), B.padxy("U4", "3"); vm = ((g2[0] + g3[0]) / 2, g2[1] + 0.6)
    B.track(g2, vm, 0.2, net="GND"); B.track(g3, vm, 0.2, net="GND"); B.via(*vm, d=0.5, drill=0.2)
    gnd_via_at(B, "U4", "5", 0, -0.6)
    so = B.padxy("U4", "4")
    y_if2 = so[1]
    B.track(so, (so[0] + 0.5, y_if2), W, net="IF_SAW_O")
    shunt_at(B, "L391", so[0] + 0.5, y_if2, down=False)
    p1, p2 = series_h(B, "R391", so[0] + 0.8, y_if2); B.track((so[0] + 0.5, y_if2), p1, W, net="IF_SAW_O")
    xn = p2[0] + 0.35                                         # ESP_RF_SEL node (tee with native path from above)
    B.track(p2, (xn, y_if2), W, net="ESP_RF_SEL")
    B.place("R392", xn, y_if2 - 0.48 - 0.25, -90)             # DNP native tee: pad1 (NAT_RF) up, pad2 down to node
    B.track(B.padxy("R392", "2"), (xn, y_if2), W, net="ESP_RF_SEL")
    shunt_at(B, "R393", xn + 0.4, y_if2, down=True)
    p1, p2 = series_h(B, "R394", xn + 0.7, y_if2); B.track((xn, y_if2), p1, W, net="ESP_RF_SEL")
    shunt_at(B, "R395", p2[0] + 0.3, y_if2, down=True)
    p1c, p2c = series_h(B, "C392", p2[0] + 0.6, y_if2); B.track(p2, p1c, W, net="PAD_O")
    shunt_at(B, "C393", p2c[0] + 0.3, y_if2, down=True)
    p1l, p2l = series_h(B, "L392", p2c[0] + 0.6, y_if2); B.track(p2c, p1l, W, net="MATCH_I")
    # ESP32: pin1 (ANT) on the IF line
    xe1 = p2l[0] + 1.6
    B.place("U1", xe1 + 3.9, y_if2 + 3.325, 0)
    ant = B.padxy("U1", "1")
    B.track(p2l, ant, W, net="ESP_ANT")
    shunt_at(B, "C394", p2l[0] + 0.4, y_if2, down=False)
    # native SMA on the top edge above the tee
    B.place("J2", xn, 2.1, 180)
    nat = B.padxy("J2", "1")
    B.track((xn, nat[1] + 1.6), B.padxy("R392", "1"), W, net="NAT_RF")
    shunt_at(B, "D302", xn, nat[1] + 2.4, down=False) if False else None
    B.place("D302", xn + 0.48, nat[1] + 2.6, 0)             # shunt ESD beside the line: pad1 on line
    for gpad in (("J1", "2"), ("J2", "2")):
        pass
    # reserve the RF region (front end, mixer, IF) against auto-placement of unrelated passives
    RF_CORRIDORS[:] = [(0.0, 0.0, 34.5, 27.0), (34.5, 0.0, 56.0, 20.5)]
    place_rest(B, D)
    return Y_LB, Y_HB, Y_MB

def route_rf(B):
    pass

def zones(B):
    # In1.Cu: solid GND (voids come from the keepout rule areas placed with the ladders)
    pts = [(0.3, 0.3), (BP.BW - 0.3, 0.3), (BP.BW - 0.3, BP.BH - 0.3), (0.3, BP.BH - 0.3)]
    B.poly_zone(pts, pcbnew.In1_Cu, "GND", name="GND_L2")
    rf = [(0.3, 0.3), (57.0, 0.3), (57.0, 21.0), (35.0, 21.0), (35.0, 28.5), (0.3, 28.5)]
    B.poly_zone(rf, pcbnew.In2_Cu, "GND", name="GND_L3_RF", priority=1)
    B.poly_zone(pts, pcbnew.In2_Cu, "3V3", name="3V3_L3", priority=0)
    import os
    if not os.environ.get("NO_OUTER_POUR"):
        B.poly_zone(pts, pcbnew.B_Cu, "GND", name="GND_L4", priority=0)
        B.poly_zone(pts, pcbnew.F_Cu, "GND", name="GND_L1", priority=0)

# ==================================================================== non-RF placement
FIXED = {   # ref: (x, y, rot)
    "Y1": (36.6, 7.2, 0), "U8": (45.0, 26.0, 0), "U9": (3.4, 4.8, 90), "U10": (29.0, 27.5, 0), "U11": (29.0, 17.5, 0),
    "U12": (38.5, 24.5, 0), "U2": (66.2, 26.0, 90), "J4": (66.4, 36.0, 90), "U5": (58.4, 36.0, 90), "U6": (52.5, 30.5, 0),
    "U7": (43.0, 34.0, 0), "U201": (44.0, 50.0, 180), "Y201": (44.0, 55.6, 0), "J201": (58.0, 59.2, 180),
    "J5": (6.0, 64.0, 90), "SW1": (16.0, 64.0, 0), "SW2": (25.0, 64.0, 0), "D101": (33.0, 66.5, 0), "J3": (2.1, 36.0, -90),
    "FB401": (59.0, 42.0, 0), "C401": (61.5, 44.0, 0),
}
for i in range(1, 9):
    FIXED[f"TP{i}"] = (4.0 + 3.0 * (i - 1), 55.0, 0)

def bbox(fp, margin=0.15):
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False)
    return (pcbnew.ToMM(bb.GetX()) - BP.OX - margin, pcbnew.ToMM(bb.GetY()) - BP.OY - margin,
            pcbnew.ToMM(bb.GetRight()) - BP.OX + margin, pcbnew.ToMM(bb.GetBottom()) - BP.OY + margin)

def overlap(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

def place_rest(B, D):
    for ref, (x, y, r) in FIXED.items():
        if ref in B.fps: B.place(ref, x, y, r)
    def _onboard(r):
        x, y = P(B.fps[r].GetPosition()); return 0 <= x <= BP.BW and 0 <= y <= BP.BH
    placed = set(FIXED) | {r for r in B.fps if _onboard(r)}
    boxes = {r: bbox(B.fps[r]) for r in placed}
    # escape rings around fine-pitch QFNs: no auto-placed passives within ~1.1 mm of the pin rows
    for ic, ring in (("U1", 1.15), ("U201", 1.15), ("U3", 0.9)):
        if ic in B.fps:
            x0, y0, x1, y1 = bbox(B.fps[ic], 0.0)
            boxes["_ring_" + ic] = (x0 - ring, y0 - ring, x1 + ring, y1 + ring)
    for k, t in enumerate(B.b.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA):
            (x, y) = P(t.GetPosition()); r = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + 0.15
            boxes[f"_v{k}"] = (x - r, y - r, x + r, y + r)
        else:
            (xa, ya), (xb, yb) = P(t.GetStart()), P(t.GetEnd()); w = pcbnew.ToMM(t.GetWidth()) / 2 + 0.15
            boxes[f"_t{k}"] = (min(xa, xb) - w, min(ya, yb) - w, max(xa, xb) + w, max(ya, yb) + w)
    # keep a corridor free over the RF lines (no auto-placed parts on top of RF)
    parts = {p["ref"]: p for p in D.parts}
    ics = [r for r in placed if r[0] in "UJTY" and len(list(B.fps[r].Pads())) >= 3]
    todo = [r for r in B.fps if r not in placed]
    # order: decoupling on power pins first
    def anchor(ref):
        nets = [n for n in parts[ref]["pins"].values() if n not in ("GND", "NC", "")]
        best = None
        for n in nets:
            for ic in ics:
                for pad in B.fps[ic].Pads():
                    if pad.GetNetname() == n:
                        q = P(pad.GetPosition())
                        c = P(B.fps[ic].GetPosition())
                        d = (q[0] - c[0], q[1] - c[1]); L = max(1e-6, (d[0] ** 2 + d[1] ** 2) ** 0.5)
                        cand = (len(list(B.fps[ic].Pads())), q, (d[0] / L, d[1] / L), ic)
                        if best is None or cand[0] > best[0]: best = cand
        return best
    for ref in todo:
        a = anchor(ref)
        fp = B.fps[ref]
        if a is None:
            q, u = (35.0, 45.0), (0.0, 1.0)
        else:
            _, q, u, ic = a
        done = False
        for dist in [x * 0.5 for x in range(2, 70)]:
            for lat in [0, 0.9, -0.9, 1.8, -1.8, 2.7, -2.7, 3.6, -3.6, 4.5, -4.5, 5.4, -5.4]:
                x = q[0] + u[0] * dist - u[1] * lat; y = q[1] + u[1] * dist + u[0] * lat
                rot = 90 if abs(u[1]) > abs(u[0]) else 0
                if not (1.5 < x < BP.BW - 1.5 and 1.5 < y < BP.BH - 1.5): continue
                B.place(ref, x, y, rot)
                bb = bbox(fp)
                if bb[0] < 0.5 or bb[1] < 0.5 or bb[2] > BP.BW - 0.5 or bb[3] > BP.BH - 0.5: continue
                if any(overlap(bb, o) for o in boxes.values()): continue
                if parts[ref]["group"] not in RF_GROUPS and rf_keepout(bb): continue
                boxes[ref] = bb; done = True; break
            if done: break
        if not done:   # global fallback: nearest free spot on a 0.5 mm grid
            cands = sorted(((gx * 0.5, gy * 0.5) for gx in range(4, int(BP.BW * 2) - 3) for gy in range(4, int(BP.BH * 2) - 3)),
                           key=lambda c: (c[0] - q[0]) ** 2 + (c[1] - q[1]) ** 2)
            for (x, y) in cands:
                B.place(ref, x, y, 0); bb = bbox(fp)
                if bb[0] < 0.5 or bb[1] < 0.5 or bb[2] > BP.BW - 0.5 or bb[3] > BP.BH - 0.5: continue
                if any(overlap(bb, o) for o in boxes.values()): continue
                if parts[ref]["group"] not in RF_GROUPS and rf_keepout(bb): continue
                boxes[ref] = bb; done = True; break
        if not done:
            print("could not place", ref)

RF_GROUPS = {"rf_in", "lb", "mb", "hb", "gain", "mixer", "if", "clock"}
RF_CORRIDORS = []      # filled by place_all: rectangles (x0,y0,x1,y1) reserved for RF
def rf_keepout(bb):
    return any(overlap(bb, r) for r in RF_CORRIDORS)

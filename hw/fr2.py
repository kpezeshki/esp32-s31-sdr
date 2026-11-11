#!/usr/bin/env python3
"""Freerouting flow for Board A/B.
  python3 fr2.py A|B export        build no-pour board, lock pre-routes, write DSN for Freerouting
  python3 fr2.py A|B import        import SES onto the locked board, add outer GND pours -> *_routed.kicad_pcb
  python3 fr2.py A|B cont-export   incremental pass: start from *_routed (router wires kept), apply FIXUPS, write *_cont.dsn
  python3 fr2.py A|B cont-import   import *_cont.ses -> *_routed.kicad_pcb
"""
import os, sys, re, json, subprocess, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
which, step = sys.argv[1].upper(), sys.argv[2]
d = os.path.join(HERE, "board_" + which.lower()); base = f"esp32sdr_{which.lower()}"
mm = pcbnew.FromMM
O = 100.0  # board origin offset (mm)

# Hand-placed connections the autorouter could not find (board-relative mm).  Each entry is
# ("track", net, layer, [(x, y), ...], width) or ("via", net, (x, y)).  Locked, so the router keeps them.
FIXUPS = {
    "B": [
        # RFFC5072 VDD pins 19 / 22 (bottom row, 0.5 mm pitch; 20/21 NC; the locked MIX_IPP pre-route runs at y 13.55
        # under pin 22): join both pins with a stub at y 13.2 (0.15 mm from the NC pad ends and from MIX_IPP), then one
        # via at (42.6, 14.2) (~1 mm from all other copper).  The router links the via to the 3V0_RF network.
        ("track", "3V0_RF", pcbnew.F_Cu, [(44.35, 12.55), (44.35, 13.2), (42.85, 13.2)], 0.2),
        ("track", "3V0_RF", pcbnew.F_Cu, [(42.85, 12.55), (42.85, 13.2), (42.6, 13.45), (42.6, 14.2)], 0.2),
        ("via", "3V0_RF", (42.6, 14.2)),
        # U12 (TPS7A20, SOT-23-5) GND pin 2 sits between the two 5V0 pins: escape under the body to a via at x 38.6
        # (0.42 mm from pins 4/5).  LF_B and RFFC_RESETX_I had been routed under the LDO body and are ripped.
        ("track", "GND", pcbnew.F_Cu, [(37.36, 25.0), (38.6, 25.0)], 0.3),
        ("via", "GND", (38.6, 25.0)),
        # rip the router's wires that block the vias (VGB B.Cu trunk, LF_B / RESETX under U12) or overlapped each
        # other (SDATA_I vs IF_CT short)
        ("rip", "VGB"), ("rip", "RFFC_SDATA_I"), ("rip", "IF_CT"), ("rip", "LF_B"), ("rip", "RFFC_RESETX_I"),
    ],
    "A": [],
}

# Applied by `fr2.py X post` to the final *_routed board (after import + stitch).  Extra op:
# ("set_end", net, (x_old, y_old), (x_new, y_new)) moves a track end (trims a scripted segment the router joined mid-way).
# Unused scripted escape vias are removed afterwards by rm_dangling.py --include-locked.
# Router-dependent entries are re-checked by DRC after every re-route.
POST_FIXUPS = {
    "A": [
        # USB DM pre-route: if the router joins the last vertical mid-way at y 10.0, trim the stub above it
        ("set_end", "USB_DM", (48.17, 9.0), (48.17, 10.0)),
        # USB-C: DP pad A6 boxed in (router's A7/B7 DM tie left, its VBUS tie at x 55.33 behind the pads): re-run the
        # VBUS tie further out (x 56.25, clear of the NPTH pegs) and tie A6-B6 with two vias at x 55.65 (B.Cu link)
        ("del_track", "VBUS", (55.332, 8.533), (55.332, 4.436)), ("del_track", "VBUS", (55.332, 4.436), (54.946, 4.05)),
        ("del_track", "VBUS", (54.915, 8.95), (55.332, 8.533)),
        ("track", "VBUS", pcbnew.F_Cu, [(54.946, 4.05), (55.3, 4.4), (56.25, 5.35), (56.25, 7.65), (55.3, 8.6), (54.915, 8.95)], 0.3),
        ("track", "USB_DP", pcbnew.F_Cu, [(54.355, 6.75), (55.65, 6.75)], 0.2), ("via", "USB_DP", (55.65, 6.75)),
        ("track", "USB_DP", pcbnew.B_Cu, [(55.65, 6.75), (55.65, 5.75)], 0.2), ("via", "USB_DP", (55.65, 5.75)),
        ("track", "USB_DP", pcbnew.F_Cu, [(55.65, 5.75), (54.355, 5.75)], 0.2),
        # J6 (socket to Board B) pins 1 and 2 are both 5V0: strap them on B.Cu
        ("track", "5V0", pcbnew.B_Cu, [(3.46, 10.0), (6.0, 10.0)], 0.5),
        # C211/C203/C207 GND pads (x 31.88) are boxed in by the PHY's west-pin escapes: chain them on F.Cu and take
        # them down through one via in C211's GND pad (vias in C203/C207 would hit B.Cu PHY_VDDL / PHY_LED2)
        ("via", "GND", (31.88, 32.7)), ("track", "GND", pcbnew.F_Cu, [(31.88, 32.7), (31.88, 34.9)], 0.25),
        # GND pads of R215 / R214 boxed in: short F.Cu bridges to the nearest GND via / the cap GND chain (x 31.88),
        # R214's through the 0.48 mm gap between the C211 / C203 supply pads
        ("track", "GND", pcbnew.F_Cu, [(31.23, 36.41), (31.28, 36.36), (32.77, 36.36), (33.05, 36.08), (33.05, 35.95)], 0.2),
        ("via", "GND", (33.05, 35.95)),
        ("track", "GND", pcbnew.F_Cu, [(29.16, 34.06), (29.16, 33.25), (31.88, 33.25)], 0.2),
        # J4 DP pads were not linked to the ESD U5 by the router: via on U5's pin1-pin6 DP vertical + B.Cu run to the
        # A6 tie via
        ("via", "USB_DP", (50.05, 6.6)), ("track", "USB_DP", pcbnew.B_Cu, [(50.05, 6.6), (55.5, 6.6), (55.65, 6.75)], 0.2),
    ],
    "B": [
        # J7 (header to Board A) pins 1 and 2 are both 5V0 (2.54 mm apart): strap them so both pins carry supply current
        ("track", "5V0", pcbnew.B_Cu, [(55.40, 15.0), (57.94, 15.0)], 0.5),   # B.Cu: RFFC_SDATA passes between the pins on F.Cu
    ],
}


def post_dsn(dsn):
    t = open(dsn).read()
    # In1 = solid GND reference plane (RF lines on F.Cu reference it): plane only, no routing.
    # In2 (GND on B, 3V3 on A) stays routable; its pour is refilled around tracks after import.
    t = re.sub(r"(\(layer In1\.Cu\s*\n\s*)\(type signal\)", r"\1(type power)", t)
    # router may only place the JLC-basic 0.45/0.2 mm via (no extra charge: 0.2 mm hole with >= 0.45 mm pad).
    # At 0.1 mm copper clearance the hole edge sits 0.225 mm from foreign copper (JLC via hole-to-track 0.2 mm).
    t = re.sub(r'\(via "Via\[0-3\]_450:200_um"[^)]*\)\n', '(via "Via[0-3]_450:200_um")\n', t, count=1)
    assert '(via "Via[0-3]_450:200_um")' in t, "netclass via padstack not found in DSN"
    open(dsn, "w").write(t)
    print("DSN", dsn, "classes:", re.findall(r'\(class (\S+)', t))


def add_outer_pours(b):
    import pcb2
    W, H = pcb2.SIZES[which]
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(b.FindNet("GND")); z.SetLocalClearance(mm(0.2))
        z.SetMinThickness(mm(0.15)); z.SetThermalReliefGap(mm(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        ol = z.Outline(); ol.NewOutline()
        for (x, y) in [(0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)]:
            ol.Append(mm(O + x), mm(O + y))
        b.Add(z)


def save_routed(b):
    out = os.path.join(d, base + "_routed.kicad_pcb"); pcbnew.SaveBoard(out, b)
    # project rules always come from the master esp32_sdr.kicad_pro (JLC basic 4L)
    pro = json.load(open(os.path.join(HERE, "esp32_sdr.kicad_pro"))); pro["meta"]["filename"] = base + "_routed.kicad_pro"
    json.dump(pro, open(os.path.join(d, base + "_routed.kicad_pro"), "w"), indent=2)
    print("saved", out)


def apply_fixups(b, tracks, zones):
    # KiCad 10 SWIG: after any b.Remove(), GetTracks()/Zones() stop working, so the caller collects both lists
    # up front.  rip = remove the router's (unlocked) wires on these nets so the incremental pass redoes them;
    # outer F/B GND pours are removed too (re-added at import).
    rip = {f[1] for f in FIXUPS[which] if f[0] == "rip"}
    doomed = [t for t in tracks if t.GetNetname() in rip and not t.IsLocked()]
    doomed += [z for z in zones if z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) and not z.GetIsRuleArea()]
    for item in doomed:
        b.Remove(item)
    for f in FIXUPS[which]:
        if f[0] == "rip": continue
        net = b.FindNet(f[1])
        if f[0] == "via":
            v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(O + f[2][0]), mm(O + f[2][1])))
            v.SetWidth(mm(0.45)); v.SetDrill(mm(0.2)); v.SetNet(net); v.SetLocked(True); b.Add(v)
        else:
            _, _, layer, pts, w = f
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(mm(O + xa), mm(O + ya))); t.SetEnd(pcbnew.VECTOR2I(mm(O + xb), mm(O + yb)))
                t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(net); t.SetLocked(True); b.Add(t)
    print("fixups applied:", len(FIXUPS[which]))


if step == "export":
    subprocess.run([sys.executable, os.path.join(HERE, "pcb2.py"), which], env=dict(os.environ, NO_OUTER_POUR="1"), capture_output=True)
    b = pcbnew.LoadBoard(os.path.join(d, base + "_nopour.kicad_pcb"))
    for t in b.GetTracks(): t.SetLocked(True)
    for fp in b.GetFootprints(): fp.SetLocked(True)
    # hand connections that are independent of the router's result go in as locked pre-routes (rip entries ignored)
    saved = FIXUPS[which]; FIXUPS[which] = [f for f in saved if f[0] != "rip"]
    apply_fixups(b, [], []); FIXUPS[which] = saved
    pcbnew.SaveBoard(os.path.join(d, base + "_locked.kicad_pcb"), b)
    dsn = os.path.join(d, base + ".dsn")
    pcbnew.ExportSpecctraDSN(b, dsn); post_dsn(dsn)
elif step == "import":
    b = pcbnew.LoadBoard(os.path.join(d, base + "_locked.kicad_pcb"))
    print("SES", pcbnew.ImportSpecctraSES(b, os.path.join(d, base + ".ses")))
    add_outer_pours(b); save_routed(b)
elif step == "cont-export":
    b = pcbnew.LoadBoard(os.path.join(d, base + "_routed.kicad_pcb"))
    apply_fixups(b, list(b.GetTracks()), list(b.Zones()))
    pcbnew.SaveBoard(os.path.join(d, base + "_cont.kicad_pcb"), b)
    dsn = os.path.join(d, base + "_cont.dsn")
    pcbnew.ExportSpecctraDSN(b, dsn); post_dsn(dsn)
elif step == "post":
    out = os.path.join(d, base + "_routed.kicad_pcb"); b = pcbnew.LoadBoard(out)
    tracks = list(b.GetTracks())
    near = lambda p, q: abs(pcbnew.ToMM(p.x) - O - q[0]) < 0.01 and abs(pcbnew.ToMM(p.y) - O - q[1]) < 0.01
    dels = [f for f in POST_FIXUPS[which] if f[0] == "del_track"]
    doomed = [t for t in tracks if t.GetClass() != "PCB_VIA" and any(
        t.GetNetname() == f[1] and ((near(t.GetStart(), f[2]) and near(t.GetEnd(), f[3])) or (near(t.GetStart(), f[3]) and near(t.GetEnd(), f[2])))
        for f in dels)]
    for f in [f for f in POST_FIXUPS[which] if f[0] == "set_end"]:
        for t in tracks:
            if t.GetClass() == "PCB_VIA" or t.GetNetname() != f[1]: continue
            new = pcbnew.VECTOR2I(mm(O + f[3][0]), mm(O + f[3][1]))
            if near(t.GetEnd(), f[2]): t.SetEnd(new); print("trimmed", f[1])
            elif near(t.GetStart(), f[2]): t.SetStart(new); print("trimmed", f[1])
    saved = FIXUPS[which]; FIXUPS[which] = [f for f in POST_FIXUPS[which] if f[0] in ("via", "track")]
    apply_fixups(b, [], []); FIXUPS[which] = saved
    for t in doomed: b.Remove(t)          # removals last (KiCad 10: collections break after Remove)
    print("deleted tracks:", len(doomed))
    pcbnew.SaveBoard(out, b); print("saved", out)
elif step == "cont-import":
    b = pcbnew.LoadBoard(os.path.join(d, base + "_cont.kicad_pcb"))
    print("SES", pcbnew.ImportSpecctraSES(b, os.path.join(d, base + "_cont.ses")))
    add_outer_pours(b); save_routed(b)

#!/usr/bin/env python3
"""
Generate the KiCad board for the ESP32-S31 SDR from design.py.
- 70 x 70 mm, 4 layers (JLC04161H-3313): F.Cu signal/RF, In1.Cu GND (voided under RF 0402 pads), In2.Cu GND/power, B.Cu routing.
- RF filter ladders placed with exactly the geometry simulated in em/filter_em.py (ladder_geometry).
- RF chain routed by script as 50 ohm microstrip (0.19 mm over the 0.0994 mm prepreg to In1.Cu).
Output: hw/esp32_sdr.kicad_pcb
"""
import os, sys, json, math
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "em")); sys.path.insert(0, os.path.join(HERE, "..", "analysis"))
import design
import filter_em as FE
import filters as F

OX, OY = 100.0, 100.0            # board origin in KiCad coordinates (mm)
BW, BH = 70.0, 70.0
W50 = FE.W50
mm = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))
def P(v): return (pcbnew.ToMM(v.x) - OX, pcbnew.ToMM(v.y) - OY)

LIBROOT = "/usr/share/kicad/footprints"
def load_fp(fpid):
    lib, name = fpid.split(":")
    path = os.path.join(HERE, "esp32_sdr.pretty") if lib == "esp32_sdr" else os.path.join(LIBROOT, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    assert fp is not None, fpid
    return fp

class Board:
    def __init__(self):
        self.b = pcbnew.BOARD()
        self.b.SetCopperLayerCount(4)
        self.nets = {}
        self.fps = {}
        ds = self.b.GetDesignSettings()
        ds.SetCopperLayerCount(4)
        ds.m_TrackMinWidth = mm(0.09); ds.m_MinClearance = mm(0.09); ds.m_ViasMinSize = mm(0.45); ds.m_MinThroughDrill = mm(0.2)
        ds.m_CopperEdgeClearance = mm(0.2)
        nc = ds.m_NetSettings.GetDefaultNetclass()
        nc.SetClearance(mm(0.1)); nc.SetTrackWidth(mm(0.15)); nc.SetViaDiameter(mm(0.45)); nc.SetViaDrill(mm(0.2))
    def net(self, name):
        if name not in self.nets:
            n = pcbnew.NETINFO_ITEM(self.b, name); self.b.Add(n); self.nets[name] = n
        return self.nets[name]
    def add_part(self, p):
        fp = load_fp(p["footprint"])
        fp.SetReference(p["ref"]); fp.SetValue(p["value"])
        self.b.Add(fp); self.fps[p["ref"]] = fp
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num in p["pins"] and p["pins"][num] not in ("NC", ""):
                pad.SetNet(self.net(p["pins"][num]))
            elif num == "" :
                pass
        # unnumbered thermal-via pads of the ESP32 EP take pad 81's net
        if p["ref"] == "U1":
            for pad in fp.Pads():
                if pad.GetNumber() == "81": pad.SetNet(self.net("GND"))
        fp.SetPosition(V(-30, -30))          # parking spot until placed
        return fp
    def place(self, ref, x, y, rot=0.0, back=False):
        fp = self.fps[ref]
        if back and not fp.IsFlipped(): fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(V(x, y))
    def pad(self, ref, num):
        for p in self.fps[ref].Pads():
            if p.GetNumber() == str(num): return p
        raise KeyError(f"{ref}.{num}")
    def padxy(self, ref, num): return P(self.pad(ref, num).GetPosition())
    def track(self, a, b, w=W50, layer=pcbnew.F_Cu, net=None):
        t = pcbnew.PCB_TRACK(self.b); t.SetStart(V(*a)); t.SetEnd(V(*b)); t.SetWidth(mm(w)); t.SetLayer(layer)
        if net: t.SetNet(self.net(net))
        self.b.Add(t); return t
    def via(self, x, y, net="GND", d=0.5, drill=0.2):
        v = pcbnew.PCB_VIA(self.b); v.SetPosition(V(x, y)); v.SetWidth(mm(d)); v.SetDrill(mm(drill))
        v.SetNet(self.net(net)); self.b.Add(v); return v
    def poly_zone(self, pts, layer, net=None, keepout=False, name="", priority=0):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(layer)
        if keepout:
            z.SetIsRuleArea(True); z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False)
            z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        else:
            z.SetNet(self.net(net)); z.SetAssignedPriority(priority)
            z.SetLocalClearance(mm(0.2)); z.SetMinThickness(mm(0.15)); z.SetThermalReliefGap(mm(0.25))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        ol = z.Outline(); ol.NewOutline()
        for (x, y) in pts: ol.Append(mm(OX + x), mm(OY + y))
        if name: z.SetZoneName(name)
        self.b.Add(z); return z
    def outline(self):
        pts = [(0, 0), (BW, 0), (BW, BH), (0, BH)]
        for i in range(4):
            s = pcbnew.PCB_SHAPE(self.b); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(*pts[i])); s.SetEnd(V(*pts[(i + 1) % 4])); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            self.b.Add(s)

# ------------------------------------------------------------------ RF ladder placement (mirrors filter_em.ladder_geometry)
def place_ladder(B, prefix, name, x0, yl, nin, nout, flip=False):
    """Place filter parts along a horizontal 50-ohm line at y=yl starting at x0 (left = input).
    Shunt stacks hang below the line (above if flip). Returns x of the output end."""
    topo = F.FILTERS[name]["topo"]
    sgn = -1 if flip else 1
    x = x0; i = 0; node_net = nin
    nseries = sum(1 for p, _ in topo if p == "s"); si = 0
    voids = []
    prev_end = x0
    for bi, (pos, kind) in enumerate(topo):
        if pos == "s":
            si += 1
            # trace GAP_T then the part
            B.track((prev_end, yl), (x + FE.GAP_T, yl), net=node_net); x += FE.GAP_T
            ref = f"{prefix}{i+1}"; cx = x + FE.PAD_L / 2 + FE.PAD_X
            B.place(ref, cx, yl, 0)
            voids.append((x - FE.VOID_M, yl - FE.PAD_W / 2 - FE.VOID_M, x + 2 * FE.PAD_X + FE.PAD_L + FE.VOID_M, yl + FE.PAD_W / 2 + FE.VOID_M))
            node_net = nout if si == nseries else f"{prefix}_N{si}"
            x += 2 * FE.PAD_X + FE.PAD_L; prev_end = x; i += 1
        else:
            B.track((prev_end, yl), (x + FE.GAP_T, yl), net=node_net)
            xn = x + FE.GAP_T / 2; x += FE.GAP_T; prev_end = x
            y = W50 / 2
            B.track((xn, yl + sgn * (W50 / 2 - 0.05)), (xn, yl + sgn * (y + 0.25)), net=node_net); y += 0.25
            parts = 2 if kind in ("LCs", "LCp") else 1
            for k in range(parts):
                ref = f"{prefix}{i+1}"
                cy = yl + sgn * (y + FE.PAD_L / 2 + FE.PAD_X)
                B.place(ref, xn, cy, -90 if not flip else 90)
                voids.append((xn - FE.PAD_W / 2 - FE.VOID_M, yl + sgn * (y - FE.VOID_M), xn + FE.PAD_W / 2 + FE.VOID_M,
                              yl + sgn * (y + 2 * FE.PAD_X + FE.PAD_L + FE.VOID_M)))
                y += 2 * FE.PAD_X + FE.PAD_L; i += 1
                if k < parts - 1:
                    B.track((xn, yl + sgn * (y - 0.05)), (xn, yl + sgn * (y + 0.25)), net=f"{prefix}_M{bi}"); y += 0.2
            B.track((xn, yl + sgn * (y - 0.05)), (xn, yl + sgn * (y + 0.15 + FE.VIA_PAD / 2)), net="GND"); y += 0.15
            B.via(xn, yl + sgn * (y + FE.VIA_PAD / 2))
    for (a, b_, c, d) in voids:
        y0, y1 = min(b_, d), max(b_, d)
        B.poly_zone([(a, y0), (c, y0), (c, y1), (a, y1)], pcbnew.In1_Cu, keepout=True)
    return prev_end

def main():
    from placement import place_all, route_rf, zones
    D = design.build()
    B = Board()
    for p in D.parts:
        B.add_part(p)
    B.outline()
    place_all(B, D)
    route_rf(B)
    zones(B)
    out = os.path.join(HERE, "esp32_sdr_nopour.kicad_pcb" if os.environ.get("NO_OUTER_POUR") else "esp32_sdr.kicad_pcb")
    pcbnew.SaveBoard(out, B.b)
    print("saved", out, len(D.parts), "parts")


if __name__ == "__main__":
    main()

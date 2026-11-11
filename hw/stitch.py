#!/usr/bin/env python3
"""Add GND stitching vias (JLC-basic 0.45/0.2 mm) on a grid wherever they clear all other copper.
python3 stitch.py board.kicad_pcb PITCH_MM [--edge-pitch MM]
  - keeps >= 0.1 mm copper clearance (+0.05 margin) to every non-GND pad, track and via on any layer
  - stays off all pads (no via-in-pad), out of footprint courtyards, out of rule areas (RF In1 voids), and
    >= 0.6 mm from the board edge
  - --edge-pitch adds a denser row 1.0 mm inside the board outline (edge fence)
Edits the board in place; zones are refilled by the following `kicad-cli pcb drc --refill-zones --save-board`."""
import sys, math, pcbnew

src, pitch = sys.argv[1], float(sys.argv[2])
edge_pitch = float(sys.argv[sys.argv.index("--edge-pitch") + 1]) if "--edge-pitch" in sys.argv else None
b = pcbnew.LoadBoard(src)
MM = pcbnew.ToMM
O = 100.0
VR, CLR, MARG = 0.225, 0.1, 0.05
gnd = b.FindNet("GND")
bb = b.GetBoardEdgesBoundingBox()
X0, Y0, X1, Y1 = MM(bb.GetLeft()) - O, MM(bb.GetTop()) - O, MM(bb.GetRight()) - O, MM(bb.GetBottom()) - O

rects = []      # (x0, y0, x1, y1, need) : keep via centre >= need from the rectangle
segs = []       # (xa, ya, xb, yb, need)
for fp in b.GetFootprints():
    cy = fp.GetCourtyard(pcbnew.F_Cu)
    if cy.OutlineCount():
        c = cy.BBox(); rects.append((MM(c.GetLeft()) - O, MM(c.GetTop()) - O, MM(c.GetRight()) - O, MM(c.GetBottom()) - O, VR + 0.05))
    for p in fp.Pads():
        c = p.GetBoundingBox()
        rects.append((MM(c.GetLeft()) - O, MM(c.GetTop()) - O, MM(c.GetRight()) - O, MM(c.GetBottom()) - O, VR + CLR + MARG))
tracks = list(b.GetTracks())
for t in tracks:
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition(); r = MM(t.GetWidth(pcbnew.F_Cu)) / 2
        x, y = MM(p.x) - O, MM(p.y) - O
        need = VR + r + (CLR + MARG if t.GetNetCode() != gnd.GetNetCode() else 0.25)   # GND vias: keep hole spacing
        rects.append((x, y, x, y, need))
    else:
        if t.GetNetCode() == gnd.GetNetCode(): continue
        s, e = t.GetStart(), t.GetEnd()
        segs.append((MM(s.x) - O, MM(s.y) - O, MM(e.x) - O, MM(e.y) - O, VR + MM(t.GetWidth()) / 2 + CLR + MARG))
for z in b.Zones():
    if z.GetIsRuleArea():
        c = z.GetBoundingBox(); rects.append((MM(c.GetLeft()) - O, MM(c.GetTop()) - O, MM(c.GetRight()) - O, MM(c.GetBottom()) - O, VR + 0.1))


def d_rect(x, y, r):
    dx = max(r[0] - x, 0, x - r[2]); dy = max(r[1] - y, 0, y - r[3]); return math.hypot(dx, dy)


def d_seg(x, y, s):
    xa, ya, xb, yb = s[:4]; vx, vy = xb - xa, yb - ya; L2 = vx * vx + vy * vy
    u = 0 if L2 == 0 else max(0, min(1, ((x - xa) * vx + (y - ya) * vy) / L2))
    return math.hypot(x - xa - u * vx, y - ya - u * vy)


placed = []
def ok(x, y):
    if not (X0 + 0.6 <= x <= X1 - 0.6 and Y0 + 0.6 <= y <= Y1 - 0.6): return False
    if any(d_rect(x, y, r) < r[4] for r in rects): return False
    if any(d_seg(x, y, s) < s[4] for s in segs): return False
    if any(math.hypot(x - px, y - py) < 2 * VR + 0.3 for px, py in placed): return False
    return True


def add(x, y):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(O + x), pcbnew.FromMM(O + y)))
    v.SetWidth(pcbnew.FromMM(2 * VR)); v.SetDrill(pcbnew.FromMM(0.2)); v.SetNet(gnd); b.Add(v); placed.append((x, y))


cands = []
if edge_pitch:
    n = int((X1 - X0 - 2) / edge_pitch)
    for i in range(n + 1):
        x = X0 + 1 + i * (X1 - X0 - 2) / n; cands += [(x, Y0 + 1), (x, Y1 - 1)]
    n = int((Y1 - Y0 - 2) / edge_pitch)
    for i in range(1, n):
        y = Y0 + 1 + i * (Y1 - Y0 - 2) / n; cands += [(X0 + 1, y), (X1 - 1, y)]
nx, ny = int((X1 - X0) / pitch), int((Y1 - Y0) / pitch)
for i in range(nx + 1):
    for j in range(ny + 1):
        cands.append((X0 + (X1 - X0 - nx * pitch) / 2 + i * pitch, Y0 + (Y1 - Y0 - ny * pitch) / 2 + j * pitch))
for (x, y) in cands:
    if ok(x, y): add(x, y)
    else:   # nudge up to 0.6 mm to find a free spot near the grid point
        for dx, dy in ((0.3, 0), (-0.3, 0), (0, 0.3), (0, -0.3), (0.6, 0), (-0.6, 0), (0, 0.6), (0, -0.6)):
            if ok(x + dx, y + dy): add(x + dx, y + dy); break
n_grid = len(placed)

# Orphan islands: fill the GND zones, then give every filled island that holds no GND via / THT pad a via.
gnd_pts = [(MM(t.GetPosition().x) - O, MM(t.GetPosition().y) - O) for t in tracks if t.GetClass() == "PCB_VIA" and t.GetNetCode() == gnd.GetNetCode()]
gnd_pts += placed
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetCode() == gnd.GetNetCode() and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            gnd_pts.append((MM(p.GetPosition().x) - O, MM(p.GetPosition().y) - O))
zones = [z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetCode() == gnd.GetNetCode()]
pcbnew.ZONE_FILLER(b).Fill(zones)
V = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(O + x), pcbnew.FromMM(O + y))
orphans, fixed = 0, 0
rects_nocy = [r for r in rects if r[4] != VR + 0.05]     # without courtyards (second-chance search)
for z in zones:
    layer = z.GetLayer()
    polys = z.GetFilledPolysList(layer)
    for i in range(polys.OutlineCount()):
        ol = polys.Outline(i)
        if any(ol.PointInside(V(x, y)) for x, y in gnd_pts): continue
        orphans += 1
        c = ol.BBox(); bx0, by0, bx1, by1 = MM(c.GetLeft()) - O, MM(c.GetTop()) - O, MM(c.GetRight()) - O, MM(c.GetBottom()) - O
        pts = [(bx0 + i2 * 0.1, by0 + j2 * 0.1) for i2 in range(int((bx1 - bx0) / 0.1) + 1) for j2 in range(int((by1 - by0) / 0.1) + 1)]
        pts = [(x, y) for x, y in pts if ol.PointInside(V(x, y)) and polys.Outline(i).PointInside(V(x, y))]
        hit = None
        for rs in (rects, rects_nocy):
            saved = rects[:]
            rects[:] = rs
            # via must sit fully inside the island copper (centre >= VR from the island outline)
            for x, y in pts:
                if all(ol.PointInside(V(x + dx, y + dy)) for dx, dy in ((VR, 0), (-VR, 0), (0, VR), (0, -VR))) and ok(x, y):
                    hit = (x, y); break
            rects[:] = saved
            if hit: break
        if hit:
            add(*hit); gnd_pts.append(hit); fixed += 1
            print(f"  orphan island on {b.GetLayerName(layer)} bbox ({bx0:.1f},{by0:.1f})-({bx1:.1f},{by1:.1f}): via at ({hit[0]:.2f},{hit[1]:.2f})")
        else:
            print(f"  orphan island on {b.GetLayerName(layer)} bbox ({bx0:.1f},{by0:.1f})-({bx1:.1f},{by1:.1f}): NO via spot")
pcbnew.SaveBoard(src, b)
print(f"stitching vias added: {n_grid} grid + {fixed} island ({orphans} orphan islands found)")

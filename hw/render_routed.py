#!/usr/bin/env python3
"""Render a routed board: tracks by layer, pads, vias, refs, and unrouted connections (red dashed).
python3 render_routed.py board.kicad_pcb out.png [--zoom x0,y0,x1,y1]   (board-relative mm)"""
import sys, pcbnew
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon

src, out = sys.argv[1], sys.argv[2]
zoom = None
if "--zoom" in sys.argv:
    zoom = [float(v) for v in sys.argv[sys.argv.index("--zoom") + 1].split(",")]
b = pcbnew.LoadBoard(src)
mm = pcbnew.ToMM
O = 100.0  # boards are drawn with origin at (100, 100) mm
COL = {pcbnew.F_Cu: "#c0392b", pcbnew.B_Cu: "#2563eb", pcbnew.In1_Cu: "#16a34a", pcbnew.In2_Cu: "#d97706"}
NAME = {pcbnew.F_Cu: "F.Cu", pcbnew.B_Cu: "B.Cu", pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu"}
bb = b.GetBoardEdgesBoundingBox()
W, H = mm(bb.GetWidth()), mm(bb.GetHeight())
fig, ax = plt.subplots(figsize=(14, 14 * H / W if not zoom else 14 * (zoom[3] - zoom[1]) / (zoom[2] - zoom[0])))
ax.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k", lw=1))
for fp in b.GetFootprints():
    for p in fp.Pads():
        x, y = mm(p.GetPosition().x) - O, mm(p.GetPosition().y) - O
        sx, sy = mm(p.GetSize(pcbnew.F_Cu).x), mm(p.GetSize(pcbnew.F_Cu).y)
        ang = p.GetOrientation().AsDegrees()
        if abs(ang % 180 - 90) < 1: sx, sy = sy, sx
        c = "#9ca3af" if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else ("#fca5a5" if p.IsOnLayer(pcbnew.F_Cu) else "#93c5fd")
        ax.add_patch(Rectangle((x - sx / 2, y - sy / 2), sx, sy, fc=c, ec="none", alpha=0.8))
    r = fp.GetPosition()
    ax.text(mm(r.x) - O, mm(r.y) - O, fp.GetReference(), fontsize=4.5 if not zoom else 7, ha="center", va="center", color="#111", alpha=0.7, clip_on=True)
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition(); ax.add_patch(Circle((mm(p.x) - O, mm(p.y) - O), mm(t.GetWidth(pcbnew.F_Cu)) / 2, fc="#6b7280", ec="k", lw=0.2))
    else:
        s, e = t.GetStart(), t.GetEnd()
        ax.plot([mm(s.x) - O, mm(e.x) - O], [mm(s.y) - O, mm(e.y) - O], color=COL.get(t.GetLayer(), "m"),
                lw=max(0.4, mm(t.GetWidth()) * (3 if not zoom else 8)), solid_capstyle="round", alpha=0.85)
# unrouted connections: pairs of positions from the DRC report (drc_routed.rpt next to the board)
import os, re
rpt = os.path.join(os.path.dirname(os.path.abspath(src)), "drc_routed.rpt")
n_unr = 0
if os.path.exists(rpt):
    for blk in re.split(r"\n(?=\[)", open(rpt).read()):
        if not blk.startswith("[unconnected_items"): continue
        pts = [(float(x) - O, float(y) - O) for x, y in re.findall(r"@\(([\d.]+) mm, ([\d.]+) mm\)", blk)]
        if len(pts) == 2 and "Zone" not in blk:
            ax.plot([pts[0][0], pts[1][0]], [pts[0][1], pts[1][1]], "r--", lw=1.4)
            ax.plot(*zip(*pts), "rx", ms=5)
            n_unr += 1
ax.set_xlim(*(zoom[0::2] if zoom else (-1, W + 1))); ax.set_ylim(*((zoom[3], zoom[1]) if zoom else (H + 1, -1)))
ax.set_aspect("equal")
ax.set_title(f"{src.split('/')[-1]}  -  {n_unr} unrouted connections (red dashed)", fontsize=10)
for k, v in COL.items(): ax.plot([], [], color=v, lw=2, label=NAME[k])
ax.legend(loc="upper right", fontsize=7)
fig.savefig(out, dpi=170, bbox_inches="tight")
print("unrouted", n_unr, "->", out)

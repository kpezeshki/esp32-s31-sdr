#!/usr/bin/env python3
"""Per-board BOM/CPL.  python3 bom2.py A|B [board.kicad_pcb]
Board A (in-house reflow): BOM_A_kit.csv (LCSC order list, all parts) + CPL_A.csv (positions, for in-house placement).
Board B (JLC hybrid): BOM_B_JLC.csv + CPL_B_JLC.csv (JLC-placed), BOM_B_HAND_LCSC.csv, BOM_B_DNP.csv."""
import os, sys, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import design2, pcbnew
which = sys.argv[1].upper()
D = design2.build_a() if which == "A" else design2.build_b()
d = os.path.join(HERE, "board_" + which.lower())
bp = sys.argv[2] if len(sys.argv) > 2 else os.path.join(d, f"esp32sdr_{which.lower()}_routed.kicad_pcb")
board = pcbnew.LoadBoard(bp)
pos = {fp.GetReference(): (pcbnew.ToMM(fp.GetPosition().x) - 100.0, -(pcbnew.ToMM(fp.GetPosition().y) - 100.0),
                           fp.GetOrientationDegrees() % 360, "bottom" if fp.IsFlipped() else "top") for fp in board.GetFootprints()}
out = os.path.join(d, "fab"); os.makedirs(out, exist_ok=True)
fpn = lambda f: f.split(":")[-1]
groups = collections.OrderedDict()
for p in D.parts:
    groups.setdefault((p["by"], p["value"], p["footprint"], p["lcsc"]), []).append(p)
def write(name, header, rows):
    with open(os.path.join(out, name), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
if which == "A":
    write("BOM_A_kit.csv", ["LCSC Part #", "Qty per board", "Designators", "Value", "Footprint", "Note"],
          [[k[3], len(v), ",".join(sorted(p["ref"] for p in v)), k[1], fpn(k[2]), v[0]["note"][:80]] for k, v in groups.items() if k[0] != "dnp"])
    write("CPL_A.csv", ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
          [[p["ref"], f"{pos[p['ref']][0]:.4f}mm", f"{pos[p['ref']][1]:.4f}mm", pos[p['ref']][3], f"{pos[p['ref']][2]:.1f}"] for p in D.parts if p["by"] != "dnp" and p["ref"] in pos])
else:
    write("BOM_B_JLC.csv", ["Comment", "Designator", "Footprint", "LCSC Part #"],
          [[k[1], ",".join(sorted(p["ref"] for p in v)), fpn(k[2]), k[3]] for k, v in groups.items() if k[0] == "jlc"])
    write("CPL_B_JLC.csv", ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
          [[p["ref"], f"{pos[p['ref']][0]:.4f}mm", f"{pos[p['ref']][1]:.4f}mm", pos[p['ref']][3], f"{pos[p['ref']][2]:.1f}"] for p in D.parts if p["by"] == "jlc" and p["ref"] in pos])
    write("BOM_B_HAND_LCSC.csv", ["LCSC Part #", "Qty per board", "Designators", "Value", "Footprint"],
          [[k[3], len(v), ",".join(sorted(p["ref"] for p in v)), k[1], fpn(k[2])] for k, v in groups.items() if k[0] == "hand"])
write(f"BOM_{which}_DNP.csv", ["Designators", "Value", "Footprint", "Note"],
      [[p["ref"], p["value"], fpn(p["footprint"]), p["note"]] for p in D.parts if p["by"] == "dnp"])
n = collections.Counter(p["by"] for p in D.parts)
print(which, dict(n), "JLC types:", len({k[3] for k in groups if k[0] == "jlc"}), "hand/kit types:", len({k for k in groups if k[0] == "hand"}))

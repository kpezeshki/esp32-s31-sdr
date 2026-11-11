#!/usr/bin/env python3
"""BOM / CPL generation for the hybrid build (D11).
Outputs in hw/fab/:
  BOM_JLC.csv        JLC PCBA BOM (Comment, Designator, Footprint, LCSC Part #) - JLC-placed parts only
  CPL_JLC.csv        JLC pick-and-place (Designator, Mid X, Mid Y, Layer, Rotation) - JLC-placed parts only
  BOM_HAND_LCSC.csv  hand-solder parts (order from LCSC): LCSC Part #, Quantity per board, Designators, Value, Footprint
  BOM_DNP.csv        footprints left unpopulated (options)
  BOM_FULL.csv       everything, with assembly column
"""
import os, sys, csv, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import design

def main(board_path=None):
    import pcbnew
    D = design.build()
    board = pcbnew.LoadBoard(board_path or os.path.join(HERE, "esp32_sdr_routed.kicad_pcb"))
    out = os.path.join(HERE, "fab"); os.makedirs(out, exist_ok=True)
    pos = {}
    for fp in board.GetFootprints():
        p = fp.GetPosition()
        pos[fp.GetReference()] = (pcbnew.ToMM(p.x) - 100.0, -(pcbnew.ToMM(p.y) - 100.0), fp.GetOrientationDegrees() % 360,
                                  "bottom" if fp.IsFlipped() else "top")
    groups = collections.OrderedDict()
    for p in D.parts:
        key = (p["by"], p["value"], p["footprint"], p["lcsc"])
        groups.setdefault(key, []).append(p["ref"])
    def fpname(f): return f.split(":")[-1]
    with open(os.path.join(out, "BOM_JLC.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (by, val, fpn, lc), refs in groups.items():
            if by == "jlc": w.writerow([val, ",".join(sorted(refs)), fpname(fpn), lc])
    with open(os.path.join(out, "CPL_JLC.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for p in D.parts:
            if p["by"] == "jlc" and p["ref"] in pos:
                x, y, r, side = pos[p["ref"]]
                w.writerow([p["ref"], f"{x:.4f}mm", f"{y:.4f}mm", side, f"{r:.1f}"])
    with open(os.path.join(out, "BOM_HAND_LCSC.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["LCSC Part #", "Qty per board", "Designators", "Value", "Footprint"])
        for (by, val, fpn, lc), refs in groups.items():
            if by == "hand": w.writerow([lc, len(refs), ",".join(sorted(refs)), val, fpname(fpn)])
    with open(os.path.join(out, "BOM_DNP.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Designators", "Value", "Footprint", "Note"])
        for p in D.parts:
            if p["by"] == "dnp": w.writerow([p["ref"], p["value"], fpname(p["footprint"]), p["note"]])
    with open(os.path.join(out, "BOM_FULL.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["Assembly", "Qty", "Designators", "Value", "Footprint", "LCSC Part #"])
        for (by, val, fpn, lc), refs in groups.items():
            w.writerow([by, len(refs), ",".join(sorted(refs)), val, fpname(fpn), lc])
    n = collections.Counter(p["by"] for p in D.parts)
    types_jlc = len({k for k in groups if k[0] == "jlc"}); types_hand = len({k for k in groups if k[0] == "hand"})
    missing = [p["ref"] for p in D.parts if p["by"] in ("jlc", "hand") and not p["lcsc"] and not p["ref"].startswith("TP")]
    print(f"parts: {dict(n)}; JLC part types {types_jlc}; hand part types {types_hand}; missing LCSC: {missing}")
    return types_jlc, types_hand, missing

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

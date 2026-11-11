#!/usr/bin/env python3
"""Build Board A / Board B KiCad boards.  Usage: python3 pcb2.py A|B   (env NO_OUTER_POUR=1 -> *_nopour variant for DSN export)"""
import os, sys, json, shutil
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_pcb as BP, design2
SIZES = {"A": (62.0, 46.0), "B": (62.0, 40.0)}

def main(which):
    BP.BW, BP.BH = SIZES[which]
    D = design2.build_a() if which == "A" else design2.build_b()
    if which == "A":
        import placement_a as PM
    else:
        import placement_b as PM
    B = BP.Board()
    for p in D.parts:
        if p["footprint"]: B.add_part(p)
    B.outline()
    PM.place_all(B, D)
    PM.zones(B)
    d = os.path.join(HERE, "board_" + which.lower()); os.makedirs(d, exist_ok=True)
    name = f"esp32sdr_{which.lower()}" + ("_nopour" if os.environ.get("NO_OUTER_POUR") else "")
    out = os.path.join(d, name + ".kicad_pcb")
    pcbnew.SaveBoard(out, B.b)
    pro = json.load(open(os.path.join(HERE, "esp32_sdr.kicad_pro"))); pro["meta"]["filename"] = name + ".kicad_pro"
    json.dump(pro, open(os.path.join(d, name + ".kicad_pro"), "w"), indent=2)
    print("saved", out, len(D.parts), "parts")

if __name__ == "__main__":
    main(sys.argv[1])

#!/usr/bin/env python3
"""Hide reference designators on the silkscreen (outlines and pin-1 marks stay).  The boards are too dense for
legible refdes (they overlapped each other and the pads); assembly uses the CPL (JLC) or the labelled assembly
renders (render_routed.py).  python3 silk_clean.py board.kicad_pcb"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
n = 0
for fp in b.GetFootprints():
    r = fp.Reference()
    if r.IsVisible() and r.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        r.SetVisible(False); n += 1
pcbnew.SaveBoard(sys.argv[1], b)
print("refdes hidden on silk:", n)

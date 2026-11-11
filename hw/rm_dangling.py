#!/usr/bin/env python3
"""Remove router leftovers that KiCad DRC reports as track_dangling / via_dangling (unlocked items only).
python3 rm_dangling.py board.kicad_pcb drc.rpt [--include-locked]   (re-run DRC afterwards; repeat until none are left)"""
import sys, re, pcbnew
src, rpt = sys.argv[1], sys.argv[2]
b = pcbnew.LoadBoard(src)
items = []
for blk in re.split(r"\n(?=\[)", open(rpt).read()):
    m = re.match(r"\[(track|via)_dangling", blk)
    if not m: continue
    for x, y, what in re.findall(r"@\(([\d.]+) mm, ([\d.]+) mm\): (.*)", blk):
        L = re.search(r"length ([\d.]+) mm", what)
        items.append((m.group(1), float(x), float(y), re.search(r"\[(.*?)\]", what).group(1), float(L.group(1)) if L else None))
tracks = list(b.GetTracks())
doomed = []
for kind, x, y, net, L in items:
    for t in tracks:
        if (t.IsLocked() and "--include-locked" not in sys.argv) or t.GetNetname() != net or t in doomed: continue
        if kind == "via" and t.GetClass() == "PCB_VIA":
            p = t.GetPosition()
            if abs(pcbnew.ToMM(p.x) - x) < 0.01 and abs(pcbnew.ToMM(p.y) - y) < 0.01: doomed.append(t)
        elif kind == "track" and t.GetClass() != "PCB_VIA" and L is not None and abs(pcbnew.ToMM(t.GetLength()) - L) < 0.002:
            ends = [(pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)) for q in (t.GetStart(), t.GetEnd())]
            mid = ((ends[0][0] + ends[1][0]) / 2, (ends[0][1] + ends[1][1]) / 2)
            if any(abs(ex - x) < 0.6 and abs(ey - y) < 0.6 for ex, ey in ends + [mid]): doomed.append(t)
for t in doomed: b.Remove(t)
pcbnew.SaveBoard(src, b)
print("removed", len(doomed), "dangling items")

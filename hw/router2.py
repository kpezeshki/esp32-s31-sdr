#!/usr/bin/env python3
"""
Router v2: grid A* with negotiated rip-up-and-reroute.
- Fixed copper (pads, scripted RF tracks/vias, plane vias) is never moved.
- Routed copper of other nets is passable in 'soft' mode at a penalty; nets crossed by a soft path are ripped up
  and re-queued (bounded number of rip-ups, growing history penalty on contested cells).
Input: hw/esp32_sdr.kicad_pcb  Output: hw/esp32_sdr_routed.kicad_pcb, hw/route_report.txt
"""
import os, sys, math, heapq, time, json, random
import numpy as np
from scipy import ndimage
import pcbnew
import router as R1          # reuse constants / helpers / plane-via logic

HERE = R1.HERE
OX, OY, RES, NX, NY = R1.OX, R1.OY, R1.RES, R1.NX, R1.NY
CLR, SIG_W, PWR_W, VIA_D, VIA_DRILL = R1.CLR, R1.SIG_W, R1.PWR_W, R1.VIA_D, R1.VIA_DRILL
POWER, RF_REGION, in_poly, to_px, mm = R1.POWER, R1.RF_REGION, R1.in_poly, R1.to_px, R1.mm
LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]

def seg_np(arr, a, b, w, val):
    (ax, ay), (bx, by) = to_px(*a), to_px(*b); r = w / 2 / RES
    x0, x1 = int(max(0, min(ax, bx) - r - 1)), int(min(NX, max(ax, bx) + r + 2))
    y0, y1 = int(max(0, min(ay, by) - r - 1)), int(min(NY, max(ay, by) + r + 2))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]; px, py = xx + 0.5, yy + 0.5
    dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0, 1) if L2 > 0 else 0
    d2 = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
    sub = arr[y0:y1, x0:x1]; sub[d2 <= r * r] = val

def disk_np(arr, x, y, r, val):
    cx, cy = to_px(x, y); rr = r / RES
    y0, y1 = int(max(0, cy - rr - 1)), int(min(NY, cy + rr + 2)); x0, x1 = int(max(0, cx - rr - 1)), int(min(NX, cx + rr + 2))
    yy, xx = np.mgrid[y0:y1, x0:x1]
    sub = arr[y0:y1, x0:x1]; sub[(xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= rr * rr] = val

def disk_st(r):
    ri = int(math.ceil(r)); yy, xx = np.mgrid[-ri:ri + 1, -ri:ri + 1]; return (xx ** 2 + yy ** 2) <= r * r

class Router2:
    def __init__(self, path):
        self.r1 = R1.Router(path)       # rasterises fixed copper into r1.lab, r1.padmask, r1.holes
        self.b = self.r1.b
        self.netid = self.r1.netid
        self.route = {l: np.zeros((NY, NX), np.int32) for l in LAYERS}
        self.items = {}                 # net -> list of router items
        self.hist = {l: np.zeros((NY, NX), np.float32) for l in LAYERS}
        self.rholes = np.zeros((NY, NX), np.int32)
    @property
    def fixed(self): return self.r1.lab
    def add_track(self, a, b, layer, w, net):
        t = pcbnew.PCB_TRACK(self.b); t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNetCode(net); self.b.Add(t)
        seg_np(self.route[layer], a, b, w, net); self.items.setdefault(net, []).append(t)
    def add_via(self, x, y, net):
        v = pcbnew.PCB_VIA(self.b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL))
        v.SetNetCode(net); self.b.Add(v)
        for l in LAYERS: disk_np(self.route[l], x, y, VIA_D / 2, net)
        disk_np(self.rholes, x, y, VIA_DRILL / 2, net)
        self.items.setdefault(net, []).append(v)
    def ripup(self, net):
        for it in self.items.get(net, []):
            self.b.Remove(it)
        self.items[net] = []
        for l in LAYERS: self.route[l][self.route[l] == net] = 0
        self.rholes[self.rholes == net] = 0
        # restore fixed holes (cheap: recompute from fixed vias/pads in the board is expensive; holes array only gates vias, keep conservative)
    def maps(self, net, hw, win, soft):
        y0, y1, x0, x1 = win
        st = disk_st((hw + CLR) / RES)
        hard, softm = [], []
        for l in LAYERS:
            F = self.fixed[l][y0:y1, x0:x1]; Rr = self.route[l][y0:y1, x0:x1]
            ff = (F != 0) & (F != net)
            rf = (Rr != 0) & (Rr != net)
            if soft:
                hard.append(ndimage.binary_dilation(ff, structure=st)); softm.append(ndimage.binary_dilation(rf, structure=st))
            else:
                hard.append(ndimage.binary_dilation(ff | rf, structure=st)); softm.append(np.zeros_like(ff))
        stv = disk_st((VIA_D / 2 + CLR) / RES)
        vf = np.zeros((y1 - y0, x1 - x0), bool); vr = np.zeros_like(vf)
        for l in LAYERS:
            F = self.fixed[l][y0:y1, x0:x1]; Rr = self.route[l][y0:y1, x0:x1]
            vf |= (F != 0) & (F != net); vr |= (Rr != 0) & (Rr != net)
        vhard = ndimage.binary_dilation(vf | (vr if not soft else False), structure=stv)
        vhard |= ndimage.binary_dilation(self.r1.padmask[y0:y1, x0:x1], structure=disk_st((VIA_D / 2 + 0.05) / RES))
        vhard |= ndimage.binary_dilation(self.r1.holes[y0:y1, x0:x1] | (self.rholes[y0:y1, x0:x1] != 0), structure=disk_st((VIA_DRILL / 2 + 0.25) / RES))
        vsoft = ndimage.binary_dilation(vr, structure=stv) if soft else np.zeros_like(vf)
        return hard, softm, vhard, vsoft
    def astar(self, net, starts, goal, win, hw, soft=False, pen=40.0, via_cost=24.0, cap=1_200_000):
        y0, y1, x0, x1 = win; H, W = y1 - y0, x1 - x0
        hard, softm, vhard, vsoft = self.maps(net, hw, win, soft)
        hist = [self.hist[l][y0:y1, x0:x1] for l in LAYERS]
        gy, gx = np.nonzero(goal[0] | goal[1])
        if len(gy) == 0: return None
        gyc0, gyc1, gxc0, gxc1 = gy.min(), gy.max(), gx.min(), gx.max()
        def hh(y, x):
            dy = 0 if gyc0 <= y <= gyc1 else min(abs(y - gyc0), abs(y - gyc1))
            dx = 0 if gxc0 <= x <= gxc1 else min(abs(x - gxc0), abs(x - gxc1))
            return max(dx, dy) + 0.414 * min(dx, dy)
        g = np.full((2, H, W), np.inf); prev = -np.ones((2, H, W), np.int64); pq = []
        for (li, y, x) in starts:
            y -= y0; x -= x0
            if 0 <= y < H and 0 <= x < W: g[li, y, x] = 0; heapq.heappush(pq, (hh(y, x), 0.0, li, y, x))
        moves = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0), (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
        n = 0
        while pq:
            f, gc, li, y, x = heapq.heappop(pq)
            if gc > g[li, y, x]: continue
            n += 1
            if n > cap: return None
            if goal[li][y, x]:
                path = []; cur = (li, y, x)
                while True:
                    path.append((cur[0], cur[1] + y0, cur[2] + x0)); p = prev[cur]
                    if p < 0: break
                    cur = (int(p // (H * W)), int((p % (H * W)) // W), int(p % W))
                return path[::-1]
            for dy, dx, c in moves:
                ny_, nx_ = y + dy, x + dx
                if 0 <= ny_ < H and 0 <= nx_ < W and not hard[li][ny_, nx_]:
                    ng = gc + c * (1.0 + hist[li][ny_, nx_]) + (0.2 if li == 1 else 0.0) + (pen if softm[li][ny_, nx_] else 0.0)
                    if ng < g[li, ny_, nx_]:
                        g[li, ny_, nx_] = ng; prev[li, ny_, nx_] = li * H * W + y * W + x
                        heapq.heappush(pq, (ng + hh(ny_, nx_), ng, li, ny_, nx_))
            lo = 1 - li
            if not vhard[y, x] and not hard[lo][y, x]:
                ng = gc + via_cost + (pen * 3 if vsoft[y, x] else 0.0)
                if ng < g[lo, y, x]:
                    g[lo, y, x] = ng; prev[lo, y, x] = li * H * W + y * W + x
                    heapq.heappush(pq, (ng + hh(y, x), ng, lo, y, x))
        return None
    def crossed_nets(self, path, net, hw):
        """nets whose routed copper conflicts with this path (with clearance)."""
        hit = set(); r = int(math.ceil((hw + CLR + 0.15) / RES))
        for (li, y, x) in path[::2]:
            for l in ([LAYERS[li]] if True else LAYERS):
                sub = self.route[l][max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
                hit |= set(np.unique(sub[(sub != 0) & (sub != net)]).tolist())
        for k in range(1, len(path)):
            if path[k][0] != path[k - 1][0]:
                y, x = path[k][1], path[k][2]; rv = int(math.ceil((VIA_D / 2 + CLR + 0.15) / RES))
                for l in LAYERS:
                    sub = self.route[l][max(0, y - rv):y + rv + 1, max(0, x - rv):x + rv + 1]
                    hit |= set(np.unique(sub[(sub != 0) & (sub != net)]).tolist())
        return hit
    def commit(self, path, net, w):
        pts = [(li, (x + 0.5) * RES + OX, (y + 0.5) * RES + OY) for (li, y, x) in path]
        runs = []; vias = []; run = [pts[0]]
        for p in pts[1:]:
            if p[0] != run[-1][0]: runs.append(run); vias.append((p[1], p[2])); run = [p]
            else: run.append(p)
        runs.append(run)
        for run in runs:
            if len(run) < 2: continue
            simp = [run[0]]
            for i in range(1, len(run) - 1):
                a, b_, c = simp[-1], run[i], run[i + 1]
                if abs((b_[1] - a[1]) * (c[2] - a[2]) - (b_[2] - a[2]) * (c[1] - a[1])) > 1e-9: simp.append(b_)
            simp.append(run[-1])
            for a, b_ in zip(simp[:-1], simp[1:]):
                self.add_track((a[1], a[2]), (b_[1], b_[2]), LAYERS[a[0]], w, net)
        for (x, y) in vias: self.add_via(x, y, net)
        for (li, y, x) in path: self.hist[LAYERS[li]][y, x] += 0.0

def net_groups(b, net, pads):
    b.BuildConnectivity(); con = b.GetConnectivity()
    groups, seen = [], set()
    for p in pads:
        key = (p.GetParentFootprint().GetReference(), p.GetNumber())
        if key in seen: continue
        grp = {key}
        for q in con.GetConnectedPads(p):
            if q.GetNetCode() == net: grp.add((q.GetParentFootprint().GetReference(), q.GetNumber()))
        seen |= grp; groups.append(grp)
    return groups

def main():
    t0 = time.time()
    src = os.path.join(HERE, "esp32_sdr.kicad_pcb")
    RT = Router2(src); b = RT.b
    RT.r1.raster_all()
    # plane vias via router v1 logic (fixed copper)
    R1_main_plane_vias(RT.r1)
    gnd, v33 = RT.netid.get("GND"), RT.netid.get("3V3")
    allpads = {}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() and p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                allpads.setdefault(p.GetNetCode(), []).append(p)
    names = {v: k for k, v in RT.netid.items()}
    queue = []
    for net, pads in allpads.items():
        name = names.get(net, "")
        if net == gnd or not name: continue
        if net == v33:
            pads = [p for p in pads if in_poly(pcbnew.ToMM(p.GetPosition().x) - OX, pcbnew.ToMM(p.GetPosition().y) - OY, RF_REGION)]
            if pads: queue.append((name, net, "plane3v3"))
            continue
        if len(pads) >= 2: queue.append((name, net, "net"))
    def span(q):
        ps = allpads[q[1]]; xs = [p.GetPosition().x for p in ps]; ys = [p.GetPosition().y for p in ps]
        return (0 if q[0] in POWER else 1, (max(xs) - min(xs)) + (max(ys) - min(ys)))
    queue.sort(key=span)
    ripups = {}; MAXRIP = 6; total_rip = 0; failed = {}
    it = 0
    while queue and it < 2000:
        it += 1
        name, net, kind = queue.pop(0)
        w = PWR_W if name in POWER else SIG_W; hw = w / 2
        pads = allpads[net] if kind == "net" else [p for p in allpads[net] if in_poly(pcbnew.ToMM(p.GetPosition().x) - OX, pcbnew.ToMM(p.GetPosition().y) - OY, RF_REGION)]
        groups = net_groups(b, net, pads)
        padobj = {(p.GetParentFootprint().GetReference(), p.GetNumber()): p for p in allpads[net]}
        tree = set(groups[0]) if kind == "net" else set()
        rest = groups[1:] if kind == "net" else groups
        net_fail = []
        while rest:
            if tree:
                rest.sort(key=lambda gr: min((padobj[a].GetPosition() - padobj[c].GetPosition()).EuclideanNorm() for a in gr for c in tree))
            gr = rest.pop(0); src_pad = padobj[sorted(gr)[0]]
            sx, sy = pcbnew.ToMM(src_pad.GetPosition().x), pcbnew.ToMM(src_pad.GetPosition().y)
            if kind == "net":
                tx = [pcbnew.ToMM(padobj[k].GetPosition().x) for k in tree]; ty = [pcbnew.ToMM(padobj[k].GetPosition().y) for k in tree]
            else:
                tx, ty = [57.5 + OX], [24.0 + OY]
            done = False
            for soft in (False, True):
                for marg in (2.0, 6.0, 15.0):
                    X0 = max(0, int((min(tx + [sx]) - OX - marg) / RES)); X1 = min(NX, int((max(tx + [sx]) - OX + marg) / RES))
                    Y0 = max(0, int((min(ty + [sy]) - OY - marg) / RES)); Y1 = min(NY, int((max(ty + [sy]) - OY + marg) / RES))
                    win = (Y0, Y1, X0, X1)
                    goal = []
                    for l in LAYERS:
                        Lm = (RT.fixed[l][Y0:Y1, X0:X1] == net) | (RT.route[l][Y0:Y1, X0:X1] == net)
                        if kind == "plane3v3":
                            yy, xx = np.mgrid[Y0:Y1, X0:X1]; xm = (xx + 0.5) * RES; ym = (yy + 0.5) * RES
                            inside = (xm < 57.0) & ((ym < 21.0) | ((xm < 35.0) & (ym < 28.5)))
                            goal.append(Lm & ~inside & (RT.fixed[l][Y0:Y1, X0:X1] == net)); continue
                        lab = ndimage.label(Lm)[0]; keep = set()
                        for k in tree:
                            p = padobj[k]; px, py = to_px(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
                            iy, ix = int(py) - Y0, int(px) - X0
                            if 0 <= iy < lab.shape[0] and 0 <= ix < lab.shape[1] and lab[iy, ix] > 0: keep.add(lab[iy, ix])
                        goal.append(np.isin(lab, list(keep)) if keep else np.zeros_like(Lm))
                    spx, spy = to_px(sx, sy)
                    starts = [(li, int(spy), int(spx)) for li, l in enumerate(LAYERS) if src_pad.IsOnLayer(l)]
                    path = RT.astar(net, starts, goal, win, hw, soft=soft)
                    if path is None: continue
                    if soft:
                        hit = RT.crossed_nets(path, net, hw)
                        hit = {h for h in hit if ripups.get(h, 0) < MAXRIP}
                        if not hit: continue
                        for h in hit:
                            RT.ripup(h); ripups[h] = ripups.get(h, 0) + 1; total_rip += 1
                            hn = names[h]; queue.append((hn, h, "plane3v3" if h == v33 else "net"))
                        for (li, y, x) in path: RT.hist[LAYERS[li]][y, x] += 0.5
                        path = RT.astar(net, starts, goal, win, hw, soft=False)
                        if path is None: continue
                    RT.commit(path, net, w); done = True; break
                if done: break
            if done: tree |= gr
            else: net_fail.append(sorted(gr)); tree |= gr
        if net_fail: failed[name] = net_fail
        elif name in failed: del failed[name]
        if it % 20 == 0: print(f"it {it} queue {len(queue)} rip {total_rip} failed {len(failed)} ({time.time()-t0:.0f}s)", flush=True)
    out = os.path.join(HERE, "esp32_sdr_routed.kicad_pcb"); pcbnew.SaveBoard(out, b)
    rep = [f"FAIL {k}: {v}" for k, v in failed.items()]
    open(os.path.join(HERE, "route_report.txt"), "w").write(f"iterations {it}, ripups {total_rip}\n" + "\n".join(rep) + "\n")
    print("saved", out, "failed nets:", len(failed), "ripups:", total_rip, f"{time.time()-t0:.0f}s")

def R1_main_plane_vias(r1):
    """Copy of router.main's plane-via stage, operating on r1 (fixed copper)."""
    import types
    b = r1.b; gnd = r1.netid.get("GND"); v33 = r1.netid.get("3V3")
    vias = [t for t in b.GetTracks() if isinstance(t, pcbnew.PCB_VIA)]
    tracks = [t for t in b.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    def has_via_near(pad, net):
        c = pad.GetPosition()
        for t in vias:
            if t.GetNetCode() == net and (t.GetPosition() - c).EuclideanNorm() < mm(1.2): return True
        for t in tracks:
            if t.GetNetCode() == net:
                for e in (t.GetStart(), t.GetEnd()):
                    if (e - c).EuclideanNorm() < mm(0.3): return True
        return False
    nvia, fail = 0, []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNetCode()
            if net not in (gnd, v33) or not pad.IsOnLayer(pcbnew.F_Cu) or pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH: continue
            px, py = pcbnew.ToMM(pad.GetPosition().x) - OX, pcbnew.ToMM(pad.GetPosition().y) - OY
            if net == v33 and in_poly(px, py, RF_REGION): continue
            if pad.GetNumber() == "": continue
            if fp.GetReference() in ("U1", "U3", "U201") and pad.GetNumber() in ("81", "33", "41"): continue   # EP: thermal vias
            if has_via_near(pad, net): continue
            c = pad.GetPosition(); cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            sz = max(pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)) / 2
            win = (max(0, int((cy - OY - 3) / RES)), min(NY, int((cy - OY + 3) / RES)), max(0, int((cx - OX - 3) / RES)), min(NX, int((cx - OX + 3) / RES)))
            vb = r1.via_blocked(net, win); tb = r1.blocked(pcbnew.F_Cu, net, 0.125, win)
            best = None
            for rr in np.arange(sz + 0.35, sz + 1.8, 0.05):
                for ang in np.arange(0, 2 * np.pi, np.pi / 16):
                    vx, vy = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
                    iy, ix = int((vy - OY) / RES) - win[0], int((vx - OX) / RES) - win[2]
                    if not (0 <= iy < vb.shape[0] and 0 <= ix < vb.shape[1]) or vb[iy, ix]: continue
                    ok = True
                    for s in np.linspace(0, 1, 12):
                        jy, jx = int((cy + (vy - cy) * s - OY) / RES) - win[0], int((cx + (vx - cx) * s - OX) / RES) - win[2]
                        if not (0 <= jy < tb.shape[0] and 0 <= jx < tb.shape[1]) or tb[jy, jx]: ok = False; break
                    if ok: best = (vx, vy); break
                if best: break
            if best:
                r1.add_track((cx, cy), best, pcbnew.F_Cu, 0.25, net); r1.add_via(*best, net); nvia += 1
            else: fail.append(f"{fp.GetReference()}.{pad.GetNumber()}")
    print("plane vias", nvia, "failed", fail, flush=True)

if __name__ == "__main__":
    main()

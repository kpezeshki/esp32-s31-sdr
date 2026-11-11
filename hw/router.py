#!/usr/bin/env python3
"""
Simple grid maze router for the ESP32-S31 SDR board (no external autorouter available).
- Layers: F.Cu, B.Cu for routing; In1.Cu = GND plane, In2.Cu = GND (RF region) / 3V3 (digital region).
- GND pads (and 3V3 pads inside the 3V3 plane region) get a via to their plane.
- Remaining connections: A* on a 0.05 mm grid, 8-connected, with layer change (via) cost; clearance by dilating
  foreign copper by (half-width + clearance + margin). Bounding-box corridor that grows on failure.
Input: hw/esp32_sdr.kicad_pcb (placed + RF routed). Output: hw/esp32_sdr_routed.kicad_pcb, hw/route_report.txt
"""
import os, sys, math, heapq, time, json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
OX, OY, BW, BH = 100.0, 100.0, 70.0, 70.0
RES = 0.05
NX, NY = int(BW / RES), int(BH / RES)
CLR = 0.10 + 0.005            # clearance + discretisation margin
SIG_W, PWR_W = 0.127, 0.30
VIA_D, VIA_DRILL = 0.45, 0.2
EDGE_KEEP = 0.35
def mm(v): return pcbnew.FromMM(float(v))
POWER = {"5V0", "3V3_PHY", "3V0_RF", "VLNA_LB", "VLNA_MB", "VLNA_HB", "VGB", "V1P8", "VDD_SPI", "VDDA34", "PHY_VDDL",
         "PHY_3V3", "VBUS", "3V3"}
RF_REGION = [(0, 0), (57.0, 0), (57.0, 21.0), (35.0, 21.0), (35.0, 28.5), (0, 28.5)]   # In2 = GND here, 3V3 elsewhere

def in_poly(x, y, poly):
    c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c

def to_px(x, y): return ((x - OX) / RES, (y - OY) / RES)      # KiCad mm -> pixel (float)
def bxy(x, y): return (x + OX, y + OY)

class Router:
    def __init__(self, path):
        self.b = pcbnew.LoadBoard(path)
        self.netid = {}
        for name, ni in self.b.GetNetsByName().items():
            self.netid[str(name)] = ni.GetNetCode()
        self.lab = {pcbnew.F_Cu: np.zeros((NY, NX), np.int32), pcbnew.B_Cu: np.zeros((NY, NX), np.int32)}
        self.padmask = np.zeros((NY, NX), bool)        # any pad copper (no vias on pads)
        self.holes = np.zeros((NY, NX), bool)
        self.log = []
    # ---------------------------------------------------------------- rasterisation
    def draw_poly(self, layer, pts_mm, val):
        im = Image.fromarray(self.lab[layer]); d = ImageDraw.Draw(im)
        d.polygon([to_px(x, y) for x, y in pts_mm], fill=int(val)); self.lab[layer] = np.array(im, np.int32)
    def raster_all(self):
        # board edge keep-out
        k = int(EDGE_KEEP / RES)
        for L in self.lab.values():
            L[:k, :] = -1; L[-k:, :] = -1; L[:, :k] = -1; L[:, -k:] = -1
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                net = pad.GetNetCode() or -1
                for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if not pad.IsOnLayer(layer): continue
                    poly = pad.GetEffectivePolygon(layer, pcbnew.ERROR_OUTSIDE)
                    for oi in range(poly.OutlineCount()):
                        ol = poly.Outline(oi)
                        pts = [(pcbnew.ToMM(ol.CPoint(i).x), pcbnew.ToMM(ol.CPoint(i).y)) for i in range(ol.PointCount())]
                        if len(pts) >= 3:
                            self._fill(layer, pts, net)
                            if layer == pcbnew.F_Cu or pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                                self._mask(pts)
                if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                    c = pad.GetPosition(); r = pcbnew.ToMM(max(pad.GetDrillSize().x, pad.GetDrillSize().y)) / 2
                    self._disk_bool(self.holes, pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), r)
                    if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                        for layer in self.lab:
                            self._disk(layer, pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), r + 0.2, -1)
        for t in self.b.GetTracks():
            self.raster_item(t)
    def _fill(self, layer, pts, val):
        im = Image.fromarray(self.lab[layer]); d = ImageDraw.Draw(im)
        d.polygon([to_px(x, y) for x, y in pts], fill=int(val), outline=int(val)); self.lab[layer] = np.array(im, np.int32)
    def _mask(self, pts):
        im = Image.fromarray(self.padmask.astype(np.uint8)); d = ImageDraw.Draw(im)
        d.polygon([to_px(x, y) for x, y in pts], fill=1, outline=1); self.padmask = np.array(im, bool)
    def _disk(self, layer, x, y, r, val):
        cx, cy = to_px(x, y); rr = r / RES
        y0, y1 = int(max(0, cy - rr - 1)), int(min(NY, cy + rr + 2)); x0, x1 = int(max(0, cx - rr - 1)), int(min(NX, cx + rr + 2))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        m = (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= rr ** 2
        sub = self.lab[layer][y0:y1, x0:x1]; sub[m] = val
    def _disk_bool(self, arr, x, y, r):
        cx, cy = to_px(x, y); rr = r / RES
        y0, y1 = int(max(0, cy - rr - 1)), int(min(NY, cy + rr + 2)); x0, x1 = int(max(0, cx - rr - 1)), int(min(NX, cx + rr + 2))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        arr[y0:y1, x0:x1] |= (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= rr ** 2
    def _seg(self, layer, a, b, w, val):
        im = Image.fromarray(self.lab[layer]); d = ImageDraw.Draw(im)
        pa, pb = to_px(*a), to_px(*b); wp = max(1, int(round(w / RES)))
        d.line([pa, pb], fill=int(val), width=wp)
        r = w / 2 / RES
        for (px, py) in (pa, pb):
            d.ellipse([px - r, py - r, px + r, py + r], fill=int(val))
        self.lab[layer] = np.array(im, np.int32)
    def raster_item(self, t):
        net = t.GetNetCode() or -1
        if isinstance(t, pcbnew.PCB_VIA):
            c = t.GetPosition(); r = pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2
            for layer in self.lab: self._disk(layer, pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), r, net)
            self._disk_bool(self.holes, pcbnew.ToMM(c.x), pcbnew.ToMM(c.y), pcbnew.ToMM(t.GetDrillValue()) / 2)
        else:
            if t.GetLayer() not in self.lab: return
            s, e = t.GetStart(), t.GetEnd()
            self._seg(t.GetLayer(), (pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)), (pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)), pcbnew.ToMM(t.GetWidth()), net)
    # ---------------------------------------------------------------- board edits
    def add_track(self, a, b, layer, w, net):
        t = pcbnew.PCB_TRACK(self.b); t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNetCode(net); self.b.Add(t); self.raster_item(t); return t
    def add_via(self, x, y, net):
        v = pcbnew.PCB_VIA(self.b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL))
        v.SetNetCode(net); self.b.Add(v); self.raster_item(v); return v
    # ---------------------------------------------------------------- blocked maps
    def blocked(self, layer, net, hw, win):
        y0, y1, x0, x1 = win
        L = self.lab[layer][y0:y1, x0:x1]
        foreign = (L != 0) & (L != net)
        r = (hw + CLR) / RES
        ri = int(math.ceil(r))
        yy, xx = np.mgrid[-ri:ri + 1, -ri:ri + 1]
        st = (xx ** 2 + yy ** 2) <= r * r
        return ndimage.binary_dilation(foreign, structure=st)
    def via_blocked(self, net, win):
        y0, y1, x0, x1 = win
        r = (VIA_D / 2 + CLR) / RES; ri = int(math.ceil(r))
        yy, xx = np.mgrid[-ri:ri + 1, -ri:ri + 1]; st = (xx ** 2 + yy ** 2) <= r * r
        bad = np.zeros((y1 - y0, x1 - x0), bool)
        for layer in self.lab:
            L = self.lab[layer][y0:y1, x0:x1]
            bad |= (L != 0) & (L != net)
        bad = ndimage.binary_dilation(bad, structure=st)
        rp = (VIA_D / 2 + 0.05) / RES; rpi = int(math.ceil(rp)); yy, xx = np.mgrid[-rpi:rpi + 1, -rpi:rpi + 1]
        bad |= ndimage.binary_dilation(self.padmask[y0:y1, x0:x1], structure=(xx ** 2 + yy ** 2) <= rp * rp)
        rh = (VIA_DRILL / 2 + 0.25) / RES; rhi = int(math.ceil(rh)); yy, xx = np.mgrid[-rhi:rhi + 1, -rhi:rhi + 1]
        bad |= ndimage.binary_dilation(self.holes[y0:y1, x0:x1], structure=(xx ** 2 + yy ** 2) <= rh * rh)
        return bad
    # ---------------------------------------------------------------- A*
    def astar(self, net, starts, goal_mask_fn, win, hw, via_cost=24.0):
        y0, y1, x0, x1 = win
        H, W = y1 - y0, x1 - x0
        layers = [pcbnew.F_Cu, pcbnew.B_Cu]
        blk = [self.blocked(l, net, hw, win) for l in layers]
        vblk = self.via_blocked(net, win)
        goal = [goal_mask_fn(l, win) for l in layers]
        if not any(g.any() for g in goal): return None
        gy, gx = np.nonzero(goal[0] | goal[1])
        def h(y, x):
            d = np.min(np.abs(gy - y) + np.abs(gx - x)) if len(gy) < 2000 else 0
            return d
        # cheap heuristic: distance to goal centroid bbox
        gyc0, gyc1, gxc0, gxc1 = gy.min(), gy.max(), gx.min(), gx.max()
        def hh(y, x):
            dy = 0 if gyc0 <= y <= gyc1 else min(abs(y - gyc0), abs(y - gyc1))
            dx = 0 if gxc0 <= x <= gxc1 else min(abs(x - gxc0), abs(x - gxc1))
            return max(dx, dy) + 0.414 * min(dx, dy)
        INF = 1e18
        g = np.full((2, H, W), INF)
        prev = -np.ones((2, H, W), np.int64)
        pq = []
        for (li, y, x) in starts:
            y -= y0; x -= x0
            if 0 <= y < H and 0 <= x < W:
                g[li, y, x] = 0; heapq.heappush(pq, (hh(y, x), 0.0, li, y, x))
        moves = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0), (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
        n = 0
        while pq:
            f, gc, li, y, x = heapq.heappop(pq)
            if gc > g[li, y, x]: continue
            n += 1
            if n > 1_500_000: return None
            if goal[li][y, x]:
                path = []; cur = (li, y, x)
                while True:
                    path.append((cur[0], cur[1] + y0, cur[2] + x0))
                    p = prev[cur]
                    if p < 0: break
                    cur = (int(p // (H * W)), int((p % (H * W)) // W), int(p % W))
                return path[::-1]
            for dy, dx, c in moves:
                ny_, nx_ = y + dy, x + dx
                if 0 <= ny_ < H and 0 <= nx_ < W and not blk[li][ny_, nx_]:
                    ng = gc + c + (0.2 if li == 1 else 0.0)          # mild preference for F.Cu
                    if ng < g[li, ny_, nx_]:
                        g[li, ny_, nx_] = ng; prev[li, ny_, nx_] = li * H * W + y * W + x
                        heapq.heappush(pq, (ng + hh(ny_, nx_), ng, li, ny_, nx_))
            lo = 1 - li
            if not vblk[y, x] and not blk[lo][y, x]:
                ng = gc + via_cost
                if ng < g[lo, y, x]:
                    g[lo, y, x] = ng; prev[lo, y, x] = li * H * W + y * W + x
                    heapq.heappush(pq, (ng + hh(y, x), ng, lo, y, x))
        return None
    def commit(self, path, net, w):
        layers = [pcbnew.F_Cu, pcbnew.B_Cu]
        pts = [(li, (x + 0.5) * RES + OX, (y + 0.5) * RES + OY) for (li, y, x) in path]
        # split into runs per layer, simplify collinear points
        segs = []; vias = []
        run = [pts[0]]
        for p in pts[1:]:
            if p[0] != run[-1][0]:
                segs.append(run); vias.append((p[1], p[2])); run = [p]
            else:
                run.append(p)
        segs.append(run)
        for run in segs:
            if len(run) < 2: continue
            simp = [run[0]]
            for i in range(1, len(run) - 1):
                a, b_, c = simp[-1], run[i], run[i + 1]
                if abs((b_[1] - a[1]) * (c[2] - a[2]) - (b_[2] - a[2]) * (c[1] - a[1])) > 1e-9: simp.append(b_)
            simp.append(run[-1])
            for a, b_ in zip(simp[:-1], simp[1:]):
                self.add_track((a[1], a[2]), (b_[1], b_[2]), layers[a[0]], w, net)
        for (x, y) in vias:
            self.add_via(x, y, net)

def main():
    src = os.path.join(HERE, "esp32_sdr.kicad_pcb")
    R = Router(src)
    t0 = time.time()
    R.raster_all()
    print("rasterised in %.1fs" % (time.time() - t0), flush=True)
    b = R.b
    gnd = R.netid.get("GND"); v33 = R.netid.get("3V3")
    # ---------------- plane vias: GND everywhere, 3V3 inside the 3V3 region
    def has_via_near(pad, net):
        c = pad.GetPosition()
        for t in b.GetTracks():
            if t.GetNetCode() == net and (isinstance(t, pcbnew.PCB_VIA) or True):
                if isinstance(t, pcbnew.PCB_VIA):
                    if (t.GetPosition() - c).EuclideanNorm() < mm(1.2): return True
                else:
                    for e in (t.GetStart(), t.GetEnd()):
                        if (e - c).EuclideanNorm() < mm(0.3): return True
        return False
    nvia = 0; fail_v = []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNetCode()
            if net not in (gnd, v33) or not pad.IsOnLayer(pcbnew.F_Cu): continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH: continue
            px, py = pcbnew.ToMM(pad.GetPosition().x) - OX, pcbnew.ToMM(pad.GetPosition().y) - OY
            if net == v33 and in_poly(px, py, RF_REGION): continue        # routed to the plane region instead
            if fp.GetReference() == "U1" and pad.GetNumber() in ("81", ""): continue
            if has_via_near(pad, net): continue
            # search a via spot near the pad
            c = pad.GetPosition(); cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            sz = max(pcbnew.ToMM(pad.GetSize().x), pcbnew.ToMM(pad.GetSize().y)) / 2
            win = (max(0, int((cy - OY - 3) / RES)), min(NY, int((cy - OY + 3) / RES)), max(0, int((cx - OX - 3) / RES)), min(NX, int((cx - OX + 3) / RES)))
            vb = R.via_blocked(net, win); tb = R.blocked(pcbnew.F_Cu, net, 0.125, win)
            best = None
            for rr in np.arange(sz + 0.35, sz + 1.8, 0.05):
                for ang in np.arange(0, 2 * np.pi, np.pi / 16):
                    vx, vy = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
                    iy, ix = int((vy - OY) / RES) - win[0], int((vx - OX) / RES) - win[2]
                    if not (0 <= iy < vb.shape[0] and 0 <= ix < vb.shape[1]) or vb[iy, ix]: continue
                    # straight stub must be clear
                    ok = True
                    for s in np.linspace(0, 1, 12):
                        sx, sy = cx + (vx - cx) * s, cy + (vy - cy) * s
                        jy, jx = int((sy - OY) / RES) - win[0], int((sx - OX) / RES) - win[2]
                        if not (0 <= jy < tb.shape[0] and 0 <= jx < tb.shape[1]) or tb[jy, jx]: ok = False; break
                    if ok: best = (vx, vy); break
                if best: break
            if best:
                R.add_track((cx, cy), best, pcbnew.F_Cu, 0.25, net); R.add_via(*best, net); nvia += 1
            else:
                fail_v.append(f"{fp.GetReference()}.{pad.GetNumber()}")
    print(f"plane vias: {nvia}, failed: {fail_v}", flush=True)
    # ---------------- connection tasks
    b.BuildConnectivity(); con = b.GetConnectivity()
    tasks = []
    for name, net in R.netid.items():
        if net in (0, gnd) or not name: continue
        pads = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetCode() == net and (p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH)]
        if net == v33:
            pads = [p for p in pads if in_poly(pcbnew.ToMM(p.GetPosition().x) - OX, pcbnew.ToMM(p.GetPosition().y) - OY, RF_REGION)]
            if not pads: continue
            tasks.append((name, net, pads, "plane3v3")); continue
        if len(pads) < 2: continue
        tasks.append((name, net, pads, "net"))
    def tlen(t):
        xs = [pcbnew.ToMM(p.GetPosition().x) for p in t[2]]; ys = [pcbnew.ToMM(p.GetPosition().y) for p in t[2]]
        return (0 if t[0] in POWER else 1, (max(xs) - min(xs)) + (max(ys) - min(ys)))
    tasks.sort(key=tlen)
    prio_f = os.path.join(HERE, "route_priority.json")
    if os.path.exists(prio_f):
        prio = json.load(open(prio_f))
        tasks.sort(key=lambda t: (0 if t[0] in prio else 1, prio.index(t[0]) if t[0] in prio else 0))
    report = []; failed = []
    for (name, net, pads, kind) in tasks:
        w = PWR_W if name in POWER else SIG_W
        hw = w / 2
        # components already connected (scripted tracks): group pads by GetConnectedPads
        b.BuildConnectivity(); con = b.GetConnectivity()
        groups = []
        seen = set()
        for p in pads:
            key = (p.GetParentFootprint().GetReference(), p.GetNumber())
            if key in seen: continue
            grp = {key}
            try:
                for q in con.GetConnectedPads(p):
                    if q.GetNetCode() == net: grp.add((q.GetParentFootprint().GetReference(), q.GetNumber()))
            except Exception:
                pass
            seen |= grp; groups.append(grp)
        if kind == "plane3v3":
            # connect each RF-region 3V3 group to any 3V3 copper outside the RF region (plane vias)
            targets = None
        padobj = {(p.GetParentFootprint().GetReference(), p.GetNumber()): p for p in pads}
        if kind == "net" and len(groups) < 2: continue
        tree = set(groups[0]) if kind == "net" else set()
        rest = groups[1:] if kind == "net" else groups
        while rest:
            # nearest group to the tree (by pad distance)
            def gdist(gr):
                if not tree: return 0
                return min((padobj[a].GetPosition() - padobj[b_].GetPosition()).EuclideanNorm() for a in gr for b_ in tree if a in padobj and b_ in padobj)
            rest.sort(key=gdist); gr = rest.pop(0)
            src_pad = padobj[sorted(gr)[0]]
            sx, sy = pcbnew.ToMM(src_pad.GetPosition().x), pcbnew.ToMM(src_pad.GetPosition().y)
            if kind == "net":
                tx = [pcbnew.ToMM(padobj[k].GetPosition().x) for k in tree]; ty = [pcbnew.ToMM(padobj[k].GetPosition().y) for k in tree]
            else:
                tx, ty = [57.0 + OX], [24.0 + OY]
            ok = False
            for marg in (2.0, 5.0, 12.0, 40.0):
                X0 = max(0, int((min(tx + [sx]) - OX - marg) / RES)); X1 = min(NX, int((max(tx + [sx]) - OX + marg) / RES))
                Y0 = max(0, int((min(ty + [sy]) - OY - marg) / RES)); Y1 = min(NY, int((max(ty + [sy]) - OY + marg) / RES))
                win = (Y0, Y1, X0, X1)
                treemask_cache = {}
                def goal_fn(layer, win, net=net, tree=tree, kind=kind):
                    y0, y1, x0, x1 = win
                    L = R.lab[layer][y0:y1, x0:x1] == net
                    if kind == "plane3v3":
                        # any 3V3 copper whose position is outside the RF region
                        yy, xx = np.mgrid[y0:y1, x0:x1]
                        xmm = (xx + 0.5) * RES; ymm = (yy + 0.5) * RES
                        inside = (xmm < 57.0) & ((ymm < 21.0) | ((xmm < 35.0) & (ymm < 28.5)))
                        return L & ~inside
                    # copper connected to the tree: approximate with pads of the tree + net copper not part of this group
                    m = np.zeros_like(L)
                    lab_g = ndimage.label(L)[0]
                    keep = set()
                    for k in tree:
                        p = padobj[k]; px, py = to_px(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y))
                        iy, ix = int(py) - y0, int(px) - x0
                        if 0 <= iy < L.shape[0] and 0 <= ix < L.shape[1] and lab_g[iy, ix] > 0: keep.add(lab_g[iy, ix])
                    return np.isin(lab_g, list(keep)) if keep else m
                spx, spy = to_px(sx, sy)
                starts = []
                for li, layer in enumerate([pcbnew.F_Cu, pcbnew.B_Cu]):
                    if src_pad.IsOnLayer(layer): starts.append((li, int(spy), int(spx)))
                path = R.astar(net, starts, goal_fn, win, hw)
                if path:
                    R.commit(path, net, w); ok = True; break
            if ok:
                tree |= gr; report.append(f"OK   {name} {sorted(gr)[0]}")
            else:
                failed.append(f"{name}: {sorted(gr)}"); report.append(f"FAIL {name} {sorted(gr)}")
                tree |= gr
        print(f"{name}: done ({time.time() - t0:.0f}s)", flush=True)
    out = os.path.join(HERE, "esp32_sdr_routed.kicad_pcb")
    pcbnew.SaveBoard(out, b)
    fnets = []
    for f_ in failed:
        n_ = f_.split(":")[0]
        if n_ not in fnets: fnets.append(n_)
    old = json.load(open(prio_f)) if os.path.exists(prio_f) else []
    json.dump(fnets + [n_ for n_ in old if n_ not in fnets], open(prio_f, "w"))
    open(os.path.join(HERE, "route_report.txt"), "w").write("\n".join(report) + "\n\nFAILED:\n" + "\n".join(failed) + "\n")
    print("saved", out, "failed:", len(failed))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
EM co-simulation of the 0402 band-filter layouts on the JLC 4-layer stack (L1 signal over solid L2 GND,
3313 prepreg 0.0994 mm, er 4.1, tan d 0.02 assumed).

1. ladder_geometry(): physical layout of a filter topology (same code places the parts on the PCB).
2. write_son(): Sonnet project with STD ports at the box walls (filter in/out) and AGND internal ports at
   the inner edge of every component pad (2 per component).
3. Sonnet em -> N-port touchstone.
4. cosim(): attach component models between pad-port pairs (nodal admittance), Kron-reduce to the
   2 external ports. Component models: intrinsic 0402 parasitics only (pads/vias/lines are in the EM data).
5. reopt(): re-optimize component values against the EM data, restricted to the joint 0402 palette.

Usage: python3 filter_em.py NAME [--run] [--reopt]      NAME in LB_LPF MB_BPF2 HB_HPF HB_PRE
"""
import os, sys, json, math, subprocess, time, shutil
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "analysis"))
import filters as F

SON = os.environ.get("SONNET_DIR", "/home/kaveh/tools/sonnet19")
# Sonnet licence: export RLM_LICENSE=<port>@<license-server> before running (not stored in the repo)
if not os.environ.get("RLM_LICENSE"): print("warning: RLM_LICENSE not set; Sonnet em will not find a licence")
OUT = os.path.join(HERE, "filters"); os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- stack / geometry constants (mm)
H_PP, ER_PP, TAN_PP = 0.0994, 4.1, 0.02
W50 = 0.19                     # 50 ohm microstrip on 0.0994 mm 3313 (Sonnet check: S11 < -40 dB, em/test/t1)
PAD_W, PAD_L, PAD_X = 0.62, 0.56, 0.48     # KiCad C_0402_1005Metric: pad 0.56 (along axis) x 0.62, centres +-0.48
VIA_D, VIA_PAD = 0.30, 0.50
GAP_T = 0.30                   # trace length between neighbouring parts
LEAD = 1.0                     # 50 ohm lead at each wall port
CELL = 0.01                    # Sonnet cell (mm)
H_CORE, ER_CORE, TAN_CORE = 1.265, 4.5, 0.02   # JLC04161H-3313 core between L2 and L3 (L3 = GND under the RF area)
VOID_M = 0.10                  # L2 void margin around each component (both pads + body)
VOID = "--novoid" not in sys.argv

def ladder_geometry(topo):
    """Return dict: rects [(x0,y0,x1,y1,kind)], vias [(x,y)], comp list [(elem_index, padA_rect_id, edgeA, padB_rect_id, edgeB)],
    width, height. Coordinates mm, y downward, main line at y=0 (shifted later)."""
    rects, vias, comps, voids = [], [], [], []
    def rect(x0, y0, x1, y1, kind="m"):
        rects.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), kind)); return len(rects) - 1
    x = 0.0
    rect(x, -W50 / 2, x + LEAD, W50 / 2, "lead_in"); x += LEAD
    ei = 0
    for pos, kind in topo:
        n = F.NPAR[kind]
        if pos == "s":
            assert kind in ("L", "C"), "series branches are single parts in this layout"
            rect(x, -W50 / 2, x + GAP_T, W50 / 2); x += GAP_T
            a = rect(x, -PAD_W / 2, x + PAD_L, PAD_W / 2, "pad")
            b = rect(x + 2 * PAD_X, -PAD_W / 2, x + 2 * PAD_X + PAD_L, PAD_W / 2, "pad")
            comps.append((ei, a, 1, b, 3)); ei += 1
            voids.append((x - VOID_M, -PAD_W / 2 - VOID_M, x + 2 * PAD_X + PAD_L + VOID_M, PAD_W / 2 + VOID_M))
            x += 2 * PAD_X + PAD_L
        else:
            # node: short trace, then a vertical stack below the line
            rect(x, -W50 / 2, x + GAP_T, W50 / 2); xn = x + GAP_T / 2; x += GAP_T
            y = W50 / 2
            rect(xn - W50 / 2, y, xn + W50 / 2, y + 0.25); y += 0.25          # stub from line to first pad
            parts = 2 if kind in ("LCs", "LCp") else 1
            for k in range(parts):
                a = rect(xn - PAD_W / 2, y, xn + PAD_W / 2, y + PAD_L, "pad")
                b = rect(xn - PAD_W / 2, y + 2 * PAD_X, xn + PAD_W / 2, y + 2 * PAD_X + PAD_L, "pad")
                comps.append((ei, a, 2, b, 0)); ei += 1
                voids.append((xn - PAD_W / 2 - VOID_M, y - VOID_M, xn + PAD_W / 2 + VOID_M, y + 2 * PAD_X + PAD_L + VOID_M))
                y += 2 * PAD_X + PAD_L
                if k < parts - 1:
                    rect(xn - W50 / 2, y, xn + W50 / 2, y + 0.2); y += 0.2   # link between the two parts
            # via pad + via to GND
            rect(xn - W50 / 2, y, xn + W50 / 2, y + 0.15); y += 0.15
            rect(xn - VIA_PAD / 2, y, xn + VIA_PAD / 2, y + VIA_PAD, "viapad")
            vias.append((xn, y + VIA_PAD / 2))
    rect(x, -W50 / 2, x + LEAD, W50 / 2, "lead_out"); x += LEAD
    ymax = max(r[3] for r in rects)
    return dict(rects=rects, vias=vias, comps=comps, voids=voids, width=x, ymin=-PAD_W / 2, ymax=ymax)

def plane_with_voids(W, y0, y1, voids):
    """Decompose rectangle [0,W]x[y0,y1] minus void rects into non-overlapping rectangles (strips)."""
    ys = sorted(set([y0, y1] + [v[1] for v in voids] + [v[3] for v in voids]))
    ys = [y for y in ys if y0 <= y <= y1]
    out = []
    for ya, yb in zip(ys[:-1], ys[1:]):
        ym = (ya + yb) / 2
        cuts = sorted([(v[0], v[2]) for v in voids if v[1] <= ym <= v[3]])
        x = 0.0
        for (a, b) in cuts:
            if a > x + 1e-9: out.append((x, ya, a, yb))
            x = max(x, b)
        if x < W - 1e-9: out.append((x, ya, W, yb))
    return out

def snapc(v):
    return round(v / CELL) * CELL

def write_son(path, geo, f_lo=0.03, f_hi=8.0, margin=1.0):
    W = snapc(geo["width"]); top = margin; H = snapc(top + geo["ymax"] + margin)
    def tx(x): return snapc(x) * 1000.0                 # um
    def ty(y): return snapc(y + top) * 1000.0
    nx, ny = int(round(W / CELL)), int(round(H / CELL))
    L = ["FTYP SONPROJ 1 ! Sonnet Project File", "VER 19.54", "HEADER", "END HEADER", "DIM", "FREQ GHZ", "IND NH",
         "LNG UM", "ANG DEG", "CON /OH", "CAP PF", "RES OH", "END DIM", "FREQ", "ABS %.4f %.4f" % (f_lo, f_hi),
         "END FREQ", "CONTROL", "ABS", "OPTIONS  -d", "SPEED 0", "RES_ABS 300", "END CONTROL", "GEO",
         'TMET "Lossless" 0 SUP 0 0 0 0', 'BMET "Lossless" 0 SUP 0 0 0 0', 'MET "Cu35" 1 NOR 5.8e7 0 35',
         "BOX %d %.4f %.4f %d %d 20 0" % (2 if VOID else 1, W * 1000, H * 1000, nx, ny),
         '      1000.0000 1 1 0 0 0 0 "Air"', '      %.4f %.4f 1 %.4f 0 0 0 "PP3313"' % (H_PP * 1000, ER_PP, TAN_PP)]
    if VOID:
        L += ['      %.4f %.4f 1 %.4f 0 0 0 "Core"' % (H_CORE * 1000, ER_CORE, TAN_CORE)]
    rects = geo["rects"]
    # polygons: ids 1..N in rect order, then vias
    polys = []
    for i, (x0, y0, x1, y1, kind) in enumerate(rects):
        pts = [(tx(x0), ty(y0)), (tx(x1), ty(y0)), (tx(x1), ty(y1)), (tx(x0), ty(y1))]
        polys.append(("N", i + 1, pts))
    vid = len(rects)
    gnd = []
    if VOID:
        for (x0, y0, x1, y1) in plane_with_voids(W, -top, H - top, geo["voids"]):
            vid += 1
            gnd.append((vid, [(tx(x0), ty(y0)), (tx(x1), ty(y0)), (tx(x1), ty(y1)), (tx(x0), ty(y1))]))
    for (xv, yv) in geo["vias"]:
        vid += 1; r = VIA_D / 2
        pts = [(tx(xv - r), ty(yv - r)), (tx(xv + r), ty(yv - r)), (tx(xv + r), ty(yv + r)), (tx(xv - r), ty(yv + r))]
        polys.append(("V", vid, pts))
    # ports
    pn = 0
    def port_line(kind, pid, edge, x, y):
        nonlocal pn
        pn += 1
        if kind == "STD":
            return ["POR1 STD", "POLY %d 1" % pid, "%d" % edge, "%d 50 0 0 0 %.4f %.4f" % (pn, x, y)]
        return ["POR1 AGND", "POLY %d 1" % pid, "%d" % edge, "%d 50 0 0 0 %.4f %.4f FIX 0" % (pn, x, y)]
    i_in = [i for i, r in enumerate(rects) if r[4] == "lead_in"][0]
    i_out = [i for i, r in enumerate(rects) if r[4] == "lead_out"][0]
    r = rects[i_in]; L += port_line("STD", i_in + 1, 3, tx(r[0]), ty(0.0))
    r = rects[i_out]; L += port_line("STD", i_out + 1, 1, tx(r[2]), ty(0.0))
    portmap = []                                     # (elem, portA, portB)
    def edge_mid(ri, e):
        x0, y0, x1, y1, _ = rects[ri]
        return {0: (tx((x0 + x1) / 2), ty(y0)), 1: (tx(x1), ty((y0 + y1) / 2)),
                2: (tx((x0 + x1) / 2), ty(y1)), 3: (tx(x0), ty((y0 + y1) / 2))}[e]
    for (ei, a, ea, b, eb) in geo["comps"]:
        xa, ya = edge_mid(a, ea); L += port_line("AGND", a + 1, ea, xa, ya); pa = pn
        xb, yb = edge_mid(b, eb); L += port_line("AGND", b + 1, eb, xb, yb); pb = pn
        portmap.append((ei, pa, pb))
    L += ["NUM %d" % (len(polys) + len(gnd))]
    for pid, pts in gnd:
        L += ["1 5 0 N %d 1 1 100 100 0 0 0 Y" % pid] + ["%.4f %.4f" % p for p in pts + [pts[0]]] + ["END"]
    for typ, pid, pts in polys:
        L += ["VIA POLYGON"] if typ == "V" else []
        L += ["0 5 0 %s %d 1 1 100 100 0 0 0 Y" % (typ, pid)]
        if typ == "V":
            L += ["TOLEVEL GND RING COVERS"]
        L += ["%.4f %.4f" % p for p in pts + [pts[0]]]
        L += ["END"]
    L += ["END GEO", "FILEOUT", "TS D Y $BASENAME.s%dp 15 S RI R 50.00000" % pn, "END FILEOUT"]
    open(path, "w").write("\n".join(L) + "\n")
    return pn, portmap

def run_em(path):
    t0 = time.time()
    d = os.path.dirname(path)
    shutil.rmtree(os.path.join(d, "sondata"), ignore_errors=True)
    p = subprocess.run([SON + "/bin/em", "-v", os.path.basename(path)], capture_output=True, text=True, cwd=d)
    if p.returncode != 0 or "errors detected: 0" not in p.stdout:
        print(p.stdout[-3000:]); raise SystemExit("em failed")
    return time.time() - t0

def read_touchstone(path, n):
    f, data = [], []
    toks = []
    for line in open(path):
        s = line.split("!")[0].strip()
        if not s or s.startswith("#"):
            continue
        toks += s.split()
    v = np.array(toks, float)
    rec = 1 + 2 * n * n
    v = v[: (len(v) // rec) * rec].reshape(-1, rec)
    f = v[:, 0] * 1e9
    S = (v[:, 1::2] + 1j * v[:, 2::2]).reshape(-1, n, n)
    return f, S

# ---------------------------------------------------------------- co-simulation
ESL_BODY, ESR_C = 0.15e-9, 0.15          # intrinsic 0402 cap body (pads/mounting are in the EM data)
Q_L, CP_L = 35.0, 0.07e-12

def z_part(t, v, w):
    if t == "L":
        L = v * 1e-9; zs = w * L / Q_L + 1j * w * L
        return zs / (1 + 1j * w * CP_L * zs)
    C = v * 1e-12
    return 1 / (1j * w * C) + 1j * w * ESL_BODY + ESR_C

def cosim(f, S, portmap, types, vals, z0=50.0):
    n = S.shape[1]; I = np.eye(n)
    out = np.zeros((len(f), 2, 2), complex)
    for k in range(len(f)):
        w = 2 * np.pi * f[k]
        Y = np.linalg.solve((I + S[k]).T, (I - S[k]).T).T / z0       # Y = (I-S)(I+S)^-1 / z0
        for (ei, pa, pb) in portmap:
            y = 1 / z_part(types[ei], vals[ei], w)
            a, b = pa - 1, pb - 1
            Y[a, a] += y; Y[b, b] += y; Y[a, b] -= y; Y[b, a] -= y
        e = [0, 1]; i = list(range(2, n))
        Yr = Y[np.ix_(e, e)] - Y[np.ix_(e, i)] @ np.linalg.solve(Y[np.ix_(i, i)], Y[np.ix_(i, e)])
        Zr = np.linalg.inv(Yr)
        out[k] = (Zr - z0 * np.eye(2)) @ np.linalg.inv(Zr + z0 * np.eye(2))
    return out

def mask_metrics(spec, f, S2):
    s21 = 20 * np.log10(np.abs(S2[:, 1, 0]) + 1e-15); s11 = 20 * np.log10(np.abs(S2[:, 0, 0]) + 1e-15)
    m = {}
    for k, a, b, lim in spec["mask"]:
        sel = (f >= a) & (f <= b)
        if not sel.any(): continue
        if k == "pass":
            m[f"IL max {a/1e9:.2f}-{b/1e9:.2f} GHz (<= {lim})"] = -s21[sel].min()
            m[f"RL min {a/1e9:.2f}-{b/1e9:.2f} GHz (>= {spec['rl']})"] = -s11[sel].max()
        else:
            m[f"Rej min {a/1e9:.2f}-{b/1e9:.2f} GHz (>= {lim})"] = -s21[sel].max()
    return m

def mask_cost(spec, f, S2):
    s21 = 20 * np.log10(np.abs(S2[:, 1, 0]) + 1e-15); s11 = 20 * np.log10(np.abs(S2[:, 0, 0]) + 1e-15)
    c = 0.0; pm = np.zeros(len(f), bool)
    for k, a, b, lim in spec["mask"]:
        sel = (f >= a) & (f <= b)
        if k == "pass":
            c += 20 * np.sum(np.clip(-s21[sel] - lim, 0, None) ** 2); pm |= sel
        else:
            c += np.sum(np.clip(s21[sel] + lim, 0, None) ** 2)
    c += 2 * np.sum(np.clip(s11[pm] + spec["rl"], 0, None) ** 2)
    return c

def main():
    name = sys.argv[1]
    spec = F.FILTERS[name]; topo = spec["topo"]; types = F.types_of(topo)
    pal = json.load(open(os.path.join(HERE, "..", "analysis", "export", "filter_palette.json")))
    vals = np.array(pal[name])
    geo = ladder_geometry(topo)
    d = os.path.join(OUT, name + ("" if VOID else "_novoid")); os.makedirs(d, exist_ok=True)
    son = os.path.join(d, name + ".son")
    npts, portmap = write_son(son, geo)
    json.dump(dict(portmap=portmap, nports=npts, geo=geo), open(os.path.join(d, "geo.json"), "w"))
    ts = os.path.join(d, f"{name}.s{npts}p")
    if "--run" in sys.argv or not os.path.exists(ts):
        t = run_em(son); print(f"em {name}: {npts} ports, {t:.0f} s", flush=True)
    f, S = read_touchstone(ts, npts)
    # evaluate on a dense grid by interpolating the (smooth, ABS-fitted) N-port data
    S2 = cosim(f, S, portmap, types, vals)
    res = dict(f=list(f), s21=list(np.abs(S2[:, 1, 0])), s11=list(np.abs(S2[:, 0, 0])))
    m_em = mask_metrics(spec, f, S2)
    m_ideal = F.metrics(spec, vals)
    best = vals.copy()
    if "--reopt" in sys.argv:
        palette = sorted(set(tuple(x) for k in pal for x in zip(F.types_of(F.FILTERS[k]["topo"]), np.round(pal[k], 2))))
        if "--full" in sys.argv:   # any purchasable value (re-run analysis/palette-style merge afterwards)
            palette = sorted(set(palette) | set(("L", v) for v in F.L_SER) | set(("C", v) for v in F.C_SER))
        cost = lambda x: mask_cost(spec, f, cosim(f, S, portmap, types, x))
        cur = vals.copy(); cbest = cost(cur)
        for rnd in range(8):
            imp = False
            for i, t in enumerate(types):
                for (pt, pv) in palette:
                    if pt != t or pv == cur[i]: continue
                    trial = cur.copy(); trial[i] = pv; c = cost(trial)
                    if c < cbest - 1e-9: cbest, cur, imp = c, trial, True
            if not imp: break
        best = cur
    S2b = cosim(f, S, portmap, types, best)
    m_b = mask_metrics(spec, f, S2b)
    json.dump(dict(f=list(map(float, f)), s21_start=list(map(float, np.abs(S2[:, 1, 0]))),
                   s21_best=list(map(float, np.abs(S2b[:, 1, 0]))), s11_best=list(map(float, np.abs(S2b[:, 0, 0]))),
                   vals_start=list(map(float, vals)), vals_best=list(map(float, best))),
              open(os.path.join(d, "result.json"), "w"))
    lines = [f"## {name}: EM co-simulation (Sonnet, {npts} ports, layout {geo['width']:.1f} x {geo['ymax']-geo['ymin']:.1f} mm)\n",
             "| Element | Palette value (lumped design) | After EM re-opt (palette only) |", "|---|---|---|"]
    for i, t in enumerate(types):
        u = "nH" if t == "L" else "pF"
        lines.append(f"| {t}{i+1} | {vals[i]:g} {u} | **{best[i]:g} {u}** |")
    lines.append("\n| Metric | Lumped model | EM, lumped values | EM, re-optimized |\n|---|---|---|---|")
    for k in m_em:
        k2 = [kk for kk in m_ideal if kk.split("(")[0].strip() == k.split("(")[0].strip()]
        lines.append(f"| {k} | {m_ideal[k2[0]]:.2f} | {m_em[k]:.2f} | {m_b[k]:.2f} |" if k2 else f"| {k} | - | {m_em[k]:.2f} | {m_b[k]:.2f} |")
    open(os.path.join(d, "REPORT.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))

if __name__ == "__main__":
    main()

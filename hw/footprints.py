#!/usr/bin/env python3
"""Custom KiCad footprints for the ESP32-S31 SDR board -> hw/esp32_sdr.pretty/*.kicad_mod
Land patterns derived from the datasheets cited per footprint (dimensions in mm)."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "esp32_sdr.pretty")
os.makedirs(LIB, exist_ok=True)

def _pad(num, x, y, w, h, shape="roundrect", layers='"F.Cu" "F.Paste" "F.Mask"', extra=""):
    rr = " (roundrect_rratio 0.25)" if shape == "roundrect" else ""
    return f'  (pad "{num}" smd {shape} (at {x:.4f} {y:.4f}) (size {w:.4f} {h:.4f}) (layers {layers}){rr}{extra})'

def _line(x0, y0, x1, y1, layer="F.SilkS", w=0.12):
    return f'  (fp_line (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width {w}) (type solid)) (layer "{layer}"))'

def _rect(x0, y0, x1, y1, layer, w=0.05):
    return "\n".join([_line(x0, y0, x1, y0, layer, w), _line(x1, y0, x1, y1, layer, w),
                      _line(x1, y1, x0, y1, layer, w), _line(x0, y1, x0, y0, layer, w)])

def write_fp(name, body, descr, cy=1.0, attr="smd"):
    s = [f'(footprint "{name}" (version 20240108) (generator "esp32sdr_footprints") (layer "F.Cu")',
         f'  (descr "{descr}")', f'  (attr {attr})',
         f'  (fp_text reference "REF**" (at 0 {-cy - 0.8:.2f}) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         f'  (fp_text value "{name}" (at 0 {cy + 0.8:.2f}) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))',
         body, ")"]
    open(os.path.join(LIB, name + ".kicad_mod"), "w").write("\n".join(s) + "\n")

def qfn(name, n_per_side, pitch, body, lead_l, lead_b, ep, descr, toe=0.25, heel=0.05, padw=None, ep_paste=3):
    """Square QFN, pins counter-clockwise from top-left (pin 1 top of left side), KiCad y down."""
    h = body / 2
    pl = lead_l + toe + heel
    pc = h - lead_l + (lead_l + toe - heel) / 2 - heel / 2       # pad centre distance from origin
    pc = h - lead_l - heel + pl / 2
    pw = padw or min(lead_b + 0.05, pitch * 0.62)
    span = (n_per_side - 1) * pitch / 2
    out = []
    n = 1
    for i in range(n_per_side):                  # left side, top -> bottom
        out.append(_pad(n, -pc, -span + i * pitch, pl, pw)); n += 1
    for i in range(n_per_side):                  # bottom, left -> right
        out.append(_pad(n, -span + i * pitch, pc, pw, pl)); n += 1
    for i in range(n_per_side):                  # right side, bottom -> top
        out.append(_pad(n, pc, span - i * pitch, pl, pw)); n += 1
    for i in range(n_per_side):                  # top, right -> left
        out.append(_pad(n, span - i * pitch, -pc, pw, pl)); n += 1
    # exposed pad: copper + mask, paste as a grid of windows (~55 % coverage)
    out.append(_pad(n, 0, 0, ep, ep, shape="rect", layers='"F.Cu" "F.Mask"'))
    k = ep_paste; cell = ep / k; win = cell * 0.74
    for a in range(k):
        for b in range(k):
            x = -ep / 2 + cell * (a + 0.5); y = -ep / 2 + cell * (b + 0.5)
            out.append(_pad("", x, y, win, win, shape="rect", layers='"F.Paste"'))
    # thermal/ground vias in the EP (filled/tented by fab; 0.3 mm drill)
    nv = max(2, int(ep / 1.2))
    for a in range(nv):
        for b in range(nv):
            x = -ep / 2 + ep * (a + 0.5) / nv; y = -ep / 2 + ep * (b + 0.5) / nv
            out.append(f'  (pad "{n}" thru_hole circle (at {x:.4f} {y:.4f}) (size 0.5 0.5) (drill 0.3) (layers "*.Cu"))')
    c = h + 0.15
    out.append(_line(-c, -c + 0.6, -c, -c) + "\n" + _line(-c, -c, -c + 0.6, -c))
    out.append(f'  (fp_circle (center {-c - 0.35:.3f} {-c - 0.35:.3f}) (end {-c - 0.25:.3f} {-c - 0.35:.3f}) (stroke (width 0.12) (type solid)) (fill solid) (layer "F.SilkS"))')
    out.append(_line(c, -c, c - 0.6, -c) + "\n" + _line(c, -c, c, -c + 0.6))
    out.append(_line(-c, c, -c + 0.6, c) + "\n" + _line(-c, c, -c, c - 0.6))
    out.append(_line(c, c, c - 0.6, c) + "\n" + _line(c, c, c, c - 0.6))
    out.append(_rect(-h, -h, h, h, "F.Fab", 0.1))
    out.append(_rect(-h - 0.6, -h - 0.6, h + 0.6, h + 0.6, "F.CrtYd", 0.05))
    write_fp(name, "\n".join(out), descr, cy=h + 0.6)

def generic(name, pads, body, descr, extra=""):
    """pads: list of (num, x, y, w, h[, shape])"""
    out = [_pad(p[0], p[1], p[2], p[3], p[4], p[5] if len(p) > 5 else "roundrect") for p in pads]
    bx, by = body
    out.append(_rect(-bx / 2, -by / 2, bx / 2, by / 2, "F.Fab", 0.1))
    xs = [abs(p[1]) + p[3] / 2 for p in pads] + [bx / 2]; ys = [abs(p[2]) + p[4] / 2 for p in pads] + [by / 2]
    cx, cy = max(xs) + 0.25, max(ys) + 0.25
    out.append(_rect(-cx, -cy, cx, cy, "F.CrtYd", 0.05))
    if extra: out.append(extra)
    write_fp(name, "\n".join(out), descr, cy=cy)

def tht(name, holes, body_rect, descr):
    """holes: dict name -> (x, y, drill, pad or None, kind). kind 'pth'|'npth'."""
    out = []
    for num, (x, y, drill, pad, kind) in holes.items():
        if kind == "npth":
            out.append(f'  (pad "" np_thru_hole circle (at {x:.4f} {y:.4f}) (size {drill:.3f} {drill:.3f}) (drill {drill:.3f}) (layers "*.Cu" "*.Mask"))')
        else:
            shape = "rect" if num == "1" else "circle"
            out.append(f'  (pad "{num}" thru_hole {shape} (at {x:.4f} {y:.4f}) (size {pad:.3f} {pad:.3f}) (drill {drill:.3f}) (layers "*.Cu" "*.Mask"))')
    x0, y0, x1, y1 = body_rect
    out.append(_rect(x0, y0, x1, y1, "F.Fab", 0.1)); out.append(_rect(x0, y0, x1, y1, "F.SilkS", 0.12))
    cx0 = min([x0] + [h[0] - (h[3] or h[2]) / 2 for h in holes.values()]); cx1 = max([x1] + [h[0] + (h[3] or h[2]) / 2 for h in holes.values()])
    cy0 = min([y0] + [h[1] - (h[3] or h[2]) / 2 for h in holes.values()]); cy1 = max([y1] + [h[1] + (h[3] or h[2]) / 2 for h in holes.values()])
    out.append(_rect(cx0 - 0.3, cy0 - 0.3, cx1 + 0.3, cy1 + 0.3, "F.CrtYd", 0.05))
    write_fp(name, "\n".join(out), descr, cy=max(abs(y0), abs(y1)), attr="through_hole")

if __name__ == "__main__":
    # ESP32-S31 QFN80 8x8, pitch 0.35, b 0.17 (0.12-0.22), L 0.40 (0.30-0.50), EP 6.5 (6.4-6.6). Datasheet v0.5 Fig 7-1.
    qfn("Espressif_ESP32-S31_QFN-80_8x8mm_P0.35mm_EP6.5mm", 20, 0.35, 8.0, 0.40, 0.17, 6.5,
        "ESP32-S31 QFN80 8x8 0.35 pitch, EP 6.5 (datasheet v0.5 fig 7-1); pads 0.20 x 0.70", toe=0.25, heel=0.05, padw=0.20, ep_paste=4)
    import json
    PJ = json.load(open(os.path.join(HERE, "pinouts.json")))
    # Infineon BGS13SN8 TSNP-8 1.1x1.1, 0.25 x 0.25 pads on 0.4 grid (datasheet fig. 2/4)
    lp = PJ["BGS13SN8"]["custom_land_pattern"]
    generic("Infineon_PG-TSNP-8-1_1.1x1.1mm_P0.4mm", [(n, x, y, 0.25, 0.25, "rect") for n, (x, y) in lp["pads"].items()],
            (1.1, 1.1), "Infineon BGS13SN8 SP3T TSNP-8 1.1x1.1 (DS fig 2/4)",
            extra='  (fp_circle (center -0.75 -0.75) (end -0.68 -0.75) (stroke (width 0.1) (type solid)) (fill solid) (layer "F.SilkS"))')
    # TTM/Anaren BD2425N50200AHF 0404 balun
    lp = PJ["BD2425N50200AHF"]["custom_land_pattern"]
    generic("Anaren_Xinger_0404_BD2425", [(n, v["at"][0], v["at"][1], v["size"][0], v["size"][1], "rect") for n, v in lp["pads"].items()],
            (1.0, 1.0), "TTM BD2425N50200AHF 0404 balun 50:200 2.4-2.5 GHz",
            extra='  (fp_circle (center 0.7 -0.7) (end 0.77 -0.7) (stroke (width 0.1) (type solid)) (fill solid) (layer "F.SilkS"))')
    # HanRun HR911130C RJ45 magjack (THT); origin between pegs, +y toward rear
    lp = PJ["HR911130C"]["custom_land_pattern"]
    holes = {}
    for k, v in lp["holes"].items():
        if k.startswith("PEG"):
            holes["np" + k] = (v["at"][0], v["at"][1], v["drill"], None, "npth")
        elif k.startswith("SH"):
            holes["SH" if k == "SH_L" else "SH"] = (v["at"][0], v["at"][1], v["drill"], v["pad"], "pth")
            holes["SH_" + k[-1]] = (v["at"][0], v["at"][1], v["drill"], v["pad"], "pth")
        else:
            holes[k] = (v["at"][0], v["at"][1], v["drill"], v["pad"], "pth")
    holes.pop("SH", None)
    holes = {("SH" if k.startswith("SH_") else k): v for k, v in holes.items()} if False else holes
    # both shield tabs share pad number "SH"
    fixed = {}
    for k, v in holes.items():
        fixed[k] = v
    tht_sh = {k: v for k, v in fixed.items()}
    # write with shield pads both numbered SH
    out_holes = {}
    for k, v in tht_sh.items():
        out_holes[k] = v
    tht("RJ45_HanRun_HR911130C", {k: v for k, v in out_holes.items()}, (-8.0, -10.8, 8.0, 10.4),
        "HanRun HR911130C 1000BASE-T magjack with LEDs (HR911130C drawing p3; origin between pegs)")
    # rename SH_L/SH_R pads to SH in file
    fpn = os.path.join(LIB, "RJ45_HanRun_HR911130C.kicad_mod")
    t = open(fpn).read().replace('(pad "SH_L"', '(pad "SH"').replace('(pad "SH_R"', '(pad "SH"').replace('(pad "npPEG_L"', '(pad ""').replace('(pad "npPEG_R"', '(pad ""')
    open(fpn, "w").write(t)
    print("wrote", sorted(os.listdir(LIB)))


def wroom1u():
    """ESP32-S31-WROOM-1U land pattern (datasheet v0.5 fig. 11-2), origin = centre of the 18 x 20.5 mm outline."""
    pads = []
    for i in range(14):                                   # left 1..14, right 40..27
        y = -7.755 + i * 1.27
        pads.append((str(1 + i), -8.75, y, 1.5, 0.9, "rect"))
        pads.append((str(40 - i), 8.75, y, 1.5, 0.9, "rect"))
    for i in range(12):                                   # bottom 15..26
        pads.append((str(15 + i), -6.985 + i * 1.27, 10.0, 0.9, 1.5, "rect"))
    for n, x in (("64", 1.46), ("63", 2.73), ("62", 4.0)):  # top: GND, ANT2, GND
        pads.append((n, x, -10.0, 0.9, 1.5, "rect"))
    for i, n in enumerate(range(49, 41, -1)):             # inner top row 49..42
        pads.append((str(n), -4.30 + i * 0.8, -2.65, 0.4, 0.8, "rect"))
    for i in range(6):                                    # inner columns 50..55 (left), 61..56 (right)
        y = -1.65 + i * 0.8
        pads.append((str(50 + i), -4.10, y, 0.8, 0.4, "rect"))
        pads.append((str(61 - i), 1.09, y, 0.8, 0.4, "rect"))
    for gx in (-2.89, -1.49, -0.09):                      # 3x3 GND/thermal pads = pin 41
        for gy in (-1.44, -0.04, 1.36):
            pads.append(("41", gx, gy, 0.9, 0.9, "rect"))
    out = [_pad(p[0], p[1], p[2], p[3], p[4], p[5]) for p in pads]
    for vx in (-2.19, -0.79):                             # thermal vias between the GND pads
        for vy in (-0.74, 0.66):
            out.append(f'  (pad "41" thru_hole circle (at {vx:.3f} {vy:.3f}) (size 0.5 0.5) (drill 0.3) (layers "*.Cu"))')
    out.append(_rect(-9.0, -10.25, 9.0, 10.25, "F.Fab", 0.1))
    out.append(_rect(-9.0, -10.25, 9.0, 10.25, "F.SilkS", 0.12))
    out.append(_rect(-9.9, -11.0, 9.9, 11.0, "F.CrtYd", 0.05))
    out.append('  (fp_text user "U.FL" (at 6.8 -8.6) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))')
    write_fp("Espressif_ESP32-S31-WROOM-1U", "\n".join(out), "ESP32-S31-WROOM-1U (64 pins + 3x3 GND), datasheet v0.5 fig 11-2", cy=11.0)

if __name__ == "__main__" and "wroom" in __import__("sys").argv:
    wroom1u(); print("wrote WROOM-1U")

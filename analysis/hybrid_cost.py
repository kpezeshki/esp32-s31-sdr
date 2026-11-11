#!/usr/bin/env python3
"""Per-board cost of the hybrid build: JLC Standard PCBA places only the 'hard' parts
(QFN/DFN/LGA, tiny RF parts, 0402 RF passives); the user hand-solders 0603+, SOT/SOIC, connectors.
Prices: PART_SELECTION.md (LCSC 10+ break, 2026-11-09). Fees: JLC pcb-assembly-price (2026-10-22)."""

# (name, $/board, placed_by, leadless_for_xray, part_types_at_JLC)
FULL = [
    ("ESP32-S31NRV16",         5.01, "jlc", 1, 1),
    ("RFFC5072TR13",          15.62, "jlc", 1, 1),
    ("YT8531DC PHY",           1.24, "jlc", 1, 1),
    ("25 MHz xtal 3225",       0.10, "jlc", 1, 1),
    ("TCXO 40 MHz 2520",       0.33, "jlc", 1, 1),
    ("LNA_HB QPL9503 DFN",     5.08, "jlc", 1, 1),
    ("SPDT BGS12P2L6 x2",      0.76, "jlc", 2, 1),
    ("SAW 2.4G 1.4x1.1",       0.27, "jlc", 1, 1),
    ("IF balun BD2425 0404",   0.87, "jlc", 1, 1),
    ("RF ESD 0201 x2",         0.04, "jlc", 0, 1),
    ("LNA_LB PSA4-5043+ SOT343", 1.91, "jlc", 0, 1),
    ("0402 RF passives (LB LPF as LFCG-1700+ counted below; HB HPF 7 values; DC-block, chokes, ESP32 match, QFN decoupling)", 0.15, "jlc", 0, 12),
    ("LFCG-1700+ LTCC LPF",    1.20, "jlc", 0, 1),   # price: see PART_SELECTION slot 15 (approx.)
    ("Gain block GVA-63+ SOT89", 1.69, "hand", 0, 0),
    ("1:2 balun H3-TCM2-63WX+", 2.68, "hand", 0, 0),
    ("Flash SOIC-8",           0.72, "hand", 0, 0),
    ("Magjack HR911130C THT",  2.44, "hand", 0, 0),
    ("SMA edge x2",            0.64, "hand", 0, 0),
    ("USB-C + ESD",            0.24, "hand", 0, 0),
    ("LDOs (SOT-223/SOT-23-5) x3", 0.65, "hand", 0, 0),
    ("0603+ passives, ferrites, LED", 0.80, "hand", 0, 0),
]
TRIM = {"LNA_HB QPL9503 DFN": ("LNA_HB SKY67183 (low stock)", 2.93),
        "Gain block GVA-63+ SOT89": ("Gain block Tokmas GVA-63 clone (unverified)", 0.96),
        "LDOs (SOT-223/SOT-23-5) x3": ("LDOs AMS1117 + 2x LP5907", 0.50)}

def cost(bom, n, xray_per_placement, pcb_total=None, lcsc_ship=15.0):
    pcb_total = pcb_total if pcb_total is not None else (15.0 if n <= 5 else 20.0)
    comp = sum(p for _, p, *_ in bom)
    types = sum(t for *_, t in bom)
    leadless = sum(x for _, _, by, x, _ in bom if by == "jlc")
    if xray_per_placement:
        k = leadless * n; rate = 1.64 if k <= 10 else 0.82 if k <= 50 else 0.49 if k <= 200 else 0.33
        xray = k * rate
    else:
        xray = n * (1.64 if n <= 10 else 0.82)
    jlc_joints = n * 400 * 0.0016
    fixed = 25.56 + 8.21 + 1.53 * types + xray + jlc_joints + pcb_total + lcsc_ship
    return comp, types, fixed / n, comp + fixed / n

def trimmed(bom):
    out = []
    for row in bom:
        if row[0] in TRIM:
            nm, pr = TRIM[row[0]]; out.append((nm, pr) + row[2:])
        else:
            out.append(row)
    return out

if __name__ == "__main__":
    print("| Variant | qty | X-ray billing | Components | JLC part types | Fixed/board | **Total/board** |")
    print("|---|---|---|---|---|---|---|")
    for name, bom in [("Hybrid, full design", FULL), ("Hybrid, full design + cost trims", trimmed(FULL))]:
        for n in (5, 10):
            for xp in (False, True):
                c, t, f, tot = cost(bom, n, xp)
                print(f"| {name} | {n} | {'per placement' if xp else 'per board'} | ${c:.2f} | {t} | ${f:.2f} | **${tot:.2f}** |")

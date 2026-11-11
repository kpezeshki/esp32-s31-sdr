#!/usr/bin/env python3
"""Per-board cost of the two-board build from the real BOM CSVs (hw/board_*/fab).
Prices: JLC/LCSC public API by LCSC part number (cached in price_cache.json); parts bought at max(need, first price
break = MOQ); fee model as analysis/hybrid_cost.py (JLC Standard PCBA for Board B).  Writes cost.json + cost.md."""
import csv, json, os, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); HW = os.path.dirname(HERE)
CACHE = os.path.join(HERE, "price_cache.json")
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

def lookup(code):
    if code in cache: return cache[code]
    body = json.dumps({"keyword": code, "currentPage": 1, "pageSize": 5})
    out = subprocess.run(["curl", "-s", "-m", "40", "-A", "Mozilla/5.0 (X11; Linux x86_64) Chrome/120",
                          "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList",
                          "-H", "content-type: application/json", "-d", body], capture_output=True, text=True).stdout
    rec = None
    try:
        for c in ((json.loads(out).get("data") or {}).get("componentPageInfo") or {}).get("list") or []:
            if c.get("componentCode") == code:
                rec = dict(breaks=[(p["startNumber"], p["productPrice"]) for p in (c.get("componentPrices") or [])],
                           lib=c.get("componentLibraryType"), stock=c.get("stockCount"), model=c.get("componentModelEn"))
                break
    except Exception:
        pass
    cache[code] = rec; json.dump(cache, open(CACHE, "w"), indent=1); time.sleep(0.4)
    return rec

def line_cost(code, qty_board, n):
    r = lookup(code) if code else None
    if not r or not r["breaks"]: return None, r
    need = qty_board * n; moq = r["breaks"][0][0]; buy = max(need, moq)
    price = [p for s, p in r["breaks"] if s <= buy][-1]
    return buy * price / n, r

# parts with no LCSC listing (estimates, flagged in the report)
MANUAL = {"U1": ("ESP32-S31-WROOM-1U-N16R16V (not on LCSC; Espressif/distributor estimate)", 6.00)}

def read(path, des_col, qty_col=None):
    rows = []
    for r in csv.DictReader(open(path)):
        des = [d.strip() for d in r[des_col].split(",") if d.strip()]
        q = int(r[qty_col]) if qty_col else len(des)
        rows.append(dict(code=r.get("LCSC Part #", "").strip(), qty=q, des=des, value=r.get("Value") or r.get("Comment", "")))
    return rows

def board(rows, n):
    tot, lines, missing = 0.0, [], []
    for r in rows:
        man = [MANUAL[d] for d in r["des"] if d in MANUAL]
        if man:
            c = man[0][1] * r["qty"]; lines.append((r, c, None, "estimate")); tot += c; continue
        c, info = line_cost(r["code"], r["qty"], n)
        if c is None: missing.append(r); continue
        lines.append((r, c, info, "lcsc")); tot += c
    return tot, lines, missing

def jlc_fees(n, types, leadless, joints=400):
    xray = n * (1.64 if n <= 10 else 0.82)            # per-board billing (per-placement adds ~$1-3/board, see COST_PLAN)
    return 25.56 + 8.21 + 1.53 * types + xray + n * joints * 0.0016

if __name__ == "__main__":
    A = read(f"{HW}/board_a/fab/BOM_A_kit.csv", "Designators", "Qty per board")
    BJ = read(f"{HW}/board_b/fab/BOM_B_JLC.csv", "Designator")
    BH = read(f"{HW}/board_b/fab/BOM_B_HAND_LCSC.csv", "Designators", "Qty per board") if os.path.exists(f"{HW}/board_b/fab/BOM_B_HAND_LCSC.csv") else []
    out = {}
    for n in (5, 10):
        pcb = 15.0 if n <= 5 else 20.0                  # JLC 4L, JLC04161H-3313 (impedance stack), per design per order: ASSUMPTION
        a_parts, a_lines, a_miss = board(A, n)
        bj_parts, bj_lines, bj_miss = board(BJ, n)
        bh_parts, bh_lines, bh_miss = board(BH, n)
        a = dict(parts=a_parts, pcb=pcb / n, stencil=8.0 / n, total=a_parts + pcb / n + 8.0 / n)
        fees = jlc_fees(n, len(BJ), 0)
        b = dict(parts_jlc=bj_parts, parts_hand=bh_parts, pcb=pcb / n, pcba_fees=fees / n,
                 total=bj_parts + bh_parts + pcb / n + fees / n)
        ship = 35.0 / n                                 # JLC (PCB+PCBA+stencil) ~ $20 + LCSC kit ~ $15 per order: ASSUMPTION
        out[n] = dict(A=a, B=b, ship_per_system=ship, system=a["total"] + b["total"] + ship,
                      missing=[r["des"] for r in a_miss + bj_miss + bh_miss])
        if n == 5:
            def top(lines, k=8):
                return [dict(des=",".join(r["des"])[:40], value=r["value"][:40], code=r["code"], each=round(c / max(r["qty"], 1), 3),
                             per_board=round(c, 2), src=s, lib=(i or {}).get("lib"), stock=(i or {}).get("stock"))
                        for r, c, i, s in sorted(lines, key=lambda x: -x[1])[:k]]
            out["top_A"] = top(a_lines); out["top_B"] = top(bj_lines + bh_lines, 12)
            out["types"] = dict(A=len(A), B_jlc=len(BJ), B_hand=len(BH))
    json.dump(out, open(os.path.join(HERE, "cost.json"), "w"), indent=1)
    for n in (5, 10):
        o = out[n]
        print(f"qty {n}: A ${o['A']['total']:.2f} (parts {o['A']['parts']:.2f})  B ${o['B']['total']:.2f} "
              f"(JLC parts {o['B']['parts_jlc']:.2f}, hand {o['B']['parts_hand']:.2f}, fees {o['B']['pcba_fees']:.2f}, pcb {o['B']['pcb']:.2f})"
              f"  ship/sys {o['ship_per_system']:.2f}  SYSTEM ${o['system']:.2f}  missing {o['missing']}")

#!/usr/bin/env python3
"""Build the two-board design report (hw/report/site/index.html + images) from cost.json, rf_perf.json, the BOM CSVs
and the board shots.  Run cost_boards.py and rf_perf.py first."""
import csv, json, os, shutil, html, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); HW = os.path.dirname(HERE)
SITE = os.path.join(HERE, "site"); IMG = os.path.join(SITE, "img"); os.makedirs(IMG, exist_ok=True)
import cost_boards as CB
cost = json.load(open(os.path.join(HERE, "cost.json"))); rf = json.load(open(os.path.join(HERE, "rf_perf.json")))
for f in ["rf_filters.png", "rf_nf_gain.png", "rf_dynamic_range.png"]: shutil.copy(os.path.join(HERE, f), IMG)
for l in "ab":
    for f in [f"{l}_render_iso.png", f"{l}_render_top.png", f"{l}_render_bottom.png", f"{l}_copper_all.png"]:
        shutil.copy(os.path.join(HW, f"board_{l}", "shots", f), IMG)
E = html.escape
c5, c10 = cost["5"], cost["10"]
P = rf["points"]

def money(x): return f"${x:,.2f}"

def bom_table(path, des_col, qty_col, n=5):
    rows = CB.read(path, des_col, qty_col); out = []; tot = 0.0
    for r in rows:
        man = [CB.MANUAL[d] for d in r["des"] if d in CB.MANUAL]
        if man: each, line, info, note = man[0][1], man[0][1] * r["qty"], None, "estimate (not on LCSC)"
        else:
            line, info = CB.line_cost(r["code"], r["qty"], n)
            each = (line / r["qty"]) if line else None; note = ""
            if info: note = f"{'basic' if info.get('lib') == 'base' else 'extended'}, stock {info.get('stock'):,}"
        tot += line or 0
        out.append(f"<tr><td>{E(', '.join(r['des']))}</td><td>{E(r['value'])}</td><td class=mono>{E(r['code'])}</td>"
                   f"<td class=num>{r['qty']}</td><td class=num>{'' if each is None else money(each)}</td>"
                   f"<td class=num>{'' if line is None else money(line)}</td><td class=muted>{E(note)}</td></tr>")
    return ("<table class=bom><thead><tr><th>Designators</th><th>Value / part</th><th>LCSC</th><th>Qty</th>"
            "<th>Unit @5</th><th>$/board @5</th><th>Note</th></tr></thead><tbody>" + "".join(out) +
            f"</tbody><tfoot><tr><td colspan=5>Total parts per board (qty 5 build, MOQ-rounded)</td><td class=num>{money(tot)}</td><td></td></tr></tfoot></table>")

pt = lambda k: P[k]
kpi = [("Noise figure, low band", f"{pt('LB 100 MHz')['nf']}–{pt('LB 1700 MHz')['nf']} dB", "50–1750 MHz"),
       ("Noise figure, mid band", f"{pt('MB 1900 MHz')['nf']}–{pt('MB 2100 MHz')['nf']} dB", "1750–2150 MHz"),
       ("Noise figure, high band", f"{pt('HB 3500 MHz')['nf']}–{pt('HB 5800 MHz')['nf']} dB", "3.1–6 GHz"),
       ("Instantaneous DR", "≈44 dB", "40 MHz, 8-bit ADC limited"),
       ("Cost per system @5", money(c5["system"]), f"A {money(c5['A']['total'])} + B {money(c5['B']['total'])} + ship"),
       ("Cost per system @10", money(c10["system"]), f"A {money(c10['A']['total'])} + B {money(c10['B']['total'])} + ship")]
kpi_html = "".join(f"<div class=kpi><div class=kl>{E(a)}</div><div class=kv>{E(b)}</div><div class=ks>{E(c)}</div></div>" for a, b, c in kpi)

perf_rows = "".join(f"<tr><td>{E(k)}</td><td class=num>{v['nf']:.1f}</td><td class=num>{v['G']:+.1f}</td><td class=num>{v['n40']:.1f}</td>"
                    f"<td class=num>{v['clip']:.1f}</td><td class=num>{'—' if v['p1'] > 90 else f'{v['p1']:.1f}'}</td>"
                    f"<td class=num>{'—' if v['iip3'] > 90 else f'{v['iip3']:.1f}'}</td></tr>" for k, v in P.items())
fl = rf["filters"]
filt_rows = "".join(f"<tr><td>{E(n)}</td><td class=num>{v['pb_il_max']:.1f}</td><td class=num>{v['if_rej_min']:.0f}</td></tr>" for n, v in fl.items())

def cost_table():
    def col(o):
        a, b = o["A"], o["B"]
        return [money(a["parts"]), money(a["pcb"]), money(a["stencil"]), f"<b>{money(a['total'])}</b>",
                money(b["parts_jlc"]), money(b["parts_hand"]), money(b["pcb"]), money(b["pcba_fees"]), f"<b>{money(b['total'])}</b>",
                money(o["ship_per_system"]), f"<b>{money(o['system'])}</b>"]
    labels = ["A: components (incl. module est.)", "A: PCB share", "A: stencil share", "<b>Board A total</b>",
              "B: JLC-placed components", "B: hand-solder kit", "B: PCB share", "B: JLC PCBA fees share", "<b>Board B total</b>",
              "Shipping share (JLC + LCSC)", "<b>System (A + B)</b>"]
    a5, a10 = col(c5), col(c10)
    return "<table class=cost><thead><tr><th>Per board</th><th>qty 5</th><th>qty 10</th></tr></thead><tbody>" + "".join(
        f"<tr class='{'tot' if '<b>' in l else ''}'><td>{l}</td><td class=num>{x}</td><td class=num>{y}</td></tr>" for l, x, y in zip(labels, a5, a10)) + "</tbody></table>"

top_b = "".join(f"<tr><td>{E(r['des'])}</td><td>{E(r['value'])}</td><td class=num>{money(r['per_board'])}</td><td class=muted>{'' if r['stock'] is None else f'{r['stock']:,}'}</td></tr>" for r in cost["top_B"][:8])
top_a = "".join(f"<tr><td>{E(r['des'])}</td><td>{E(r['value'])}</td><td class=num>{money(r['per_board'])}</td><td class=muted>{'' if r['stock'] is None else f'{r['stock']:,}'}</td></tr>" for r in cost["top_A"][:6])

bom_a = bom_table(f"{HW}/board_a/fab/BOM_A_kit.csv", "Designators", "Qty per board")
bom_bj = bom_table(f"{HW}/board_b/fab/BOM_B_JLC.csv", "Designator", None)
bom_bh = bom_table(f"{HW}/board_b/fab/BOM_B_HAND_LCSC.csv", "Designators", "Qty per board")

CSS = """
:root{--bg:#f6f6f3;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--line:#e2e1dc;--accent:#2a78d6;--warn:#b25e00;--ok:#1a7f4b}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#121211;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8f8e86;--line:#33322f;--accent:#3987e5;--warn:#e0a040;--ok:#4fbf86}}
:root[data-theme="dark"]{--bg:#121211;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#8f8e86;--line:#33322f;--accent:#3987e5;--warn:#e0a040;--ok:#4fbf86}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
main{max-width:1120px;margin:0 auto;padding:28px 16px 64px}h1{font-size:28px;margin:0 0 4px;letter-spacing:-.01em}
h2{font-size:20px;margin:40px 0 10px;padding-top:8px;border-top:1px solid var(--line)}h3{font-size:16px;margin:22px 0 8px}
.sub{color:var(--ink2);margin:0 0 18px}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:18px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}.kl{font-size:12px;color:var(--ink2)}
.kv{font-size:22px;font-weight:650;margin:2px 0}.ks{font-size:12px;color:var(--muted)}
figure{margin:14px 0;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:10px}figure img{width:100%;height:auto;display:block;border-radius:6px;background:#fcfcfb}
figcaption{font-size:13px;color:var(--ink2);margin-top:8px}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:760px){.grid2{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--surface);border:1px solid var(--line);border-radius:8px;overflow:hidden}
th,td{padding:6px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{font-weight:600;color:var(--ink2);background:color-mix(in srgb,var(--surface) 90%,var(--accent) 10%)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}.mono{font-family:ui-monospace,Menlo,monospace;font-size:12.5px}.muted{color:var(--muted)}
tr.tot td{background:color-mix(in srgb,var(--surface) 92%,var(--accent) 8%)}tfoot td{font-weight:600}
.tw{overflow-x:auto}details{margin:10px 0;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:8px 12px}summary{cursor:pointer;font-weight:600}
.note{border-left:3px solid var(--warn);padding:8px 12px;background:var(--surface);border-radius:6px;margin:12px 0;font-size:14px}
.chain{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:10px 12px;overflow-x:auto;white-space:pre}
ul{padding-left:20px}li{margin:3px 0}a{color:var(--accent)}
"""

today = datetime.date.today().isoformat()
page = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>ESP32-S31 SDR Boards</title><style>{CSS}</style></head><body><main>
<h1>ESP32-S31 SDR: two-board design report</h1>
<p class=sub>Receive-only SDR: wideband front end, RFFC5072 mixer, 2.44 GHz IF into the ESP32-S31 raw I/Q stream over gigabit Ethernet. Status {today}: both boards placed, routed and DRC-clean to JLC basic 4-layer rules, with fab outputs generated. <b>Not ordered</b>, because of stock.</p>
<div class=kpis>{kpi_html}</div>

<h2>Architecture</h2>
<div class=chain>Board B (RF):  SMA ─ ESD ─ SP3T ─┬─ LB: PSA4-5043+ ─ LPF 1.75 GHz ─┐
                                  ├─ MB: PSA4-5043+ ─ BPF 1.75–2.15 ─┤─ SP3T ─ GVA-62+ ─ balun ─ RFFC5072 ─ 2.44 GHz SAW ─ 3 dB pad ─ U.FL
                                  └─ HB: HPF ─ QPL9503 ─ HPF 3.1 GHz ┘            (40 MHz TCXO ref; LO 290 MHz–4.2 GHz)
Board A (base): U.FL ─ ESP32-S31-WROOM-1U (raw I/Q, 40 MS/s) ─ RGMII ─ YT8531 ─ RJ45 (GbE);  USB-C power;  2×10 header → Board B control + 5 V</div>
<p>Tuning: LB 50–1750 MHz (LO = IF+RF), MB 1750–2150 MHz (LO = IF−RF), HB 3.1–6 GHz (LO = RF−IF), plus native ESP32 2.15–2.8 GHz on Board A alone (antenna on the module's U.FL). There is a gap at 2.8–3.1 GHz. The IF is 61 × 40 MHz, which parks the reference harmonic on the DC spike.</p>

<h2>Boards</h2>
<div class=grid2>
<figure><img src="img/a_render_iso.png" alt="Board A 3D render"><figcaption><b>Board A, base board</b>, 62×46 mm. WROOM-1U (left), YT8531 PHY + magjack (right), USB-C (top right), 2×10 socket to Board B (left edge). 67 parts, all assembled in house (stencil + hotplate for module/PHY). The 3D models aren't installed, so parts show as pads.</figcaption></figure>
<figure><img src="img/b_render_iso.png" alt="Board B 3D render"><figcaption><b>Board B, RF front end</b>, 62×40 mm. RF input SMA (left), three band chains + filters (centre/left), RFFC5072 mixer (top right), IF U.FL (right), header to Board A (right edge). 160 parts, 95 placed by JLC.</figcaption></figure>
</div>
<figure><img src="img/a_copper_all.png" alt="Board A copper layers"><figcaption>Board A copper. In1 is solid GND with no routing. RGMII is scripted: TX lanes on B.Cu, RX lanes on In2 (3V3 pour). 127 GND stitching vias.</figcaption></figure>
<figure><img src="img/b_copper_all.png" alt="Board B copper layers"><figcaption>Board B copper. The RF chain is on F.Cu over solid In1 GND. The white combs on In1 are the EM-designed voids under the filter 0402 pads. 234 stitching vias plus a 2 mm edge fence.</figcaption></figure>
<details><summary>Top / bottom renders</summary><div class=grid2>
<figure><img src="img/a_render_top.png" alt=""><figcaption>Board A top</figcaption></figure><figure><img src="img/a_render_bottom.png" alt=""><figcaption>Board A bottom</figcaption></figure>
<figure><img src="img/b_render_top.png" alt=""><figcaption>Board B top</figcaption></figure><figure><img src="img/b_render_bottom.png" alt=""><figcaption>Board B bottom</figcaption></figure></div></details>

<h2>Simulated RF performance</h2>
<h3>Band filtering</h3>
<figure><img src="img/rf_filters.png" alt="Filter responses"><figcaption>Sonnet EM model of the as-routed 0402 filter layouts (pads, lines, In1 voids, vias), co-simulated with the final part values and part parasitic models. The shaded band is the 5–95 % spread over 300 Monte-Carlo draws (C ±0.05 pF W-grade, L ±0.1 nH B-grade). The orange stripe is the 2.40–2.48 GHz IF, which every mixer band must reject to stop direct IF feed-through. The 2nd-order HB pre-filter only protects the HB LNA from strong low-band signals; the elliptic HB HPF provides the IF rejection.</figcaption></figure>
<div class=tw><table><thead><tr><th>Filter</th><th class=num>Passband IL max (dB)</th><th class=num>IF rejection min (dB)</th></tr></thead><tbody>{filt_rows}</tbody></table></div>

<h3>Noise figure and gain</h3>
<figure><img src="img/rf_nf_gain.png" alt="NF and gain"><figcaption>Cascade from the antenna SMA to the ESP32 ADC. Stage models are datasheet values (SP3T BGS13SN8, PSA4-5043+, QPL9503, GVA-62+, H3-TCM2-63WX+, RFFC5072, SAW). Filter loss comes from the EM co-simulation above. Trace loss uses the measured RF trace lengths on Board B times Sonnet's line loss (0.028 dB/mm at 6 GHz). The IF tail is the 3 dB pad and the U.FL cable. ESP32-S31 NF is <b>assumed</b> to be 5 dB; it isn't published. Pre-LNA trace adds only ~0.15–0.2 dB.</figcaption></figure>

<h3>Dynamic range</h3>
<figure><img src="img/rf_dynamic_range.png" alt="Dynamic range"><figcaption>Input-referred levels. With the ESP32 gain set so that analog noise sits 6 dB above the 8-bit quantization floor, full scale is ≈ −52 dBm at the antenna and the instantaneous dynamic range is ≈44 dB in 40 MHz. Narrowband signals gain processing gain on top of that, e.g. +46 dB in 1 kHz. The analog chain compresses ~27 dB above ADC full scale, so lowering the ESP32 gain index trades sensitivity for strong-signal headroom without analog compression. The ESP32's AGC does not protect the ADC, so gain must be set manually.</figcaption></figure>
<div class=tw><table><thead><tr><th>Point</th><th class=num>NF (dB)</th><th class=num>Gain (dB)</th><th class=num>Noise (dBm/40 MHz)</th><th class=num>ADC FS @ant (dBm)</th><th class=num>P1dB in (dBm)</th><th class=num>IIP3 (dBm)</th></tr></thead><tbody>{perf_rows}</tbody></table></div>
<div class=note><b>Known RF limitations</b> (from the frequency-plan analysis):
<ul>
<li>In the HB, 1×3 / 1×5 mixer spurs fall in-band at 15–22 dBc for tuning around 3.5–4.1 GHz and 4.5–5.26 GHz. Software should flag those ranges.</li>
<li>The MB BPF costs up to 4.1 dB, so the MB is the noisiest mixer band.</li>
<li>Rates below 40 MS/s decimate without filtering in the current esp-sdr firmware (aliasing).</li>
</ul></div>

<h2>Cost per board</h2>
<div class=grid2><div>{cost_table()}</div>
<div><h3 style="margin-top:0">Largest line items (B)</h3><div class=tw><table><thead><tr><th>Ref</th><th>Part</th><th class=num>$/board</th><th>LCSC stock</th></tr></thead><tbody>{top_b}</tbody></table></div>
<h3>Largest line items (A)</h3><div class=tw><table><thead><tr><th>Ref</th><th>Part</th><th class=num>$/board</th><th>LCSC stock</th></tr></thead><tbody>{top_a}</tbody></table></div></div></div>
<p class=muted>Prices: JLC/LCSC parts API by LCSC number on {today}, bought at max(need, first price break). JLC Standard PCBA fees for B: $25.56 setup, $8.21 stencil, $1.53 × {cost['types']['B_jlc']} part types, X-ray billed per board, per-joint charge. <b>Assumptions:</b> PCB $15 per design per order (5 pcs) or $20 (10 pcs), not yet a live quote; Board A stencil $8; shipping $35 per order; WROOM-1U $6 estimate (not on LCSC, 0 stock). Board B's RFFC5072 alone is $14.61, about 23 % of the board.</p>

<h3>Bill of materials</h3>
<details><summary>Board A: in-house kit ({cost['types']['A']} lines)</summary><div class=tw>{bom_a}</div></details>
<details><summary>Board B: JLC-placed ({cost['types']['B_jlc']} part types)</summary><div class=tw>{bom_bj}</div></details>
<details><summary>Board B: hand-solder kit ({cost['types']['B_hand']} lines, 0603+ / SOT / connectors)</summary><div class=tw>{bom_bh}</div></details>

<h2>Layout and process</h2>
<ul>
<li><b>Process (D22):</b> JLC basic 4-layer, JLC04161H-3313 stack, no surcharge items. 0.45/0.2 mm vias, 0.1/0.1 mm track/space, 0.2 mm hole and edge clearance. Verified on the final boards: 0 tracks on In1, no via outside the no-surcharge range.</li>
<li><b>RF lines:</b> 0.19 mm microstrip over In1 GND (0.1 mm prepreg) = 50.8 Ω (Sonnet), ≈ ±10 % with JLC tolerance. The RF copper is locked exactly as in the EM model.</li>
<li><b>DRC (KiCad, JLC rules):</b> 0 unconnected / shorts / clearance / hole-clearance on both boards. Accepted flags:
  <ul><li>edge-launch SMA copper at the board edge;</li>
  <li>courtyard overlaps in the RF ladders at the EM-model spacing;</li>
  <li>silk.</li></ul></li>
<li><b>Board A:</b>
  <ul><li>RGMII module-to-PHY lanes are scripted: intra-group skew ≈ 50 ps, far inside RGMII-ID tolerance.</li>
  <li>The USB 2.0 HS pair is a scripted coupled pair (≈90 Ω) along the board's top edge over solid In1 GND, with DM/DP matched to 0.9 mm.</li>
  <li>TX 33 Ω resistors were dropped (D21): the reference places them at the MAC, which is impossible under the module.</li>
  <li>PHY decoupling sits at the pins.</li></ul></li>
<li><b>Board B:</b>
  <ul><li>The RFFC5072 loop filter is pinned next to the mixer; all LF nets are ≤13 mm on F.Cu.</li>
  <li>The reference-clock option links sit at the TCXO, so there is no long stub on the 40 MHz reference.</li>
  <li>Three scripted hand fixes.</li></ul></li>
<li><b>Autorouter:</b> Freerouting, statically audited (not malicious) and run network-isolated in a memory-capped unit.</li>
</ul>

<h2>Before ordering</h2>
<ol>
<li><b>JLC CPL/DFM preview:</b> check part rotations, and that JLC accepts the 0402 RF ladders at the EM-model pad gaps.</li>
<li><b>Sourcing:</b> WROOM-1U is not on LCSC; RFFC5072 has 66 in stock and the T2 IF balun 25 (as of {today}). Re-check stock first.</li>
<li><b>Get a live JLC quote</b> with these Gerbers/BOM/CPL to replace the PCB and shipping assumptions.</li>
</ol>
<p class=muted>Resolved since the first version of this report:
<ul class=muted>
<li><b>USB HS pair:</b> now a scripted, coupled 0.17/0.11 mm pair (≈90 Ω differential) over solid GND, with DM/DP matched to 0.9 mm (was 13.5 mm skew and 4 vias).</li>
<li><b>USB-C pad ties:</b> scripted.</li>
<li><b>40 MHz reference stub:</b> the DNP option links now sit at the TCXO/C384, so REFCLK_RF is 13 mm in total (was 43 mm).</li>
<li><b>PHY decoupling:</b> three caps rotated so the supply pads face the PHY pins.</li>
</ul></p>

<h2>Files</h2>
<ul class=mono>
<li>claude_out:esp32_sdr/hw/board_a/fab/: Gerbers+drill zip, BOM_A_kit.csv, CPL_A.csv, layer PDFs</li>
<li>claude_out:esp32_sdr/hw/board_b/fab/: Gerbers+drill zip, BOM_B_JLC.csv, CPL_B_JLC.csv, BOM_B_HAND_LCSC.csv, layer PDFs</li>
<li>claude_out:esp32_sdr/hw/board_{{a,b}}/esp32sdr_{{a,b}}_routed.kicad_pcb: KiCad boards</li>
<li>claude_out:esp32_sdr/hw/LAYOUT_STATUS_SPLIT.md, DECISIONS.md, em/EM_REPORT.md, SIGNAL_CHAIN_ANALYSIS.md</li>
<li>claude_out:esp32_sdr/hw/report/: this report's generators (cost_boards.py, rf_perf.py, build_report.py)</li>
</ul>
</main></body></html>"""
open(os.path.join(SITE, "index.html"), "w").write(page)
print("wrote", os.path.join(SITE, "index.html"), sum(os.path.getsize(os.path.join(IMG, f)) for f in os.listdir(IMG)) // 1024, "KB images")

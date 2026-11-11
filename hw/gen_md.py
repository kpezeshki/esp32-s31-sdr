#!/usr/bin/env python3
import json, sys
d = json.load(open(sys.argv[1]))
L = []
L.append("# ESP32-S31 SDR board: netlist-ready pinouts and application circuits (T18)\n")
L.append("Generated 2026-11-09. The same data is in machine-readable form in `hw/pinouts.json`. Datasheets are in "
         "`claude_db/esp32_sdr_datasheets/`, and page numbers refer to the PDF pages. Footprint names are checked against the KiCad 10.0.6 libraries "
         "(`/usr/share/kicad/footprints`). **UNVERIFIED** marks values that do not come from a primary document.\n")
L.append("""## Surprises and action items

1. **H3-TCM2-63WX+ / TCM2-63WX+ has no centre tap** (Config K transmission-line balun). Pin 6 (secondary dot) is DC-tied to ground and pin 4 is DC-tied to the primary input. The RFFC5072 mixer inputs must not see DC, so **fit a series DC-block cap on both mixer legs** (100 pF 0402). Pins 1 and 2 go to GND, pin 3 is the input, and pin 5 is not used (the clone has no lead there).
2. **BD2425N50200AHF does have a DC-feed pin.** Pin 1 is "GND / DC feed + RF GND", the balanced-side centre tap. Feed ANA_VDD2 into pin 1, bypass it right at the pad, and wire pins 3/4 straight to RFFC pins 27/28. No chokes are needed. The DC current rating is not stated (**UNVERIFIED**). There is no KiCad footprint, so a custom 0404 land is given.
3. **GD25Q32E**S**IGR is SOP-8 208 mil**, not 150 mil. Use `Package_SO:SOIC-8_5.23x5.23mm_P1.27mm`.
4. **BWSMA-KE-P001 is a straddle edge-mount** (centre pin and 2 legs on top, 2 legs below, 1.7 mm gap), so it suits a 1.6 mm board. Its geometry fits `Connector_Coaxial:SMA_Samtec_SMA-J-P-X-ST-EM1_EdgeMount` on paper (legs at x=±2.55 mm, 0.9 mm wide, 4 mm long). This is **UNVERIFIED** by a test fit.
5. **No KiCad footprints** exist for BGS13SN8 (TSNP-8 1.1×1.1), BD2425 (0404), or HR911130C. The KiCad `RJ45_Hanrun_HR911105A` is a 10/100 part with a different pin-out and must not be used. Custom land patterns for all three are given below and in the JSON.
6. **SAW SAFEA2G45MC0F0A needs shunt-L matching.** Murata characterises it with a 4.3 nH (ideal) shunt inductor at both ports. Its pin numbering matches `Filter:Filter_1411-5_1.4x1.1mm`.
7. **RFFC5072 loop filter** values come from the datasheet eval board (8.2 pF ‖ (22 k + 180 pF), then 470 R / 330 pF ×2). The datasheet quotes them for a **52 MHz reference / 200 kHz loop bandwidth**. At 40 MHz the bandwidth is about 150 kHz with the same charge-pump setting, which is fine. REXT = 51 k.
8. **RFFC5072 pin-name inconsistency:** the pin table (p4) says 27 = MIX_OPN and 28 = MIX_OPP, but the eval schematic (p7) labels 27 as "IOIP" (+) and 28 as "IOIN". This only affects IF polarity.
9. **RFFC ENBL/MODE** become outputs (GPO5/6) under SPI control (`sipin=1`). Route them to GPIOs or through resistors, never hard-tie them to a rail.
10. **GVA-62+ is specified 4.8–5.2 V at the device.** The 4.5 V LDO rail is below spec. Feed it from VBUS through a ferrite + LC filter, or accept lower current and P1dB.
11. **No part needs a negative supply.** All are single positive supply: RFFC 2.7–3.3 V, LNAs 3–5 V, switch 1.65–3.4 V.
12. The PSA4-5043+ and GVA-62+ datasheets give **no choke values** (their eval boards use Mini-Circuits bias tees, TCBT-14+ and ADCH-80A+). The two-section discrete chokes suggested here are **UNVERIFIED** engineering choices.
13. BGS13SN8: abs max DC on RF ports is 0 V, and the switched paths are DC-connected inside the switch. Every port next to an LNA or gain-block pin needs a DC block. Its ±8 kV SLT ESD rating assumes a 27 nH shunt inductor, which is unusable at 50 MHz.
14. HR911130C: the common centre tap (pin 1) goes to GND through 100 nF, as in the Espressif reference (0.1 µF per TCT). It is not powered, because YT8531 is a voltage-mode PHY.
""")
for name, v in d.items():
    L.append(f"\n---\n\n## {name}\n")
    L.append(f"- **MPN / mfr:** {v.get('mpn')} ({v.get('mfr')}); **LCSC:** {v.get('lcsc')}")
    L.append(f"- **Function:** {v.get('function')}")
    L.append(f"- **Source:** {v.get('source')}")
    pk = v.get("package", {})
    L.append(f"- **Package:** {pk.get('name')}" + (f" (body {pk.get('body_mm')} mm)" if pk.get('body_mm') else ""))
    for k in ("supply", "logic", "output", "impedance"):
        if v.get(k): L.append(f"- **{k.capitalize()}:** {v[k]}")
    fp = v.get("kicad_footprint")
    L.append(f"- **KiCad footprint:** `{fp}`" if fp else "- **KiCad footprint:** none in library, so use the custom land pattern below")
    if v.get("kicad_footprint_alt"): L.append(f"- **Alt footprint:** `{v['kicad_footprint_alt']}`")
    if v.get("kicad_footprint_check"): L.append(f"- **Pad-numbering check:** {v['kicad_footprint_check']}")
    L.append("\n| Pin | Name | Function |\n|---|---|---|")
    for pn, pv in v["pins"].items():
        L.append(f"| {pn} | {pv['name']} | {pv['function']} |")
    if v.get("truth_table"):
        L.append("\n**Truth table:** " + "; ".join(f"{k} → {t}" for k, t in v["truth_table"].items()))
    if v.get("app_circuit"):
        L.append("\n**Application circuit**\n\n| Ref | Value | Pkg | Connects | Source |\n|---|---|---|---|---|")
        for a in v["app_circuit"]:
            L.append(f"| {a['ref_hint']} | {a['value']} | {a['package']} | {' ↔ '.join(a['connects'])} | {a.get('source','')} |")
    for k in ("loop_filter_note", "control_note"):
        if v.get(k): L.append(f"\n**{k.replace('_',' ').capitalize()}:** {v[k]}")
    c = v.get("custom_land_pattern")
    if c:
        L.append(f"\n**Custom land pattern `{c.get('name')}`** ({c.get('units','mm')}; origin: {c.get('origin','')})\n")
        L.append("```json\n" + json.dumps({k: c[k] for k in c if k not in ('name',)}, indent=1) + "\n```")
    if v.get("notes"):
        L.append("\n**Notes**\n")
        for n in v["notes"]: L.append(f"- {n}")
open(sys.argv[2], "w").write("\n".join(L) + "\n")
print("ok")

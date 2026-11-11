# ESP32-S31 RX-only SDR: part selection (rev 0, 2026-11-09)

Task T18. This draft follows the architecture as revised on 2026-11-09 (DECISIONS D1, D7):

```
SMA ─ ESD ─ SPDT_in ─┬─ LNA_LB ─ LPF (1.75 GHz) ─────────────────┬─ SPDT_out ─ [gain block | 0R] ─ 1:2 balun ─ RFFC5072 ─ 4:1 IF balun ─ SAW 2.44 G ─ 0R tee ─ ESP32-S31
                     └─ HPF2 (~2.5 G) ─ LNA_HB ─ HPF (2.95 GHz) ─┘
```

There is no diplexer. The same SPDT part is used twice. The band filters are lumped 0402 parts (D7). The catalog LTCC filters in slot 15 are listed for comparison only.

Where the numbers come from:
- **Price/stock:** JLCPCB parts API (`jlcpcb.com/api/.../selectSmtComponentList`), queried 2026-11-09. This is the same inventory LCSC sells. Prices are LCSC/JLC USD at the stated break, and "stock" is LCSC/JLC stock on that date. Every part found was "extended" in the JLC library except AMS1117-3.3 (C6186) and W25Q128JVSIQ (C97521), which are **basic**. The basic/extended difference does not matter here: the QFN80 forces Standard PCBA, which charges every part type the same loading fee (see the budget section).
- **Mouser/DigiKey/Octopart:** all three blocked automated access (403 errors and timeouts), so their prices are **unverified** unless noted. Where I found a manufacturer-direct price (Qorvo store, Mini-Circuits web store) I give it instead.
- **Specs:** taken from the downloaded datasheets in `claude_db/esp32_sdr_datasheets/` (tag [DS]). If a spec is tagged [LCSC], only the distributor listing was available.

---

## 1. LNA_LB (50–1750 MHz)

SPF5189Z status: Qorvo EOL. The PCN 21-0060 notice was issued 2021-03-08, with last-time buy on 2021-09-15. **Qorvo names QPL9547 as the replacement.** LCSC/JLC list the SPF5189Z as "no longer manufactured" with 0 stock. Searching for "SPF5189" and "5189" found **no clone listed at LCSC.**

| Part | Range | Gain | NF | OIP3 / OP1dB | Supply | Package | LCSC # | LCSC price 10+ / 100+ | Stock | Other source |
|---|---|---|---|---|---|---|---|---|---|---|
| **Mini-Circuits PSA4-5043+ (recommended, cost)** | 0.05–4 GHz | 18.4 dB @1 GHz [DS] | 0.75 dB @1 GHz, 0.98 @2 GHz [DS] | +33.5 / +21 dBm [DS] | 3 V/33 mA or 5 V/56 mA | SOT-343 (leaded, no X-ray fee) | C5240848 | $1.91 / $1.47 | 2755 | Mouser/DK unverified |
| Qorvo QPL9547TR7 (official SPF5189Z successor; best single part for 0.1–6 GHz) | 0.1–6 GHz | S21 25.8 @0.7, 24.5 @0.9, 20.3 @1.7, 16.4 @2.9, 15.0 @3.5, 12.3 @4.9, 11.2 @5.5 GHz [DS] | 0.38 / 0.30 / 0.45 dB @0.9/1.9/2.6 GHz [DS] | +38.5…+39.2 / +22…+23 dBm [DS] | 3.15–5.25 V, 65 mA @5 V, 1.8 V shutdown pin | DFN-8 2×2 | C5367093 | $6.27 / $5.74 | 4810 | Mouser/DK unverified |
| Qorvo TQP3M9036 | 0.05–2 GHz | 22.5 @0.6, 19.1 @0.9, 15.1 @1.5, 13.0 @2.0 GHz [DS] | 0.38–0.52 dB [DS] | +36 @0.9 GHz / +23 dBm [DS] | 3.3–5 V, 68 mA @5 V | DFN-8 2×2 | C920261 | $3.54 / $2.99 | 946 | |

Notes:
- PSA4-5043+ is Mini-Circuits' drop-in for the SPF5043Z. It is the cheapest genuine LNA that meets NF < 1 dB, OIP3 > 30 dBm, gain about 18 dB and 3–5 V. It is leaded, which avoids the X-ray fee. I did not extract gain below 500 MHz from the datasheet plot. Expect it to rise toward the low end, as it does in all of these E-pHEMT parts.
- QPL9547 has a 0.7 GHz input match of only −7.9 dB, and Qorvo's EVB is characterised over 0.6–4.2 GHz. Below 0.6 GHz the gain is above 26 dB and not specified. Check stability there.

## 2. LNA_HB (2.95–6 GHz)

| Part | Range | Gain | NF | OIP3 / OP1dB | Supply | Package | LCSC # | 10+ / 100+ | Stock |
|---|---|---|---|---|---|---|---|---|---|
| **Qorvo QPL9503TR7 (recommended, performance)** | 0.6–6 GHz, flat to ±1 dB over 3–6 GHz | 21.6 dB @5.5 GHz (min 18.5) [DS] | 0.9 dB typ, 1.3 max @5.5 GHz [DS] | +35.5 / +19 dBm [DS] | 3.3–5 V, 56 mA, shutdown pin | DFN-8 2×2 | C470924 | $5.08 / $4.27 | 760 |
| Qorvo QPL9504TR7 | 0.6–6 GHz | 20.6 / 21.6 / 20.0 dB @5.0/5.5/6.0 GHz [DS] | 0.71 / 0.76 / 0.85 dB [DS] | +33.4…+34.4 / +17.5…+18.7 [DS] | 3.3–5.5 V, 55 mA | DFN-8 2×2 | C22432296 | $5.87 / $4.86 | 46 |
| **Skyworks SKY67183-396LF (recommended, cost; low stock)** | 0.4–6 GHz | 18.2 dB @4.5 GHz (min 16.5) [DS] | 0.5 dB typ, 1.0 max @4.5 GHz [DS] | +29 / +19 dBm @4.5 GHz [DS] | 3.3–5.25 V | DFN-8 2×2 | C1870735 | $2.93 / $2.83 | **11** |
| MACOM MAAL-011078 | 0.7–6 GHz | 23 dB @2.6, 15 dB @6 GHz [DS] | 0.35 @1.9, 0.5 @2.6 GHz [DS] | OIP3 +33 [DS] | 3–5 V | DFN-8 2×2 | C559045 | $3.68 / $3.57 | 9 |

- MGA-665P8, the GRF20xx parts and Infineon 5 GHz LNAs are not stocked at LCSC. GRF2073 and GRF2080 have listings but 0 stock.
- **SKY67183 is also a candidate single wideband LNA from 0.4 GHz upward**, if the lean variant gives up LB coverage below 400 MHz.

## 3. Wideband gain block (50 MHz–6 GHz, 0R bypass)

| Part | Range | Gain | NF | OIP3 / OP1dB | Supply | Package | LCSC # | 10+ / 100+ | Stock |
|---|---|---|---|---|---|---|---|---|---|
| **Mini-Circuits GVA-63+ (recommended)** | 0.01–6 GHz | 21.9 / 21.1 / 19.9 / 18.5 / 17.3 / 15.9 dB @0.05/0.8/2/3/4/6 GHz [DS] | 3.6 / 3.8 / 3.7 / 3.7 / 4.0 / 4.6 dB [DS] | OIP3 +33.5 / +34.8 / +32.2 / +28.6 / +26.6 / +25.0; OP1dB +18.7 … +11.8 @6 GHz [DS] | 4.8–5.2 V at device, 69 mA | SOT-89 | C3193270 | $1.69 / $1.32 | 3263 |
| Mini-Circuits GVA-62+ (flatter, lower gain) | 0.01–6 GHz | 16.5 / 15.6 / 15.4 / 15.3 / 15.0 / 14.5 dB [DS] | 4.7 @0.05, 5.0 @1, 5.1 @2 GHz [DS] | OIP3 +37.8 / +37.5 / +33.6 / +30.4 / +28.1 / +23.0; OP1dB +19.7 … +11.7 [DS] | 4.8–5.2 V, 82 mA | SOT-89 | C5445184 | $2.53 / $2.10 | 206 |
| Tokmas "GVA-63" clone | n/s | 17.5 dB [LCSC] | n/s | OP1dB +21.9 [LCSC] | 3–5 V, 89 mA | SOT-89 | C55019278 | $0.96 / $0.72 | 299 |
| ADI ADL5611 | 0.03–6 GHz | 22.2 dB [LCSC] | 2.1 dB [LCSC] | OIP3 +40, OP1dB +21 [LCSC] | 5 V | SOT-89 | C208262 | $5.04 / $3.91 | 2515 |

Mini-Circuits PGA-103+ and Qorvo TQP3M9028 stop at 4 GHz, so I excluded them. HMC311ST89 is out of stock at LCSC.

## 4. SPDT ×2 (SPDT_in sets the NF, so it needs low IL and IIP3 of at least +50 dBm)

| Part | Range | IL | Isolation | Linearity | Control / supply | Package | LCSC # | Price | Stock |
|---|---|---|---|---|---|---|---|---|---|
| **Infineon BGS12P2L6 (recommended)** | 0.05–6 GHz | 0.20 / 0.25 / 0.31 / 0.39 / 0.47 / **0.51 dB typ (0.64 max) @5.15–5.925 GHz** [DS] | 45 dB @0.6–0.96 GHz, 27 dB @5.9 GHz [DS] | **IIP3 +74 dBm typ (+71 min)** [DS] | VDD 1.65–3.4 V, V_ctrl,H ≥ 1.35 V (1.8/3.3 V GPIO OK), 65 µA, no decoupling needed | TSLP-6-4, 0.7×1.1 mm | C3312945 | $0.38 (1+), $0.30 (50+), $0.26 (150+) | 5041 |
| Infineon BGS12SN6 | 0.1–6 GHz | 0.23–0.29 dB to 2.7 GHz, 0.53 @5 GHz, 0.65 @6 GHz [DS] | – | P0.1dB +34 dBm, H2 −80 dBc [DS] | VDD 1.8–3.5 V, V_ctrl,H ≥ 1.35 V | TSNP-6, 0.7×1.1 mm | C114953 | $0.49 / $0.41 | 34180 |
| Skyworks SKY13453-385LF (used ×7 in HackRF One) | 0.01–6 GHz | 0.40 dB to 2 GHz, 0.45 @2–3 GHz, 0.70 dB (0.85 max) @4.8–6 GHz [DS] | 27 → 15 dB @6 GHz [DS] | IP0.1dB +33 dBm; IIP3 not extracted (unverified) | VDD 2.5–3.7 V, VCTL 1.8 V logic | QFN-6, 1×1 mm | C150878 | $0.42 / $0.32 | 1418 |

pSemi PE42420 costs $2.58 and has IL 1.6 dB. PE4259 and AS179 (and their clones) stop at 3 GHz.

## 5. 1:2 wideband balun (50 Ω SE → 100 Ω diff, RFFC5072 RF input)

**One part does cover 30 MHz–6 GHz: Mini-Circuits TCM2-63WX+.** At LCSC it costs $19–22, against about $8–9 direct from Mini-Circuits. A HenryTech clone costs $2.2–2.7.

| Part | Range | IL | Amplitude / phase unbalance | Package | LCSC # | 10+ / 100+ | Stock | Other |
|---|---|---|---|---|---|---|---|---|
| Mini-Circuits TCM2-63WX+ | 30–6000 MHz | 0.9 typ (1.9 max) @100–4000 MHz; 1.5 typ (2.9 max) @30–5000; **2.5 typ (3.9 max) @5–6 GHz** [DS] | ±0.4 dB / ±4° (100–4500 MHz); ±0.5 dB / ±5° (30–6000) [DS]; CMRR 25 / 20 dB | DB1627, about 4 mm | C2683590 | $22.09 / $19.25 | 296 | **Mini-Circuits direct $9.38 @20, $8.08 @100, >1000 in stock** |
| **HenryTech H3-TCM2-63WX+ (recommended, cost; clone)** | 30–6000 MHz | "0.6 / 3.9 dB" [LCSC; clone, unverified] | "6°" [LCSC] | 4.2×4.2 mm, 5-pad | C22383437 | $2.70 / $2.17 | 199 (findchips: 511) | |
| MACOM MABA-011118 | 10–10000 MHz | 2.0 (10–1000 MHz), 1.2 (1–4 GHz), 1.9 (4–7 GHz) [DS] | 0.3 / 1.0 / 1.5 dB; 8° / 12° [DS] | 3.8 mm SMD-6 | C3305026 | $5.98 / $5.80 | 0 | Clone H3-MABA-011118: $8.99, 207 in stock |

**What HackRF One uses:** T1 "MIX_IN_BALUN" and T2 "MIX_OUT_BALUN" are both **TTM/Anaren B0310J50100AHF**. This is an 0805 LTCC 50:100 Ω balun rated for only **300–1000 MHz** (source: `hardware/hackrf-one/frontend.kicad_sch` on GitHub). HackRF runs it far outside that range, from 2.15 to 2.75 GHz IF and up to 6 GHz RF. It is cheap ($0.69 at LCSC, C5160223, 0 stock), but at the band edges you should expect several dB of extra loss and poor balance.

**Lean option:** drive the mixer single-ended and AC-ground the other input. This costs nothing in parts, but even-order spurs/IIP2 get worse and LO→RF leakage rises.

## 6. 2.45 GHz IF balun (RFFC5072 MIX_OUT ±, 200 Ω balanced → 50 Ω)

| Part | Band | Ratio | IL | Package | LCSC # | 10+ | Stock |
|---|---|---|---|---|---|---|---|
| Johanson 2450BL15B200 / 2450BL15B0200001E | 2.4–2.5 GHz | 50:200 | ≈1 dB [LCSC] | 0805 | C26505306 / C17341095 | – | **0 / 0** |
| **Anaren/TTM BD2425N50200AHF (recommended)** | 2.4–2.5 GHz | 50:200 | 0.7 typ / 1.0 dB, ±2° [LCSC] | 0404 | C502748 | $0.87 | **25** |
| Lumped LC balun (lattice, 0402) | design | any | about 1–1.5 dB | 0402 | basic passives | ≈ $0.02 | – |

- I have not checked whether BD2425N50200AHF has a DC-feed pin. If it does not, MIX_OUT needs two RF chokes to VCC.
- Murata LDB212G4020C-001 (50:200) is no longer made.
- At LCSC, 25 BD2425 parts are enough for 5 boards.

## 7. 2.4 GHz SAW/BAW (2400–2483.5 MHz)

| Part | IL | Rejection near the band (min/typ, Murata DS) | Far rejection | Power | Package | LCSC # | Price | Stock |
|---|---|---|---|---|---|---|---|---|
| **Murata SAFEA2G45MC0F0AR00 (recommended)** | 2.3 typ / 2.8 max (2411–2483); 2.7 / 4.8 at 2401–2406 [DS] | 2300–2320: 45/54; **2320–2370 (−100 MHz): 37/44**; 2370–2380: 10/42; **2483–2570 (+100 MHz): not specified**; 2570–2620: 42/46; 2620–2690: 40/44; 2110–2170 (≈ −300 MHz): 40/44 | 10–1559 MHz: 43/47; **2690–6000 MHz: 30/37** (so +250 MHz is about 30 dB) | +28 dBm, 20000 h | 1.4×1.1 mm, 5-pad | C910550 | $0.27 (1+), $0.21 (50+) | 9394 |
| Murata SAFFB2G45MA0F0AR1X (low IL) | 1.2 typ / 2.0 max [DS] | 2302–2368: 27/34; 2496–2501: 16/27; 2507–2688: 28/32 | 26–30 dB | +25 dBm | 1.1×0.9 mm | C910680 | $0.10 | 14 |
| Qualcomm (ex-TDK) B39242B7520P810 | 1.8 dB [LCSC] | 22–38 dB [LCSC] (datasheet font-encoded, not parsed) | – | – | 1.1×0.9 mm | C5950078 | $0.35 | 1468 |

Compared with the assumption in section 3 of the signal-chain analysis (10/25/35/45 dB at 60/100/150/250 MHz): SAFEA gives more rejection at −100 MHz (37–44 dB) but **less at ≥ +250 MHz (30–37 dB)**. For the LO-leakage estimate, use 30 dB at offsets of 250 MHz and above.

## 8. RFFC5072 (mixer + LO synthesizer)

| Ordering code | Source | Price | Stock | Status |
|---|---|---|---|---|
| **RFFC5072TR13** | LCSC C3034742 | **$16.39 (1+), $15.62 (10+), $13.10 (100+)** | **22** | listed |
| RFFC5072 | Qorvo store (store.qorvo.com/…/416380) | $28.26 (1–24), $22.19 (25–99), $17.51 (100–249) | 262; 1708 + 2500 due 2026-11-19/20 | "Standard", no current notices |
| RFFC5072A | Qorvo store (…/458068) | $41.79 (1–24), $32.82 (25–99), $25.89 (100+) | 2506 | "Standard", no notices |
| RFFC5072ATR13 | LCSC C38057303 | $26.61, $10.62 at 200+ | 0 | |
| RFFC5071 / RFFC5071A | LCSC | – | 0 | |
| RFFC5072SR | Mouser | – | – | flagged End-of-Life (per search snippet) |

- **The cheapest legitimate source is LCSC at $15.62 (10+).** Its 22 parts are enough for 5 boards.
- The base part is not NRND on Qorvo's own store (the store now reads "Qorvo, part of Skyworks").
- Broker listings (Chip Stock 4509 pcs, Vyrian 381) were seen on findchips. Their prices were not listed and the parts are unverified.

## 9. ESP32-S31

| Item | Source | Price | Stock | Note |
|---|---|---|---|---|
| **ESP32-S31NRV16** (16 MB in-package Octal PSRAM, QFN80 8×8, **0.35 mm pitch**) | LCSC C55601453 | **$5.81 (1+), $5.01 (10+), $4.12 (100+)** | **0** | The part has to come through JLC global sourcing or a pre-order. Lead time and fee are unverified. |
| ESP32-S31NRV32 | JLC placeholder only | – | 0 | |
| ESP32-S31-WROOM-3 / -3U / -1 / -MINI-1 | JLC global-sourcing placeholders only | unverified | 0 | Not stocked at LCSC. A module's RF can't be routed into our IF chain (the U variant has a u.FL), so it doesn't fit this design. |

- **External SPI flash is required** [Espressif DS]. GigaDevice GD25Q32ESIGR (4 MB, SOP-8, C2832998) costs $0.72 at 10+ with 26465 in stock. Winbond W25Q128JVSIQ (C97521, basic) costs $2.01 at 10+.
- An **external 40 MHz clock is supported**: drive XTAL_P and leave XTAL_N floating [Espressif DS]. That means one TCXO can feed both the ESP32 and the RFFC5072, as planned.

## 10. 40 MHz TCXO (clipped sine, ±0.5 ppm, 3.3 V)

| Part | Stability | Output | Supply | Package | LCSC # | 10+ / 100+ | Stock |
|---|---|---|---|---|---|---|---|
| **Epson TG2520SMN 40.000000 MHz MCGNNM = X1G0054210307 (recommended)** | ±0.5 ppm initial (±1.5 ppm after 2 reflows), **±0.5 ppm over −40…+85 °C**, ±0.5 ppm/yr [DS] | clipped sine ≥ 0.8 Vpp into 10 kΩ ∥ 10 pF, needs an external DC-block | 2.66–3.465 V, 1.8 mA | 2.5×2.0 | C3007519 | $0.33 / $0.23 | 5288 |
| HCI 8132S-40.000NQ33FTL | ±0.5 ppm [LCSC/DS family] | clipped sine 0.8 Vpp | 3.3 V | 3.2×2.5 | C19674261 | $1.38 / $1.04 | 1184 |
| ECS-TXO-25CSMV-400-BN-TR | ±1 ppm | clipped sine | 1.7–3.465 V | 2.5×2.0 | C2594506 | $2.89 | 20 |

Fan-out: one 10 kΩ ∥ 10 pF output has to drive both RFFC REF_IN (0.5–1.5 Vpp, AC-coupled) and ESP32 XTAL_P. Check the ESP32's XTAL_P input amplitude spec. A small buffer, or a resistive split, may be needed (see open issues).

## 11. GbE PHY + magjack

**Espressif's ESP32-S31-Function-CoreBoard-1 uses a Motorcomm YT8531DC-CA with a 25 MHz crystal.** This comes from the schematic `esp32-s31-function-coreboard-1-schematics.pdf`, now in the datasheet folder. ESP-IDF notes that this PHY needs auto-negotiation re-enabled after reset and RGMII delay tuning. ESPHome PR #17277 adds YT8531 RGMII support for the S31.

| Part | Package | LCSC # | 10+ / 100+ | Stock | Note |
|---|---|---|---|---|---|
| **Motorcomm YT8531DC-CA (recommended: matches Espressif's reference and firmware)** | QFN-40 5×5 | C47544379 | $1.24 / $0.94 | 3422 | |
| Realtek RTL8211F-CG | WQFN-40 5×5 | C187932 | $1.03 / $0.79 | 50814 | cheapest |
| Realtek RTL8211F-VD-CG | QFN-40 | C19100357 | $1.31 / $0.99 | 2485 | |
| **HanRun HR911130C magjack (10/100/1000, integrated magnetics, LEDs)** | THT | C50933 | $2.44 / $1.80 (87+) | 7767 | THT: hand-solder fee applies |
| HanRun HR911130A | THT | C54408 | $2.20 / $1.74 | 19842 | |

## 12. LDOs

| Rail | Part | Key specs | LCSC # | Price | Stock |
|---|---|---|---|---|---|
| (a) 5 V → 3.3 V digital, ~600 mA | **AMS1117-3.3 (JLC basic)** | 1 A, 1.1 V dropout @800 mA, SOT-223 | C6186 | $0.21 (1+), $0.16 (50+) | 1.57 M |
| | Diodes AP7361C-33ER-13 (better PSRR, 75 dB) | 1 A, 340 mV dropout, SOT-223R | C3743528 | $0.48 / $0.37 | 1474 |
| (b) Low noise 3.3 V (or 3.0 V) 200 mA for the RFFC5072 | **TI TPS7A2033PDBVR** (3.0 V: TPS7A2030PDBVR C963429, 18135 in stock) | 300 mA, 7–10 µVrms, 140 mV dropout, SOT-23-5 | C2862740 | $0.21 (1+), $0.16 (50+) | 116624 |
| | TI LP5907MFX-3.3/NOPB | 250 mA, 6.5–10 µVrms, SOT-23-5 | C80670 | $0.16 (1+), $0.13 (50+) | 67057 |
| | onsemi NCP167AMX330TBG | 700 mA, 8.5 µVrms, XDFN 1×1 (leadless, so X-ray fee) | C603662 | $0.47 | 2578 |
| (c) LNA / gain-block rail | **TI TPS7A2045PDBVR (4.5 V)**; TPS7A2042 (4.2 V) as an alternative | 300 mA, 10 µVrms, 140 mV dropout, so it regulates down to VBUS ≈ 4.65 V | C2873627 | $0.23 (1+), $0.19 (50+) | 7274 |

- **Thermal check for (a):**
  - At the full 0.6 A budget the regulator drops (5.0 − 3.3) × 0.6 = 1.0 W. In SOT-223 (θJA ≈ 60–90 °C/W with a good pour) that is a 60–90 °C rise, which is marginal.
  - The realistic load is ESP32 Wi-Fi RX + CPU + PHY at 1000BASE-T + flash, estimated at 300–450 mA (not yet checked against datasheets). That gives 0.5–0.8 W, which is acceptable with a 4-layer ground pour.
  - Mitigations: a 0.5–1 Ω 1206 series resistor ahead of the LDO to take 0.3–0.5 W, or split the PHY onto its own SOT-223.
- **(c) Supply the LNAs from an LDO, not raw VBUS:**
  - USB host VBUS carries switching ripple (tens of mV), and LNA PSRR is poor, so the ripple would become AM sidebands.
  - PSA4-5043+, QPL9503, QPL9547 and SKY67183 are all specified to 3.0–3.3 V minimum and work at 4.5 V (OIP3 drops slightly).
  - **GVA-63+/GVA-62+ are specified at 4.8–5.2 V at the device.** Either feed the gain block from VBUS through a ferrite + LC π-filter, or accept a reduced bias current at 4.5 V.

## 13. RF ESD (SMA input, < 0.3 pF)

| Part | C | Package | LCSC # | Price | Stock |
|---|---|---|---|---|---|
| **KUU KLXES15AAA1 (recommended; clone of Murata LXES15AAA1)** | 0.05 pF | 0402 | C2892490 | $0.017 | 135646 |
| Leiditech LXES15AAA1-153 | 0.05 pF | 0402 | C5210978 | $0.035 (100+) | 23741 |
| TECH PUBLIC LXES15AAA1-133 | 0.05 pF | 0402 | C19829536 | $0.028 | 18326 |

- HackRF One uses the Murata LXES15AAA1-100 at its antenna port. The genuine Murata part is no longer listed at LCSC.
- 0.05 pF is 530 Ω at 6 GHz, so the added loss is under 0.05 dB.
- These are gap-type suppressors with a high trigger voltage. Keep the DC-block cap and rely on the LNA's own ESD rating as a second stage.

## 14. Edge-launch SMA (1.6 mm board, 6 GHz)

| Part | Type | LCSC # | 10+ / 100+ | Stock |
|---|---|---|---|---|
| **BAT WIRELESS BWSMA-KE-P001 (recommended)** | SMD edge/board-side, offset pin | C496550 | $0.32 / $0.23 | 92289 |
| BAT WIRELESS BWSMA-KE-Z001 | THT edge, rated 6 GHz [LCSC] | C496549 | $0.31 / $0.22 | 153455 |
| DreamLNK SMA-KE-P901 | edge, rated 6 GHz [LCSC] | C914556 | $0.63 / $0.46 | 457 |

Check the slot width against 1.6 mm, and check the 6 GHz return loss of the P001 footprint. Only the Z001 and the DreamLNK list a 6 GHz rating.

## 15. Catalog band filters (LTCC), compared against the new spec

Spec:
- LPF: pass 50–1750 MHz, ≥35 dB at 2.38–2.50 GHz, ≥50 dB at 4.8–7.6 GHz.
- HPF: pass 2.95–6 GHz, ≥35 dB at 2.38–2.50 GHz, ≥50 dB below 1.9 GHz.

Data are Mini-Circuits typical tables [DS].

| Part | IL in band | @2.38–2.5 GHz | @4.8–7.6 GHz or <1.9 GHz | Verdict | LCSC # | 10+ | Stock |
|---|---|---|---|---|---|---|---|
| **LFCG-1700+** (LPF, 2×1.2 mm) | 0.91 dB @1.7 GHz (max 1.8) | 43.5 @2.4, 39.2 @2.5 GHz | 53 @4 G, 52.5 @5 G, 41.9 @8 G; spec ≥35 (typ 50) over 2.8–8 GHz | **Best LPF.** It meets the 2.4 GHz spec and is close to 50 dB at 4.8–7.6 GHz. | C4989808 | $4.43 | 61 |
| LFCN-1700+ (LPF, 3.2×1.6) | 0.97 dB @1.74 GHz | 35.0 @2.325, 45.7 @2.5 GHz | 45 @4.5 G, 41 @5.5 G, 44 @6 G, **22.5 @6.9 G, 12.8 @7.5 G (spurious re-entry)** | Fails the 4.8–7.6 GHz spec above 6.5 GHz | C879846 | $2.09 | 228 |
| LFCN-1800+ | 0.86 dB @1.85 GHz | 32.5 @2.45 GHz | 38 @6 G, 33 @7.2 G | Fails | C879884 | $2.32 | 73 |
| LFCN-1575+ | 0.76 @1.575, 2.3 dB @1.875 GHz (cut-off too low for 1.75 GHz) | 35 @2.2, 41.8 @2.5 GHz | 43 @5 G, 37 @6 G, 35 @6.8 G, 20.7 @7.2 G | Fails at both ends | C4989723 | $4.06 | 6 |
| HFCN-3100+ (HPF) | 2.22 dB @3.1 GHz, 6.2 dB @2.92 GHz, 1.0 @3.4 GHz, 0.66 @5 GHz | 40 @2.45, 33.4 @2.5 GHz | 54 @1.81 GHz | Corner too high for 2.95 GHz | C3008194 | $3.18 | 44 |
| HFCN-2700+ (HPF) | 1.04 @2.9, 0.9 @3.0, 0.89 @5.7, 1.85 @6.5 GHz | **7.1 @2.35, 3.9 @2.5 GHz** | 48.6 @1.5, 29.6 @1.8 GHz | Fails the 2.4 GHz spec | C4990121 | $2.41 | 12 |

- **No catalog LTCC HPF meets both "low IL at 2.95 GHz" and "≥35 dB at 2.5 GHz".** That is an 18 % transition band, which needs a high-order elliptic filter.
- A lumped 0402 design on FR4 will lose about 1.5–3 dB at 2.95 GHz to get there. Either relax the spec to about 25 dB at 2.5 GHz (the IF-feedthrough path also has the SAW and mixer RF→IF isolation behind it), or move the HB lower edge up to about 3.1–3.2 GHz.

---

## Signal-chain parameters that change (versus section 2 of the analysis)

| Stage | Assumed | Selected part (datasheet) | Effect |
|---|---|---|---|
| LNA_LB | SPF5189Z: 23→13.8 dB, NF 0.55–0.8, OIP3 +38.5 | PSA4-5043+: 18.4 dB @1 GHz, NF 0.75–0.98, OIP3 +33.5, OP1dB +21 | Similar; about 5 dB lower OIP3. QPL9547 instead gives +3–6 dB gain and OIP3 +39. |
| LNA_HB | 18→15 dB, NF 1.1–1.5, OIP3 +25 | QPL9503: 21.6 dB, NF 0.9, OIP3 +35.5 (flat 3–6 GHz) | **HB system NF improves several dB.** HB without the gain block is now viable. |
| SPDT | 0.4 / 0.6–0.9 dB | BGS12P2L6: 0.2–0.31 dB below 2.7 GHz, 0.51 @5.9 GHz; IIP3 +74 | About 0.3 dB better. Note there are now two SPDTs in the chain. |
| Gain block | 16 / 15 / 12 dB, OIP3 +32…+25 | GVA-63+: 21.9 / 19.9 / 15.9 dB, NF 3.6–4.6, OP1dB +18.7…+11.8 | **4–6 dB more gain, so the mixer compresses earlier** (input P1dB about 5 dB lower). Use GVA-62+ (16.5→14.5 dB) to stay close to the original plan. |
| 1:2 balun | −1.0 / −1.2…−1.8 | TCM2-63WX+: 0.9 typ ≤ 4 GHz, **2.5 typ at 5–6 GHz** | HB top end about 0.7 dB worse |
| SAW | −2.5 dB, 25 dB @100 MHz, 45 dB @250 MHz | SAFEA: 2.3–2.8 dB; 37–44 dB @−100 MHz; **30–37 dB ≥ +250 MHz** | Update the LO-leakage numbers |
| HB filters | lumped | LTCC can't meet the 2.5 GHz rejection | see slot 15 |

---

## BOM cost roll-up (RF + digital core, per board, components only)

Full architecture, using LCSC prices:

| Block | qty 10 (10+ break) | qty 100 (100+ break) |
|---|---|---|
| RF: SMA×2, ESD, SPDT×2, PSA4-5043+, QPL9503, 0402 filters, GVA-63+, H3-TCM2-63WX+, RFFC5072, BD2425, SAW, TCXO | $29.99 | $24.69 |
| Digital: ESP32-S31NRV16, GD25Q32, YT8531DC + 25 MHz, HR911130C, USB-C + ESD, 3 LDOs, misc passives | $11.23 | $8.72 |
| **Total components** | **$41.2** | **$33.4** |

The RFFC5072 alone is $15.6, which is 38 % of the total.

## Budget check: < $50 per board at qty 5, PCB and JLC assembly included

JLC fees (jlcpcb.com/help/article/pcb-assembly-price, dated 2026-10-22; capabilities page):
- **The ESP32-S31 QFN80 has 0.35 mm pitch, and Economic PCBA's minimum is 0.4 mm. Standard PCBA is therefore required.** Standard's minimum board size is 70×70 mm.
- Standard PCBA charges:
  - setup $25.56 and stencil $8.21 per order
  - **feeder loading $1.53 per part type, for basic and extended parts alike**, so the basic/extended distinction no longer saves money
  - X-ray for every QFN/DFN/LGA part: $1.64 each for 1–10 pcs, $0.82 for 11–50, $0.49 for 51–200
  - SMT $0.0016 per joint, manual THT $0.0164 per joint, plus $3.58 hand-solder labour per order
- For comparison, Economic charges setup $8.18, stencil $1.53 and $3.07 per extended part type, but it can't place the QFN80.
- The 4-layer 70×70 mm PCB (5 pcs, JLC04161H-7628 impedance stack) is assumed at about **$15. I could not verify this price.** Check the live quote.

Per board, excluding shipping (script: `analysis/bom_cost.py`; part queries: `analysis/jlc_parts_query.py`):

| Variant | Part types | Leadless parts/board | Components | PCB | Setup + stencil | Loading | X-ray | Joints/THT | **Total @5** | **Total @10** |
|---|---|---|---|---|---|---|---|---|---|---|
| FULL (as architected) | ~50 | 9 | $41.22 | 3.00 | 6.75 | 15.30 | 7.38 | 2.00 | **$75.7** | $59.8 |
| LEAN (cuts below, keeps GbE) | ~34 | 7 | $31.54 | 3.00 | 6.75 | 10.40 | 5.74 | 2.00 | **$59.4** | $46.7 |
| LEAN-USB (LEAN with no GbE; stream over HS-USB at 20 MS/s) | ~28 | 6 | $27.56 | 3.00 | 6.75 | 8.57 | 4.92 | 1.74 | **$52.5** | $41.0 |

If X-ray is charged per part *type* rather than per placement, subtract about $3–4.4 per board at qty 5.

**What breaks the $50 budget at qty 5:**
1. RFFC5072 at $15.6.
2. The fixed JLC Standard-PCBA fees (about $28 per board at 5 boards). That is $34 of setup and stencil plus $1.53 for every unique part, passives included.
3. The second LNA (QPL9503, $5.1).
4. The balun ($2.7, or $8–22 genuine).
5. GbE (PHY + crystal + magjack + part types ≈ $6/board).

**LEAN cuts and their cost:**
- **Single LNA (PSA4-5043+) after SPDT_in instead of two LNAs.** Saves $5.1 plus one part type and one X-ray.
  - HB gets no LNA: NF at 5.8 GHz goes from about 3 dB to about 9 dB (the analysis's "HB, LNA only" row, made worse by the missing LNA).
  - Alternative: put one SKY67183 (0.4–6 GHz, $2.9, only 11 in stock) ahead of SPDT_in. LB then starts at 400 MHz, but both bands keep a 0.5 dB NF LNA.
- **No gain block (0R fitted).** Saves $1.7 and one part type.
  - LB NF goes from about 2.2 to about 4.5 dB at 1 GHz, and HB is worse still.
  - Input IIP3/P1dB improves by about 15 dB, which helps against out-of-band blockers.
  - Keep the footprint.
- **Single-ended mixer drive instead of the 1:2 balun.** Saves $2.7. Expect about 1–3 dB conversion loss, worse IIP2/even-order spurs, and more LO leakage at the antenna port. Keep a balun footprint for rev B.
- **Keep the TCXO.** It costs only $0.33, and the RFFC5072 needs a driven REF_IN anyway. A 40 MHz crystal ($0.10) would only save money on the ESP32 side, and it adds an IF × Δε frequency error.
- **Keep YT8531DC.** RTL8211F saves only $0.21 but breaks parity with Espressif's reference and firmware.
- **Cut unique part types hard.** Every extra passive value costs $0.31 per board at qty 5. Use one decoupling value (100 nF), one DC-block (100 pF), one bulk value (10 µF), and the same SPDT, LDO family and inductor values everywhere.

**What actually fits under $50:**
- **qty 10 boards** (LEAN $46.7, or LEAN-USB $41.0), or
- **qty 5 in LEAN-USB with ≤ 22 part types**, about $49–50.
- At qty 5 *with* GbE, the budget is only reachable if the RFFC5072 is cheaper than LCSC's $15.6 (a grey-market source, at a risk of fakes), or if the user hand-places nothing and JLC charges X-ray per type.

---

## Open issues

1. **ESP32-S31NRV16 shows 0 stock at LCSC** (and the modules are only global-sourcing placeholders). Confirm JLC global-sourcing price and lead time, or pre-order. This is a schedule risk.
2. **The RFFC5072 is the single largest cost.** LCSC has only 22 parts. Buy now if rev A goes ahead. Qorvo direct is $22–28.
3. Confirm with a live JLC quote: the PCB price, whether X-ray is charged per placement or per part type, and the "pre-reflow $0.016/joint" line, which I left out. If it applies to every SMT joint, it adds about $10 per board.
4. **HB HPF spec** (≥35 dB at 2.5 GHz with passband from 2.95 GHz) is not met by catalog LTCC. Decide between a high-order lumped design (with its loss cost), relaxing the spec to about 25 dB, or raising the HB edge.
5. The GVA-63+ gain is 4–6 dB above the cascade assumption. Re-run `cascade.py` with the datasheet numbers, or choose GVA-62+.
6. One TCXO driving both RFFC REF_IN and ESP32 XTAL_P: check the XTAL_P amplitude/DC-bias requirement. A buffer or resistive splitter may be needed.
7. BD2425N50200AHF: check its DC-feed pin and its footprint (0404). Only 25 are in stock. The fallback is a lumped LC balun plus chokes.
8. Clone parts (H3-TCM2-63WX+ balun, KLXES15AAA1 ESD) have no verified RF data. Measure on rev A, and keep a footprint that fits the genuine Mini-Circuits DB1627 / Murata part.
9. PSA4-5043+ is specified only to 4 GHz. In LEAN it also has to serve 4–6 GHz, so its gain and NF there are unverified.
10. The AMS1117 thermal margin depends on the real ESP32 + PHY current. Measure it, or split the rails.
11. Mouser/DigiKey prices are unverified (automated access blocked).

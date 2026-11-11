# Decisions log

| Date | # | Decision | Notes |
|---|---|---|---|
| 2026-11-09 | D1 | ~~Diplexer at antenna~~ → revised same day: SPDT_in → per-band LNA → post-LNA 0402 LC filter (LPF 1.75 / HPF 2.95 GHz) → SPDT_out; GPIO controlled | user worried about lumped-filter Q/loss on FR4 ahead of the LNA |
| 2026-11-09 | D2 | Keep high band 2.95–6 GHz | add optional application-BPF footprint in HB |
| 2026-11-09 | D3 | Wideband gain block fitted, with 0R bypass footprint | decide population after rev A measurements |
| 2026-11-09 | D4 | Mixer input: wideband 1:2 transformer balun | |
| 2026-11-09 | D5 | Power: USB-C 5 V only; linear regulators OK | no PoE |
| 2026-11-09 | D6 | IF 2441 MHz (2.4 GHz ISM SAW), RFFC5072 single mixer, mixer/native select by 0R 3-pad tee | from analysis recommendations, not objected to |
| 2026-11-09 | D7 | Very cost sensitive: ESP32 hack only worthwhile if far cheaper than an AD9361/AD9363 design; cost is the first criterion for every part | lumped 0402 filters instead of LTCC; revisit balun, HB LNA, gain block, RFFC5072 with real prices |
| 2026-11-09 | D8 | Budget: BOM < $50 per board incl. PCB + JLC assembly, at build qty 5 | count JLC extended-part loading fees; prefer basic parts; reuse parts across slots |
| 2026-11-09 | D9 | Optional external reference input (DNP): edge SMA + DC block + 49.9 R termination + 0R select (TCXO vs EXT) into RFFC5072 REF_IN (10–104 MHz, 0.5–1.5 Vpp); second DNP 0R to route a 40 MHz ext ref to ESP32 XTAL_P | zero placement cost; footprints only |
| 2026-11-09 | D10 | Keep one cheap 40 MHz TCXO (Epson TG2520SMN ±0.5 ppm, $0.33) shared by ESP32 XTAL_P and RFFC REF_IN | RFFC needs an oscillator anyway; TCXO ≈ XO price; avoids ±60–120 kHz error/drift at 5.8 GHz |
| 2026-11-09 | D11 | Hybrid assembly: JLC places hard parts (QFN/DFN/LGA, tiny RF parts, 0402 RF passives); user hand-solders 0603+, SOT/SOIC/QFP, connectors | user request; design rule: every non-RF passive in 0603+ to minimise JLC part types |
| 2026-11-09 | D12 | Accept hybrid build of the full design at ≈$62–71/board @5 (≈$52–56 @10), over the $50 target | user choice; still ~10x below AD9361-class |
| 2026-11-09 | D13 | HB lower edge raised to 3.1 GHz; lumped elliptic HPF with transmission zero on 2.40–2.48 GHz | relaxes HPF transition; 2.95–3.1 GHz loss is mostly radar |
| 2026-11-09 | D14 | Add mid band (MB) 1.75–2.15 GHz: shares LNA_LB (PSA4-5043+), low-side LO = IF − RF (290–690 MHz), lumped 0402 BPF with notch on IF; band switches become SP3T ×2 | closes the 1.75–2.15 GHz gap (cellular B1/B2/B3/B25/B66, DECT); ≈ +$3/board |
| 2026-11-10 | D15 | (proposed, under analysis) Split into Board A (WROOM-3U, power, GbE, USB) + Board B (RF front end) joined by 90° 2x10 header + U.FL IF cable; no fab until stock is available | user request; see SPLIT_ARCHITECTURE.md |
| 2026-11-10 | D16 | Board A assembled in house, option A1 (stencil + hotplate/hot-air reflow for module + PHY; rest by iron) | user |
| 2026-11-10 | D17 | Board B assembled by JLC (Standard PCBA, hybrid per D11: JLC places hard/0402 parts, 0603+/connectors by hand); keep minimizing part types | user |
| 2026-11-10 | D18 | Board A module: ESP32-S31-WROOM-1U (castellated + 29 inner pads; reflow) | user |
| 2026-11-10 | D19 | Boards mate edge-to-edge coplanar via right-angle 2x10 2.54 mm header pair + U.FL IF patch cable | user |
| 2026-11-10 | D20 | Board B keeps a DNP 0R option: ESP32-synthesised 40 MHz -> RFFC REF_IN (TCXO default) | user |
| 2026-11-10 | D21 | Board A: drop RGMII TX 33R series resistors (R202–R207); TX routed direct from the module to the PHY. RX 33R kept at the PHY (the RX source) | reference places them "next to ESP32 pins" (source termination), impossible with the WROOM-1U's inner RGMII pads; at the PHY (receiver end) they add nothing and blocked the MDIO/MDC/RST escape. S31 GPIO drive strength sets the TX edge rate. Agent decision under the routing go-ahead |
| 2026-11-10 | D22 | PCB process held to JLC basic 4-layer (no surcharge): 0.45/0.2 mm vias, 0.1/0.1 mm track/space, 0.2 mm hole-to-copper, 0.2 mm copper-to-edge; In1 = solid GND (no routing), In2 routable | user |

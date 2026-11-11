# PCB layout status (2026-11-10)

## Generated board
- Generator: `design.py` holds the netlist and BOM data for 253 parts and 185 nets. `footprints.py` builds the custom footprints (ESP32-S31 QFN-80 0.35 mm, BGS13SN8, BD2425, HR911130C). `build_pcb.py` with `placement.py` does placement and scripted RF routing. Run it with `python3 build_pcb.py`.
- `esp32_sdr.kicad_pcb` is 70×70 mm, 4 layers (JLC04161H-3313), and opens in KiCad 10. Design rules are in `esp32_sdr.kicad_pro`: 0.1 mm clearance, 0.127 mm tracks, 0.45/0.2 mm vias.
- **Placement is complete and DRC-clean.** There are 0 shorts and 0 clearance violations. Remaining warnings are the edge-launch SMA pads at the board edge, which is inherent, plus silk and courtyard cosmetics.
- **The RF chain is fully routed by script.** It runs from the SMA, ESD and SP3T, through three LNA+filter branches, the SP3T, the gain block with its 0 Ω bypass, the balun and the RFFC5072, then the BD2425, the SAW, the 0 Ω tee and 3 dB pad, and the CLC match into ESP32 pin 1. The SMA_NAT tee is included. All RF lines are 0.19 mm 50 Ω microstrip, the filter ladders exactly match the EM models, and In1.Cu is voided under every RF-filter 0402.
- Planes: In1.Cu is solid GND (with the RF voids). In2.Cu is GND under the RF area and 3V3 under the digital area. F.Cu and B.Cu get GND pours.

## Routing of the digital/power section: NOT finished
- Freerouting (external Java tool) was downloaded to `~/tools/freerouting/`, but **running it was blocked by the permission system**. It is waiting for your OK.
- I wrote a fallback maze router (`router.py`, `router2.py` with rip-up). Its best result, `esp32_sdr_routed_v2.kicad_pcb`, routes about 90 % of connections but has 41 nets incomplete and about 140 clearance violations under 0.09 mm from grid discretisation. **It is a reference only. Do not fabricate it.**
- One-command path once Freerouting is allowed:
  ```
  python3 fr_route.py export        # locks footprints + RF tracks, writes fab/esp32_sdr.dsn (outer pours removed; In1/In2 planes kept)
  ~/tools/freerouting/jdk-21.0.13+9-jre/bin/java -jar ~/tools/freerouting/freerouting.jar -de fab/esp32_sdr.dsn -do fab/esp32_sdr.ses -mp 30
  python3 fr_route.py import        # imports SES, re-adds outer GND pours, fills zones, DRC -> fab/drc_fr.rpt
  ```
  You can also open `fab/esp32_sdr.dsn` in the Freerouting GUI yourself.
- After routing:
  - generate Gerbers and drill files with `kicad-cli pcb export gerbers/drill`,
  - regenerate the CPL with `python3 bom.py esp32_sdr_fr.kicad_pcb`,
  - get a live JLC quote.

## BOM / CPL (`hw/fab/`, `python3 bom.py <board>`)
- `BOM_JLC.csv` and `CPL_JLC.csv` cover the JLC-placed parts: 178 placements, **59 part types**.
- `BOM_HAND_LCSC.csv` lists the hand-solder kit: 63 parts, 37 types.
- `BOM_DNP.csv` lists the 12 option footprints: native-path tee, ext-ref input, gain-block bypass, tune caps.
- `BOM_FULL.csv` has everything.
- Every placed part has an LCSC number. RF filter caps are Murata GJM1555 W/B grade; inductors are LQW15AN, plus LQG15HS B-grade for 1.0 and 2.0 nH.

## Cost update
- At $1.53 per JLC part type, the 59 types cost about $18/board in loading fees at qty 5. The estimate becomes **≈ $75/board @5, ≈ $60 @10**, compared with the earlier ≈ $62 @5 that assumed 24 types.
- **Proposed next cut:** move non-RF 0402 passives to 0603 and solder them by hand, following your "0603+ is easy" rule. Candidates are the RGMII 33 Ω resistors, PHY straps, RBIAS, the RFFC loop filter, control-line RCs and pull-ups, roughly 12–15 types. That saves about $4–5/board @5. It needs a re-place/re-route, which is cheap once Freerouting is available.

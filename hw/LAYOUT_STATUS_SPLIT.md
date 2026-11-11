# Two-board layout status (2026-11-10)

Status: **both boards placed, routed and DRC-checked**. Nothing is ordered; stock is still unavailable, so this is analysis only (D15).

| | Board A: base | Board B: RF front end |
|---|---|---|
| Size / stack | 62 × 46 mm, JLC04161H-3313 4L | 62 × 40 mm, same stack |
| Parts | 67 (61 fitted, 6 DNP), 31 types, **all in-house** (A1: stencil + hotplate for module/PHY, rest by iron) | 160 (95 JLC-placed, 45 JLC types; 52 hand 0603+/connectors; 13 DNP) |
| Layers | F: parts + signals · In1: **solid GND, no routing** · In2: 3V3 pour + signals · B: GND pour + signals | F: RF chain + parts · In1: **solid GND** (voids under RF 0402 pads per EM model) · In2: GND pour + signals · B: GND pour + signals |
| Routing | Freerouting (sandboxed, D22 rules) + scripted RGMII lanes / module escapes + 1 post-route fix | Freerouting (sandboxed) + 3 scripted fixes (mixer VDD pins, LDO GND pin, J7 5V0 strap) |
| Stitching | 127 GND vias (3 mm grid + edge row) | 234 GND vias (2.5 mm grid + 2 mm edge fence) |
| DRC (KiCad, JLC basic rules) | **0** unconnected / shorts / clearance / hole-clearance | **0** unconnected / shorts / clearance / hole-clearance |
| Remaining DRC flags (accepted) | silk only | 10 copper-edge (edge-launch SMA pads by design), 75 courtyard overlaps (RF ladders at EM-model spacing), silk |
| Fab outputs | `board_a/fab/`: Gerbers+drill zip, BOM_A_kit, CPL_A, DNP list, layer PDFs | `board_b/fab/`: Gerbers+drill zip, BOM_B_JLC + CPL_B_JLC, BOM_B_HAND_LCSC, DNP list, layer PDFs |

## Process rules (D22, JLC basic 4-layer, no surcharge)
- Vias: 0.45 mm pad / 0.2 mm drill everywhere. Footprint thermal vias are 0.5/0.2 (PHY, mixer EP) and 0.5/0.3 (module).
- Track/space: 0.1 mm netclass clearance. Minimum track is 0.15 mm; PWR netclass (5V0, VBUS, 3V3, 3V0_RF, VLNA_*, VGB) is 0.3 mm.
- Hole-to-copper ≥ 0.2 mm, copper-to-edge ≥ 0.2 mm (`esp32_sdr.kicad_pro`).
- Checked on the final boards: no tracks on In1, and no via outside the no-surcharge range.

## Board A design notes
- **RGMII.** The module's inner pads fan out to vias. Module→resistor lanes are scripted (`placement_a.rgmii_lanes`): TX on B.Cu, RX on In2, with lane order chosen so nothing crosses.
  - Intra-group length spread: TX 27–35 mm, RX 44–53 mm including the PHY side. That's ~7–8 mm, ≈50 ps, far inside RGMII-ID tolerance.
  - **D21:** TX 33 Ω resistors removed. The reference places them at the MAC, which is impossible under the module, and at the PHY they're useless. RX 33 Ω are kept at the PHY, which is the RX source.
- **PHY.** Decoupling sits at the pins (3 corners + a VDDL column), RBIAS is 1.5 mm, and XI/XO are 6–8 mm. MDI pairs run 5–8 mm to the magjack.
- **Mounting holes.** H4 moved to (31.5, 3) and H3 to (58.6, 43.4) to clear U6/J201/U5.

## Board B design notes
- **RF chain.** Pre-routed and locked exactly as in the EM model (filters, 50 Ω lines, L2 voids); the autorouter never touched it.
- **Loop filter.** The RFFC5072 loop filter (C380–C383, R380–R382) is pinned as a 3×3 cluster next to U3 pins 6–8. Auto-placement had scattered it (LF_B was 61 mm with 3 vias). After re-routing, every LF net is 5.5–12.4 mm, F.Cu only, with no vias.
- **Scripted fixes** (`fr2.FIXUPS`):
  - U3 pins 19/22 (3V0_RF) are joined under the NC pins 20/21 and taken to a via.
  - U12 GND pin 2 escapes under the SOT-23 body to a via.

## Before ordering (open items)
1. **USB HS pair (A):** autorouted with DM 57 mm / DP 70 mm and 4 vias on DP. That's 13.5 mm skew (≈90 ps, at the USB 2.0 HS limit) and not impedance-controlled. Re-route it as a coupled 90 Ω pair with KiCad's diff-pair router, or accept full-speed USB only. Ethernet is the primary data path.
2. **MDI pairs (A):** short, but P/N length differs by up to 3.4 mm and they're not coupled. Tidy with the diff-pair router; optional.
3. **Silkscreen:** about 250 silk-overlap/silk-over-pad flags on each board. Gerbers are exported with `--subtract-soldermask`, so silk is clipped from pads, but refdes text overlaps. Tidy or move refs to Fab and use the assembly PDFs.
4. **JLC DFM/CPL preview (B):**
   - Check part rotations in JLC's viewer (QFN/SOT rotation offsets).
   - Confirm they accept 0402s at the EM-model 0.3 mm pad gaps (the courtyard overlaps).
5. **Sourcing:** U1 (WROOM-1U) has no LCSC listing and LCSC shows 0 stock for the S31; the RFFC5072 shows 22. Recheck before ordering.
6. **40 MHz reference stub (B):** REFCLK_RF is 43 mm with 3 vias because the DNP option 0 Ω parts R704 (ext-ref SMA) and R708 (ESP32 clock) sit at the south edge. With them unfitted, that's a dangling stub on the RFFC reference input and could pick up reference spurs. Move R704/R708 next to R701/C384 so the stub is ≤ 3 mm and the long runs sit on their own option nets, then do an incremental re-route (`fr2.py B cont-export` with a move).
7. **Optional re-check:** re-run Sonnet on the final routed RF regions. Stitching vias were kept clear of the In1 voids, and the RF copper is unchanged from the EM model.

## Flow (reproducible)
```
cd hw
python3 fr2.py A|B export            # pcb2 build (no outer pours), lock pre-routes + FIXUPS, DSN (In1 plane-only, 0.45/0.2 via)
bash run_freerouting.sh <unit> board_x/esp32sdr_x.dsn board_x/esp32sdr_x.ses board_x/freerouting.log   # sandboxed: no network, 3 GB cap
python3 fr2.py A|B import            # SES -> *_routed.kicad_pcb + outer GND pours + JLC rules
python3 stitch.py board_x/esp32sdr_x_routed.kicad_pcb 2.5|3.0 --edge-pitch 2.0|3.0
python3 fr2.py A post                # post-route fixes (A)
kicad-cli pcb drc --refill-zones --save-board -o board_x/drc_routed.rpt board_x/esp32sdr_x_routed.kicad_pcb
python3 rm_dangling.py board_x/esp32sdr_x_routed.kicad_pcb board_x/drc_routed.rpt [--include-locked]
bash fab_export.sh a|b ; python3 bom2.py A|B ; python3 render_routed.py board_x/esp32sdr_x_routed.kicad_pcb out.png
```
`python3 fr2.py X cont-export` / `cont-import` run an incremental pass that keeps the router wires, applies FIXUPS and rips the listed nets. Freerouting was audited statically (`claude_notes/FREEROUTING_AUDIT.md`): not malicious, but it phones home for update checks, so always run it via `run_freerouting.sh`.

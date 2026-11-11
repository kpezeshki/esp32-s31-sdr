# ESP32-S31 SDR

A low-cost, receive-only, general-purpose SDR. It uses the ESP32-S31's raw I/Q streaming (community "esp-sdr" firmware: continuous 8-bit I/Q at 40 MS/s over gigabit Ethernet) behind a wideband mixer front end.

```
Board B (RF):   SMA ─ ESD ─ SP3T ─┬─ LB: PSA4-5043+ ─ LPF 1.75 GHz ─┐
                                  ├─ MB: PSA4-5043+ ─ BPF 1.75–2.15 ─┤─ SP3T ─ GVA-62+ ─ balun ─ RFFC5072 ─ 2.44 GHz SAW ─ pad ─ U.FL
                                  └─ HB: HPF ─ QPL9503 ─ HPF 3.1 GHz ┘
Board A (base): U.FL ─ ESP32-S31-WROOM-1U (raw I/Q) ─ RGMII ─ YT8531 ─ RJ45 (GbE);  USB-C;  2×10 header → Board B
```

Coverage:

| Band | Range | LO |
|---|---|---|
| LB | 50–1750 MHz | IF+RF |
| MB | 1750–2150 MHz | IF−RF |
| HB | 3.1–6 GHz | RF−IF |
| Native ESP32 (Board A alone) | 2.15–2.8 GHz | none |

The IF is 2440 MHz (61 × 40 MHz).

**Design report** (board renders, copper layers, simulated filters / noise figure / dynamic range, priced BOM, cost per board): [`docs/report/index.html`](docs/report/index.html). It can be served with GitHub Pages from `/docs`.

## Status (2026-11)
- Both boards are placed, routed and DRC-clean to the JLC basic 4-layer process (JLC04161H-3313 stack, 0.45/0.2 mm vias, 0.1/0.1 mm track/space).
- Gerbers, BOM and CPL are in `hw/board_{a,b}/fab/`.
- **Not yet fabricated or measured.** All performance numbers are simulated:

| | LB | MB | HB |
|---|---|---|---|
| Simulated NF | 1.4–2.1 dB | 2.5–3.1 dB | 2.2–3.0 dB |

- Instantaneous dynamic range is ≈44 dB in 40 MHz, limited by the 8-bit ADC.
- Cost: about $87 per system at qty 5, about $68 at qty 10. That is from LCSC prices; the PCB and shipping figures are estimates.
- Before ordering: run a JLC CPL/DFM preview, and check stock for the ESP32-S31 module and the RFFC5072.

## Repository layout
| Path | What |
|---|---|
| `SIGNAL_CHAIN_ANALYSIS.md`, `PART_SELECTION.md`, `RISK_RESEARCH.md`, `COST_PLAN.md` | Analysis: cascade and power levels, frequency plan and spurs, parts, risks, cost |
| `DECISIONS.md` | Decision log (D1–D22) |
| `SPLIT_ARCHITECTURE.md` | Why there are two boards (A: base / B: RF) and the header pinout |
| `analysis/` | Python models: cascade, frequency plan, lumped filter synthesis, cost |
| `em/` | Sonnet EM models of the 0402 filter layouts. EM-in-the-loop optimisation and Monte Carlo (`em/EM_REPORT.md`, `em/filters/FINAL_FILTERS.md`). `RLM_LICENSE` must be set to run Sonnet |
| `hw/design2.py` | Netlists for both boards (`build_a`, `build_b`) |
| `hw/placement_a.py`, `hw/placement_b.py` | Placement and scripted routes. Board A: module escapes, RGMII lanes, USB HS pair. Board B: RF chain exactly as EM-modelled |
| `hw/pcb2.py`, `hw/build_pcb.py`, `hw/footprints.py` | KiCad 10 board generation (pcbnew Python) and custom footprints (`hw/esp32_sdr.pretty`) |
| `hw/fr2.py`, `hw/run_freerouting.sh` | Freerouting flow: DSN export/SES import, incremental passes, scripted fixes. Freerouting runs network-isolated (see `claude_notes/FREEROUTING_AUDIT.md`) |
| `hw/stitch.py`, `hw/rm_dangling.py`, `hw/silk_clean.py`, `hw/render_routed.py` | Post-route: GND stitching, cleanup, silk, renders |
| `hw/board_a/`, `hw/board_b/` | KiCad boards (`*_routed.kicad_pcb`), DRC reports, `fab/` outputs, `shots/` images |
| `hw/report/` | Report generators (`cost_boards.py`, `rf_perf.py`, `build_report.py`) |
| `hw/LAYOUT_STATUS_SPLIT.md` | Layout status and open items |
| `hw/esp32_sdr*.kicad_pcb`, `hw/LAYOUT_STATUS.md`, `hw/router*.py`, `hw/fr_route.py`, `hw/bom.py`, `hw/fab/` | Superseded single-board design, kept for reference (replaced by the two-board split, D15) |

## Reproducing the boards
```
cd hw
python3 fr2.py A export && bash run_freerouting.sh fr-a board_a/esp32sdr_a.dsn board_a/esp32sdr_a.ses board_a/freerouting.log
python3 fr2.py A import && python3 stitch.py board_a/esp32sdr_a_routed.kicad_pcb 3.0 --edge-pitch 3.0 && python3 fr2.py A post
kicad-cli pcb drc --refill-zones --save-board -o board_a/drc_routed.rpt board_a/esp32sdr_a_routed.kicad_pcb
bash fab_export.sh a && python3 bom2.py A          # same for B (stitch pitch 2.5, edge 2.0)
```
Requirements:
- KiCad 10 with its Python bindings;
- Freerouting 2.1 and a Java 21 runtime;
- numpy, scipy and matplotlib;
- Sonnet 19 for the EM models.

Most of the design work was done with Claude (Anthropic) as an engineering agent. `claude_notes/` holds its working notes.

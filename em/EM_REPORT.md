# EM simulation report (Sonnet 19, 2026-11-10)

All runs use the JLC04161H-3313 stackup: L1 signal, 0.0994 mm 3313 prepreg (εr 4.1, tanδ 0.02 assumed), and L2 solid GND. Where L2 is voided, L3 GND sits 1.265 mm below through the core (εr 4.5). Scripts are in `em/`, and Sonnet projects and touchstones are under `em/filters/*` and `em/lines/`.

## 1. 50 Ω RF trace (`line_check.py`, `lines/Z0_REPORT.md`)

| Geometry | Z0 | Loss @ 6 GHz |
|---|---|---|
| 0.19 mm microstrip | 50.8 Ω | 0.028 dB/mm |
| 0.19 mm + coplanar GND pour, gap 0.4 / 0.3 / 0.2 / 0.15 mm | 50.7 / 50.6 / 50.4 / 49.8 Ω | 0.028 dB/mm |

The prepreg is thin, so the coplanar pour barely changes Z0. A **0.2 mm pour clearance on RF nets** is fine.

## 2. Band filters: layout EM + component co-simulation

**Method** (`filter_em.py`, `em_opt.py`, `em_robust.py`, `final_palette.py`):
1. Sonnet solves the exact copper of each 0402 ladder (pads, 50 Ω links, ground vias, L2 voids). This is the same geometry code that places the parts on the PCB (`build_pcb.place_ladder`). Every component pad gets an internal (AGND) port.
2. Component models are attached between pad-port pairs, and the result is Kron-reduced to a 2-port. Each evaluation is just matrix algebra, so component values can be optimized with the EM data in the loop.
3. Optimization steps:
   - global search against the EM model, run remotely;
   - tolerance-aware polish using W-grade caps (±0.05 pF) and B-grade inductors (±0.1 nH);
   - a joint palette across the four filters to cut JLC part types (19 values).

**Key layout finding:** on 0.1 mm prepreg each 0402 pad is about 0.13 pF to ground. Without L2 voids under the parts, the high-band pre-filter alone reached 1.9 dB loss and 5 dB RL at 6 GHz. **The PCB therefore voids In1.Cu under every RF-filter 0402**, which keeps the L2-plane rule areas at the pads' 0.1 mm margin.

Final values and metrics: `filters/FINAL_FILTERS.md`. Figure: `figs/filters_em.png`.

| Filter | Passband loss (nominal / MC 95%) | IF 2.40–2.48 GHz rejection (nominal / MC 5%) | Image band rejection |
|---|---|---|---|
| LB LPF 50–1750 MHz (9 parts) | 1.28 / 1.36 dB | 46.1 / 38.2 dB | ≥ 46 dB (4.8–7.6 GHz) |
| MB BPF 1.75–2.15 GHz (14 parts) | 4.1 / 6.1 dB | 34.7 / 25.2 dB | ≥ 39 dB (2.7–3.15 GHz); 27 dB below 1.5 GHz (1×3) |
| HB pre-HPF (3 parts) | 0.37 / 0.41 dB | – | 14 dB below 1 GHz |
| HB HPF 3.1–6 GHz (9 parts) | 2.7 / 3.4 dB | 40.2 / 34.0 dB | ≥ 50 dB (< 1.9 GHz) |

What this means for the system:
- The filters all sit after an LNA, so even the 4–6 dB MB loss adds only about 0.3 dB to system NF. The 2.7 dB HB loss adds about 0.1 dB.
- IF rejection of 25 dB or more keeps strong local 2.4 GHz Wi-Fi (−30 dBm at the antenna) within a few dB of the 40 MHz noise floor, because the mixer's RF→IF feedthrough is about 35 dB below conversion. The 35–46 dB nominal values keep it below the floor.
- The MB filter is the most tolerance-sensitive. Its IF notch can be re-centred at bring-up by swapping C4/C10 (0.5 pF) by ±0.1 pF.

## 3. Not simulated (bring-up items)
- The SMA edge launch, the SP3T/LNA/gain-block interconnects, and the ESP32 CLC match. The match values must be tuned with a VNA in any case, per Espressif.
- Real S-parameters of the parts. Component models use Q=35, Cp=0.07 pF for inductors and ESL=0.15 nH for capacitors. Replace them with Murata/TDK S2P files before a second spin.

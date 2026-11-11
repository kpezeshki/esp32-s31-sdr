# ESP32-S31 SDR board: netlist-ready pinouts and application circuits (T18)

Generated 2026-11-09. The same data is in machine-readable form in `hw/pinouts.json`. Datasheets are in `claude_db/esp32_sdr_datasheets/`, and page numbers refer to the PDF pages. Footprint names are checked against the KiCad 10.0.6 libraries (`/usr/share/kicad/footprints`). **UNVERIFIED** marks values that do not come from a primary document.

## Surprises and action items

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


---

## RFFC5072

- **MPN / mfr:** RFFC5072TR13 (Qorvo (ex-RFMD)); **LCSC:** C3034742
- **Function:** Wideband synthesizer/VCO (LO 85-4200 MHz, frac-N) + one double-balanced mixer (in 30-6000 MHz, out 30-4500 MHz)
- **Source:** claude_db/esp32_sdr_datasheets/RFFC5071_5072_RFMD.pdf (Prelim DS101020): spec p2-3, pin table p4, pinout p6, wideband app schematic p7, 3.7 GHz narrowband app schematic p8, package p19
- **Package:** QFN-32 5x5 mm, 0.5 mm pitch, exposed paddle (body [5.0, 5.0, 0.85] mm)
- **Supply:** VDD 2.7-3.0-3.3 V (abs max 3.6 V); IDD ~100 mA (MIX_IDD=1) / 125 mA (MIX_IDD=6) with 1 GHz LO; 300 uA power-down
- **Logic:** VIH 1.5 V..VDD, VIL <0.5 V (referenced to DIG_VDD) -> 3.3 V ESP32 GPIO OK when DIG_VDD=3.3 V
- **KiCad footprint:** `Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm`
- **Pad-numbering check:** Pads 1-32 CCW from top-left (pin 1 on left side, top), pad 33 = EP 3.7x3.7 -> matches DS p6/p19. Pads 0.8x0.25 at x=+-2.45 cover 0.35 mm leads. Use the _ThermalVias variant or add 3x3 or more GND vias in EP.

| Pin | Name | Function |
|---|---|---|
| 1 | ENBL/GPO5 | Device enable (high=on). Becomes GPO5 if SPI-controlled (SDI_CTRL.sipin=1). |
| 2 | EXT_LO | External LO input - unused (left open on DS eval p7) |
| 3 | EXT_LO_DEC | External-LO decoupling - unused; left open on DS eval p7 (add DNP 33 pF to GND, UNVERIFIED need) |
| 4 | REXT | Bandgap bias resistor: 51 k to GND (LF-noise sensitive) |
| 5 | ANA_VDD1 | Analog supply (synth). Good RF decoupling |
| 6 | LFILT1 | Phase-detector output / loop-filter op-amp input (noise-sensitive) |
| 7 | LFILT2 | Loop-filter op-amp output (noise-sensitive) |
| 8 | LFILT3 | VCO tuning input (noise-sensitive) |
| 9 | MODE/GPO6 | Mode select (path 1/2 register bank in pin mode). GPO6 if SPI-controlled. |
| 10 | REF_IN | Reference input 10-104 MHz, 0.5-1.5 Vpp, AC-coupled (labelled XTALP on eval sheet) |
| 11 | NC | No connect (labelled XTALN on eval sheet, unconnected) |
| 12 | TM | Test mode - connect to GND |
| 13 | NC | MIX1_IPN on RFFC5071; NC on RFFC5072 |
| 14 | NC | MIX1_IPP on RFFC5071; NC on RFFC5072 |
| 15 | GPO1/ADD1 | General-purpose output / MultiSlice address bit 1 (eval: test point) |
| 16 | GPO2/ADD2 | General-purpose output / MultiSlice address bit 2 (eval: test point) |
| 17 | NC | MIX1_OPN on RFFC5071; NC on RFFC5072 |
| 18 | NC | MIX1_OPP on RFFC5071; NC on RFFC5072 |
| 19 | DIG_VDD | Digital supply; decouple at pin |
| 20 | NC | No connect |
| 21 | NC | No connect |
| 22 | ANA_VDD2 | Analog supply (mixer / LO buffers). Good RF decoupling. Also the DC source for the mixer open-collector outputs |
| 23 | MIX_IPP (MIX2_IPP) | Mixer RF input +, 100 ohm differential. NO DC may be applied (AC-couple or transformer) |
| 24 | MIX_IPN (MIX2_IPN) | Mixer RF input -, NO DC |
| 25 | GPO3/FM | GPO / frequency-control input (eval: test point) |
| 26 | GPO4/LD/DO | GPO / lock detect / serial data out (4-wire readback) |
| 27 | MIX_OPN (MIX2_OPN) | Mixer IF output - (open collector). Must get DC from ANA_VDD2 via RF choke or centre-tapped balun |
| 28 | MIX_OPP (MIX2_OPP) | Mixer IF output + (open collector), as pin 27 |
| 29 | RESETX | Async reset, active low. Tie to DIG_VDD if not used |
| 30 | ENX | Serial interface select, active low |
| 31 | SCLK | Serial clock |
| 32 | SDATA | Serial data (bidirectional in 3-wire mode) |
| 33 | EP / GND | Exposed paddle = ground reference; low-impedance vias to GND |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| R_REXT | 51k 1% | 0402 | U.4 REXT ↔ GND | p4 note 3, p7 R1 |
| C_VA1a | 33pF C0G | 0402 | U.5 ANA_VDD1 ↔ GND | p7 C5 |
| C_VA1b | 10nF X7R | 0402 | U.5 ANA_VDD1 ↔ GND | p7 C34 |
| C_VA2a | 33pF C0G | 0402 | U.22 ANA_VDD2 ↔ GND | p7 C2 |
| C_VA2b | 10nF X7R | 0402 | U.22 ANA_VDD2 ↔ GND | p7 C18 |
| C_VDa | 33pF C0G | 0402 | U.19 DIG_VDD ↔ GND | p7 C3 |
| C_VDb | 10nF X7R | 0402 | U.19 DIG_VDD ↔ GND | p7 C19 |
| C_LF8 | 8.2pF C0G | 0402 | U.6 LFILT1 ↔ U.7 LFILT2 | p7 C8 (op-amp feedback, parallel branch) |
| R_LF3 | 22k | 0402 | U.6 LFILT1 ↔ NET_LF_A (to C_LF9) | p7 R3 |
| C_LF9 | 180pF C0G | 0402 | NET_LF_A ↔ U.7 LFILT2 | p7 C9 (R3+C9 in series, LFILT1->LFILT2) |
| R_LF2 | 470R | 0402 | U.7 LFILT2 ↔ NET_LF_B | p7 R2 |
| C_LF10 | 330pF C0G | 0402 | NET_LF_B ↔ GND | p7 C10 |
| R_LF6 | 470R | 0402 | NET_LF_B ↔ U.8 LFILT3 | p7 R6 |
| C_LF17 | 330pF C0G | 0402 | U.8 LFILT3 ↔ GND | p7 C17 |
| C_REF | 10nF C0G/X7R (eval uses 1nF; Epson TCXO wants >=10nF DC-cut) | 0402 | TCXO OUT (or REF select 0R) ↔ U.10 REF_IN | p7 C16=1nF; Epson DS Cc>=0.01uF |
| C_ENBL | 33pF | 0402 | U.1 ENBL ↔ GND | p7 C35 (RC filter per note 1) |
| C_MODE | 33pF | 0402 | U.9 MODE ↔ GND | p7 C36 |
| C_RST | 33pF | 0402 | U.29 RESETX ↔ GND | p7 C1 |
| C_ENX | 33pF | 0402 | U.30 ENX ↔ GND | p7 C13 |
| C_SCLK | 33pF | 0402 | U.31 SCLK ↔ GND | p7 C14 |
| C_SDATA | 33pF | 0402 | U.32 SDATA ↔ GND | p7 C15 |
| R_ser_x4 | 100R-1k series (optional RC with the 33pF, note 1) | 0402 | ESP32 GPIO ↔ U.29/30/31/32 | p4 note 1 (values not given; suggestion) |
| R_RSTPU | 10k (suggestion) | 0402 | U.29 RESETX ↔ DIG_VDD | p4: tie to DIG_VDD if unused; pull-up so a GPIO can still reset |
| R_LED | 220R | 0402 | U.26 GPO4/LD ↔ D_LD anode | p7 R25 |
| D_LD | green LED (lock detect) | 0603 | R_LED ↔ GND | p7 D1; also route LD to an ESP32 GPIO |
| C_TM | - | - | U.12 TM ↔ GND (direct) | p4 |
| C_IN_P / C_IN_N | DC block, 100pF C0G 0402 each leg (our addition: TCM2 Config K windings DC-ground pin 6 and DC-link pin 4 to pin 3) | 0402 | T_IN secondary (pin 6 / pin 4) ↔ U.23 MIX_IPP / U.24 MIX_IPN | p4 note 4 + TCM2-63WX+ schematic Config K |
| T_IN | H3-TCM2-63WX+ (1:2, 50 ohm SE -> 100 ohm diff) | DB1627 | pin3 <- RF from gain block (already DC-blocked) ↔ pins1,2 -> GND ↔ pin4,6 -> C_IN_N/C_IN_P ↔ pin5 NC | eval p7 uses RFXF9503 with its pin 6 AC-grounded by C23 100pF and balanced CT open |
| T_OUT | BD2425N50200AHF (50 ohm SE : 200 ohm balanced, 2.4-2.5 GHz) | 0404 | pin3 -> U.27 MIX_OPN (or 28; polarity irrelevant) ↔ pin4 -> U.28 MIX_OPP ↔ pin1 (DC feed / CT) -> ANA_VDD2 + bypass ↔ pin2 -> SAW in | eval p7 uses RFXF8553 4:1 with CT (pin 2) to VDDA2 + C6 100pF |
| C_CT | 100pF C0G (eval C6); 10-15 pF 0402 self-resonates near 2.44 GHz and is a better IF ground (suggestion) | 0402 | T_OUT.1 ↔ GND | p7 C6 |
| C_CT2 | 100nF | 0402 | T_OUT.1 / ANA_VDD2 feed ↔ GND | suggestion |

**Loop filter note:** Topology (p7/p8 identical): active op-amp integrator between LFILT1 (in) and LFILT2 (out): C8 8.2pF in parallel with series R3 22k + C9 180pF; then 2-pole RC post-filter LFILT2 -R2 470R- (C10 330pF to GND) -R6 470R- LFILT3 with C17 330pF to GND. The synthesizer spec (p3) is quoted for 'loop bandwidth 200 kHz, 52 MHz reference'; typical plots (p9) use 26 MHz and 52 MHz TCXOs (NDK ENA3523A / ENA3560A). With our 40 MHz ref (PFD 40 MHz <= 52 MHz max) and the same charge-pump setting, loop BW scales ~ with f_PFD: ~200*40/52 = ~150 kHz, phase margin roughly kept. Fine to copy the values; charge-pump current is programmable (Slice2 register guide, not downloaded - UNVERIFIED).

**Control note:** 3-wire SPI: ENX, SCLK, SDATA to ESP32 GPIOs (+33pF each per eval). RESETX to GPIO with 10k pull-up to DIG_VDD. ENBL and MODE: route to ESP32 GPIOs (or 0R/10k to DIG_VDD/GND); do NOT hard-tie to a rail if firmware sets SDI_CTRL.sipin=1, because they then become outputs GPO5/GPO6 (HackRF-style SPI control). GPO4/LD -> ESP32 GPIO (lock detect) + optional LED. GPO1/2/3 -> test pads. Pins 2,3,11,13,14,17,18,20,21 open; 12 to GND.

**Notes**

- DS pin table (p4) names pin 27 MIX2_OPN and pin 28 MIX2_OPP, while the eval schematic (p7) labels pin 27 MIX2_IOIP (net RF_OP2_P) and pin 28 MIX2_IOIN. Polarity only flips IF phase - irrelevant for a balun - but do not rely on the names.
- Supply max 3.3 V operating: TPS7A2033 (3.3 V) is at the top of range; TPS7A2030 (3.0 V) is the safer nominal (C963429).
- Mixer input return loss spec is for 100 ohm differential; output spec is 'driving 4:1 balun' (200 ohm) - matches BD2425N50200AHF.
- UNVERIFIED: DC current through the BD2425 DC-feed pin (mixer output stage bias, set by MIX_IDD) vs the balun's DC rating (not stated in its DS).

---

## PSA4-5043+

- **MPN / mfr:** PSA4-5043+ (Mini-Circuits); **LCSC:** C5240848
- **Function:** E-pHEMT LNA 50 MHz-4 GHz, internally matched, self-biased (no bias resistor)
- **Source:** claude_db/esp32_sdr_datasheets/PSA4-5043.pdf p2 (specs), p3 (pinout), p4 (Fig.2 app circuit); eval TB-653+ claude_db/esp32_sdr_datasheets/PSA4-5043_TB-653_P02.pdf; layout PL-361 claude_db/esp32_sdr_datasheets/PSA4-5043_PL-361_layout.pdf
- **Package:** SOT-343 (SC-70-4), Mini-Circuits case MMM1362 (body [2.0, 1.25, 1.0] mm)
- **Supply:** Vd 3 V/33 mA or 5 V/56-58 mA (max 66 mA @5 V); abs max 6 V, 76 mA. At 4.5 V rail expect ~50 mA (0.01 mA/mV).
- **KiCad footprint:** `Package_TO_SOT_SMD:SOT-343_SC-70-4`
- **Pad-numbering check:** KiCad pad 1 (-0.95,-0.65) top-left, 2 bottom-left, 3 bottom-right, 4 top-right = DS p3 (1 RF-OUT top-left, 2 GND bottom-left, 3 RF-IN bottom-right, 4 GND top-right). Matches. DS drawing shows lead 2 (GND) wider; KiCad pads are all 0.65x0.4 - consider widening pad 2 to ~0.6 mm (UNVERIFIED lead width).

| Pin | Name | Function |
|---|---|---|
| 1 | RF-OUT & DC-IN | RF output; Vd fed through RF choke L1; output DC block C2 |
| 2 | GND | Ground (vias at pad) |
| 3 | RF-IN | RF input via DC block C1 (pin has DC bias) |
| 4 | GND | Ground |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C1 | 1000pF C0G (TB-653+ value) | 0402 | RF in (SP3T RFx port) ↔ U.3 | TB-653+ BOM |
| C2 | 1000pF C0G (TB-653+ uses the DC block inside a TCBT-14+ bias tee) | 0402 | U.1 ↔ RF out (to LPF/BPF) | Fig.2 + TB-653+ |
| L1a | 33 nH high-SRF (e.g. 0402 wirewound, SRF > 2.5 GHz) next to pin 1 | 0402 | U.1 ↔ NET_CHOKE | UNVERIFIED engineering choice: DS gives no value (eval uses TCBT-14+ bias tee, 10 MHz-10 GHz) |
| L1b | 1 uH (0603 wirewound or ferrite) to cover 50 MHz | 0603 | NET_CHOKE ↔ VDD_LNA (4.5 V) | UNVERIFIED engineering choice: X_L(50 MHz)=314 ohm >> 50 ohm |
| R_damp | 10-22R in series with L1b (optional, damps L1a/L1b resonance) | 0402 | L1b ↔ VDD_LNA | suggestion |
| C3 | 100nF (TB-653+ C2=0.1uF bypass) + 100pF | 0402 | VDD_LNA at choke ↔ GND | TB-653+ BOM (0.1 uF), FLTR 1500 pF feed-through |

**Notes**

- No bias resistor: device is internally biased, Vd applied straight through the choke (Fig.2: 'Resistance of L1 0.1-0.2 ohm typically').
- Specified only 50 MHz-4 GHz; gain 25.4 dB @50 MHz -> check low-frequency stability with the choke you choose.
- ESD HBM 500 V (class 1B) - keep the SMA ESD diode.

---

## QPL9503

- **MPN / mfr:** QPL9503TR7 (Qorvo); **LCSC:** C470924
- **Function:** Flat-gain ultra-low-noise LNA 0.6-6 GHz (optimised 3-6 GHz), shutdown pin
- **Source:** claude_db/esp32_sdr_datasheets/QPL9503.pdf (Apr 2018): specs p2, eval schematic + BOM p3 (QPL9503EVB-01, 5-6 GHz tuned), pinout p5, package + PCB pattern p6
- **Package:** DFN-8 2x2x0.85 mm, 0.5 mm pitch, EP 0.80x1.60 mm (body [2.0, 2.0, 0.85] mm)
- **Supply:** VDD 3.3-5.0-5.25 V (abs max 7 V); IDD 56 mA typ (35-90) @5 V; 3 mA in shutdown
- **KiCad footprint:** `Package_DFN_QFN:DFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.6mm`
- **Pad-numbering check:** Pads 1-4 left (top->bottom), 5-8 right (bottom->top), pad 9 EP 0.8x1.6 -> standard JEDEC numbering = DS p5. Qorvo land (p6): pads 0.30x0.67 at x=+-0.885, EP land 0.70x1.60, 3 vias 0.254 mm. Do NOT use Qorvo_DFN-8-1EP_2x2mm_P0.5mm (its EP is 0.6x1.2, a different Qorvo part).

| Pin | Name | Function |
|---|---|---|
| 1 | Vbias | Sets Icq: R4 4.3k from VDD |
| 2 | RF In | RF input, DC block required |
| 3 | NC | Not connected; solder to grounded land |
| 4 | GND | Ground |
| 5 | Shut Down | >1.17 V = OFF, <0.63 V or GND = ON (1.8 V logic; 140 uA at high) |
| 6 | GND | Ground |
| 7 | RF Out / DC bias | RF output; VDD via RF choke L1 |
| 8 | NC | Not connected; solder to grounded land |
| 9 | EP | RF/DC ground, vias |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C1 | 10pF (1%) | 0402 | RF in (from HPF2) ↔ U.2 | p3 BOM |
| C8 | 0.2pF (DNP-able input tune) | 0402 | U.2 ↔ GND | p3 BOM (5-6 GHz tune) |
| R4 | 4.3k | 0402 | VDD ↔ U.1 Vbias | p3 BOM; note 7 sets current |
| C5 | 100pF | 0402 | VDD/R4 node ↔ GND | p3 BOM |
| L1 | 18nH (Coilcraft 0402CS-18NXJL) | 0402 | U.7 ↔ VDD | p3 BOM |
| C3 | 100pF | 0402 | VDD (L1 end) ↔ GND | p3 BOM |
| C4 | 1uF X5R | 0402 | VDD ↔ GND | p3 BOM |
| C2 | 5.6pF | 0402 | U.7 ↔ RF out (to HB HPF) | p3 BOM |
| C9 | 0.4pF (DNP-able output tune) | 0402 | RF out after C2 ↔ GND | p3 BOM |
| R2 | 20k pull-down | 0402 | U.5 SD ↔ GND | p3 BOM (LNA on by default) |
| R1 | 0R (or 1k) to ESP32 GPIO for shutdown (optional) | 0402 | U.5 SD ↔ ESP32 GPIO / NC | p3 BOM R1=0R to J5 PD |

**Notes**

- Eval is tuned for 5-6 GHz; for 3.1-6 GHz keep C8/C9 as DNP footprints and tune on rev A.
- Eval at VDD=5 V; on the 4.5 V rail Idd drops slightly (R4 to VDD). Still in spec (min 3.3 V).
- Shutdown pin: drive with 3.3 V GPIO OK (abs VEN up to VDD). Could be used to turn off the unused HB LNA.

---

## GVA-62+

- **MPN / mfr:** GVA-62+ (Mini-Circuits); **LCSC:** C5445184
- **Function:** Flat-gain InGaP HBT gain block 10 MHz-6 GHz, internally biased
- **Source:** claude_db/esp32_sdr_datasheets/GVA-62.pdf p2 (specs), p3 (pins), p4 (app circuit); eval claude_db/esp32_sdr_datasheets/GVA-62_WTB-410-62+_P02.pdf; layout claude_db/esp32_sdr_datasheets/GVA-62_98-pl255.pdf
- **Package:** SOT-89 (Mini-Circuits DF782) (body [4.5, 2.5, 1.5] mm)
- **Supply:** Device voltage 4.8-5.0-5.2 V, 82 mA (72-92); 0.035 mA/mV. No bias resistor in Mini-Circuits circuit (Vd = Vcc through choke).
- **KiCad footprint:** `Package_TO_SOT_SMD:SOT-89-3`
- **Pad-numbering check:** KiCad pad 1, 2 (centre lead merged with tab), 3. DS: 1 RF-IN, 2 GND (and tab, called pin 4), 3 RF-OUT&DC-IN. Matches. PL-255 adds 8 GND vias around/under the tab.

| Pin | Name | Function |
|---|---|---|
| 1 | RF-IN | RF input; DC block required |
| 2 | GND | Ground (centre lead + tab '4') |
| 3 | RF-OUT & DC-IN | RF output + bias via RF choke; DC block required |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C1 | 2400pF on eval (any low-ESL cap free of resonance to 6 GHz; e.g. 100pF 0201/0402 + accept LF roll-off, or 1nF 0402) | 0402 | RF in (SP3T_out common) ↔ U.1 | TB-410-62+ BOM note 4 |
| C2 | 2400pF on eval (same remark) | 0402 | U.3 ↔ balun T_IN pin 3 | TB-410-62+ |
| CHK | eval: Mini-Circuits ADCH-80A+ wideband choke (50-8000 MHz). Discrete: 22 nH high-SRF 0402 at pin + 1 uH 0603 toward Vcc (UNVERIFIED) | 0402+0603 | U.3 ↔ Vcc | TB-410-62+ BOM |
| C3 | 0.1uF bypass (+100pF) | 0402 | Vcc ↔ GND | TB-410-62+ BOM |

**Notes**

- Specified 4.8-5.2 V at the device. The 4.5 V LDO rail (TPS7A2045) is BELOW spec (Idd ~70 mA, lower P1dB). Either feed from VBUS through ferrite + LC pi filter, or accept. A series bias resistor is not used by Mini-Circuits; any choke DCR drops voltage (82 mA x R).
- Choke must be broadband 10 MHz-6 GHz equivalent: two-section choke recommended (UNVERIFIED values).

---

## BGS13SN8

- **MPN / mfr:** BGS13SN8E6327 (Infineon); **LCSC:** C3312946
- **Function:** SP3T RF switch 0.1-6 GHz, GPIO control (x2: SP3T_in, SP3T_out)
- **Source:** claude_db/esp32_sdr_datasheets/BGS13SN8.pdf rev 2.4: features p1, abs max p4 (VRFDC=0), op ranges p5, RF p6, pins + truth table p9 (Fig.2/Tab.8/Tab.9), package + footprint p10 (Fig.3/Fig.4)
- **Package:** PG-TSNP-8-1, 1.1x1.1x0.375 mm, 3x3 grid minus centre, 0.4 mm pitch, pads 0.2x0.2 (body [1.1, 1.1, 0.375] mm)
- **Supply:** VDD 1.65-3.4 V (abs max 3.6), IDD 80 uA; VCtrl_H 1.35 V..VDD+0.3, VCtrl_L <0.45 V -> 3.3 V ESP32 GPIO OK with VDD=3.3 V
- **KiCad footprint:** none in library, so use the custom land pattern below

| Pin | Name | Function |
|---|---|---|
| 1 | VDD | Supply 1.65-3.4 V |
| 2 | V2 | Control 2 |
| 3 | V1 | Control 1 |
| 4 | RF3 | RF port 3 |
| 5 | RF1 | RF port 1 |
| 6 | RFin | Common RF port |
| 7 | RF2 | RF port 2 |
| 8 | GND | Ground |

**Truth table:** V1=0,V2=0 → Isolation (all off); V1=1,V2=0 → RFin-RF1; V1=0,V2=1 → RFin-RF2; V1=1,V2=1 → RFin-RF3

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_VDD | 100nF (+ optional 33pF) - not required by DS, recommended | 0402 | U.1 ↔ GND | DS shows none; suggestion |
| DC blocks | Required on every RF port that sees DC (all of ours: LNA in/out, gain block, SMA). DS: 'No blocking capacitors required if no DC applied'; abs max VRFDC = 0 V; internal DC connection between switched paths. | 0402 | RFx / RFin ↔ neighbour | p1, p4 Table 1 + footnote |
| R/C on V1,V2 | optional 1k series (ESP32 GPIO noise) - suggestion | 0402 | ESP32 GPIO ↔ U.3/U.2 | suggestion |

**Custom land pattern `Infineon_PG-TSNP-8-1_1.1x1.1mm_P0.4mm`** (mm; origin: package centre, top view, +x right, +y down (KiCad))

```json
{
 "units": "mm",
 "origin": "package centre, top view, +x right, +y down (KiCad)",
 "pad_shape": "rect 0.25 x 0.25 copper (Fig.4); stencil 0.25 round; solder mask: optional dam between pads (NSMD)",
 "pads": {
  "1": [
   -0.4,
   -0.4
  ],
  "8": [
   0.0,
   -0.4
  ],
  "7": [
   0.4,
   -0.4
  ],
  "2": [
   -0.4,
   0.0
  ],
  "6": [
   0.4,
   0.0
  ],
  "3": [
   -0.4,
   0.4
  ],
  "4": [
   0.0,
   0.4
  ],
  "5": [
   0.4,
   0.4
  ]
 },
 "pad_size": [
  0.25,
  0.25
 ],
 "courtyard": [
  1.6,
  1.6
 ],
 "pin1_mark": "top-left (pin 1 VDD)",
 "check": "Fig.2 (footprint top view) gives 1 VDD TL, 8 GND TM, 7 RF2 TR, 2 V2 ML, 6 RFin MR, 3 V1 BL, 4 RF3 BM, 5 RF1 BR; consistent with Fig.3 bottom view mirrored."
}
```

**Notes**

- Both switches share V1/V2 (2 GPIOs) and VDD 3.3 V.
- Specified 0.1-6 GHz only; 50-100 MHz unverified (see SIGNAL_CHAIN 12).
- DS ESD SLT rating (+-8 kV) is with a 27 nH shunt inductor at the RF port - NOT usable here (8.5 ohm at 50 MHz).

---

## SAFEA2G45MC0F0AR00

- **MPN / mfr:** SAFEA2G45MC0F0AR00 (Murata); **LCSC:** C910550
- **Function:** 2.4 GHz ISM SAW bandpass, unbalanced in/out, 5-pad 1411
- **Source:** claude_db/esp32_sdr_datasheets/SAFEA2G45MC0F0AR00.pdf p1 (ratings), p2 (dimensions, land pattern, measurement circuit; doc page '2/7')
- **Package:** 1.35x1.05x0.5 mm max, 5 pads (bottom pads 0.25x0.325) (body [1.35, 1.05, 0.5] mm)
- **Impedance:** 50 ohm nominal at both ports, BUT the characterisation (measurement circuit p2) uses a 4.3 nH ideal shunt inductor at each port (R1=R2=50 ohm, L1=L2=4.3 nH). So the specified response needs shunt-L matching on both sides.
- **KiCad footprint:** `Filter:Filter_1411-5_1.4x1.1mm`
- **Pad-numbering check:** KiCad: pad1 (-0.5,0), pad2 (0,+0.2875), pad3 (+0.5,+0.2875), pad4 (+0.5,-0.2875), pad5 (0,-0.2875) (KiCad +y down). Murata top view: 1 left, 5 top-middle, 4 top-right, 2 bottom-middle, 3 bottom-right -> numbering MATCHES. KiCad pads are 0.25x0.325 (= package pads); Murata's recommended land is larger - use the custom variant below if you want Murata's land.

| Pin | Name | Function |
|---|---|---|
| 1 | IN (unbalanced, 'PA side') | Input; DS: input power must be applied to terminal 1 -> mixer/balun side |
| 2 | GND | Ground |
| 3 | GND | Ground |
| 4 | OUT (unbalanced, 'Ant side') | Output -> ESP32 tee |
| 5 | GND | Ground |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| L_SAWin | 4.3nH ideal -> start 3.9-4.3nH high-Q 0402, tune | 0402 | U.1 ↔ GND | p2 measurement circuit |
| L_SAWout | 4.3nH ideal -> start 3.9-4.3nH high-Q 0402, tune | 0402 | U.4 ↔ GND | p2 measurement circuit |
| DC | max 3 V DC between terminals; shunt L shorts DC anyway - keep the BD2425 DC feed (pin 1) isolated from its unbalanced pin 2 (it is, inside the balun) and put no DC on SAW | - |  | p1 |

**Custom land pattern `Murata_SAFEA_1411-5_RecommendedLand`** (mm; origin: centre, top view, +y up (Murata drawing); flip y for KiCad)

```json
{
 "units": "mm",
 "origin": "centre, top view, +y up (Murata drawing); flip y for KiCad",
 "pads": {
  "1": {
   "at": [
    -0.5875,
    0.0
   ],
   "size": [
    0.425,
    0.325
   ]
  },
  "5": {
   "at": [
    0.0,
    0.3875
   ],
   "size": [
    0.25,
    0.525
   ]
  },
  "2": {
   "at": [
    0.0,
    -0.3875
   ],
   "size": [
    0.25,
    0.525
   ]
  },
  "4": {
   "at": [
    0.5875,
    0.2875
   ],
   "size": [
    0.425,
    0.325
   ]
  },
  "3": {
   "at": [
    0.5875,
    -0.2875
   ],
   "size": [
    0.425,
    0.325
   ]
  }
 },
 "check": "From p2 land drawing: overall 1.600 wide, columns 0.425/0.250/0.250/0.250/0.425; right pads 0.325 tall, 0.900 outer span; middle pads 0.525 tall with 0.25 gap. Positions derived, tolerance +-0.02 (read from drawing)."
}
```

**Notes**

- Max input power +28 dBm.
- Shunt inductors also give an ESD/DC path to ground for the IF line.

---

## BD2425N50200AHF

- **MPN / mfr:** BD2425N50200AHF (TTM (Anaren Xinger)); **LCSC:** C502748
- **Function:** 2.4-2.5 GHz balun, 50 ohm unbalanced : 200 ohm balanced (2x100), with DC-feed / RF-ground pin
- **Source:** claude_db/esp32_sdr_datasheets/BD2425N50200AHF.pdf (Rev D, downloaded from cdn.ttm.com): specs + outline + pin table p1, mounting footprints (no DC bias / with DC bias) p4
- **Package:** 0404 LGA, 1.04x1.04x0.56 mm, 4 pads 0.25x0.25 on 0.51 mm pitch (bottom) (body [1.04, 1.04, 0.56] mm)
- **KiCad footprint:** none in library, so use the custom land pattern below

| Pin | Name | Function |
|---|---|---|
| 1 | GND / DC Feed + RF GND | Balanced-side centre tap. Apply DC here (ANA_VDD2) and RF-bypass it to GND close to the pad; DC then appears on both balanced pins 3/4. Without DC bias: connect straight to GND. |
| 2 | Unbalanced port | 50 ohm -> SAW input (pin 1) |
| 3 | Balanced port | -> RFFC5072 MIX_OPN (27) |
| 4 | Balanced port | -> RFFC5072 MIX_OPP (28) |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_CT | bypass at pin 1: 10-15pF (series-resonant ~2.4 GHz) + 100nF; eval-equivalent 100pF | 0402 | T.1 ↔ GND | p4 DC-bias footprint (cap value not given); RFFC eval C6=100pF |
| FB/R_feed | 0R or ferrite bead (optional) | 0402 | T.1 node ↔ ANA_VDD2 (3.3 V) | suggestion |
| no DC block | pins 3/4 connect directly to RFFC pins 27/28 (they must carry DC) | - | T.3-U.27 ↔ T.4-U.28 | RFFC DS note 5 |

**Custom land pattern `Anaren_Xinger_0404_BD2425`** (mm; origin: centre, TOP view, +x right, +y down)

```json
{
 "units": "mm",
 "origin": "centre, TOP view, +x right, +y down",
 "pads": {
  "2": {
   "at": [
    -0.255,
    -0.255
   ],
   "size": [
    0.28,
    0.28
   ],
   "net_hint": "Unbalanced (50 ohm)"
  },
  "1": {
   "at": [
    0.255,
    -0.255
   ],
   "size": [
    0.36,
    0.36
   ],
   "net_hint": "GND / DC feed + RF GND (larger pad)"
  },
  "3": {
   "at": [
    -0.255,
    0.255
   ],
   "size": [
    0.28,
    0.28
   ],
   "net_hint": "Balanced"
  },
  "4": {
   "at": [
    0.255,
    0.255
   ],
   "size": [
    0.28,
    0.28
   ],
   "net_hint": "Balanced"
  }
 },
 "solder_mask": "NSMD, mask openings ~0.05 mm larger; trace exits 0.28 mm (TTM example, retune for JLC stack)",
 "check": "p1 bottom view: 1 TL, 2 TR, 4 BL, 3 BR; mirrored to top view -> 2 TL, 1 TR, 3 BL, 4 BR. p4 'with DC bias' footprint shows the large 0.36 pad (pin 1) at top-right with a trace to a bypass-cap pad and via - consistent."
}
```

**Notes**

- DC current rating through pin 1 is not stated (power handling 1 W) - UNVERIFIED for the RFFC output bias current.
- Only 25 in stock at LCSC (C502748). Fallback: two RF chokes from pins 27/28 to ANA_VDD2 + lumped LC balun.
- IL 0.6 typ/0.7 max dB, RL >=18 dB, amplitude 0.5/1.0 dB, phase 2/6 deg (p1).

---

## H3-TCM2-63WX+

- **MPN / mfr:** H3-TCM2-63WX+ (HenryTech (Chengdu) - clone of Mini-Circuits TCM2-63WX+); **LCSC:** C22383437
- **Function:** 1:2 transmission-line balun 30-6000 MHz, 50 ohm SE -> 100 ohm balanced, NO centre tap (Config K)
- **Source:** claude_db/esp32_sdr_datasheets/H3-TCM2-63WX.pdf p1 (pins, dims, land); genuine claude_db/esp32_sdr_datasheets/TCM2-63WX.pdf p2 (schematic, pin connections, Config K), p3 (outline, land, demo board TB-676+ PL-380)
- **Package:** Clone: 4.21x4.21x2.40 mm, 6-position top-hat (5 leads; position 5 'not used'); genuine DB1627: 4.06x3.81x(<=2.9?) mm
- **KiCad footprint:** `RF_Mini-Circuits:Mini-Circuits_DB1627`
- **Pad-numbering check:** KiCad DB1627: pads 1,2,3 top row (x=-1.27,0,+1.27, y=-1.59), 4,5,6 bottom row (x=+1.27,0,-1.27) -> same as Mini-Circuits outline (1-2-3 top, 6-5-4 bottom, dot at pin 1). Pads 0.76x1.65 vs clone recommended 0.76x1.40, same 1.27 pitch and 4.83 span -> fits clone and genuine. Pad 5 = no net.

| Pin | Name | Function |
|---|---|---|
| 1 | PRIMARY (GND) | Primary return - GND |
| 2 | PRIMARY (GND) | Primary return - GND |
| 3 | PRIMARY DOT | 50 ohm unbalanced input |
| 4 | SECONDARY | Balanced output (-) |
| 5 | NOT USED | No lead on clone / not used on genuine - leave unconnected |
| 6 | SECONDARY DOT | Balanced output (+) |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_dc_P | 100pF C0G 0402 (DC block) | 0402 | T.6 ↔ RFFC U.23 MIX_IPP | Config K: SEC DOT is DC-tied to PRI GND through the third winding; RFFC note 4 forbids DC on mixer inputs |
| C_dc_N | 100pF C0G 0402 (DC block) | 0402 | T.4 ↔ RFFC U.24 MIX_IPN | Config K: SEC is DC-tied to PRI DOT |
| C_comp x2 | 0.5pF shunt each secondary pin (genuine demo board; DNP footprints) | 0402 | T.4 / T.6 ↔ GND | TCM2-63WX+ p2 electrical schematic (C1, C2 0.5pF) |

**Notes**

- The genuine part's schematic shows NO centre tap: pins 1,2 are primary/ground, 3 = primary dot (input), 4 = secondary, 6 = secondary dot, 5 not used. The clone pin table omits 5 (consistent).
- Config K implies DC continuity between primary and secondary windings and to GND -> series DC-block caps on both mixer legs are mandatory (eval-board equivalent: RFMD AC-grounded the primary 'ground' via C23 100pF).
- Clone RF data (IL 2.1/2.9 dB 30-5000 MHz, 3.2/3.9 dB 5-6 GHz) unverified vs genuine (0.9/1.5/2.5 dB typ).

---

## TG2520SMN-40M

- **MPN / mfr:** X1G0054210307 (TG2520SMN 40.000000 MHz MCGNNM) (Epson); **LCSC:** C3007519
- **Function:** 40 MHz TCXO, +-0.5 ppm, clipped sine, no Vc
- **Source:** claude_db/esp32_sdr_datasheets/X1G0054210307.pdf: operating conditions + electrical p1, pin info p2, outline + recommended footprint p14
- **Package:** 2.5x2.0x0.8 mm, 4-pad ceramic (body [2.5, 2.0, 0.8] mm)
- **Supply:** Vcc 2.66-3.465 V, Icc <=1.8 mA
- **Output:** Clipped sine >=0.8 Vpp into 10 kohm || 10 pF (load spec 9-11 kohm, 9-11 pF); 3rd harmonic <= -5 dBc; DC-cut cap NOT included - external >=0.01 uF required
- **KiCad footprint:** `Oscillator:Oscillator_SMD_SeikoEpson_TG2520SMN-xxx-xxxxxx-4Pin_2.5x2.0mm`
- **Pad-numbering check:** KiCad footprint is rotated 90 deg (long axis vertical): pads 1.0x0.8 at (+-0.7, +-1.05), 1 TL, 2 BL, 3 BR, 4 TR (CCW) = Epson land (0.8x1.0 pads, 2.1 x 1.4 pitch, 1 BL, 2 BR, 3 TR, 4 TL CCW). Matches; it carries a keep-out between pads (Epson: no pattern between pads).

| Pin | Name | Function |
|---|---|---|
| 1 | N.C. | No connect (Vc on VC-TCXO). Leave OPEN or GND; it is not a ground pin |
| 2 | GND | Ground |
| 3 | OUT | Clipped-sine output; external DC-cut cap >=10 nF |
| 4 | VCC | Supply |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_byp | 100nF (0.01-0.1 uF per DS), as close as possible | 0402 | X.4 VCC ↔ GND | p14 note |
| R/FB_vcc | optional 10-47R or ferrite from 3.3 V (RFFC eval feeds its TCXO through R31 120R + C44 10nF) | 0402 | 3V3_RF ↔ X.4 | RFFC DS p7 |
| C_dc_RFFC | 10nF | 0402 | X.3 OUT ↔ RFFC REF_IN | p1 Cc>=0.01uF |
| C_dc_ESP | 10nF + series 24nH (ESP32 HW guide: series L on XTAL_P required) | 0402/0201 | X.3 OUT ↔ ESP32 XTAL_P | S31 HW design guidelines 1.3.5; ESP32 drive level UNVERIFIED |

**Notes**

- Driving two loads (RFFC REF_IN and ESP32 XTAL_P) exceeds the 10 kohm||10 pF load spec only if the inputs are low-impedance; input impedances UNVERIFIED - keep a buffer/resistive-split option (open issue 6 in PART_SELECTION).
- Frequency vs load coefficient only +-0.1 ppm for +-10 % load.

---

## TPS7A2033PDBVR

- **MPN / mfr:** TPS7A2033PDBVR (TI); **LCSC:** C2862740
- **Function:** 300 mA low-noise LDO, 3.3 V (RFFC5072 / RF 3.3 V rail)
- **Source:** claude_db/esp32_sdr_datasheets/TPS7A20.pdf (SBVS338H) Pin Functions X2SON/SOT-23 table (sec. 4), Rec. op. cond. (5.3), EN thresholds (5.5)
- **Package:** SOT-23-5 (DBV) 2.9x2.8 mm
- **KiCad footprint:** `Package_TO_SOT_SMD:SOT-23-5`
- **Pad-numbering check:** Standard SOT-23-5 numbering (1-3 left top->bottom, 4-5 right bottom->top) = DBV pinout. Matches.

| Pin | Name | Function |
|---|---|---|
| 1 | IN | Input 1.6-6.0 V |
| 2 | GND | Ground |
| 3 | EN | Enable: >0.9 V on, <0.3 V off; internal 500k pull-down (tie to IN or GPIO) |
| 4 | NC | No internal connection |
| 5 | OUT | Regulated output |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_in | 1uF min (use 2.2-4.7uF X5R/X7R) | 0603 | U.1 IN ↔ GND | TPS7A20 DS 5.3 Rec. op. cond. CIN 1 uF |
| C_out | 1uF min effective (1-200 uF, ESR<100 mohm); use 2.2-4.7uF X5R/X7R | 0603 | U.5 OUT ↔ GND | DS 5.3 COUT |
| EN | tie EN to IN, or ESP32 GPIO + 100k to IN | - | U.3 ↔ U.1 or GPIO | DS pin table |

**Notes**

- Dropout 145 mV max at 300 mA. 'P' suffix = active output discharge.
- Consider TPS7A2030 (3.0 V) for RFFC (VDD max 3.3 V).

---

## TPS7A2045PDBVR

- **MPN / mfr:** TPS7A2045PDBVR (TI); **LCSC:** C2873627
- **Function:** 300 mA low-noise LDO, 4.5 V (LNA / gain-block rail)
- **Source:** claude_db/esp32_sdr_datasheets/TPS7A20.pdf
- **Package:** SOT-23-5 (DBV)
- **KiCad footprint:** `Package_TO_SOT_SMD:SOT-23-5`
- **Pad-numbering check:** Same as TPS7A2033.

| Pin | Name | Function |
|---|---|---|
| 1 | IN | Input 1.6-6.0 V |
| 2 | GND | Ground |
| 3 | EN | Enable: >0.9 V on, <0.3 V off; internal 500k pull-down (tie to IN or GPIO) |
| 4 | NC | No internal connection |
| 5 | OUT | Regulated output |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_in | 1uF min (use 2.2-4.7uF X5R/X7R) | 0603 | U.1 IN ↔ GND | TPS7A20 DS 5.3 Rec. op. cond. CIN 1 uF |
| C_out | 1uF min effective (1-200 uF, ESR<100 mohm); use 2.2-4.7uF X5R/X7R | 0603 | U.5 OUT ↔ GND | DS 5.3 COUT |
| EN | tie EN to IN, or ESP32 GPIO + 100k to IN | - | U.3 ↔ U.1 or GPIO | DS pin table |

**Notes**

- Needs VIN >= ~4.65 V at 300 mA (145 mV dropout) - marginal on a sagging USB VBUS (4.4-4.75 V allowed by USB spec): it will drop out, not fail.
- Load budget: PSA4 x2 (~50 mA each, only one arm on unless both powered) + QPL9503 56 mA + GVA-62 82 mA ~ 240 mA if all on - within 300 mA but check thermal ((5-4.5) x 0.24 = 0.12 W OK).

---

## AMS1117-3.3

- **MPN / mfr:** AMS1117-3.3 (Advanced Monolithic Systems); **LCSC:** C6186
- **Function:** 1 A LDO 3.3 V (digital rail: ESP32, PHY, flash)
- **Source:** claude_db/esp32_sdr_datasheets/AMS1117-3.3.pdf (LCSC copy) p1 pin connections, p4 'Stability' application note
- **Package:** SOT-223 (tab = VOUT)
- **KiCad footprint:** `Package_TO_SOT_SMD:SOT-223-3_TabPin2`
- **Pad-numbering check:** Pad 1 GND/ADJ, 2 VOUT (+tab), 3 VIN = DS. Matches.

| Pin | Name | Function |
|---|---|---|
| 1 | GND/ADJ | Ground (fixed version) |
| 2 | VOUT | Output (also tab) |
| 3 | VIN | Input |
| TAB | VOUT | Tab = output; use copper pour for heat |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_out | 22uF tantalum (DS: ensures stability for all conditions); 22uF ceramic + 0.5-1 ohm ESR is the usual substitute (UNVERIFIED with pure MLCC) | 3528 tantalum or 1206 MLCC | U.2 VOUT ↔ GND | DS p4 'Stability' |
| C_in | 10uF | 0805/1206 | U.3 VIN ↔ GND | common practice; DS no explicit value (UNVERIFIED) |

**Notes**

- Minimum load 5-10 mA.
- Dropout ~1.1 V @ 800 mA: 5.0 V -> 3.3 V OK only while VBUS > 4.4 V.
- Thermal: SOT-223 theta_JA 90 C/W (DS) - see PART_SELECTION thermal check.

---

## TYPE-C-31-M-12

- **MPN / mfr:** TYPE-C-31-M-12 (Korean Hroparts (HRO)); **LCSC:** C165948
- **Function:** USB Type-C receptacle, USB 2.0 only (16 pins), SMD + 4 THT shell tabs
- **Source:** claude_db/esp32_sdr_datasheets/TYPE-C-31-M-12.pdf (HRO drawing): pin table, recommended PCB layout
- **Package:** 8.94 x 7.35 mm, top-mount SMD, 16 signal pads (12 positions), 4 THT shell tabs, 2 NPTH pegs d0.65
- **KiCad footprint:** `Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12`
- **Pad-numbering check:** Pad order left-to-right A1/B12, A4/B9, B8, A5, B7, A6, A7, B6, A8, B5, A9/B4, A12/B1 at x=-3.25..+3.25 = HRO layout. Matches. Shell = pad 'S1' (4 THT).

| Pin | Name | Function |
|---|---|---|
| A1,B1,A12,B12 | GND | Ground |
| A4,B4,A9,B9 | VBUS | 5 V |
| A5 | CC1 | 5.1k Rd to GND (own resistor) |
| B5 | CC2 | 5.1k Rd to GND (own resistor) |
| A6,B6 | D+ (DP1/DP2) | Tie together -> USBLC6 -> ESP32 USB D+ |
| A7,B7 | D- (DN1/DN2) | Tie together -> USBLC6 -> ESP32 USB D- |
| A8,B8 | SBU1/SBU2 | NC |
| S1 | SHIELD | Shell: to GND via 1M || 4.7nF, or direct GND |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| R_CC1 | 5.1k 1% | 0603 | J.A5 CC1 ↔ GND | USB-C spec Rd (sink) |
| R_CC2 | 5.1k 1% | 0603 | J.B5 CC2 ↔ GND | USB-C spec Rd - separate resistors, never one shared |
| C_VBUS | 10uF + 100nF | 0805/0603 | VBUS ↔ GND | suggestion |
| F/FB | optional PTC 500 mA-1 A / ferrite on VBUS | 1206 | VBUS connector ↔ VBUS board | suggestion |

**Notes**

- Rated 5 A / 20 V.

---

## USBLC6-2SC6

- **MPN / mfr:** USBLC6-2SC6 (ST); **LCSC:** C7519
- **Function:** 2-line USB ESD + VBUS clamp
- **Source:** claude_db/esp32_sdr_datasheets/USBLC6-2SC6.pdf (LCSC copy) p1 pinout, p2 characteristics (C I/O-GND 2.5-3.5 pF)
- **Package:** SOT-23-6L
- **KiCad footprint:** `Package_TO_SOT_SMD:SOT-23-6`
- **Pad-numbering check:** Standard SOT-23-6 numbering (1-3 left, 4-6 right bottom->top) = ST pinout. Matches.

| Pin | Name | Function |
|---|---|---|
| 1 | I/O1 | Line 1 (pass-through to pin 6) |
| 2 | GND | Ground |
| 3 | I/O2 | Line 2 (pass-through to pin 4) |
| 4 | I/O2 | Line 2 |
| 5 | VBUS | Connect to VBUS (5 V) - clamp reference |
| 6 | I/O1 | Line 1 |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| route | D+ through pins 1-6, D- through 3-4 (flow-through), pin 5 to VBUS, pin 2 to GND with via | - |  | DS |

**Notes**

- Alternative JLC-cheaper parts exist (e.g. SRV05-4) - not checked.

---

## KLXES15AAA1

- **MPN / mfr:** KLXES15AAA1 (KUU (clone of Murata LXES15AAA1)); **LCSC:** C2892490
- **Function:** Polymer ESD suppressor, bidirectional, 0.05 pF typ, for the SMA RF inputs
- **Source:** claude_db/esp32_sdr_datasheets/KLXES15AAA1.pdf p1 (specs), p4 (dimensions, footprint)
- **Package:** 0402 (1.00x0.52x0.38 mm), 2 terminals, non-polar
- **KiCad footprint:** `Diode_SMD:D_0402_1005Metric`
- **Alt footprint:** `Capacitor_SMD:C_0402_1005Metric`
- **Pad-numbering check:** DS footprint: pads 0.50x0.65 at 0.90 mm centre spacing; KiCad 0402 pads ~0.59x0.64 at +-0.48 - compatible. Non-polar: pin order irrelevant.

| Pin | Name | Function |
|---|---|---|
| 1 | Line | RF line (shunt) |
| 2 | GND | Ground |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| D_ESD | KLXES15AAA1 shunt | 0402 | SMA centre / RF line right at connector ↔ GND (via at pad) | DS sec. 9 |
| C_dcblk | DC block after ESD (keep, gap-type suppressor triggers at ~450 V) | 0402 | RF line ↔ SP3T_in RFin | PART_SELECTION 13 |

**Notes**

- Trigger 450 V, clamp 40 V (8 kV contact), VDC max 5 V, leakage <10 nA, C 0.05 pF @10 MHz. RF data at GHz unverified (clone).

---

## BWSMA-KE-P001

- **MPN / mfr:** BWSMA-KE-P001 (BAT WIRELESS); **LCSC:** C496550
- **Function:** SMA female (jack, inner hole), board-edge straddle mount, 'offset pin', 0-6 GHz
- **Source:** claude_db/esp32_sdr_datasheets/BWSMA-KE-P001.pdf p4 (spec), p6 (mechanical drawing)
- **Package:** 6.5 mm square flange, 13.5 mm long; rear: centre pin d0.95 + 2 upper legs (same plane as centre pin) + 2 lower legs, legs 0.9 wide, 4 mm long; vertical gap between upper and lower legs 1.7 mm -> straddles a 1.6 mm board
- **KiCad footprint:** `Connector_Coaxial:SMA_Samtec_SMA-J-P-X-ST-EM1_EdgeMount`
- **Pad-numbering check:** Footprint exists. Pads: centre 1.27x3.6 (F.Cu) at x=0; GND 1.35x4.2 at x=+-2.825 on F.Cu AND B.Cu. BWSMA legs span x=2.1..3.0 (pad spans 2.15..3.5) and 4 mm long (pad 4.2) -> geometric fit OK on paper (UNVERIFIED by test fit). Centre pin d0.95 lies on the top surface like the Samtec.

| Pin | Name | Function |
|---|---|---|
| 1 | Centre | RF |
| 2 | Body (4 legs) | GND |

**Custom land pattern `BWSMA-KE-P001_EdgeMount_1.6mm (if preferred)`** (mm; origin: board edge, centre line; +y into board)

```json
{
 "units": "mm",
 "origin": "board edge, centre line; +y into board",
 "pads": {
  "1": {
   "layer": "F.Cu",
   "at": [
    0,
    2.1
   ],
   "size": [
    1.2,
    4.2
   ]
  },
  "2a": {
   "layer": "F.Cu",
   "at": [
    -2.55,
    2.1
   ],
   "size": [
    1.3,
    4.2
   ]
  },
  "2b": {
   "layer": "F.Cu",
   "at": [
    2.55,
    2.1
   ],
   "size": [
    1.3,
    4.2
   ]
  },
  "2c": {
   "layer": "B.Cu",
   "at": [
    -2.55,
    2.1
   ],
   "size": [
    1.3,
    4.2
   ]
  },
  "2d": {
   "layer": "B.Cu",
   "at": [
    2.55,
    2.1
   ],
   "size": [
    1.3,
    4.2
   ]
  }
 },
 "note": "pads start at board edge; stitch GND pads F/B with >=4 vias each; void L2 (and L3 if needed) under pad 1 to keep ~50 ohm on the 1.2 mm wide pad; taper to the 50 ohm microstrip"
}
```

**Notes**

- Earlier notes called it 'SMD edge/board-side'; the drawing confirms a straddle edge-mount for ~1.6 mm boards (gap 1.7 mm). Use 1.6 mm board thickness.
- No RL data at 6 GHz in DS (only IL 0.15 dB @6 GHz). Alternatives listed in PART_SELECTION (C496549 Z001 THT, DreamLNK C914556).

---

## GD25Q32ESIGR

- **MPN / mfr:** GD25Q32ESIGR (GigaDevice); **LCSC:** C2832998
- **Function:** 32 Mbit (4 MB) QSPI NOR flash, 2.7-3.6 V
- **Source:** claude_db/esp32_sdr_datasheets/GD25Q32ESIGR.pdf (LCSC copy) p4-5 pin assignment, Table 1; LCSC package field 'SOP-8-208mil'
- **Package:** SOP-8 208 mil (5.23 mm body width, 7.9 mm lead span), 1.27 mm pitch
- **KiCad footprint:** `Package_SO:SOIC-8_5.23x5.23mm_P1.27mm`
- **Pad-numbering check:** The 'S' package code = SOP8 208mil (LCSC lists SOP-8-208mil). Do NOT use SOIC-8_3.9x4.9mm. Standard numbering 1-4 left, 5-8 right = DS.

| Pin | Name | Function |
|---|---|---|
| 1 | CS# | Chip select (ESP32 SPICS0) |
| 2 | SO (IO1) | Data out / IO1 (SPIQ) |
| 3 | WP# (IO2) | Write protect / IO2 (SPIWP) |
| 4 | VSS | Ground |
| 5 | SI (IO0) | Data in / IO0 (SPID) |
| 6 | SCLK | Clock (SPICLK) |
| 7 | HOLD# (IO3) | Hold / IO3 (SPIHD) |
| 8 | VCC | 2.7-3.6 V |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_flash | 100nF (+1uF) | 0402 | U.8 ↔ GND | common practice |
| R_CS | 10k pull-up (CS# must not float after power-up) | 0402 | U.1 ↔ VCC | DS Table 1 note |

**Notes**

- ESP32-S31 flash pin mapping per Espressif HW guide/ref schematic (not extracted here).

---

## HR911130C

- **MPN / mfr:** HR911130C (HanRun); **LCSC:** C50933
- **Function:** RJ45 jack, integrated 10/100/1000BASE-T magnetics (1CT:1CT), Bob-Smith termination, green+yellow LEDs, shielded, THT, tab-up
- **Source:** claude_db/esp32_sdr_datasheets/HR911130C.pdf p1 (schematic), p2 (mechanical, LED table), p3 (PCB layout, component-side view)
- **Package:** THT 16.00 W x 21.20 D x 13.30 H mm (body [16.0, 21.2, 13.3] mm)
- **KiCad footprint:** none in library, so use the custom land pattern below
- **Pad-numbering check:** No HR911130C in Connector_RJ. RJ45_Hanrun_HR911105A_Horizontal is a 10/100 jack with 8 signal pins (LEDs 9-12) - pin count/positions differ, NOT usable.

| Pin | Name | Function |
|---|---|---|
| 1 | CT (common) | All four chip-side centre taps tied: decouple 100nF to GND (Espressif ref: 0.1uF/50V per TCT) - do not power for voltage-mode PHY (YT8531 / RTL8211F) |
| 2 | MDI0+ (TRD0+) | PHY MDI0_P |
| 3 | MDI0- (TRD0-) | PHY MDI0_N |
| 4 | MDI1+ | PHY MDI1_P |
| 7 | MDI1- | PHY MDI1_N |
| 5 | MDI2+ | PHY MDI2_P |
| 6 | MDI2- | PHY MDI2_N |
| 8 | MDI3+ | PHY MDI3_P |
| 9 | MDI3- | PHY MDI3_N |
| 10 | CHS GND | Bob-Smith node (4x75R + internal 1000pF/2kV) - connect to chassis/shield GND or board GND |
| 11 | LED_G anode | Green LED (left) anode |
| 12 | LED_G cathode | Green LED cathode |
| 13 | LED_Y cathode | Yellow LED (right) cathode |
| 14 | LED_Y anode | Yellow LED anode |
| SH | Shield | Shell tabs -> chassis GND (to board GND via 0R/1nF 2kV) |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| C_CT | 100nF 50V | 0603 | J.1 CT ↔ GND | Espressif CoreBoard schematic (C65-C69 0.1uF/50V on TCT1-4) |
| R_LEDG | 330R-1k (LED 20 mA max, VF 1.8-2.8 V) | 0603 | PHY LED pin / 3V3 ↔ J.11 or J.12 | DS p2 LED table; polarity depends on PHY LED drive |
| R_LEDY | 330R-1k | 0603 | PHY LED pin / 3V3 ↔ J.14 or J.13 | DS p2 |
| R_SH | 0R or 1M || 1nF/2kV | 1206 | J.SH / J.10 ↔ GND | suggestion |

**Custom land pattern `RJ45_Hanrun_HR911130C_Horizontal`** (mm; origin: midpoint between the two d3.25 pegs, component side (top) view, +x right, +y toward the rear (away from the panel/opening))

```json
{
 "units": "mm",
 "origin": "midpoint between the two d3.25 pegs, component side (top) view, +x right, +y toward the rear (away from the panel/opening)",
 "front_face_y": -10.8,
 "rear_y": 10.4,
 "body_width": 16.0,
 "holes": {
  "PEG_L": {
   "at": [
    -5.715,
    0.0
   ],
   "drill": 3.25,
   "type": "NPTH"
  },
  "PEG_R": {
   "at": [
    5.715,
    0.0
   ],
   "drill": 3.25,
   "type": "NPTH"
  },
  "SH_L": {
   "at": [
    -7.745,
    3.05
   ],
   "drill": 1.63,
   "pad": 2.5,
   "type": "PTH shield"
  },
  "SH_R": {
   "at": [
    7.745,
    3.05
   ],
   "drill": 1.63,
   "pad": 2.5,
   "type": "PTH shield"
  },
  "14": {
   "at": [
    -6.625,
    -4.9
   ],
   "drill": 1.02,
   "pad": 1.6
  },
  "13": {
   "at": [
    -4.085,
    -4.9
   ],
   "drill": 1.02,
   "pad": 1.6
  },
  "12": {
   "at": [
    4.085,
    -4.9
   ],
   "drill": 1.02,
   "pad": 1.6
  },
  "11": {
   "at": [
    6.625,
    -4.9
   ],
   "drill": 1.02,
   "pad": 1.6
  },
  "1": {
   "at": [
    5.715,
    8.89
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "2": {
   "at": [
    4.445,
    6.35
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "3": {
   "at": [
    3.175,
    8.89
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "4": {
   "at": [
    1.905,
    6.35
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "5": {
   "at": [
    0.635,
    8.89
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "6": {
   "at": [
    -0.635,
    6.35
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "7": {
   "at": [
    -1.905,
    8.89
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "8": {
   "at": [
    -3.175,
    6.35
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "9": {
   "at": [
    -4.445,
    8.89
   ],
   "drill": 0.89,
   "pad": 1.4
  },
  "10": {
   "at": [
    -5.715,
    6.35
   ],
   "drill": 0.89,
   "pad": 1.4
  }
 },
 "check": "p3 dims: pegs 11.43 apart; shield 15.49 apart, 3.05 behind pegs; LED pins 13.25 (outer) / 2.54 inset, 4.90 in front of pegs; signal rows 6.35 and 8.89 behind pegs (8.89-2.54), 1.27 pitch staggered, pin 6/5 at -/+0.635 from centre line. Positions read from drawing: pin x values snapped to the 1.27 grid. Pad diameters are suggestions."
}
```

**Notes**

- Signal pin numbering is HanRun's (1-10 incl. CT and CHS), not RJ45 contact numbering (J1-J8).
- Operating 0-70 C.

---

## UART_HEADER_1x3

- **MPN / mfr:** 2.54-1*3P pin header (BOOMELE (any)); **LCSC:** C49257
- **Function:** 3-pin UART0 header (hand-soldered, D11)
- **Source:** JLC parts API 2026-11-09 (C49257, extended); ESP32-S31 HW design guidelines 1.3.7 (U0TXD=GPIO58, U0RXD=GPIO59, 499R series on TX)
- **Package:** 1x3 2.54 mm THT
- **KiCad footprint:** `Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical`
- **Pad-numbering check:** exists

| Pin | Name | Function |
|---|---|---|
| 1 | GND | Ground |
| 2 | TXD (from ESP32) | ESP32 U0TXD = GPIO58 via 499R |
| 3 | RXD (into ESP32) | ESP32 U0RXD = GPIO59 |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| R_TX | 499R | 0603 | ESP32 GPIO58 ↔ J.2 | S31 HW guide 1.3.7 |

**Notes**

- Order/labels are a suggestion; silkscreen them.

---

## TACT_SW_TS-1187A-B-A-B

- **MPN / mfr:** TS-1187A-B-A-B (XKB Connection); **LCSC:** C318884
- **Function:** SMD tact switch 5.1x5.1x1.5 mm, 4 pads (JLC BASIC part, 833k stock, $0.02) - x2: BOOT and RESET
- **Source:** claude_db/esp32_sdr_datasheets/TS-1187A-B-A-B.pdf (XKB drawing): PCB layout top view; JLC API: componentLibraryType 'base'
- **Package:** SMD-4P 5.1x5.1 mm; land: pads 1.0x0.75 at x=+-3.0, y=+-1.875 (7.0/5.0 and 4.5/3.0 mm spans)
- **KiCad footprint:** `Button_Switch_SMD:SW_SPST_TL3342`
- **Pad-numbering check:** TL3342 pads 1.7x1.0 at (+-3.15, +-1.9) cover the XKB land (1.0x0.75 at +-3.0, +-1.875). TL3342 pad '1' = top pair, '2' = bottom pair; XKB: A-B (top pair) internally connected, C-D (bottom pair) connected, switch between pairs -> matches.

| Pin | Name | Function |
|---|---|---|
| 1 (A,B) | Contact 1 | pair, internally shorted |
| 2 (C,D) | Contact 2 | pair, internally shorted |

**Application circuit**

| Ref | Value | Pkg | Connects | Source |
|---|---|---|---|---|
| SW_BOOT | TS-1187A-B-A-B | SMD | ESP32 GPIO61 ↔ GND | S31 HW guide Table 4: GPIO61=0 at reset release -> Joint Download Boot (GPIO60 must be 1) |
| R_BOOT | 10k pull-up (optional; check internal pull in S31 datasheet) | 0402 | GPIO61 ↔ 3V3 | UNVERIFIED default pull |
| SW_RST | TS-1187A-B-A-B | SMD | ESP32 CHIP_PU ↔ GND | S31 HW guide 1.3.x CHIP_PU |
| R_PU | 10k | 0402 | CHIP_PU ↔ 3V3 | S31 HW guide: RC delay R=10k |
| C_PU | 1uF | 0402 | CHIP_PU ↔ GND | S31 HW guide: C=1uF; CHIP_PU must not float |

**Notes**

- The switch is a JLC basic part; at Standard PCBA the basic/extended loading fee is the same anyway (PART_SELECTION).

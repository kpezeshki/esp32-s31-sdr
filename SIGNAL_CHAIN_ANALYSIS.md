# ESP32-S31 RX-only SDR: signal-chain analysis (rev 1, 2026-11-09: switch-first band selection, no diplexer)

Scope: a low-cost, receive-only, general-purpose SDR board. The RF front end is an LNA, then an integrated PLL/VCO + mixer (RFFC507x), then a 2.4 GHz IF filter, then the ESP32-S31's Wi-Fi receiver used as a raw I/Q digitizer (ESP-SDR hack), then gigabit Ethernet. A 0 Ω link selects either the mixer path or the ESP32's native 2.4 GHz front end, each on its own SMA. Board: 4-layer FR4 from JLCPCB.

Files:
- `analysis/cascade.py` computes the gain, NF, IIP3 and P1dB cascade and the power level at every node. Output goes to `analysis/export/cascade_tables.md` and `auto_nf_contrib.png`/`auto_levels_*.png`.
- `analysis/freqplan.py` covers LO selection, images, the mixer spur search and the IF choice. Output goes to `analysis/export/freqplan_tables.md` and `auto_freqplan.png`/`auto_spurs.png`/`auto_if_choice.png`.
- Datasheets are in `claude_db/esp32_sdr_datasheets/`. They include the RFFC5071/5072 and the SPF5189Z.

Numbers tagged **[DS]** come from a datasheet. Numbers tagged **[ESP-SDR]** come from the ESPARGOS esp-sdr docs. Everything else is an engineering assumption that has to be replaced with real part data during part selection.

---

## 0. Summary

1. **What the ESP32-S31 can do as a digitizer** [ESP-SDR]:
   - It streams 8-bit I/Q continuously at up to **40 MS/s over GbE**, or 20 MS/s over HS-USB. The streaming firmware is still marked experimental.
   - Its PLL locks from about **2.20 to 2.85 GHz**. Below roughly 2.15 GHz it fails.
   - Analog channel bandwidth is 13–54 MHz.
   - Gain is set by an index that is *not calibrated in dB*. The Wi-Fi AGC does **not** protect the ADC from strong continuous signals, so we have to use manual gain.
   - This defines the IF: any IF from 2.2 to 2.85 GHz works. **2441 MHz (the 2.4 GHz ISM band)** is the obvious choice because it is the best-characterized point and the cheapest SAW/BAW filters are made for it.
2. **The IF filter does not reject the image.** Once the mixer has folded the image onto the IF, no filter after it can separate the two. Image rejection has to come from an **RF preselector before the mixer**. The IF SAW still matters for other reasons: it stops LO leakage, RF feedthrough and broadband mixer noise from reaching the ESP32. The architecture therefore needs both filters.
3. **Recommended frequency plan:**
   - **Low band (LB), 50–1750 MHz:** up-convert with a **high-side LO = IF + RF** (2.49–4.19 GHz). The image sits at 2·IF + RF (4.9–6.6 GHz), and the IF-feedthrough frequency (2.44 GHz) is out of band, so a 1.75 GHz low-pass removes both. In the passband the worst spur is about 55 dBc. The low-side LO choice is worse: it has a 1×3 response at roughly 15 dBc for RF > 1 GHz.
   - **High band (HB), 2.95–6.0 GHz:** down-convert with a **low-side LO = RF − IF** (0.5–3.56 GHz). The image is at |RF − 2·IF| (0–1.9 GHz), so a high-pass filter removes it. The HB has a structural weakness:
     - 1×3 and 1×5 LO-harmonic responses fall inside any broadband HB filter. They cost about 15–22 dBc over roughly 3.5–4.1 GHz and 4.5–5.25 GHz.
     - There is a hole near RF = 2·IF = 4.88 GHz, where the LO itself lands in the IF.
     - Clean reception there needs a narrow application filter. I recommend leaving an optional BPF footprint, for example 5.8 GHz.
   - **Native ESP32 path:** 2.20–2.85 GHz.
   - **Coverage gaps:** 1.75–2.2 GHz, 2.85–2.95 GHz, and everything below about 50 MHz. With ESP-SDR you cannot shift the IF to cover these.
4. **Power levels and noise figure.** The table below assumes an ESP32 NF of 5 dB. Every figure except the clip level excludes the ESP32's own gain and ADC.

   | Path | Gain to ESP32 pin | System NF | Input IIP3 | Input P1dB | Noise in 40 MHz | 8-bit in-band clip (antenna) |
   |---|---|---|---|---|---|---|
   | LB, LNA only (100/1090/1600 MHz) | +12 / +6 / +3 dB | 2.5 / 4.5 / 6.4 dB | +2 / +8 / +11 dBm | −9 / −3 / 0 dBm | −95 to −92 dBm | ≈ −50 dBm |
   | **LB + gain block (chosen, D3)** | +28 / +22 / +18 dB | **1.6 / 1.7 / 2.0 dB** | −15 / −8 / −5 dBm | −25 / −19 / −15 dBm | −96 dBm | ≈ −52 dBm |
   | HB, LNA only (3.5/5.8 GHz) | +4 / −1.5 dB | 6.3 / 10.2 dB | +5 / +6 dBm | −6 / −5 dBm | −92 / −88 dBm | ≈ −46 dBm |
   | **HB + gain block (chosen, D3)** | +18 / +11 dB | **2.9 / 4.5 dB** | −8 / −6 dBm | −19 / −17 dBm | −95 / −94 dBm | ≈ −50 dBm |
   | Native ESP32 (2.44 GHz) | −0.7 dB | ≈5.7 dB | (ESP32) | (ESP32) | −92 dBm | ≈ −48 dBm |

   - **The RFFC507x is the dominant noise source.** Its NF is 11–13 dB [DS] and its conversion gain is about −4 dB [DS], so 20 dB of LNA gain is not enough. The LB also loses NF at its top end because SPF5189Z-class gain falls to 13.8 dB at 1.7 GHz [DS].
   - **A second gain stage before the mixer roughly halves the NF.** A wideband gain block of about 15 dB does this. An IF amplifier after the SAW does not help much (0.6–1 dB), because the mixer noise is already in the signal.
   - **The cost is linearity.** Input P1dB drops to about −20 dBm. In-band, the 8-bit ADC is still the real limit: it clips at about −50 dBm per 40 MHz. Out of band, strong signals inside the band filter's passband (FM broadcast, cellular) can compress the gain block or produce IM3 products. Since the filters now come after the LNA, the LNA itself sees the whole antenna spectrum. That is fine for the LB LNA (OIP3 +38 dBm). The HB LNA gets a cheap 2nd-order high-pass in front of it.
   - **Recommendation: populate the gain block with a 0 Ω bypass** and decide on rev A by measurement. If you want it switchable from software, an SPDT pair adds about $0.6.
5. **The 8-bit ADC sets the dynamic range.** Put the ESP32's manual gain where the analog noise sits about 6 dB above quantization noise. That gives about **44 dB of instantaneous dynamic range in 40 MHz**. In a narrow channel it is more: about 80 dB in 10 kHz for a single strong carrier. The analog chain (SFDR 80–90 dB in 10 kHz) is never the in-band limit.
6. **Nothing in the chain can be over-driven into the ESP32.** The mixer saturates at about +7 dBm output, which is about +4 dBm at the ESP32 pin. The ESP32's rated maximum RX level is +5 dBm [DS].
7. **Risks to check before layout:**
   - Whether the ESP32's PHY transmits during calibration. Its startup and background calibration "can transmit" [ESP-SDR], and that energy would go back into the mixer IF port and out of the native SMA.
   - Whether the ESP32-S31 accepts an external 40 MHz clock. The plan is one shared TCXO for both chips.
   - RFFC507x performance with an IF of 2.44 GHz and an LO up to 4.2 GHz. The datasheet plots stop at 2 GHz. HackRF One runs the same chip with a 2.3–2.7 GHz IF, which suggests it works.
   - Which GbE PHY the ESP-SDR S31 streaming firmware supports.

---

## 1. Architecture

```
                         ┌─ LB: LNA_LB (SPF5189Z-class, 5 V) ─ LPF 1.75 GHz (0402 LC) ────────────────┐
SMA_MIX ─ ESD ─ SPDT_in ─┤                                                                            SPDT_out ─ [gain block | 0R] ─ balun 1:2 ─┐
                         └─ HB: HPF2 (2 parts) ─ LNA_HB (0.5–6 GHz) ─ HPF 2.95 GHz (0402 LC) ─ [opt. app BPF | 0R] ┘                          │
                                                                                                                         RFFC5072 mixer
            40 MHz TCXO ──────────┬──────────────── REF_IN (RFFC507x, LO 85–4200 MHz, frac-N) ◄────────────────────────────┤
                                  │                                                                                         │
                                  │                     4:1 LTCC balun 2.45 GHz ─ SAW/BAW 2400–2483 ─ [opt IF LNA | 0R] ◄─┘
                                  │                                                                      │
                                  │                                                                  ┌─[0R]─┐ 3-pad tee
SMA_NAT ─ ESD ──────────────────────────────────────────────────────────────────────────────────────┴─[0R]─┴── π-match ─ ESP32-S31 ANT
                                  └──── XTAL_P (if external clock is supported) ── ESP32-S31 ── RGMII ── GbE PHY ── RJ45 magjack
```

Notes on the choices:
- **RFFC5072 instead of RFFC5071.** The 5072 has one mixer, uses the same synthesizer, and costs less. The 5071's second mixer would only help in one design, where each band gets its own balun and mixer and the two open-collector outputs are tied together at the IF. That design is undocumented and risky, so I don't recommend it.
- **Switch first, then one LNA per band, then the band filter (decision D1, revised 2026-11-09: no diplexer):**
  - The input SPDT costs 0.4–0.9 dB of NF. That is less than a lumped diplexer arm, which would cost 0.6–1.5 dB.
  - The image and IF-feedthrough filters sit **after** the LNA, so their loss and Q barely affect NF. They are standalone 50 Ω ladders, which avoids the junction interaction of a diplexer.
  - Both SPDTs are the same part and run from one ESP32 GPIO (about $0.3–0.6 each).
  - The LNA sees the unfiltered antenna. The LB SPF5189Z class handles that (OIP3 +38 dBm). The HB LNA gets a 2-element high-pass (series C, shunt L) to keep FM, VHF and UHF out.
- **Mixer-or-native selection uses a 0 Ω link, as you asked.** Use a three-pad footprint whose shared middle pad is the ESP32 RF net, with an 0402 0 Ω placed to one side or the other. The unused branch then leaves only about 0.5 mm of open stub. At 2.4 GHz λg is about 68 mm, so that stub is negligible. You can fit a DC-block capacitor instead of the 0 Ω.
- **Shared 40 MHz TCXO.** Both the LO and the ESP32's tuning come from one reference, so the frequency error at the input is RF × ε, the same as a single-conversion radio. With independent crystals it would be RF × ε₁ + IF × (ε₁ − ε₂). The RFFC507x REF_IN accepts 10–104 MHz at 0.5–1.5 Vpp AC-coupled [DS], which suits a clipped-sine TCXO.

## 2. Stage parameters (inputs to `cascade.py`)

| Stage | Gain | NF | IIP3 / P1dB (input) | Source / comment |
|---|---|---|---|---|
| SMA + ESD + 5–10 mm GCPW on FR4 | −0.3 (LB), −0.4…−0.6 (HB) | = loss | – | FR4 tanδ ≈ 0.02 costs ≈ 0.03 dB/mm at 6 GHz. Keep the run from SMA to LNA under 10 mm. |
| SPDT_in (band select) | −0.4 (LB), −0.6…−0.9 (HB) | = loss | IIP3 +60 | Assumed, typical of SOI switches. Before the LNA, so its loss adds directly to NF. |
| HB pre-LNA HPF (2nd order) | −0.3 | = loss | – | Assumed. HB only. |
| LNA_LB, SPF5189Z-class, 5 V / 90 mA | 23 (100 MHz)…18.7 (0.9 GHz)…13.8 (1.7 GHz) | 0.8 / 0.55 / 0.75 | OIP3 +38.5, OP1dB +22.4 | [DS] at 0.8–1.7 GHz. Below 0.8 GHz is extrapolated. The genuine Qorvo part is NRND and clones are plentiful, so a successor part needs to be chosen. |
| LNA_HB, 0.5–6 GHz MMIC | 18 (3 GHz)…15 (6 GHz) | 1.1…1.5 | OIP3 +25, OP1dB +12 | Assumed, roughly MGA-665P8 class (1.45 dB / 16 dB at 5.25 GHz). |
| Post-LNA band filter (0402 LC ladder, 7th-order elliptic) | −0.8…−1.6 (LB LPF), −1.2…−1.6 (HB HPF) | = loss | – | Assumed. A lumped low-pass re-enters at about 5–8 GHz through parasitics, so check this against the LB image band (4.9–7.6 GHz). |
| SPDT_out | −0.4 (LB), −0.6…−0.9 (HB) | = loss | IIP3 +60 | Same part as SPDT_in. |
| Gain block (optional, 0 Ω bypass) | 16…15…12 | 3.0…3.5…4.5 | OIP3 +32…+25, OP1dB +18…+14 | Assumed, generic 50 MHz–6 GHz MMIC. |
| Input balun 1:2 (50 Ω → 100 Ω diff) | −1.0 (LB), −1.2…−1.8 (HB) | = loss | – | The RFFC507x input is 100 Ω differential [DS]. A wideband transformer costs about $1–3. Fallback: drive single-ended with the other pin AC-grounded (worse IIP2 and isolation). |
| RFFC507x mixer + 4:1 IF LTCC balun | −5 (LB), −6…−8 (HB) | 13 (LB), 14…16 (HB) | IIP3 +22 (LB) / +20…+16 (HB); IP1dB ≈ +11 | [DS] at a 100 MHz IF: Gc −3…−5 dB, NF 11–13 dB, IIP3 +23…+25 dBm, IP1dB +11…+12 dBm (MIX_IDD 4–5). I derated these for the 2.44 GHz IF and for RF above 2 GHz. |
| IF SAW/BAW 2400–2483.5 MHz | −2.5 | 2.5 | – | Assumed, typical of Wi-Fi SAW/BAW parts. |
| Optional IF LNA, 2.4 GHz | 14 | 1.3 | OIP3 +25 | Assumed. |
| 0 Ω tee + ESP32 π-match | −0.4 | = loss | – | |
| ESP32-S31 receiver | n/a | **5 (assumed)** | AGC / manual | See 2.6. |

### 2.6 ESP32-S31 noise figure
From the datasheet sensitivities [DS Table 6-4]:
- 802.11b 1 Mbps at −99.5 dBm, with an 11 MHz noise bandwidth (−103.6 dBm), 10.4 dB DSSS processing gain and Eb/N0 ≈ 10 dB, implies NF ≈ 4.5 dB.
- 802.11g 6 Mbps at −94.5 dBm, with a 16.6 MHz noise bandwidth (−101.8 dBm) and about 5 dB required SNR, implies NF ≈ 2.3 dB.

So the chip itself has an NF of roughly 2.5–4.5 dB, measured at the pin under the best Wi-Fi gain state. I used **5 dB** because ESP-SDR's manual gain table may not be in the best state. The sensitivity table in `cascade_tables.md` shows the trade-off:
- The native path follows the ESP32's NF one for one.
- The mixer path with the gain block barely moves: 2.2 → 2.3 dB in LB even if the ESP32 NF were 10 dB.
- The mixer path without the gain block depends on it heavily: 4.1 → 6.3 dB in LB.

## 3. Power levels through the chain

See `analysis/export/cascade_tables.md` for every node at antenna levels of −100, −60 and −30 dBm. The plots are `auto_levels_lb1090.png` and `auto_levels_hb5800.png`.

Example: **LB 1090 MHz (ADS-B), with the gain block.** The second column is the output-referred noise density at that node.

| Node | Gain from antenna | Noise | −100 dBm signal | −30 dBm signal | Stage limit (output) |
|---|---|---|---|---|---|
| Antenna | 0 | −174.0 dBm/Hz (−98.0 dBm/40 MHz) | −100 | −30 | |
| LNA_LB out | +16.1 | −155.8 dBm/Hz | −83.9 | −13.9 | OP1dB +22.4 (36 dB margin) |
| Gain block out | +31.2 | −140.7 dBm/Hz | −68.8 | +1.2 | OP1dB ≈ +17.5 (16 dB margin) |
| Mixer input (after balun) | +30.2 | −141.7 dBm/Hz | −69.8 | +0.2 | IP1dB ≈ +11 (11 dB margin) |
| Mixer + IF balun out | +25.2 | −146.6 dBm/Hz | −74.8 | −4.8 | OP1dB ≈ +7 |
| ESP32 pin | +22.3 | −149.5 dBm/Hz (−73.5 dBm/40 MHz) | −77.7 | −7.7 | ESP32 max RX +5 dBm [DS] |

Things to notice:
- **The first stage to compress is the mixer.** It hits input P1dB at about −19 dBm at the antenna in this configuration, and at about −4 dBm without the gain block. The gain block itself compresses about 6 dB later, at about −13 dBm.
- **At the ESP32 pin, the noise in 40 MHz is about −73.5 dBm.** This is about 20 dB above the ESP32's own input noise (−98 + 5 = −93 dBm), which is why the ESP32 NF stops mattering. It also means the ESP32's internal gain must run about 20 dB below maximum. That is good for its linearity.
- **ADC loading:**
  - The 8-bit I/Q quantization noise is −49.9 dBFS in 40 MHz, which is −125.9 dBFS/Hz.
  - Put the analog noise at −44 dBFS. A carrier at the antenna then reaches full scale at −96 + 44 ≈ **−52 dBm in band**.
  - Multiple carriers need crest-factor back-off of about 6–10 dB.
  - The in-band clip point does not depend on the front-end gain, because the ESP32's internal gain absorbs it. The front-end gain only moves the NF and the out-of-band compression point.
- **Out-of-band blockers inside the preselector passband.** Example: you are tuned to 1090 MHz and an FM broadcast station 1 km away puts −25 dBm at the antenna.
  - With the gain block: IM3 = 3·(−25) − 2·(−9) ≈ −57 dBm input-referred. Only IM3 products that land in your channel matter. The 2nd harmonic (190–216 MHz) is not a problem at 1090 MHz.
  - Without the gain block (IIP3 about +7): the same calculation gives about −89 dBm.
  - This is the main reason to keep the 0 Ω bypass.

### LO leakage into the ESP32 (low RF only)
- The RFFC507x LO leaks out of its IF port at about −35 to −50 dBm for LO ≤ 2 GHz [DS fig., p.16]. I assume −30 dBm at 2.5–4.2 GHz, where there is no data.
- With the high-side plan, the LO is offset from the IF by exactly RF. A typical 2.4 GHz SAW gives about 10/25/35/45 dB of rejection at 60/100/150/≥250 MHz offset.
- The resulting LO level at the ESP32 pin:
  - RF = 50 MHz: about −35 dBm, inside the SAW skirt. It forces the ESP32 gain down and desensitizes the receiver.
  - RF = 100 MHz: about −58 dBm, close to the noise power and just outside the ESP32 analog filter. Usable with BW ≤ 20 MHz.
  - RF ≥ 150 MHz: −65 dBm or lower. The ESP32's analog LPF and decimation remove it.
- **The practical lower limit of the mixer path is therefore about 70–100 MHz at full bandwidth.** 50–100 MHz works with reduced capture bandwidth, and FM broadcast is marginal. This has to be measured on rev A.

### Native path
SMA, ESD, then the ESP32 directly. NF ≈ ESP32 NF + 0.7 dB. There is no external filtering, so the ESP32's own selectivity is all you get. It is fine for 2.4 GHz ISM and LTE B7/B41/B40.

## 4. Frequency plan and spurs (`freqplan.py`)

`auto_freqplan.png` shows the LO, image, half-IF and 1×3 locations against RF. `auto_spurs.png` and `auto_if_choice.png` show the worst spur from an input *inside* the preselector passband. The spur levels use a generic Gilbert-cell table:
- 1×3 ≈ 15 dBc (3rd harmonic of a square-wave LO)
- 1×5 ≈ 22 dBc
- 1×2 ≈ 35 dBc (balance)
- 2×n ≈ 55–65 dBc and 3×n ≈ 65–70 dBc, both at −10 dBm into the mixer

These are assumptions. The RFFC507x datasheet gives no spur table, so this is a rev A measurement item.

| Band | LO choice | Image | Worst in-passband spur |
|---|---|---|---|
| LB 50–1750, LPF 1.75 G | **LO = IF + RF** | 2 IF + RF = 4.9–6.6 GHz (rejected by the LPF) | 2×0 at 1220 MHz (RF harmonic at the IF), plus the half-IF 2×2 at RF + 1220 (for RF < 530 MHz): about **55–60 dBc** |
| LB | LO = IF − RF | 2 IF − RF = 3.1–4.9 GHz | 1×3 at 2 IF − 3 RF for RF > 1 GHz: **15 dBc**. Rejected. |
| HB 2.95–6.0, one HPF | LO = RF − IF | \|RF − 2 IF\| = 0–1.9 GHz (rejected by the HPF) | 1×3 / 1×5 at 15–22 dBc over 2.95–5.26 GHz |
| HB split 2.95–3.7 / 3.7–6.0 | same | same | 15–22 dBc only at about 3.5–4.1 GHz (1×5) and 4.49–5.26 GHz (1×3). Otherwise 35–65 dBc. |

Conclusions:
- **LB is clean with one LPF and the high-side LO.** The LPF must still give ≥ 50 dB from 4.9 GHz up to about 7.6 GHz to cover the image and the 3·LO ± IF 1×3 responses. The SPF5189Z's falling gain above 4 GHz helps. A lumped LPF made of 0402 parts will re-enter, so simulate it with real component models or use an LTCC LPF.
- **HB with a broadband HPF works as a look-around receiver but not a clean one.** For each application, add a narrow BPF in an optional footprint. One example is a 5.65–5.925 GHz FPV filter, whose 1×2 input at 4.26 GHz then falls outside the filter.
- **Moving the IF to 2350 MHz** (an LTE B40 SAW, 2300–2400) moves the 1×3 region down to 4.37–5.13 GHz. That cleans up U-NII-1 (5.15–5.25 GHz) but does nothing above 5.4 GHz. It also puts the IF next to 2.4 GHz Wi-Fi channel 1. The gain is small, so I recommend **staying at 2441**.
- **Hole at RF ≈ 4.86–4.92 GHz.** Here LO ≈ IF and the LO leaks straight into the IF. Small IF shifts within the SAW passband move the hole by ±20–40 MHz.

## 5. Bandwidth and data path
- 40 MS/s × 2 × 8 bit = 640 Mb/s, so GbE is required. The S31 GMAC uses an RGMII-style 4-bit interface [DS pin list]. Use **the same PHY as Espressif's S31 reference design**, so the ESP-IDF driver and the esp-sdr streaming firmware run unchanged. Candidates are RTL8211F and YT8531. To be confirmed.
- Fallback: 20 MS/s over HS-USB. The USB 2.0 HS OTG pins are on the chip, so a USB-C connector gives both power and a backup data path for about $0.3.

## 6. Power budget (rough)
| Rail | Load | Current |
|---|---|---|
| 5 V | LNA_LB 90 mA *or* LNA_HB about 20 mA (power-gated by band); gain block about 60 mA | ≈ 150 mA |
| 3.3 V | ESP32-S31 RX + CPU streaming (about 110 mA RX [DS] + CPU), GbE PHY (about 100–150 mA), RFFC507x (100–125 mA [DS]), TCXO, flash | ≈ 450–500 mA |
| Total | | ≈ 2.3 W, which USB-C at 5 V / 1 A covers. PoE would add about $3–5 and is not recommended for a cost-optimized board. |

Use a low-noise LDO for the RFFC507x analog and VCO rails, and for the LNA bias. Buck converters cause spurs that land right in the 8-bit DR budget, so run them at a fixed frequency and filter them.

## 7. PCB notes (4-layer JLC FR4)
- Use a stack-up with a thin L1–L2 prepreg, for example JLC04161H-3313 at about 0.1 mm. 50 Ω GCPW then comes out at about 0.2 mm wide, which matches 0402 pads. L2 is solid ground, L3 carries power, and L4 carries slow signals.
- Keep every RF run short. At 6 GHz FR4 costs about 0.03 dB/mm, so 30 mm is about 1 dB, which goes straight into the HB NF.
- Stitch vias along all RF lines. Isolate the 2.44 GHz IF trace from the HB LO (0.5–3.6 GHz) and from the ESP32 digital section. Ambient 2.4 GHz Wi-Fi picked up directly on the IF trace is an in-band interferer. Leave room for a can or fence around the mixer, IF and ESP32 RF area.
- Put footprints for 0402 π-pads at the mixer input and the ESP32 input, populated with 0 Ω by default. They let you trade NF for linearity, or absorb ESP32 calibration TX bursts, without a respin.

## 8. Open risks and what to verify
| # | Risk | Check before layout | Fallback |
|---|---|---|---|
| R1 | The ESP32 PHY transmits during its startup or background calibration. That energy goes into the SAW and the mixer IF port (abs max +15 dBm [DS]) and out of the native SMA. | Ask on the esp-sdr issue tracker or read the code. Measure on a devkit with a spectrum analyzer. | A 3–6 dB pad footprint before the ESP32. Firmware: stored calibration, TX calibration disabled. |
| R2 | The ESP32-S31 may not accept an external 40 MHz clock on XTAL_P. | S31 hardware design guidelines. | A separate 40 MHz crystal for the ESP32 and a TCXO for the RFFC (an extra frequency error of IF × Δε). |
| R3 | RFFC507x Gc, NF and LO leakage at a 2.44 GHz IF and a 4.2 GHz LO are uncharacterized above 2 GHz in the datasheet. | HackRF One schematics and measurements (same chip, 2.3–2.7 GHz IF). The RFFC5071A datasheet revision. | Margin is already in the derating. |
| R4 | ESP-SDR S31 streaming is experimental. Its gain table is in indices, not dB. | Run esp-sdr on an S31 devkit before tape-out. Map gain index to dB with a signal generator. | 20 MS/s over USB. |
| R5 | Lumped 0402 band filters: parasitic re-entry (LPF), and tolerance of the 2.95 GHz HPF edge. | Simulate with vendor S-parameters (Murata/Coilcraft) and run a Monte-Carlo on tolerances. | An LTCC LPF/HPF (about $0.3–1.5 each). |
| R6 | SPF5189Z is NRND. | Choose a currently produced pin-compatible SOT-89 pHEMT LNA. | Clones. |
| R7 | 1×3 / 1×5 spurs in HB. | Measure them on rev A. | Application BPF footprint. |

## 9. Decisions needed from you
Decided 2026-11-09 (see DECISIONS.md):
- D1: SPDT band switching, with no diplexer. A switch at the input and filters after the LNA.
- D2: keep 3–6 GHz.
- D3: gain block with a 0 Ω bypass.
- D4: wideband transformer balun.
- D5: USB-C 5 V with linear regulators.
- D7: **strongly cost-driven.** The ESP32 approach only makes sense if the BOM stays far below an AD9361/AD9363 design. Every part choice is judged on cost first.

## 10. Rev 1 updates from the risk research (2026-11-09, details in RISK_RESEARCH.md)

| Finding | Evidence | Change to the design |
|---|---|---|
| **R1. The ESP32 transmits calibration tones at every boot.** `esp_wifi_start()` runs the normal PHY calibration. On the C5 this was measured at 0.35–0.7 s of tones out of the antenna after each reset. The power on the S31 is unknown, so assume up to the PA's +21 dBm. Periodic recalibration is compiled out of the S31 streaming build (`CONFIG_ESP_PHY_DISABLE_PLL_TRACK=y`). | esp-sdr `streaming/receiver.c:518`, issue #9 | **Fit a 3 dB π-pad (0402 basic resistors, 300 Ω / 18 Ω / 300 Ω) between the 0 Ω tee and the ESP32 match by default.** Worst case at the mixer IF port: +21 − 3 (pad) − about 3.5 (SAW + balun) = **+14.5 dBm**, which is under the +15 dBm abs max [DS]. NF cost is 0.1–0.4 dB: LB 1.6/1.8/2.2 dB, HB 3.1/4.9 dB. Measure the real tone level on rev A, then decide whether to replace the pad with 0 Ω. |
| **R2. An external 40 MHz clock is allowed.** "For an active crystal oscillator, connect to P and leave N floating", ±10 ppm. The 24 nH series inductor on XTAL_P stays. | S31 datasheet pin table, HW design guidelines | **One 40 MHz TCXO feeds both chips** through AC coupling and a divider to about 0.8–1 Vpp each. Optional buffer. |
| The 40 MHz reference harmonic 61 × 40 = 2440 MHz sits inside the IF. | arithmetic | **The IF moves to 2440 MHz.** The reference harmonic then lands on DC, together with the zero-IF DC spike, which is already a dead bin. ESP-SDR tunes in 1 MHz steps from 2150 to 2800 MHz. The RFFC5072 LO takes up any fine offset. |
| **R3. Streaming firmware.** It targets the ESP32-S31-Function-CoreBoard-1 (S31NRV16, PSRAM required). It uses the IDF *generic* PHY driver (MDC 5, MDIO 6, reset 7, RGMII on GPIO 8–19), and the reference board's PHY is the YT8531. Rates are 4/8/16/20/40 MS/s, 8-bit I/Q. **Rates below 40 MS/s simply drop samples, with no filter, so they alias.** The receiver is zero-IF, so there is a DC spike. **GPIO 20–25, 33–40, 42–44 carry the internal sample bus and GPIO35 the capture clock. They must stay unconnected.** GPIO36 is the flash-voltage strap, so set the flash voltage by eFuse. | `streaming/network.c:183-190`, `receiver.c:41,474-504`, `control.c:96` | Use the **YT8531 PHY** (cheapest, and the reference choice). Run at 40 MS/s and decimate on the host. Leave those GPIOs unrouted. Control GPIOs we need: RFFC SPI (3) + ENBL + RESETX, band SPDT (1), LNA power gates (2). That leaves plenty. |
| **R4. RFFC5072 at a 2.4 GHz IF works, by HackRF precedent.** HackRF One runs a 2.34–2.74 GHz IF, LO up to about 4.5 GHz (unreliable above about 4.4), MIX_IDD = 2, no IF filter, 1.88 GHz LPF and 2.4 GHz HPF, and it hops the IF to dodge spurs. | HackRF schematics and firmware | Our LO tops out at 4.19 GHz, which leaves margin. **Option:** replace the 83 MHz ISM SAW with a wider 2.3–2.6 GHz IF filter (or none, as HackRF does) so the IF can hop by about ±100 MHz to dodge spurs. It moves the HB 1×3 crossover by 2·ΔIF. The narrow SAW is better against LO leakage below 150 MHz. Decide once the part survey shows filter prices. |
| **R5. No ESP32 datasheet gives an abs-max RF input.** The functional maximum is +5 dBm (S31). | datasheets | The mixer chain tops out at about +4 dBm at the pin, or about +1 dBm with the pad. Put an ESD diode on each SMA. |

## 11. Cascade with the selected parts (rev 2, `analysis/cascade_parts.py`)
Chain: PSA4-5043+ (LB) / QPL9503 (HB), BGS12P2L6 ×2, LFCG-1700+ LPF, lumped HB HPF, H3-TCM2-63WX+ balun (2.5 dB at 5–6 GHz), RFFC5072, SAFEA2G45MC0 SAW, 3 dB pad (R1).

| Case | No gain block: NF / P1dB in | **GVA-62+**: NF / P1dB in | GVA-63+: NF / P1dB in |
|---|---|---|---|
| LB 100 MHz | 2.95 dB / −8.8 dBm | **1.55 / −25.3** | 1.50 / −30.6 |
| LB 1090 MHz | 4.64 / −4.5 | **1.62 / −20.1** | 1.47 / −25.3 |
| LB 1700 MHz | 6.25 / −1.9 | **1.96 / −17.4** | 1.71 / −22.1 |
| HB 3500 MHz | 4.98 / −9.4 | **2.18 / −24.6** | 2.08 / −27.3 |
| HB 5800 MHz | 6.89 / −11.1 | **2.75 / −25.6** | 2.65 / −27.1 |

- **Gain block: GVA-62+.** GVA-63+ improves NF by only 0.05–0.25 dB but costs about 5 dB of compression headroom. The 0 Ω bypass (D3) stays for strong-signal sites.
- The QPL9503's high gain makes HB much better than in rev 0: NF 2.2–2.8 dB, compared with 2.9–4.5 dB.
- **HB high-pass spec.** No catalog LTCC part meets it (PART_SELECTION slot 15). Ambient 2.4 GHz Wi-Fi at −30 dBm reaches the IF through the mixer's RF→IF feedthrough of about 40 dB:
  - With 25 dB of HPF rejection at 2.44 GHz, it shows up as an in-band interferer about 20 dB above the 40 MHz noise floor.
  - With 35 dB, about 10 dB above.
  - Proposal: a lumped elliptic HPF with a transmission zero placed *on* 2.40–2.48 GHz (≥ 45 dB in that band) and the **HB lower edge raised to 3.1 GHz**, which relaxes the transition band. The 2.95–3.1 GHz loss is small, mostly S-band radar. To be designed in the filter phase.

## 12. Three-band mixer path (rev 3, 2026-11-09: D13, D14)

```
                       ┌─ LB  50–1750 MHz : PSA4-5043+ ─ LFCG-1700+ LPF ──────────────────────────────┐
SMA_MIX ─ ESD ─ SP3T_in┼─ MB 1750–2150 MHz: (same PSA4-5043+ via its own SP3T port, 2nd LNA footprint) ─ BPF (0402, IF notch) ┤ SP3T_out ─ [GVA-62+ | 0R] ─ H3-TCM2 ─ RFFC5072 ...
                       └─ HB 3100–6000 MHz: HPF2 (1.6 pF / 2 nH) ─ QPL9503 ─ HPF (0402, IF notch) ─ [app BPF | 0R] ┘
```
LB and MB need the same LNA but different filters. Two ways to wire it:
- **(a) Two PSA4-5043+**, one each in the LB and MB arms. This costs one extra LNA ($1.91) but no extra part *type*. **Recommended:** the LNA always sits before its filter, and the SP3T stays 1 in, 3 out.
- **(b) One LNA before SP3T_in.** The MB/LB LNA is then in front of the switch, and the HB arm would need its own path.

Band table (IF = 2440 MHz):

| Band | RF | LO | Image (rejected by) | Worst in-band spur | NF (GVA-62+) | Input P1dB |
|---|---|---|---|---|---|---|
| LB | 50–1750 MHz | IF + RF = 2.49–4.19 GHz | 2IF + RF = 4.93–6.63 GHz (LFCG-1700+) | ≈55 dBc | 1.5–2.0 dB | −17 to −25 dBm |
| MB | 1750–2150 MHz | IF − RF = 290–690 MHz | 2IF − RF = 2.73–3.13 GHz (MB BPF) | ≈60 dBc (35 dBc at 2.10–2.15 GHz, 1×2) | 2.2–2.5 dB | −15 dBm |
| Native | 2150–2800 MHz | ESP32 internal | – | – | ≈5.7 dB + pad | – |
| HB | 3100–6000 MHz | RF − IF = 0.66–3.56 GHz | \|RF − 2IF\| ≤ 1.78 GHz (HB HPF) | 15–22 dBc over 3.1–5.26 GHz (1×3/1×5); use the app-BPF footprint | 2.1–3.0 dB | −25 dBm |
| Gap | 2800–3100 MHz | | | | | |

- **Switches: Infineon BGS13SN8 SP3T ×2,** $0.32 at LCSC (292 in stock), TSNP-8 1.1×1.1 mm. IL 0.22/0.25/0.28/0.33/0.65 dB typ at 0.7–0.96/1.4–2.0/1.9–2.2/2.2–2.7/5.15–5.7 GHz. Isolation 35/30/27/25/15 dB. P0.1dB ≥ +34 dBm [DS]. Control is V1/V2 from 1.35 V up to VDD, so both switches share **2 GPIOs**.
  - The datasheet range is **0.1–6 GHz**, so 50–100 MHz is outside spec and has to be verified on rev A. Fallback is the SKY13317 (20 MHz–6 GHz, $1.91, DFN-8 1.5×1.5, a different footprint).
- **MB 1×3 inputs** sit at 3RF − 2IF = 0.37–1.57 GHz. The 1×3 response is only about 15 dBc, so the **MB BPF must give ≥ 40 dB below 1.55 GHz**. Together that is about 55 dBc.

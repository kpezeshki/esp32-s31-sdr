# ESP32-S31 RX-only SDR: open-risk research (R1–R5), 2026-11-09

Scope: answers to risks R1–R5 raised in `SIGNAL_CHAIN_ANALYSIS.md` §0.7 and §8. Every claim comes with evidence. Tags used:
- **[CODE]** the esp-sdr repo, cloned at `a8eaac1` (2026-11-09) from https://github.com/ESPARGOS/esp-sdr. It was read only, never built or run.
- **[IDF]** ESP-IDF at commit `c712a0dd`, the commit `firmware-targets.json` pins for the `esp32s31-stream` profile. I sparse-fetched `components/esp_phy`, `components/esp_eth` and the docs.
- **[DS]** a vendor datasheet or hardware design guideline (HDG).
- **[HRF]** the HackRF repo, cloned at `3a63b29` (2026-11-05) from https://github.com/greatscottgadgets/hackrf. The netlist was exported with `kicad-cli`.
- **[ISSUE]** an esp-sdr GitHub issue.
- **UNVERIFIED** marks a claim that I inferred but could not confirm.

Paths written `esp-sdr/…` are relative to the clone at `/tmp/claude-1000/-home-kaveh-claude/73262aa8-2faf-4273-a4fa-c18966225833/scratchpad/esp-sdr`. The scratchpad may be cleaned, so re-clone at the commit above if needed.

---

## Bottom line

| # | Question | Answer | Action before layout |
|---|---|---|---|
| R1 | Does the S31 transmit during calibration? | **Yes, at boot.** `esp_wifi_start()` runs the PHY calibration, and that calibration puts tones out of the antenna pin for about 0.35–0.7 s after every reset. This was measured on the C5, and the same code path runs on the S31. ESP-SDR's own retune calibration was changed so it no longer runs the loopback IQ step, which removed the retune tone on C3, S3 and C5. Nobody has measured this on the S31. In the S31 streaming build the periodic temperature-tracking recalibration (RX and TX cal) is compiled out (`CONFIG_ESP_PHY_DISABLE_PLL_TRACK=y`). **No absolute tone power has been published.** The only hard upper bound is the PA's rated output, about +21 dBm. | Stop the boot tone from reaching the mixer: an IF amplifier with reverse isolation, or an RF switch that defaults to a 50 Ω load. See §R1. |
| R2 | Can a TCXO drive XTAL_P? | **Yes.** Datasheet Table 2-9 says: "For an active crystal oscillator, connect to P and leave N floating". It must be 40 MHz and within ±10 ppm. No input amplitude is specified for an oscillator. The other Espressif HDGs (S2) say to AC-couple through about 50 pF. | Drive both chips from one 40 MHz TCXO, each through its own AC coupling and level divider. Keep the 24 nH series inductor on XTAL_P. Keep a crystal footprint as a fallback. |
| R3 | What does the S31 streaming firmware expect? | The **ESP32-S31-Function-CoreBoard-1**: WROOM-3 module, 16 MB flash, 16 MB octal PSRAM (= ESP32-S31NRV16), **Motorcomm YT8531 over RGMII**, MDC=5, MDIO=6, PHY reset=7, RGMII on GPIO 8–19. It streams 8-bit I/Q at 4/8/16/20/40 MS/s, tunes 2150–2800 MHz in **1 MHz steps**, and takes JSON over HTTP or USB. It is direct-conversion, so there is a DC spike, which the firmware corrects with its DC DACs. It needs PSRAM (`CONFIG_SPIRAM=y`, XIP from PSRAM). **17 GPIOs are used as an internal loopback and must stay unconnected**, including the strapping pins GPIO36/37. | Copy the CoreBoard's ESP32, Ethernet and USB pin-out exactly. Leave the 17 loopback GPIOs unrouted. Handle the GPIO36 VDD_SPI strap with an eFuse. |
| R4 | Does the RFFC5072 work with a 2.4 GHz IF and a 4.2 GHz LO? | **Yes, by precedent.** HackRF One runs an RFFC5072 with a 2.34–2.74 GHz IF and LO up to about 4.51 GHz. It uses 50:100 Ω baluns rated for 0.3–1 GHz, open-collector outputs on 10 µH chokes, **no IF filter**, and MIX_IDD apparently at 2. HackRF also moves the IF with RF to dodge spurs (Pro: a lookup table over 2320–2570 MHz), and puts the LO on a coarse grid with the fine remainder made up in the IF. No published NF-vs-frequency or LO-leakage data exists for HackRF. | Consider a wider IF filter, about 2.3–2.6 GHz, so the IF can hop. Our ESP32 only steps in 1 MHz, so remove the residual offset with a host-side NCO. |
| R5 | What is the ANT absolute maximum? | **Not specified** in any Espressif datasheet I checked (ESP32, S2, S3, S31, C3, C5, C6, C61, H2, ESP8266). The absolute-maximum tables list only supply voltage. The functional "maximum RX level" is +5 dBm on the S31 (802.11b) and up to +8 dBm (BLE) on other chips. | Keep worst-case drive at or below about +5 dBm. That already holds, since the mixer saturates at about +4 dBm at the pin. Fit an ESD diode on the SMA paths. |

---

## R1. Does the ESP32 PHY transmit out of ANT during calibration in the S31 streaming firmware?

### Answer
- **Startup calibration: yes, it transmits.** `receiver_init()` initializes Wi-Fi normally, and `esp_wifi_start()` runs the ESP-IDF PHY RF calibration.
  - The ESP-SDR contributors measured this calibration putting tones out of the antenna. On ESP32-C5 boards they were visible 0.35–0.7 s after each reset, in 5 MHz steps.
  - Every chip family uses the same ESP-IDF calibration framework. Whether the S31 calibration specifically emits tones is **UNVERIFIED by measurement**, but it is very likely.
- **Power level: unknown.** No absolute level is published. The only quantitative data is relative: at the same listener setting, startup tones reached about −6 dBFS against −11 to −15 dBFS for the old retune tone. That gives no dBm figure.
  - The hard upper bound is the PA's rated output, +21 dBm typical for 802.11b ([DS] S31 Table 6-2).
  - Calibration tones are probably much weaker than full PA power (**UNVERIFIED**). Design for the bound or measure it.
- **Retune calibration (ESP-SDR's own): the TX step is removed.** Re-running the loopback IQ calibration is what produced a tone. On S31 the firmware now preserves the startup IQ coefficients and refreshes only the DC and gain tables.
  - Measurements showed 0/200 tone snapshots after the fix on C3, S3 and C5.
  - The S31 was not in that test set (**UNVERIFIED** for S31).
- **Periodic background calibration: disabled in the S31 streaming build.** The ESP-IDF "PLL track" timer calls `phy_param_track_tot()`. On S31 that routine re-runs RFPLL, Wi-Fi power, **RX cal and TX cal** whenever the temperature drifts.
  - The streaming sdkconfig sets `CONFIG_ESP_PHY_DISABLE_PLL_TRACK=y`, which compiles that timer out.
  - The ESP-SDR docs still warn that "startup and background calibration can still transmit". The firmware also still watches for PHY-initiated DC re-measurements (`rx_recalibration_stale()`). So whether some remaining background path could transmit is **UNVERIFIED**.
- **Wi-Fi traffic:** the code puts the chip in STA mode with promiscuous RX on channel 1, power save off. It never calls connect or scan. By code reading, no packets are transmitted (**UNVERIFIED** by measurement).
- **Can it be disabled?** Partly, and only with a firmware rebuild. The firmware is GPL-3.0, so a fork is allowed.
  1. `CONFIG_ESP_PHY_RF_CAL_NONE=y` together with `CONFIG_ESP_PHY_CALIBRATION_AND_DATA_STORAGE=y`, which is on by default.
     - The first boot, or any boot after an NVS erase, a MAC change, a PHY library version change or corrupt data, still forces a **full** calibration. Later boots skip calibration.
     - Espressif documents NONE only for deep-sleep wake. Whether the startup IQ coefficients ESP-SDR depends on are then restored correctly from NVS is **UNVERIFIED**.
  2. Do the first-boot full calibration at the factory, with ANT terminated in 50 Ω.
  3. Attenuate the tone. `phy_start_tx_tone_step` has a power argument; issue #9 reports that 8 dB of attenuation is fine and that calibration fails at 19 dB. That function is internal, and on the S31 it would mean patching the startup calibration, which is not practical.

### Evidence
- `esp-sdr/main/targets/esp32s31/streaming/receiver.c:512-521`: `esp_wifi_power_domain_on(); esp_phy_rftest_config(1); esp_wifi_init(); … esp_wifi_set_mode(WIFI_MODE_STA); esp_wifi_start(); esp_wifi_set_ps(WIFI_PS_NONE); esp_wifi_set_promiscuous(true); esp_wifi_set_channel(1, …)`. There is no connect or scan anywhere in the streaming sources.
- `receiver.c:104-109`, `prepare_rx()`: `phy_pbus_xpd_tx_off(); phy_pbus_xpd_rx_on(1);`. The TX chain is forced off after every configuration.
- `esp-sdr/docs/rx-controls.md:77-81`: "The PHY can still perform its own startup and background calibration … Startup and background calibration can still transmit; removing the retune IQ sweep does not make the whole firmware RF-silent." Lines 89-91: "H2 and both S31 profiles currently disable periodic PLL tracking".
- `esp-sdr/main/common/rx_recalibration.c:48-49` (C5 branch): "Loopback IQ calibration emits a tone through the antenna. Refresh DC without that TX step." Lines 72-80 (C61/S31 branch): `*flags &= ~0x280u; /* Preserve the startup IQ coefficients; expire only DC/table caches */`.
- `esp-sdr/sdkconfig.defaults.esp32s31-stream:3-5`: `CONFIG_ESP_PHY_ENABLE_CERT_TEST=y`, `CONFIG_ESP_PHY_DEBUG=y`, `CONFIG_ESP_PHY_DISABLE_PLL_TRACK=y`. The partition table `partitions-stream.csv` has `nvs` at 0x9000 and `phy_init`, so calibration data is stored in NVS.
- [ISSUE] https://github.com/ESPARGOS/esp-sdr/issues/9, by contributor 14sea, measured in a shielded box with a second board listening:
  - "every `FREQ` on the C5 runs the PHY's loopback IQ calibration, which drives the transmitter with a test tone about 5 MHz above the LO for several milliseconds. The tone leaks to the antenna…"
  - "A normal start-up emits tones too. Resetting a C5 40 times … 68–152 snapshots with tones in the 0.35–0.7 s after each reset … That is `esp_wifi_start`'s own calibration … the strongest of those tones reach about −6 dBFS, against −11 to −15 dBFS for the retune tone."
  - "It is not C5-specific: … two ESP32-C3 and two ESP32-S3 boards … the listener sees a tone at +5/+6 MHz."
  - "Attenuating the tone instead (third argument of `phy_start_tx_tone_step`) buys about 8 dB before the calibration degrades and fails at 19 dB."
  - The maintainer applied the fix to all targets in commits `77ffc12`, `5ede49b`, `27de31c` and `e74f2a4`. After the fix: "Retune tone: 0 of 200 snapshots on every pair" (C5, C3, S3).
- [IDF] `components/esp_phy/src/phy_common.c:38-56`: with PLL track enabled, `phy_param_track_tot()` reports flags `RFPLL`, `WIFI_POWER`, `RXCAL`, `TXCAL`. The whole block is `#if !CONFIG_ESP_PHY_DISABLE_PLL_TRACK`. `Kconfig:213-220` describes `ESP_PHY_DISABLE_PLL_TRACK` as "Disable pll track (only for experimental) … depends on ESP_PHY_DEBUG".
- [IDF] `components/esp_phy/src/phy_init.c:945-971`: the calibration mode comes from `CONFIG_ESP_PHY_CALIBRATION_MODE`. A deep-sleep reset gives NONE. If loading from NVS fails, it falls back to `PHY_RF_CAL_FULL`. Without NVS storage, FULL is always used.
- [IDF] `components/esp_phy/include/esp_phy_init.h:57-61` defines `PHY_RF_CAL_PARTIAL`, `PHY_RF_CAL_NONE` ("only suggested to be used after deep sleep reset") and `PHY_RF_CAL_FULL`. `Kconfig:156-170` is the `ESP_PHY_CALIBRATION_MODE` choice.
- [IDF] `docs/en/api-guides/RF_calibration.rst:19-43` lists the full-calibration triggers: NVS missing or erased, MAC changed, PHY library version changed, data broken. It says "The no calibration method is only used when the device wakes up from Deep-sleep mode."
- [IDF] `Kconfig:8-21`, help text for `ESP_PHY_CALIBRATION_AND_DATA_STORAGE`: "If your board is easy to be booted up with antenna disconnected … choose 'n'". So the calibration result depends on the load at ANT, which means calibration interacts with the external port.
- [DS] ESP32-S31 HDG §1.3.6 (master, PDF https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s31/esp-hardware-design-guidelines-en-master-esp32s31.pdf): "if RF function is enabled, make sure an antenna is connected. Operation without an antenna may result in unstable behavior or potential damage to the RF circuit."
- [DS] ESP32-S31 datasheet v0.5, Table 6-2: TX power is 21.0 dBm typical for 802.11b and 20 dBm for 11g/n MCS0.
- [DS] RFFC5071/5072 datasheet (Prelim DS101020), absolute maximum ratings: "RF/IF mixer input power +15 dBm".

### What it means for our board
- The calibration tone sits at about 2412 MHz ± a few MHz, the PHY's calibration channels. That is inside the 2400–2483 MHz IF SAW passband, so the SAW does **not** block the tone. The reverse path is ESP32 ANT → π-match → (optional IF LNA) → SAW (about 2 dB) → 4:1 balun → RFFC5072 open-collector IF port.
- The +21 dBm worst-case bound minus about 3 dB of passive loss is **+18 dBm, above the mixer's +15 dBm absolute maximum**. The realistic level is probably far lower, but it is unknown.
- On the native path, the tones leave through SMA_NAT for well under 1 s at each boot. At ISM frequencies and duty cycle that matches a normal Wi-Fi device, so it is a minor regulatory concern. It does matter if a sensitive DUT or LNA is connected to SMA_NAT.
- The ESP32 also needs a sane, roughly 50 Ω load during calibration. The HDG warns of possible damage with the antenna disconnected, and calibration quality depends on the load. The SAW is 50 Ω in band, so that is fine. An open 0 Ω tee with nothing fitted is not.

### Recommended mitigation (pick one or more)
1. **Populate the optional IF amplifier between the SAW and the ESP32.** A typical 2.4 GHz MMIC LNA has |S12| of 20–30 dB.
   - That isolation protects the mixer from any tone level the ESP32 can produce.
   - It also lowers the ESP32's NF contribution.
   - Check the amplifier's own output-port power handling against about +21 dBm (**UNVERIFIED**, part-dependent).
2. **Use an SPDT/SP3T RF switch at the ESP32 ANT** whose power-on default (set by a pull resistor) is a 50 Ω termination. Firmware moves it to the IF or native path after `esp_wifi_start()` returns.
   - This needs about 5 lines added to the GPL fork. `app_main` → `receiver_init()` is the point where `esp_wifi_start()` returns (`receiver.c:518`).
   - This blocks the boot tone from both the mixer and SMA_NAT, and gives the calibration a clean 50 Ω.
   - Cost is about $0.3–0.6 for a switch. The local `SKY13453` and `BGS12*` datasheets are candidates.
3. **Cheap fallback:** a 6 dB π-pad footprint between the SAW and the ESP32. Fit 0 Ω on rev A and measure.
   - A 6 dB pad passes +21 dBm − 6 − 3 = +12 dBm at the worst-case bound, under +15 dBm.
   - It costs ESP32-side NF directly. Use `cascade.py` to check whether the SAW-to-ESP32 NF term matters.
4. **Firmware:** build with `CONFIG_ESP_PHY_RF_CAL_NONE=y` (plus NVS storage) and do the first boot at the factory into a 50 Ω load. Treat this as a secondary measure: it is undocumented for power-on use, and a PHY library update re-triggers a full calibration.
5. **Measure on rev 0.** The CoreBoard's WROOM-3 has a PCB antenna, so conducted measurement there is awkward. Use a WROOM-3U, which has an antenna connector, or our own rev-A board.
   - Set the spectrum analyzer to max-hold at 2.40–2.50 GHz, behind a 30 dB pad, through 20 power cycles.
   - Measure first boot (full cal, after an NVS erase) and later boots (partial cal) separately.

---

## R2. Does the ESP32-S31 accept an external 40 MHz clock on XTAL_P?

### Answer
- **Yes.** The S31 datasheet pin table names active oscillators explicitly: drive **XTAL_P** and leave **XTAL_N floating**.
- The frequency must be **40 MHz**. The firmware supports only a 40 MHz crystal, and the PARLIO sample clock (REF_80M = 2 × XTAL) also derives from it. Accuracy must be within ±10 ppm.
- **No amplitude, waveform or input-impedance spec** is published for the oscillator case, for the S31 or any other family.
  - The only number is for crystals: "recommended that the amplitude of the crystal is greater than 500 mV".
  - The ESP32-S2 HDG is the one Espressif document that describes the oscillator circuit: oscillator → DC-blocking cap of about 50 pF → XTAL_P, with XTAL_N floating.
- The S31 HDG says a **series 24 nH inductor on XTAL_P is "required for normal system startup. Even if RF function is not used, this inductor is still required."** It also reduces the effect of crystal harmonics on RF performance.
  - Keeping it in the oscillator path is my inference (**UNVERIFIED** whether it is needed with an oscillator). Keeping it costs nothing.

### Evidence
- [DS] ESP32-S31 Series Datasheet v0.5 (Pre-release), Table 2-9 "Analog Pins", pins 78/79 XTAL_N/XTAL_P: "External clock input/output for connecting active or passive crystal oscillators of ESP32-S31. For an active crystal oscillator, connect to P and leave N floating." https://documentation.espressif.com/esp32-s31_datasheet_en.pdf. The datasheet also lists the clock tree: XTAL_CLK is a 40 MHz external crystal; BBPLL, CPLL, MPLL, APLL and XTALX2 are all referenced to XTAL_CLK.
- [DS] ESP32-S31 HDG §1.3.5 "External Crystal Clock Source (Compulsory)": "The ESP32-S31 firmware only supports 40 MHz crystal … accuracy … within ±10 ppm. A series inductor must be added on the XTAL_P clock trace … 24 nH (0201). This inductor is required for normal system startup … It is recommended that the amplitude of the crystal is greater than 500 mV." The S31 HDG has **no** oscillator paragraph or figure.
- [DS] ESP32-S2 HDG §1.3.5: "If an oscillator is used, its output should be connected to XTAL_P on the chip through a DC blocking capacitor (about 50 pF). XTAL_N can be floating. Please make sure that the oscillator output is stable and its accuracy is within ±10 ppm. It is also recommended that the circuit design for the oscillator is compatible with the use of the crystal…" https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s2/
- [DS] Current HDGs for ESP32, S3, C3, C5, C6, C61, H2 and P4 (master PDFs downloaded 2026-11-09) cover only the crystal. None has oscillator text.
  - ESP32: series element 0 Ω initially.
  - S3/C3/C5/C6/C61/H2: 24 nH.
  - P4: 40 MHz, no inductor mentioned.
  - **C5: 48 MHz**, not 40.
- Forum (not official): Espressif staff on esp32.com/viewtopic.php?t=2742 say an external oscillator works if it meets the stability requirements, connected to XTAL_P. The often-quoted "<1.2 V sine / <1 V square" limits apply to the **32 kHz** input, not XTAL_P.
- [DS] RFFC5071/5072 datasheet p.2: external reference 10–104 MHz, level **500 / 800 / 1500 mVp-p (min/typ/max), AC-coupled**. Pin 10 REF_IN: "Use AC coupling capacitor."
- [HRF] HackRF drives RFFC REF_IN from an Si5351C CMOS output (CLK4, net `MIX_CLK`) through **33 pF in series (C67) and 100 pF shunt (C70)**. That capacitive divider brings 3.3 Vpp down to about 0.8 Vpp. Netlist from `hardware/hackrf-one/frontend.kicad_sch`. The firmware uses a 40 MHz RFFC reference (`firmware/common/rffc5071.c`, `REF_FREQ_HZ 40 MHz`).

### What it means for our board
- One shared 40 MHz TCXO is supported in principle. Both loads want AC coupling and roughly 0.5–1.5 Vpp: RFFC 0.5–1.5 Vpp, and ESP32 "> 500 mV" by analogy with the crystal spec.
- Unknowns:
  - the ESP32 XTAL_P input impedance and maximum safe swing;
  - whether a clipped-sine TCXO (about 0.8 Vpp into 10 kΩ‖10 pF) can drive two loads plus traces and still meet both minimums.
- A shared reference also makes the ESP32's 80 MS/s sample clock TCXO-accurate.
- Spur warning (frequency-plan detail, not a show-stopper):
  - The 61st harmonic of 40 MHz is **2440 MHz**, 1 MHz from our 2441 MHz IF centre.
  - The esp-sdr capture clock is REF_80M, output on GPIO35 and looped back. Its harmonics fall at 2400 and 2480 MHz.
  - The Ethernet PHY's 25 MHz crystal has harmonics at 2425, 2450 and 2475 MHz.
  - A square-wave reference makes the odd harmonics worse. A clipped-sine TCXO or a filtered buffer is better.

### Recommended mitigation
1. Use a TCXO (clipped sine, ±0.5–2 ppm, 40.000 MHz) into a **single-gate CMOS buffer or a 1:2 clock fan-out**. Drive each output through a **series R or C plus a shunt C divider to about 0.8–1.0 Vpp**, as HackRF does with 33 pF + 100 pF, AC-coupled.
   - Into the ESP32: DC block of about 50 pF, then the 24 nH series inductor, then XTAL_P. Leave XTAL_N open.
   - Into the RFFC: 33 pF + 100 pF as in HackRF.
2. Keep a **40 MHz crystal footprint and its load caps** for the ESP32 (DNP), with 0 Ω options, as the S2 HDG recommends. If the oscillator drive fails, the fallback is the "two crystals" plan in `SIGNAL_CHAIN_ANALYSIS.md` R2.
3. Verify on rev A: the ESP32 boots, the Wi-Fi frequency offset is within ±10 ppm (HDG TX-tone test, or check an RX CW tone), and the PLL locks across temperature.
4. Frequency plan: put the IF so that n×40 and n×25 MHz harmonics fall away from DC and from the band of interest, or accept them as known spurs. The current IF of 2441 MHz puts one at −1 MHz. Consider 2445 or 2430 MHz, and recheck in `freqplan.py`.

---

## R3. What the S31 continuous-streaming firmware expects

### Answer (all from the code)
| Item | Value | Evidence |
|---|---|---|
| Dev board | **ESP32-S31-Function-CoreBoard-1**: ESP32-S31-WROOM-3 module, 16 MB flash, 16 MB PSRAM, PCB antenna, RJ45 GbE, ES8311 codec | `docs/s31-streaming.md:5-7`; `firmware-targets.json` profile `esp32s31-stream`, label "ESP32-S31 Function-CoreBoard · Ethernet / USB for SoapyESPSDR"; [DS] esp-dev-kits S31 user guide, ordering table "ESP32-S31-Function-CoreBoard-1 / WROOM-3 / 16 MB / 16 MB / PCB" |
| Chip variant | Needs in-package PSRAM. **ESP32-S31NRV16** (16 MB octal PSRAM) matches the devkit. The only other variant is NRV32 (32 MB), which is likely compatible (**UNVERIFIED**). Flash is external. | `sdkconfig.defaults.esp32s31-stream:12-16` (`CONFIG_SPIRAM=y`, `SPIRAM_MODE_OCT`, `SPIRAM_SPEED_250M`, `SPIRAM_XIP_FROM_PSRAM=y`); [DS] S31 datasheet Table 1-1 (NRV16 / NRV32, QFN80 8×8) |
| Flash size | sdkconfig says 16 MB. The app partition is 3 MB at 0x10000, so a 4 MB flash would hold the image if `ESPTOOLPY_FLASHSIZE` is changed (**UNVERIFIED**; the web-flasher image may assume 16 MB) | `sdkconfig.defaults.esp32s31-stream:2`, `partitions-stream.csv` |
| Ethernet MAC/PHY | Internal EMAC, **RGMII**, `esp_eth_phy_new_generic()` with address autodetect (`phy_addr=-1`). The PHY is the **Motorcomm YT8531** (named in the docs). Firmware writes YT8531 extended registers: 0xA001 bit 8 (`RXC_DLY_EN`, RX clock 2 ns delay) and 0xA003 GE/FE TX delay = 13 (×150 ps = 1.95 ns). | `streaming/network.c:178-209`; `docs/s31-streaming.md:5-6`; register meaning per Linux `drivers/net/phy/motorcomm.c` (`YT8521_CHIP_CONFIG_REG 0xA001`, `YT8521_CCR_RXC_DLY_EN BIT(8)`, `YT8521_RGMII_CONFIG1_REG 0xA003`, `GE_TX_DELAY_MASK GENMASK(3,0)`, `FE_TX_DELAY_MASK GENMASK(7,4)`, 150 ps steps) |
| Ethernet GPIOs | MDC = **GPIO5**, MDIO = **GPIO6**, PHY reset = **GPIO7** (set in code). RGMII from the IDF default for S31: TXD0..3 = **8, 9, 10, 11**; TX_CTL = **12**; TX_CLK = **13**; RX_CLK = **14**; RX_CTL = **15**; RXD3..0 = **16, 17, 18, 19**. No reference clock out (`clock_phy_ref_gpio = -1`), so the PHY needs its own 25 MHz crystal. | `network.c:184-188`; [IDF] `components/esp_eth/include/esp_eth_mac_esp.h:273-318` (`#elif CONFIG_IDF_TARGET_ESP32S31`, `.interface = EMAC_DATA_INTERFACE_RGMII`); [DS] S31 datasheet pin table lists `GMAC_PHY_TXD0..3_PAD` on GPIO8–11 and `GMAC_PHY_TXEN_PAD` on GPIO12 as IO-MUX P1 functions |
| **Reserved GPIOs (must stay unconnected)** | **GPIO20–25, 33, 34, 36–40, 42–44** carry the 16 data bits of the internal loopback from the diagnostic bus through the GPIO matrix into PARLIO. **GPIO35** outputs the 80 MHz capture clock and loops it back. All are configured `GPIO_MODE_INPUT_OUTPUT` and driven. | `streaming/receiver.c:41-44` (`SAMPLE_CLOCK_PIN 35`, `pins[16] = {20,21,22,23,24,25,33,34,36,37,38,39,40,42,43,44}`), `:469-505`; `docs/s31-streaming.md:102-106` ("which must stay unconnected") |
| Strap conflict | GPIO36 and GPIO37 are **strapping pins**, floating by default. GPIO36 selects **VDD_SPI 3.3 V or 1.8 V** unless the eFuse `PMU_FLASH_POWER_SEL_EN` is burnt. GPIO37 selects the JTAG source. GPIO33/34 are the USB-Serial/JTAG pins, so that port is not usable. | [DS] S31 datasheet §3, Table 3-1 (GPIO36/37 "Floating"), Table 3-4 (VDD_SPI control), §2.3.5 P3 list |
| Console / flashing | UART0 **GPIO58 (TX) / GPIO59 (RX)**. Flash over UART; the firmware "takes over the USB PHY". Boot straps are GPIO60/61 (weak pull-up). | `docs/s31-streaming.md:29-31`; `sdkconfig.defaults.esp32s31:23-24` (UART pins 58/59, burst profile); `README.md:49`; [DS] S31 datasheet Table 3-3 |
| USB streaming | High-speed USB (dedicated USB_DP/DM pins 44/45), VID:PID 303a:4531, vendor class, up to 20 MS/s | `docs/s31-streaming.md:12, 43-47`; `streaming/stream.h:245-246` |
| Sample format | Signed **8-bit I + 8-bit Q**: the upper 8 of the 10-bit diagnostic-bus samples, because PARLIO has one 16-bit unit. Packet = 32-byte header ("ESR2", version 2, bits = 8, epoch, rate, 64-bit sample position, µs timestamp) + 672 I/Q pairs = 1376 B, one per UDP datagram. I+jQ is not negated. | `docs/s31-streaming.md:74-93, 126-128`; `stream.h:240-255` |
| Sample rates | **4, 8, 16, 20, 40 MS/s** over GbE; USB up to 20. All are taken from an 80 MHz REF clock through the PARLIO divider, so **lower rates keep every n-th sample with no decimation filter**. At 4 and 8 MS/s, aliasing cannot be prevented with the 13 MHz minimum analog bandwidth. 40 MS/s needs about 687 Mbit/s and a 32 MB host `rmem_max`. | `control.c:100-104`; `receiver.c:43, 353-361`; `docs/s31-streaming.md:9-13, 36-39, 130-132` |
| Control protocol | Ethernet: `POST /api/rx` with JSON; USB: bulk EP 01/81. Ops `status`, `configure`, `start` (UDP port), `stop`. Fields: `frequency` (Hz), `rate`, `gain` (PHY table index 0…`gain_max`), `agc` (0 manual / 1 hardware), `bandwidth` (0 or 13–54 MHz in 1 MHz steps; 0 = follow the rate, minimum 13), `dc_correction` (0/1). Unauthenticated. | `docs/s31-streaming.md:41-70`; `control.c:83-120` |
| Tuning range | `frequency` is accepted **2150–2800 MHz in 1 MHz steps** only. Measured reception on C61/S31 is about 2150/2200–2850 MHz. The tuning sequence: calibrate on a Wi-Fi channel, then program the PLL directly (`phy_set_freq`), then run a PLL capacitor recovery below 2400 MHz. | `control.c:96`; `targets/esp32s31/tuning.h:1-15`; `common/rx_pll_cal.h`; `docs/rx-controls.md:116-136` |
| Gain | Index into the PHY's generated gain table. `gain_max` is read from register `0x2010702c` bits 8–14. Not calibrated in dB. Default 40. The hardware AGC is a packet AGC and does not protect against continuous strong signals. | `receiver.c:71, 128-143`; `docs/rx-controls.md:11-18` |
| DC behaviour | **Direct conversion**, LO = tuned frequency, so there is a DC spike at the centre. On each start with manual gain, the firmware re-runs the PHY RX DC cal, then measures the residual (50 ms settle, ≥16384 samples) and trims the two baseband DC DACs using a 2×2 Jacobian, in at most 5 steps. AGC mode relies on the PHY's own DC tables. Docs: "Experimental. Signal quality, especially the DC peak, still needs work." User report: the residual DC wanders by about 1 LSB at 0–40 kHz. | `streaming/dc.c`; `docs/s31-streaming.md:3, 134-144`; [ISSUE] #21 closing comment by rkucbel1 |
| Stability | Issue #21: a ring-lap corruption (19 % of samples misplaced at 40 MS/s) was fixed on 2026-11-08 (`ddc31f9`, `89193f1`). After the fix the reporter saw about 27 dB equalized SNR and −28 dB EVM on a 20 MHz 64-QAM OFDM signal at 40 MS/s. | [ISSUE] https://github.com/ESPARGOS/esp-sdr/issues/21 |
| IDF dependency | Pinned to ESP-IDF `c712a0dd`, `idf.py --preview`. It wraps private PHY symbols (`--wrap=phy_write_gain_mem`, `phy_set_channel_rfpll_freq`) and hard-codes register addresses. **Any IDF or PHY library bump can break it.** | `firmware-targets.json`; `streaming/CMakeLists.txt:8-9`; `docs/s31-streaming.md:19-20` |

### What it means for our board
- Copy the **CoreBoard's** ESP32-to-YT8531 RGMII wiring, power, strapping and USB exactly. That way the unmodified `esp32s31-stream` image runs on our board.
  - The EMAC pins are IO-MUX-fixed (P1), so this is mandatory anyway.
  - Another RGMII PHY would need code changes. `esp_eth_phy_new_generic` plus the YT8531-specific delay writes in `network.c:196-209`, which would hit the wrong registers on another PHY.
- **17 GPIOs must be unrouted**: 20–25, 33–40 and 42–44.
  - That leaves roughly GPIO0–4, 26–32, 41, 45–57 and 60/61 for the RFFC5072 3-wire SPI (SCLK, SDATA, ENX, RESETX), the band SPDT control and LEDs. Check each one against the flash/PSRAM pin list in datasheet §2.6.
  - Fewer pins are free if a CoreBoard-style audio codec or other peripherals are copied. Don't copy them.
- **GPIO36 (VDD_SPI strap) cannot take an external pull resistor** without loading a pin that carries live sample data.
  - Either burn eFuse `PMU_FLASH_POWER_SEL_EN` + `PMU_FLASH_POWER_SEL` to fix the flash voltage (3.3 V flash), or
  - check how the WROOM-3 module handles it (**UNVERIFIED**: the CoreBoard schematic PDF is linked from the esp-dev-kits guide and should be checked).
  - A weak pull (≥ 10 kΩ) on a short stub would probably also work (**UNVERIFIED**).
- The **80 MHz clock on GPIO35** is an on-board aggressor. Its harmonics land at 2400 and 2480 MHz, at the SAW band edges. Keep GPIO35 as a pad-only net under the shield.
- Flashing needs UART0 (GPIO58/59), so put a USB-UART bridge or a 6-pin header plus BOOT/EN buttons on the board.
- The 1 MHz tuning step means fine tuning must come from the RFFC5072 LO or a host-side NCO. The ESP32 can't resolve less than 1 MHz.
- DC spike: offset-tune so the signal of interest is not at the ESP32 DC. For example, place the RF signal 3–5 MHz off centre with the LO and shift it back on the host. SoapyESPSDR can also remove DC.
- Use 40 MS/s and decimate on the host. The 4/8 MS/s modes alias, and our SAW (83 MHz wide) does nothing about that.

---

## R4. RFFC5072 with a 2.3–2.7 GHz IF and LO up to 4.2 GHz: what HackRF One does

### Hardware (HackRF One, `hardware/hackrf-one/frontend.kicad_sch` and `baseband.kicad_sch`, netlist via kicad-cli)
| Item | HackRF One | Notes |
|---|---|---|
| Mixer | U4 **RFFC5072TR7** | Single mixer. Firmware comment: the RFFC5071 is a drop-in. |
| Mixer input balun | T1 **TTM/Anaren B0310J50100AHF**, 50 Ω : 100 Ω balanced, 0805. Unbalanced side DC-blocked by C28 100 nF to switch U7 (SKY13453). L1 is a DNP shunt across MIX_IPP/IPN. | The local datasheet says **300–1000 MHz**: IL 0.8 dB, amplitude balance 2.5 dB, phase balance 34°. HackRF uses it far above its rated band, from 1 MHz to 6 GHz. |
| Mixer output | **Open-collector** MIX_OPP/OPN biased to VAA by **L3/L2 = 10 µH** (Taiyo Yuden BRL1608T100M). L4 is a DNP shunt across the outputs. T2 is the **same B0310J50100AHF** (50:100 Ω, not 4:1), then C46 100 nF to switch U10. | The RFFC datasheet specs are stated "Mixer output driving 4:1 balun". HackRF uses 2:1. |
| IF filter | **None.** Mixer → U10 SKY13453 (RX/TX) → U11 SKY13453 (mixer-bypass select) → C48 22 pF → T3 **Johanson 2500BL14M100T** (2.5 GHz 50:100 balun) → MAX2837 RX input. Channel selection is done entirely by the MAX2837 baseband LPF. | |
| Front-end LPF (low-band image filter) | U3 **AVX LP0603A1880ANTR**, 1.88 GHz thin-film LPF | Used for RF < 2170 MHz with a high-side LO |
| Front-end HPF (high-band image filter) | U8 **TDK DEA162400HT-8004B1**, multilayer HPF "for 2400–2500 MHz" (TDK catalog, discontinued) | Used for RF > 2740 MHz with a low-side LO |
| RF amps | U13/U25 **MGA-81563** (about 11 dB, switched in or out) | |
| Reference | Si5351C CLK4 → 33 pF series + 100 pF shunt → REF_IN, at 40 MHz | See R2 |
| Loop filter | C14 8.2 pF, C15 180 pF, C12 330 pF, R3 22 kΩ, R1/R2 470 Ω; REXT R4 51 kΩ | Copy as a starting point |

### Firmware
- **MIX_IDD:** HackRF never sets MIX_IDD explicitly. `rffc5071_init()` writes the default table, which has **reg 0x0B = 0x0400** (`firmware/common/rffc5071.c:66`).
  - HackRF's own bitfield definitions are `P2MIXIDD` = reg 11 bits 11:9 and `P1MIXIDD` = bits 14:12 (`rffc5071_regs.def:132-135`). Decoded, that gives **P2MIXIDD = 2, P1MIXIDD = 0**.
  - HackRF runs the single mixer on **path 2** (`set_RFFC5071_FULLD(0); set_RFFC5071_MODE(1);`, `rffc5071.c:134-136`), so the effective **MIX_IDD = 2**.
  - That sits near the datasheet's low-current setting. The datasheet gives MIX_IDD=1: NF 10 dB, IIP3 +10 dBm, 100 mA; MIX_IDD=6: NF 13 dB, IIP3 +23 dBm, 125 mA.
  - This decode uses HackRF's register definitions and is **not cross-checked against the RFMD programming guide (UNVERIFIED)**.
- **Other synthesizer settings** (`rffc5071.c:144-152, 272-342`):
  - dither disabled (`SDM=0b11`);
  - VCO warm-up maximized;
  - reference standby on;
  - LO clamped to 84.375 MHz–**5400 MHz**;
  - above fVCO = 3.2 GHz, `fbkdivlog = 2` and charge-pump leakage = 3.
- **LO is put on a coarse grid on purpose:** "Round to nearest step = ref_MHz / 2**s. For s=6, step=625000 Hz". The low fractional bits are zeroed and `P2NLSB` is left at 0, so the LO avoids fine fractional-N values, which reduces fractional spurs. The IF is then recomputed and the MAX2837 makes up the remainder (`radio.c:570-588`).
- **IF selection, HackRF One** (`firmware/common/tuning.c:32-117`, `radio.c:517-588`):
  - **Bypass** (no mixer): 2170–2740 MHz.
  - **Low band** (RF < 2170 MHz, LPF): **IF = 2650 − RF/7 MHz** (graduated from 2650 down to 2340 MHz). **High-side LO = IF + RF**, so the LO runs from about 2650 up to **about 4510 MHz** at 2170 MHz RF.
  - **High band** (RF > 2740 MHz, HPF): low-side LO = RF − IF, with IF graduated 2170→2740 MHz (2740–3600 RF), 2350→2650 (3600–5100), 2500→2738 (5100–7250). The LO spans about 570 MHz to about 4.5 GHz.
- **IF selection, HackRF Pro (Praline):** a per-segment lookup table instead of a formula. RX IF hops between **2320 and 2570 MHz** every few tens to hundreds of MHz of RF, with high-side injection up to about 2.1 GHz RF (`firmware/common/tune_config.h:241+`, `praline_tune_config_rx`). Sweep mode has its own table (`:93+`). This is how they keep spurs out of band.
- Maintainer statement ([GitHub issue #1725](https://github.com/greatscottgadgets/hackrf/issues/1725), mossmann, 2026-04-09):
  - spurs seen there "appear to be normal";
  - high-side injection below 2100 MHz "suppresses spurs from LO harmonics";
  - from 2100 to 2320 MHz "the RFFC5072 synthesizer does not reliably produce an LO high enough for high-side injection". With an IF around 2.3–2.5 GHz that means an LO of roughly 4.4–4.8 GHz.

### Published measurements
- **NF:** rtl-sdr.com, summarizing David Rowe's real-time NF method (https://www.rtl-sdr.com/measuring-the-noise-figure-of-airspy-and-hackrf-sdrs-in-real-time/), reports HackRF **3.4 dB with the RF amp on and 11.1 dB with it off**. Frequency and gain were not stated in the summary. The Rowetel original returned 403.
  - I found **no NF-vs-frequency sweep** and **no LO-leakage table** for HackRF.
- **Spurs:** a community rule of thumb (hackrf.net guide) is that "bad spurs occur when LO or an integer multiple of LO is within 10 MHz … of RF", attributed to LO leakage in the RFFC5072. A 0xStubs blog measured about −35 dBc internal spurs when using a HackRF as a spectrum analyzer.
- **RFFC5072 datasheet** (local `RFFC5071_5072_RFMD.pdf`, Prelim DS101020):
  - mixer output port range **30–4500 MHz**, so a 2441 MHz IF is in spec;
  - input range 30–6000 MHz;
  - LO 85–4200 MHz;
  - typical step 1.5 Hz.
  - The plots stop at about 2 GHz, as noted before.

### What it means for our board
- The 2.44 GHz IF is proven on the same chip, and so is an LO up to 4.2 GHz: HackRF One routinely uses about 4.5 GHz, above the 4.2 GHz datasheet limit. Our top LB LO of **4.19 GHz has margin**, but test it across temperature on rev A. GSG reports the LO becomes unreliable above about 4.4 GHz.
- Our balun choice is better matched to the datasheet than HackRF's: a 4:1 LTCC at 2.45 GHz on the output, and 1:2 on the input. HackRF uses an out-of-band 0.3–1 GHz part on both ports.
- HackRF has **no IF filter** and gets away with it. Its preselection, the LPF and HPF, keeps 2.4 GHz energy off the mixer RF port, the same as ours.
- The big difference is **IF agility**. HackRF moves the IF over 2.32–2.74 GHz to dodge spurs, which a fixed 2400–2483 MHz SAW prevents. Our ESP32 can tune 2150–2800 MHz.
- Our ESP32 only tunes in **1 MHz** steps. To use a HackRF-style coarse LO grid (625 kHz), the remaining offset must be removed on the host with an NCO, which is free in a 40 MS/s stream. Alternatively, use full fractional resolution and accept the fractional spurs.

### Recommended mitigation
1. Replace the 2400–2483 MHz ISM SAW with a **wider IF bandpass, about 2.3–2.6 GHz** (LTCC or a 2.5 GHz-class part). Or keep the SAW footprint but add a 0 Ω/LTCC alternative. Then port HackRF Pro's IF-hopping table idea into our host driver, using `freqplan.py` to find spur-free IFs per RF segment.
   - The wider filter still rejects LO feedthrough at 2.5–4.2 GHz on the LB only partly. Check against `freqplan.py`, since the LO can lie just above the IF band.
2. Start with **MIX_IDD = 2** (HackRF practice). Fit a register-poke option to try 1 (best NF) and 6 (best IIP3) on rev A.
3. Put the RFFC LO on a coarse grid (for example 625 kHz or 1 MHz), disable dither, set ESP32 IF steps of 1 MHz, and remove the residual offset digitally.
4. Copy HackRF's loop-filter values, 10 µH open-collector chokes and REF_IN divider as the starting schematic. Leave DNP shunt-L footprints across the mixer input and output (L1/L4 in HackRF) for matching at 2.44 GHz.

---

## R5. ESP32 RF input maximum safe power at ANT

### Answer
- **No Espressif datasheet gives an RF input power absolute maximum** at the ANT or LNA_IN pin. I checked ESP32, S2, S3, **S31**, C3, C5, C6, C61, H2 and ESP8266EX. Their absolute-maximum tables list only supply voltage (−0.3 to 3.6 V), cumulative IO current and storage temperature.
- The nearest numbers are functional "maximum RX level" or "maximum received signal" specs, which are performance figures, not damage limits:
  - **ESP32-S31: +5 dBm** (802.11b/g 6 Mbps / n MCS0 / ax MCS0) and 0 dBm (54 Mbps / MCS7 / MCS9), Table 6-5.
  - ESP32-C6, C61, H2, S3 (BLE): **+8 dBm**.
  - C3, C5: +5 dBm.
  - ESP32 (classic) BLE: 0 dBm.
- The ANT pin is shared with an on-chip PA that delivers +21 dBm through an integrated T/R switch. So the RX front end is designed to sit next to +20 dBm of its own TX. That does **not** mean it survives an external +20 dBm while in RX mode (**UNVERIFIED**).

### Evidence
- [DS] ESP32-S31 datasheet v0.5: §5.1 Table 5-1 Absolute Maximum Ratings (no RF entry); §6.1.2 Table 6-5 "2.4 GHz Maximum RX Level". https://documentation.espressif.com/esp32-s31_datasheet_en.pdf
- [DS] ESP32-C3/C5/C6/C61/H2/S2/S3/ESP32 datasheets from `https://documentation.espressif.com/<chip>_datasheet_en.pdf`, downloaded 2026-11-09. Their absolute-maximum tables have no RF entry. C6 Table 6-5 and S3 Table 6-5 give a maximum RX level of +5 dBm (Wi-Fi), and BLE "Maximum received signal @30.8 % PER" is +8 dBm.
- [DS] S31 HDG §1.3.6 is the only damage-related RF statement: running RF without an antenna "may result in … potential damage".

### What it means for our board
- The mixer path cannot overdrive the ESP32. The RFFC5072 output saturates around +7 dBm, which is about +4 dBm at the ESP32 pin after the SAW (`SIGNAL_CHAIN_ANALYSIS.md` §0.6). That is at the +5 dBm functional limit, and an ADC-clipping problem long before any damage.
- If the optional IF LNA is populated, its P1dB/Psat sets the maximum drive. A gain block with Psat ≥ +15 dBm could exceed the +5 dBm functional spec. Pick an IF LNA with P1dB ≤ about +10 dBm, or check that the SAW and mixer saturation limit it.
- The native SMA path is unprotected: whatever is connected goes straight to ANT.

### Recommended mitigation
1. Design rule: **≤ +5 dBm continuous at the ESP32 pin under worst-case drive** (functional limit from the datasheet). Treat anything above +10 dBm as a damage risk (engineering assumption, **UNVERIFIED**).
2. Fit a low-capacitance ESD/TVS diode on each SMA (< 0.3 pF at 2.4 GHz). HackRF uses a Murata **LXES15AAA1-100** bidirectional TVS (D1) at its antenna port.
3. On SMA_NAT, an optional limiter or a 0 Ω/pad footprint is cheap insurance for users who connect a transmitter or a strong LNA.

---

## Additional findings worth carrying into the design
1. **GPIO budget:** 17 loopback GPIOs (R3) plus 15 Ethernet pins (GPIO5–19) plus flash/PSRAM plus UART0 (58/59) plus straps (60/61) leaves a modest set of free GPIOs. Allocate the RFFC SPI and switch controls early.
2. **Clock spurs in the IF window:** 40 MHz × 61 = 2440 MHz, 80 MHz (GPIO35) × 30/31 = 2400/2480 MHz, and the PHY's 25 MHz × 97/98/99 = 2425/2450/2475 MHz. Shield the ESP32 together with the SAW and IF section, and keep RGMII and GPIO35 away from the IF trace. Expect some fixed spurs and plan offset tuning around them.
3. **Firmware fragility:** the streaming image depends on private PHY symbols at a pinned preview IDF commit and is "experimental". The 2026-11-08 ring-lap bug shows it is still moving. Budget for carrying a GPL fork that adds the RF-switch GPIO (R1) and the RFFC5072 control.

## Sources (URLs)
- esp-sdr: https://github.com/ESPARGOS/esp-sdr (commit a8eaac1); docs https://espargos.net/espsdr/; issues #9 https://github.com/ESPARGOS/esp-sdr/issues/9 and #21 https://github.com/ESPARGOS/esp-sdr/issues/21
- ESP-IDF at c712a0dd: https://github.com/espressif/esp-idf/tree/c712a0dde385d659a1470a136251980d31a70bc1 (`components/esp_phy`, `components/esp_eth`); RF calibration guide https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/RF_calibration.html
- ESP32-S31 datasheet v0.5: https://documentation.espressif.com/esp32-s31_datasheet_en.pdf
- ESP32-S31 HDG: https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s31/esp-hardware-design-guidelines-en-master-esp32s31.pdf
- ESP32-S2 HDG (oscillator paragraph): https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s2/esp-hardware-design-guidelines-en-master-esp32s2.pdf
- esp-dev-kits ESP32-S31 (Function-CoreBoard-1): https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s31/esp-dev-kits-en-master-esp32s31.pdf
- Espressif forum, TCXO on XTAL_P: https://esp32.com/viewtopic.php?t=2742
- Linux motorcomm PHY driver (YT8531 registers): https://github.com/torvalds/linux/blob/master/drivers/net/phy/motorcomm.c
- HackRF: https://github.com/greatscottgadgets/hackrf (commit 3a63b29); issue #1725 https://github.com/greatscottgadgets/hackrf/issues/1725
- TDK DEA162400HT-8004B1: https://product.tdk.com/en/system/files?file=dam%2Fdoc%2Fproduct%2Frf%2Frf%2Ffilter%2Fcatalog%2Frf_hpf_dea162400ht-8004b1_en.pdf
- HackRF NF summary: https://www.rtl-sdr.com/measuring-the-noise-figure-of-airspy-and-hackrf-sdrs-in-real-time/
- RFFC5071/5072 datasheet: local `/home/kaveh/claude_out_remote/claude_db/esp32_sdr_datasheets/RFFC5071_5072_RFMD.pdf`

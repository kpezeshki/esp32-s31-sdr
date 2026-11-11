# Gigabit Ethernet PHY circuit: ESP32-S31 → YT8531DC-CA → HR911130C

Netlist data: `hw/phy_circuit.json`. It has 43 components with pin→net maps, plus a `nets` section for the PHY, the magjack and the ESP32 pins. Reference designators (U201, R2xx, C2xx…) are hints in a 200 series to avoid collisions. Items not confirmed from a source are marked **UNVERIFIED**.

## Sources

| Tag | Source |
|---|---|
| [CB] | `claude_db/esp32_sdr_datasheets/ESP32-S31-Function-CoreBoard-1_schematic.pdf` V1.0 (2026-05-13). Page 3 is "03_Ethernet". Page 2 has the module GPIOs. Rendered at 600 dpi and read from crops. |
| [YT] | `claude_db/esp32_sdr_datasheets/YT8531C-CA_YT8531DC-CA_datasheet.pdf` (+ `.txt`), the Motorcomm YT8531(D)H-CA/(D)C-CA/P-CA datasheet (LCSC C22472312 copy) |
| [HR] | `claude_db/esp32_sdr_datasheets/HR911130C.pdf` (+ `.txt`), HanRun Rev B (LCSC C50933 copy) |
| [DS] | ESP32-S31 datasheet, https://documentation.espressif.com/esp32-s31_datasheet_en.html: Table 2-1 (pins/power domains), Table 2-3 (IO MUX), Table 2-8 |
| [IDF] | ESP-IDF c712a0dd (2026-09-07): `esp_eth/include/esp_eth_mac_esp.h` (S31 `ETH_ESP32_EMAC_DEFAULT_CONFIG`), `esp_hal_emac/esp32s31/emac_periph.c` (RGMII IOMUX tables), `esp_eth/src/phy/esp_eth_phy_generic.c` |
| [FW] | esp-sdr `main/targets/esp32s31/streaming/network.c` `network_init()`, `sdkconfig.defaults.esp32s31-stream` |
| [JLC] | JLC parts API, queried 2026-11-09 |

## 1. YT8531DC-CA pin table (QFN-40 5×5, 0.4 mm pitch, EP 3.7×3.7) [YT Table 1, CB p3]

| Pin | Name | Function | Net on our board |
|---|---|---|---|
| 1 | TRXP0 | MDI pair 0 + | MDI0_P → J201.2 |
| 2 | TRXN0 | MDI pair 0 − | MDI0_N → J201.3 |
| 3 | AVDDL | analog 1.1 V | PHY_VDDL (+100 nF C203) |
| 4 | TRXP1 | MDI pair 1 + | MDI1_P → J201.4 |
| 5 | TRXN1 | MDI pair 1 − | MDI1_N → J201.7 |
| 6 | TRXP2 | MDI pair 2 + | MDI2_P → J201.5 |
| 7 | TRXN2 | MDI pair 2 − | MDI2_N → J201.6 |
| 8 | AVDDL | analog 1.1 V | PHY_VDDL (+100 nF C204) |
| 9 | TRXP3 | MDI pair 3 + | MDI3_P → J201.8 |
| 10 | TRXN3 | MDI pair 3 − | MDI3_N → J201.9 |
| 11 | AVDD33 | analog 3.3 V | PHY_3V3 (+100 nF C213) |
| 12 | RESET_N | HW reset, active low | ETH_PHY_RST_N → ESP GPIO7; 4.7k pull-up R219 |
| 13 | MDC | management clock | ETH_MDC → GPIO5 |
| 14 | MDIO | management data | ETH_MDIO → GPIO6; 4.7k pull-up R218 |
| 15 | TXD3 | RGMII TX data | PHY_TXD3 –R205 33R– ETH_TXD3 → GPIO11 |
| 16 | TXD2 | " | PHY_TXD2 –R204– ETH_TXD2 → GPIO10 |
| 17 | TXD1 | " | PHY_TXD1 –R203– ETH_TXD1 → GPIO9 |
| 18 | TXD0 | " | PHY_TXD0 –R202– ETH_TXD0 → GPIO8 |
| 19 | TX_CTL | RGMII TX control | PHY_TX_CTL –R206– ETH_TX_CTL → GPIO12 |
| 20 | TX_CLK | RGMII TX clock (from MAC) | PHY_TX_CLK –R207– ETH_TX_CLK → GPIO13 |
| 21 | DVDDL | digital 1.1 V | PHY_VDDL (+100 nF C206) |
| 22 | RXD3/PHYAD0 | RX data; strap (int. PD) | PHY_RXD3 –R211– ETH_RXD3 → GPIO16 |
| 23 | RXD2/PLLOFF | RX data; strap (int. PD) | PHY_RXD2 –R210– ETH_RXD2 → GPIO17 |
| 24 | RXD1/TXDLY | RX data; strap (int. PD) | PHY_RXD1 –R209– ETH_RXD1 → GPIO18 |
| 25 | RXD0/RXDLY | RX data; strap (int. PU) | PHY_RXD0 –R208– ETH_RXD0 → GPIO19 |
| 26 | RX_CTL/PHYAD2 | RX control; strap (int. PD) | PHY_RX_CTL –R212– ETH_RX_CTL → GPIO15 |
| 27 | RX_CLK/PHYAD1 | RX clock to MAC; strap (int. PD) | PHY_RX_CLK –R213– ETH_RX_CLK → GPIO14 |
| 28 | DVDD_RGMII | RGMII/MDIO I/O supply | PHY_3V3 (+10 µF C208, 100 nF C209) |
| 29 | DVDD33 | digital 3.3 V; feeds internal LDO | PHY_3V3 (+10 µF C210, 2×100 nF C211/C212) |
| 30 | LDO_O | internal 1.1 V LDO output (D variant) | PHY_VDDL (+100 nF C207) |
| 31 | INT_N/PME_N | open-drain interrupt | ETH_INTN, 4.7k pull-up R217; DNP 0R R223 → GPIO4 |
| 32 | LED0/CFG_EXT | strap CFG_EXT = 1 (LED0 unused) | PHY_CFG_EXT, 4.7k pull-up R216 |
| 33 | LED1/CFG_LDO0 | 100M LED; strap CFG_LDO0 = 0 | PHY_LED1: 4.7k PD R215, 330R R221 → J201.14 (yellow) |
| 34 | LED2/CFG_LDO1 | 1000M LED; strap CFG_LDO1 = 0 | PHY_LED2: 4.7k PD R214, 330R R220 → J201.11 (green) |
| 35 | CLKOUT | ref clock out | NC (datasheet: float if unused) |
| 36 | XTAL_I | 25 MHz crystal | PHY_XI → Y201.1, 15 pF C201 |
| 37 | XTAL_O | 25 MHz crystal | PHY_XO → Y201.3, 15 pF C202 |
| 38 | AVDDL | analog 1.1 V | PHY_VDDL (+100 nF C205) |
| 39 | RBIAS | bias | 2.49k 1% R201 to GND |
| 40 | AVDD33 | analog 3.3 V | PHY_3V3 (+100 nF C214) |
| 41 | EPAD | GND | GND, with thermal vias |

## 2. External components: CoreBoard vs. our board

| Function | CoreBoard [CB p3] | Our board (JSON) | Notes |
|---|---|---|---|
| Clock | Y2 25 MHz, 4-pad; C22/C25 **8.2 pF/50V ±0.25 pF**. Crystal part number not stated. | Y201 YXC X322525MOB4SI 25 MHz CL 12 pF ±10 ppm (C9006, basic) with **15 pF** C0G (C1548, basic) | [YT] 7.3 requires ±50 ppm, ESR ≤ 50 Ω, drive ≤ 0.5 mW. 15 pF/2 + ~4 pF stray ≈ 12 pF. ESR of C9006 is **UNVERIFIED**. The CoreBoard's 8.2 pF suggests its crystal has CL ≈ 8 pF. |
| RBIAS | R41 2.49k 1% | R201 2.49k 1% (C25884) | Required value [YT] Table 8 |
| PHY_VDDL decoupling | C44/C46/C48 0.1 µF at pins 3, 8, 38; C52 0.1 µF at pin 21; C58 0.1 µF at LDO_OUT | C203–C207 100 nF 0402 (C1525) | LDO_OUT is tied straight to PHY_VDDL; [YT] tested the D variant with 0 Ω on pin 30. No external 1.1 V regulator and no ferrite on VDDL. |
| DVDD_RGMII (28) | C45 4.7 µF + C47 0.1 µF | C208 10 µF 0603 + C209 100 nF | We use 10 µF so the board needs only one bulk value |
| DVDD33 (29) | C50 4.7 µF + C53, C54 0.1 µF | C210 10 µF + C211, C212 100 nF | |
| AVDD33 (11, 40) | C55, C56 0.1 µF | C213, C214 100 nF | |
| 3.3 V feed | VCC_3V3 → L4 **BLM18PG330SN1D** → ETH_PHY_3V3. VCC_3V3 comes from a TLV62569 buck shared with the module. | FB201 BLM18PG121SN1D (C14709, basic). BLM18PG330SN1D (C88984) is a drop-in alternative. | Shared rail, not separate. Current: **226 mA typ / 250 mA max** at 3.3 V [YT Tables 103/106], about 0.75–0.82 W, because the internal LDO burns 3.3→1.1 V. Budget 260 mA with LEDs. Check the AMS1117 thermal budget (PART_SELECTION 12a). |
| Straps | Footprints R53/54/57/60/63/65 (PHYAD0-2, RXDLY, TXDLY, PLLOFF), **all NC**. Fitted: R35 4.7k LED2→GND, R36 4.7k LED1→GND, R38 4.7k CFG_EXT→3V3. | Same: R214/R215/R216 4.7k. PHYAD/DLY/PLLOFF footprints omitted. | Result: **PHY address 0**, PLLOFF 0, **RXDLY = 1** (internal PU, 2 ns RX_CLK delay), **TXDLY = 0**, CFG_EXT = 1 with CFG_LDO = 00, i.e. external **3.3 V** RGMII I/O. This matches ESP32-S31 VDDPST_1 (GPIO8-19) at 3.0-3.6 V [DS]. |
| RGMII delays | All delays come from the PHY | Same | [FW]: ext 0xA001 bit 8 Rxc_dly_en = 1 (RX +2 ns). Ext 0xA003 [7:4] = [3:0] = 13 gives TX_CLK +13×150 ps ≈ **1.95 ns** at 1000M and 10/100M. The defaults are 0x1 and 0xF [YT Table 15]. The ESP32 adds no delay, so do not add PCB clock delay. |
| RGMII series R | 33R 1% on all 12 lines. TX group (R55/56/58/59/61/62) labelled "Resistors close to PHY"; RX group (R46-R51) labelled "Resistors close to MAC"; both "50 ohm single end impedance". | R202–R213 33R 0402 (C25105, basic). **We place them at the driver: TX at the ESP32, RX at the PHY.** | The CoreBoard notes place each resistor at the receiving end, which is unusual for series termination. With traces under 40 mm either placement works. To copy the CoreBoard exactly, swap the placement; the netlist does not change. |
| MDIO pull-up | R66 4.7k to ETH_PHY_3V3 | R218 4.7k | No pull-up on MDC |
| Reset | ETH_PHY_RST straight to GPIO7. **No RC and no pull-up.** | GPIO7 plus R219 4.7k pull-up (**UNVERIFIED** addition) | [YT] 3.6: "Requires an external pull-up resistor". [YT] 5.1: reset low ≥ 10 ms and released ≥ 10 ms after power is stable. IDF generic PHY holds it low for 10 ms (`DEFAULT_PHY_GENERIC_RESET_ASSERTION_TIME_US 10000`), which also re-latches the straps once the ESP RX pins are inputs. A pull-down instead would keep the PHY off during boot (saves about 230 mA) but then needs the firmware to release it. |
| Interrupt | INT_N: R40 4.7k pull-up → ETH_INTN → R83 0R → GPIO4 | R217 4.7k pull-up; R223 0R **DNP** to GPIO4 | [FW] does not use the interrupt. Whether GPIO4 is free on our board is **UNVERIFIED**. |
| LEDs | LED2 → R77 330R → J8.A11 green (cathode A12 to GND); LED1 → R81 330R → J8.A9 yellow (cathode A10 to GND). Active high. | R220 330R → J201.11 green (12 to GND); R221 330R → J201.14 yellow (13 to GND) | LED2 = 1000M, LED1 = 100M, blinking on activity. The datasheet does not document LED polarity; we copy the CoreBoard. |
| MDI centre taps | Discrete T1 ML-G24P02S: each chip-side CT (pins 1/4/7/10) has 0.1 µF/50V to GND (C65/66/67/69) | HR911130C ties all CTs to P1, so one C215 100 nF/50V 0603 (C14663) goes to GND | Voltage-mode PHY: the CT must not be biased to 3.3 V |
| Bob Smith / chassis | Line-side CMT1-4 → 4×75R (R75/76/78/80) → C71 1000 pF/2 kV → GND_RJ45. J8 shield G1/G2 → GND_RJ45. GND_RJ45 → R82 0R → GND (C72 "TBD(NC)" in parallel). | All 75R + 1000 pF/2 kV are **inside** the HR911130C, which brings the node out on P10 "CHS GND". P10 and shield tabs → GND_CHASSIS → R222 0R → GND, with C216 1 nF/2 kV 1206 DNP in parallel. | [HR] p1 schematic |

## 3. HR911130C pinout → MDI pairs [HR p1, p3]

| J201 pin | Function | Net | PHY pin |
|---|---|---|---|
| 1 | Chip-side common centre tap | MAG_CT (100 nF to GND) | – |
| 2 / 3 | MDI0+ / MDI0− (contacts 1/2, A) | MDI0_P / MDI0_N | 1 / 2 |
| 4 / 7 | MDI1+ / MDI1− (contacts 3/6, B) | MDI1_P / MDI1_N | 4 / 5 |
| 5 / 6 | MDI2+ / MDI2− (contacts 4/5, C) | MDI2_P / MDI2_N | 6 / 7 |
| 8 / 9 | MDI3+ / MDI3− (contacts 7/8, D) | MDI3_P / MDI3_N | 9 / 10 |
| 10 | CHS GND (Bob Smith 1000 pF/2 kV node) | GND_CHASSIS | – |
| 11 / 12 | Green LED anode / cathode | LED_GRN_A / GND | via R220 from 34 |
| 14 / 13 | Yellow LED anode / cathode | LED_YEL_A / GND | via R221 from 33 |
| 2× Ø1.63 PTH | Shield tabs | GND_CHASSIS | – |
| 2× Ø3.25 | NPTH plastic pegs | – | – |

Footprint (component side, [HR] p3): signal pins are Ø0.89 in two staggered rows, even pins 10-8-6-4-2 and odd pins 9-7-5-3-1, at 2.54 mm pitch with a 1.27 mm offset between rows. LEDs are 14/13 (left) and 12/11 (right), Ø1.02. Take exact row coordinates from the HR p3 drawing (10.40 / 8.89 / 2.54 / 3.05 / 4.90 mm dims). A KiCad footprint should be checked against it (**UNVERIFIED**). Body is 16.0 × 21.2 × 13.3 mm. Isolation 2250 Vdc, OCL 350 µH, 0-70 °C.

## 4. ESP32-S31 GPIO ↔ RGMII (confirmed)

| GPIO | QFN80 pin [DS T2-1] | Signal | IO MUX F2 [DS T2-3] | IDF default [IDF] |
|---|---|---|---|---|
| 5 | 10 | MDC | GPIO matrix (any pin) | mdc_num = 5; FW sets 5 |
| 6 | 12 | MDIO | GPIO matrix | mdio_num = 6; FW sets 6 |
| 7 | 13 | PHY RESET_N | GPIO | FW reset_gpio_num = 7 |
| 8 | 14 | TXD0 | GMAC_PHY_TXD0_PAD | txd0_num = 8 |
| 9 | 15 | TXD1 | GMAC_PHY_TXD1_PAD | 9 |
| 10 | 16 | TXD2 | GMAC_PHY_TXD2_PAD | 10 |
| 11 | 17 | TXD3 | GMAC_PHY_TXD3_PAD | 11 |
| 12 | 19 | TX_CTL | GMAC_PHY_TXEN_PAD | tx_ctl_num = 12 |
| **13** | 20 | **TX_CLK (GTX_CLK, MAC output)** | GMAC_RMII_CLK_PAD | `clock_tx_gpio = 13`; `emac_rgmii_iomux_clko = {13, 43}` |
| 14 | 21 | RX_CLK (input) | GMAC_RX_CLK_PAD | clock_rx_gpio = 14 |
| 15 | 22 | RX_CTL | GMAC_PHY_RXDV_PAD | rx_ctl_num = 15 |
| 16 | 23 | RXD3 | GMAC_PHY_RXD3_PAD | 16 |
| 17 | 24 | RXD2 | GMAC_PHY_RXD2_PAD | 17 |
| 18 | 25 | RXD1 | GMAC_PHY_RXD1_PAD | 18 |
| 19 | 26 | RXD0 | GMAC_PHY_RXD0_PAD | 19 |

- **GPIO13 is the RGMII TX clock output.** In RGMII mode its pad name, GMAC_RMII_CLK_PAD, is reused for TX_CLK.
- **GPIO35 (REF_GMAC_CLK) is not needed.** IDF sets `clock_phy_ref_gpio = -1` for S31, and the PHY runs from its own 25 MHz crystal.
- **The CoreBoard uses the same GPIO4-19 mapping** [CB p2], with GPIO4 for INT_N.
- **Alternate IO MUX set:** GPIO36-47 (VDDPST_3). GPIO36/37 are strapping pins.
- **No strap conflicts in GPIO4-19.** The S31 strapping pins are GPIO36, 37, 60 and 61 [DS T3-1].
- **I/O voltage:** GPIO8-19 are in the VDDPST_1 domain, 3.0/3.3/3.6 V, which is consistent with the 3.3 V RGMII strap.
- **Firmware:** `esp_eth_phy_new_generic` with `phy_addr = -1` (address auto-detect). It re-enables autonegotiation, then writes the delay registers listed above.

## 5. Layout notes

- **RGMII**
  - Route all 12 lines at 50 Ω single-ended over solid GND, with no plane splits.
  - Place the PHY within about 25-40 mm of ESP32 pins 14-26. They all sit on one side of the QFN80.
  - Length-match within each group to ±1.3 mm: TXD0-3 + TX_CTL to TX_CLK, and RXD0-3 + RX_CLK/RX_CTL to RX_CLK.
  - Do not add delay serpentines to the clocks.
  - Give the 125 MHz clocks 3W spacing and no vias. Keep them away from the RF chain and the TCXO.
- **MDI**
  - Route 100 Ω differential with P/N matched to 0.15 mm. Pair-to-pair matching is loose (< 10 mm). Keep the pairs short (< 50 mm) with no stubs.
  - **Pin-order catch:** MDI1 is on J201 pins 4/7, which straddle MDI2 on pins 5/6. One pair must change layer, with both lines through equal vias.
- **Magjack keep-out**
  - The magnetics are internal, so the chip side (pins 1-9) can see logic GND.
  - Give GND_CHASSIS (shield tabs, pin 10) its own island under the front half of the jack. Keep ≥ 2 mm from logic copper and keep no signals underneath.
  - Join chassis to GND at a single point through R222/C216.
- **PHY**
  - EPAD 3.7 mm: 9-16 vias of 0.3 mm to GND. About 0.75 W at θJA 33 °C/W gives roughly +25 °C.
  - Put each 100 nF cap at its pin. Make the pin-30 → VDDL pins trace short and ≥ 0.3 mm wide.
  - Put the crystal right at pins 36/37 with a GND guard and nothing routed underneath.
  - Put R201 at pin 39.

## Open / UNVERIFIED

1. The JLC record for YT8531DC-CA **C47544379** is named "【邮寄专用】" ("for mailing only") and has no LCSC page link, unlike normal parts. Check that JLC will place it in PCBA. Other YT8531 listings show 0 stock or EOL.
2. ESR of C9006 and the final load-cap value. The crystal frequency could be trimmed by measuring CLKOUT or the 125 MHz RX_CLK.
3. R219 (RESET_N pull-up) is added beyond the CoreBoard.
4. LED polarity: we copy the CoreBoard (active high).
5. Whether GPIO4 is free for INT_N.
6. KiCad footprint for QFN-40 5×5 P0.4 EP3.7.

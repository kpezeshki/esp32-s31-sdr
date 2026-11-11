# Two-board split: analysis (2026-11-10)

The proposal is to split the design into two boards:
- **Board A ("ESP-SDR base")** carries the ESP32-S31-WROOM-3U module, power, gigabit Ethernet and USB. It is usable on its own.
- **Board B ("RF front end")** carries the mixer front end. It plugs into A through a 90° header, and a U.FL patch cable carries the 2.44 GHz IF into the module's antenna connector.

Status: analysis only. The ESP32-S31 (chip and module) shows 0 stock at LCSC, and the RFFC5072 shows 22. Recheck stock before committing.

## 1. Verdict
The split is a good idea. Overall cost is about the same as the single board, but:
- Board A becomes a cheap, self-contained gigabit-Ethernet ESP32-S31 SDR. In native mode it covers 2.15–2.8 GHz with an antenna on the module's U.FL. Its hardware matches the reference the esp-sdr streaming firmware was developed on (WROOM-3 + YT8531), which lowers firmware risk.
- Board B holds all the hard RF work and fine-pitch parts. It can be revised without respinning A.
- Native/mixer selection becomes "move the U.FL cable". The 0 Ω tee, the second SMA and its ESD diode all go away.

Board A **cannot be done entirely with a soldering iron**, for two reasons:
1. **The WROOM-3U is an LGA module.** It has 94 perimeter pads (0.4×0.8 mm, 0.85 mm pitch) on the underside, no castellations, plus 9 GND/thermal pads in the centre (datasheet v0.7 fig. 10-2/11-2).
2. **No gigabit PHY exists in a leaded package.** The YT8531 is QFN-40 at 0.4 mm. The RTL8211E is QFN-48, the RTL8211EG is QFN-64, and Marvell parts are BGA or QFN.

Workable options for A:

| Option | How | Cost/effort |
|---|---|---|
| **A1 (recommended)** | Order a JLC stencil (about $7) and reflow the module and PHY on a hotplate or with hot air. Everything else on A is 0603+, SOT, USB-C and THT, done with an iron. | Cheapest. Reliable if a hotplate is available. |
| A2 | JLC Economic PCBA places only the module, the PHY and its 0402 crystal and decoupling parts. You hand-solder the rest. | About $5/board extra at qty 5 (setup $8.18, stencil $1.53, 2 extended types at $3.07, X-ray). Board A is about $19. |
| A3 | Iron-only: an extended-pad module footprint (pads extended about 1.2 mm past the module edge) plus plated holes under the 9 centre GND pads, soldered from the back. The PHY by drag soldering. | Possible but fiddly. I don't recommend it for the 0.4 mm PHY. |
| A4 | No Ethernet on A: stream over HS-USB at 20 MS/s instead of 40 MS/s. | Removes the PHY and magjack (about $4, about 43 parts). A becomes fully hand-assemblable apart from the LGA module. |


## 1b. ESP32-S31-WROOM-1U instead of WROOM-3U (checked 2026-11-10, datasheet v0.5 fig. 3-2 / 11-2)
- WROOM-1U is 18 × 25.5 mm with 64 pins. Pins **1–40 and 62–64 are castellated** (1.27 mm pitch): 3V3, EN, GPIO0–7, 33–40, 42–47, 54–57, 60/61, UART0, GND, ANT2.
- **GPIO8–19 (all RGMII signals), USB DM/DP and GPIO48–53 are on 20 inner bottom pads** (0.4 × 0.8 mm, pins 42–61). The module also has 9 bottom GND pads.
- The castellated pins alone are therefore not enough. Neither gigabit Ethernet (RGMII) nor HS-USB streaming is available without the inner pads, which leaves only the 3 Mbit/s UART. **Board A needs reflow (stencil + hotplate/hot air) for the module's inner pads whichever module is used.** The PHY needs reflow anyway.
- With reflow, the WROOM-1U is still slightly preferable to the WROOM-3U:
  - it is smaller;
  - most joints are visible and reworkable castellations, and only 29 pads are hidden versus 103;
  - it has the same chip, U.FL (gen 1) and ANT2 pad.

  The firmware is pin-level (GPIO numbers), so it does not care which module is used.
- Stock: WROOM-1-N16R16V shows 0 at LCSC (C55371224). The 1U variant is not listed yet.
- **Header GPIOs with WROOM-1U:** 10 free castellated GPIOs are available (2, 3, 4, 45, 46, 47, 54, 55, 56, 57). The remaining 4 come from inner pads GPIO48–51, which get reflowed anyway. GPIO0/1 (possible 32 kHz crystal) and GPIO60/61 (boot straps) are avoided.

## 2. Board A (base) contents

67 parts (61 fitted), 31 types; layout done (`hw/LAYOUT_STATUS_SPLIT.md`). The bare chip's support parts, flash and native-path parts are gone because the module contains them.

- **U1:** ESP32-S31-WROOM-3U-N16R16V. Includes the 40 MHz crystal, 16 MB flash, 16 MB PSRAM, RF match and U.FL (gen-1, U.FL/MHF-I compatible). About $6, stock 0.
- **Ethernet:** YT8531DC-CA, 25 MHz crystal, about 24 passives, HR911130C magjack. This is the CoreBoard reference circuit (`hw/phy_circuit.json`) minus the TX 33 Ω series resistors (D21: they belong at the MAC, which sits under the module). RGMII on GPIO8–19, MDC/MDIO/RST on GPIO5/6/7.
- **USB-C:** power in, plus HS USB data on USB_DP/DM (module pins 40/41), ESD protection, 5.1k CC resistors.
- **Power:** 2× AMS1117-3.3 (module about 600 mA peak, PHY about 250 mA), linear as agreed. 5 V is passed through to the header for Board B.
- **Other:** UART0 header (GPIO58/59), BOOT (GPIO61) and RESET (EN) buttons, status LED.
- **Pins left unsoldered/unconnected** (firmware sample bus): module pins 27–32 (GPIO20–25) and 42–54 (GPIO33–40, 42–44). On an LGA these pads still get soldered; they just get no traces.
- **Layers:** 4 layers recommended. RGMII and the 100 Ω MDI pairs want a solid reference plane, and a small JLC 4-layer board (about 50×45 mm) costs about $2/board at qty 5.
- **Estimated cost (qty 5):** components about $12, PCB about $2, so **about $14/board** with A1, or about $19 with A2.

## 3. Board B (RF front end) contents

About 136 parts, **about 50 JLC part types**. It is the current RF chain unchanged, except:
- The ESP32 CLC match goes away, because it is inside the module.
- The native tee, SMA_NAT and its ESD diode go away.
- The IF chain ends at **SAW → 3 dB pad → DC block → U.FL (IF out)**. The 3 dB pad stays because the module's calibration TX bursts now arrive through the cable (risk R1).
- **Clock:** the TCXO now feeds only the RFFC5072, since the module has its own ±10 ppm crystal. Consequences:
  - There is a static baseband offset of up to about ±24 kHz (= IF × ε_module). It is independent of the tuned RF and corrected in software like an RTL-SDR ppm setting.
  - There is a few-kHz drift while warming up.
  - An unfitted option routes a 40 MHz clock synthesised by the ESP32 PLL (LEDC or CAM_XCLK through the GPIO matrix) over the header to the RFFC REF_IN for coherent operation. Its phase noise is unverified.
- **Power:** 5 V from the header, about 250–300 mA. Board B makes its own 3.0 V RF rail and the 4.5 V LNA and gain-block rails, and takes 3.3 V from A for the SP3T VDD.
- **Estimated cost (qty 5, JLC Standard assembly):** components about $34 (RFFC5072 $15.60), PCB about $2, fees about $23 (setup + stencil + 50 types × $1.53 + X-ray). That gives **about $59/board @5, about $46 @10**.
  - Moving the loop filter, control-line RCs and pull-ups to hand-soldered 0603 saves about $2/board.
  - Economic assembly is not cheaper here, because about 40 of the types are extended at $3.07 each.

**Total system ≈ $73 @5** (A1 + B), compared with about $75 for the single board. The real gains are modularity, firmware risk and Board A's standalone use.

## 4. Board-to-board interface

**Mechanical:** a right-angle 2×10 2.54 mm female header on A's edge mates with a right-angle male header on B's edge, so the boards sit edge to edge and coplanar. Add 2 M2.5 holes on each board for a bridge plate or standoffs. The U.FL patch cable (1.13 mm, about 10 cm) runs from B's IF out to the module's U.FL. Its loss is about 0.3–0.5 dB at 2.44 GHz, which comes after about 15–25 dB of front-end gain, so the NF impact is under 0.1 dB.

**Proposed pinout** (GPIOs chosen from those not reserved by the firmware and not used by Ethernet). GPIO0/1 are avoided because the module may fit a 32 kHz crystal on them.

| Pin | Signal | ESP32 GPIO | Pin | Signal | ESP32 GPIO |
|---|---|---|---|---|---|
| 1 | 5V0 | – | 2 | 5V0 | – |
| 3 | GND | – | 4 | GND | – |
| 5 | 3V3 | – | 6 | GND | – |
| 7 | RFFC_SCLK | 45 | 8 | RFFC_SDATA | 46 |
| 9 | RFFC_ENX | 47 | 10 | RFFC_ENBL | 48 |
| 11 | RFFC_RESETX | 49 | 12 | RFFC_LD (in) | 50 |
| 13 | SW1_V1 | 2 | 14 | SW1_V2 | 3 |
| 15 | SW2_V1 | 52 | 16 | SW2_V2 | 53 |
| 17 | LDO_EN_LB | 4 | 18 | LDO_EN_MB | 54 |
| 19 | LDO_EN_HB | 55 | 20 | REFCLK option (40 MHz from ESP32 PLL, DNP on B) | 51 |

Notes:
- GPIO54/55 are JTAG MTDO/MTCK. JTAG isn't usable during streaming anyway, because GPIO33–40 carry the sample bus.
- Pins 7–20 double as a general-purpose GPIO header when A is used alone.
- All B-side inputs keep their 1 kΩ series resistors and pull-downs, so B is safe while A boots, with GPIOs floating and the LNA LDOs off.

## 5. Signal-chain impact (vs. SIGNAL_CHAIN_ANALYSIS rev 3)
- **Mixer path:** the U.FL pair plus cable adds about 0.5 dB before the ESP32, roughly equivalent to the old 0 Ω tee and π-match loss. System NF is unchanged to within about 0.1 dB: LB about 1.6–2.0 dB, MB about 2.2–2.5 dB, HB about 2.2–3.0 dB.
- **Native path (A alone):** the module's own match feeds the U.FL, so NF ≈ ESP32 NF plus antenna-cable loss. That is about 0.7 dB better than the old SMA → tee → pad route, because the 3 dB pad is not in this path.
- **Frequency accuracy:** see §3 (static offset, software-corrected).
- **Isolation:** splitting the boards puts the ESP32 digital noise and the PHY (125 MHz RGMII) about 10 cm from the LNAs. That helps spur performance compared with the single 70×70 mm board.

## 6. Open decisions
1. Board A assembly route: A1 hotplate/hot air (recommended), A2 JLC places module + PHY, or A4 USB-only without the PHY.
2. Header geometry: coplanar edge-to-edge (proposed), or B stacked on top as a shield-like daughter board.
3. Keep the unfitted ESP32-PLL REFCLK option on B? It is cheap: one 0 Ω and a trace.
4. Stock: wait for ESP32-S31 module and RFFC5072 availability. Alternatives to monitor: Mouser/DigiKey/Espressif store. The RFFC5072 is also at Qorvo direct (about $22–28).

## 7. What carries over unchanged
- The EM-optimised filters (`em/EM_REPORT.md`, `em/filters/FINAL_FILTERS.md`), RF placement and routing scripts, LNA, switch and gain-block circuits, RFFC5072 circuit, PHY circuit and BOM tooling.
- The generator (`hw/design.py` → `build_pcb.py`) splits into two design files. The Freerouting flow (`fr_route.py`) is now allowed, and will be used for both boards once the split is approved.

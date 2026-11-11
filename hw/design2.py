#!/usr/bin/env python3
"""
Two-board split (D15-D20):
  Board A "ESP-SDR base": ESP32-S31-WROOM-1U, USB-C (5 V + HS USB), 2x AMS1117, YT8531 GbE PHY + HR911130C,
                          UART header, BOOT/RESET, LED, 2x10 right-angle socket to Board B.  In-house reflow (A1).
  Board B "RF front end": RF chain (SIGNAL_CHAIN_ANALYSIS s.12) -> IF U.FL, RF LDOs, TCXO (+ext-ref and ESP32-clock
                          options), 2x10 right-angle header to Board A.  JLC hybrid assembly (D17).
Header (A socket J6 <-> B header J7), see SPLIT_ARCHITECTURE.md s.4 (pin 20 = REFCLK option on GPIO55/CAM_XCLK).
"""
import os, json
import design as D0
from design import Design, FP, LCSC, lc

HDR = {1: "5V0", 2: "5V0", 3: "GND", 4: "GND", 5: "3V3", 6: "GND", 7: "RFFC_SCLK", 8: "RFFC_SDATA", 9: "RFFC_ENX",
       10: "RFFC_ENBL", 11: "RFFC_RESETX", 12: "RFFC_LD", 13: "SW_V1", 14: "SW_V2", 15: "SW2_V1", 16: "SW2_V2",
       17: "LDO_EN_LB", 18: "LDO_EN_MB", 19: "LDO_EN_HB", 20: "ESP_REFCLK"}

def helpers(D):
    def R(ref, val, a, b, pkg="R0603", by=None, dnp=False, group="", note=""):
        D.add(ref, val, pkg, {1: a, 2: b}, lc(pkg, val), by or ("jlc" if pkg.endswith("0402") else "hand"), dnp, group, note)
    def C(ref, val, a, b="GND", pkg="C0603", by=None, dnp=False, group="", note=""):
        D.add(ref, val, pkg, {1: a, 2: b}, lc(pkg, val), by or ("jlc" if pkg.endswith("0402") else "hand"), dnp, group, note)
    def L(ref, val, a, b, pkg="L0402", lcsc="", by=None, dnp=False, group="", note=""):
        D.add(ref, val, pkg, {1: a, 2: b}, lcsc, by or ("jlc" if pkg.endswith("0402") else "hand"), dnp, group, note)
    return R, C, L

# --------------------------------------------------------------------------------------------- Board A
def build_a():
    D = Design(); R, C, L = helpers(D)
    g = "module"
    m = {i: "NC" for i in range(1, 65)}
    m.update({1: "GND", 2: "3V3", 3: "CHIP_PU", 4: "SW_V1", 5: "SW_V2", 6: "LDO_EN_LB", 7: "ETH_MDC", 10: "ETH_MDIO",
              11: "ETH_PHY_RST_N", 26: "GPIO60", 27: "BOOT", 31: "RFFC_SCLK", 32: "RFFC_SDATA", 33: "RFFC_ENX",
              34: "LDO_EN_MB", 35: "ESP_REFCLK", 36: "U0RXD", 37: "U0TXD", 38: "LDO_EN_HB", 39: "LED_STAT", 40: "GND", 41: "GND",
              42: "ETH_TXD0", 43: "ETH_TXD1", 44: "ETH_TXD2", 45: "ETH_TXD3", 46: "ETH_TX_CTL", 47: "ETH_TX_CLK",
              48: "ETH_RX_CLK", 49: "ETH_RX_CTL", 50: "ETH_RXD3", 51: "ETH_RXD2", 52: "ETH_RXD1", 53: "ETH_RXD0",
              54: "USB_DM", 55: "USB_DP", 56: "RFFC_ENBL", 57: "RFFC_RESETX", 58: "RFFC_LD", 59: "NC", 60: "SW2_V1", 61: "SW2_V2",
              62: "GND", 63: "NC", 64: "GND"})
    # pins 12-25, 28-30 (GPIO35, 33, 34, 20-25, 36-40, 42-44) = esp-sdr internal sample bus -> unconnected; 8/9 (GPIO0/1) avoided
    D.add("U1", "ESP32-S31-WROOM-1U-N16R16V", "esp32_sdr:Espressif_ESP32-S31-WROOM-1U", m, "", "hand", group=g,
          note="reflow in house (A1); stock 0 at LCSC 2026-11-10; U.FL ANT1 -> patch cable to Board B J8")
    C("C101", "22uF", "3V3", pkg="C0805", group=g); C("C102", "100nF", "3V3", group=g); C("C103", "10uF", "3V3", pkg="C0805", group=g)
    R("R101", "10k", "3V3", "CHIP_PU", group=g); C("C104", "1uF", "CHIP_PU", group=g, note="EN RC delay")
    D.add("SW1", "RESET", "Button_Switch_SMD:SW_SPST_TL3342", {1: "CHIP_PU", 2: "CHIP_PU", 3: "GND", 4: "GND"}, "C318884", "hand", group=g)
    D.add("SW2", "BOOT", "Button_Switch_SMD:SW_SPST_TL3342", {1: "BOOT", 2: "BOOT", 3: "GND", 4: "GND"}, "C318884", "hand", group=g)
    R("R102", "10k", "3V3", "BOOT", group=g)
    D.add("J5", "UART", "HDR1x3", {1: "GND", 2: "U0TXD", 3: "U0RXD"}, "C49257", "hand", group=g)
    R("R103", "1k", "LED_STAT", "LED_A", group=g)
    D.add("D101", "LED", "LED0603", {1: "GND", 2: "LED_A"}, lc("LED0603", "G"), "hand", group=g)
    D.add("TP1", "GPIO60", "TestPoint:TestPoint_Pad_D1.0mm", {1: "GPIO60"}, "", "hand", group=g)
    # USB-C: power in + HS USB data
    g = "usb"
    D.add("J4", "USB-C", "USBC", {"A1": "GND", "B12": "GND", "A12": "GND", "B1": "GND", "A4": "VBUS", "B9": "VBUS", "A9": "VBUS", "B4": "VBUS",
                                  "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM",
                                  "A8": "NC", "B8": "NC", "S1": "GND"}, "C165948", "hand", group=g)
    R("R401", "5.1k", "CC1", "GND", group=g); R("R402", "5.1k", "CC2", "GND", group=g)
    D.add("U5", "USBLC6-2SC6", "SOT23-6", {1: "USB_DP", 2: "GND", 3: "USB_DM", 4: "USB_DM", 5: "VBUS", 6: "USB_DP"}, "C7519", "hand", group=g)
    L("FB401", "120R@100MHz", "VBUS", "5V0", pkg="FB0603", lcsc=lc("FB0603", "120R"), group=g)
    C("C401", "22uF", "5V0", pkg="C0805", group=g)
    # power
    g = "power"
    D.add("U6", "AMS1117-3.3", "SOT223", {1: "GND", 2: "3V3", 3: "5V0"}, "C6186", "hand", group=g, note="3V3: module (+ Board B switches)")
    C("C601", "22uF", "3V3", pkg="C0805", group=g); C("C602", "10uF", "5V0", pkg="C0805", group=g)
    D.add("U7", "AMS1117-3.3", "SOT223", {1: "GND", 2: "3V3_PHY", 3: "5V0"}, "C6186", "hand", group=g, note="3V3 PHY (~250 mA)")
    C("C603", "22uF", "3V3_PHY", pkg="C0805", group=g); C("C604", "10uF", "5V0", pkg="C0805", group=g)
    # header to Board B (right-angle socket on the board edge)
    D.add("J6", "To RF board", "Connector_PinSocket_2.54mm:PinSocket_2x10_P2.54mm_Horizontal", HDR, "C239361", "hand", group="hdr",
          note="2x10 2.54 mm right-angle female; doubles as GPIO header when used alone")
    for i in range(1, 5):
        D.add(f"H{i}", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5", {}, "", "dnp", group="mech")
    # Ethernet PHY (CoreBoard reference circuit, hw/phy_circuit.json)
    phy = json.load(open(os.path.join(D0.HERE, "phy_circuit.json")))
    # D21: the reference's TX series resistors (R202-R207, "next to ESP32 pins") cannot sit at the source: the
    # WROOM-1U's RGMII pads are under the module.  Next to the PHY (the receiver) they do nothing, so they are dropped
    # and TX is routed direct (S31 GPIO drive strength sets the edge rate).  RX resistors stay at the PHY = source.
    netmap = {"+3V3": "3V3_PHY", "PHY_TXD0": "ETH_TXD0", "PHY_TXD1": "ETH_TXD1", "PHY_TXD2": "ETH_TXD2",
              "PHY_TXD3": "ETH_TXD3", "PHY_TX_CTL": "ETH_TX_CTL", "PHY_TX_CLK": "ETH_TX_CLK"}
    for c in phy["components"]:
        ref = c["ref_hint"]
        if ref in ("R202", "R203", "R204", "R205", "R206", "R207"): continue
        pins = {k: netmap.get(v, v) for k, v in c["pins"].items()}; pk = c.get("package", "")
        if "QFN-40" in pk: fp = "QFN40"
        elif "3225" in pk: fp = "XTAL3225"
        elif "0402" in pk: fp = "R0402" if ref.startswith("R") else "C0402"
        elif "0603" in pk: fp = "R0603" if ref.startswith("R") else ("FB0603" if ref.startswith(("FB", "L")) else ("LED0603" if ref.startswith(("D", "LED")) else "C0603"))
        elif "0805" in pk: fp = "C0805"
        elif "1206" in pk: fp = "Capacitor_SMD:C_1206_3216Metric"
        else: fp = pk
        if "HR911130" in c.get("part", "") or ref.startswith("J2"): fp = "esp32_sdr:RJ45_HanRun_HR911130C"
        D.add(ref, c.get("value", ""), fp, pins, c.get("lcsc", ""), "dnp" if c.get("dnp") else "hand", c.get("dnp", False), "phy", c.get("note", "")[:120])
    return D

# --------------------------------------------------------------------------------------------- Board B
def build_b():
    D = Design(); R, C, L = helpers(D)
    g = "power"
    for i, (rail, en) in enumerate([("VLNA_LB", "LDO_EN_LB"), ("VLNA_MB", "LDO_EN_MB"), ("VLNA_HB", "LDO_EN_HB"), ("VGB", "5V0")]):
        D.add(f"U{9+i}", "TPS7A2045PDBVR", "SOT23-5", {1: "5V0", 2: "GND", 3: en, 4: "NC", 5: rail}, "C2873627", "hand", group=g)
        C(f"C{607+2*i}", "1uF", "5V0", group=g); C(f"C{608+2*i}", "4.7uF", rail, group=g)
        if en != "5V0": R(f"R{601+i}", "100k", en, "GND", group=g, note="LDO off while ESP32 boots / board unplugged")
    D.add("U8", "TPS7A2030PDBVR", "SOT23-5", {1: "5V0", 2: "GND", 3: "5V0", 4: "NC", 5: "3V0_RF"}, "C963429", "hand", group=g)
    C("C605", "1uF", "5V0", group=g); C("C606", "4.7uF", "3V0_RF", group=g); C("C615", "22uF", "5V0", pkg="C0805", group=g)
    C("C616", "10uF", "3V3", pkg="C0805", group=g, note="3V3 from Board A (SP3T VDD)")
    # header to Board A
    D.add("J7", "To base board", "Connector_PinHeader_2.54mm:PinHeader_2x10_P2.54mm_Horizontal", HDR, "C492438", "hand", group="hdr")
    for i in range(1, 5):
        D.add(f"H{i}", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5", {}, "", "dnp", group="mech")
    # control-line pull-downs so the RF board is defined while the ESP32 boots
    for sig in ("SW_V1", "SW_V2", "SW2_V1", "SW2_V2"):
        R(f"R6{10 + ['SW_V1','SW_V2','SW2_V1','SW2_V2'].index(sig)}", "100k", sig, "GND", group="hdr")
    # clock: TCXO default; ESP32-synthesised 40 MHz option (D20); external reference option (D9)
    g = "clock"
    D.add("Y1", "TG2520SMN 40MHz", "TCXO2520", {1: "NC", 2: "GND", 3: "TCXO_OUT", 4: "3V0_RF"}, "C3007519", "jlc", group=g)
    C("C701", "100nF", "3V0_RF", pkg="C0402", group=g)
    R("R701", "0", "TCXO_OUT", "REFCLK_RF", pkg="R0402", group=g, note="TCXO -> RFFC REF_IN (default)")
    R("R706", "1k", "ESP_REFCLK", "ESPCLK_DIV", group=g, dnp=True, note="ESP32 40 MHz option: 3.3 V CMOS -> ~0.9 Vpp divider")
    R("R707", "390", "ESPCLK_DIV", "GND", group=g, dnp=True)
    R("R708", "0", "ESPCLK_DIV", "REFCLK_RF", group=g, dnp=True, note="fit + remove R701 for coherent ESP32 clock")
    D.add("J3", "SMA_REF", "Connector_Coaxial:SMA_Samtec_SMA-J-P-X-ST-EM1_EdgeMount", {1: "EXT_REF", 2: "GND"}, "", "dnp", dnp=True, group=g)
    C("C702", "100nF", "EXT_REF", "EXTREF_AC", group=g, dnp=True)
    R("R703", "49.9", "EXTREF_AC", "GND", group=g, dnp=True)
    R("R704", "0", "EXTREF_AC", "REFCLK_RF", group=g, dnp=True, note="external 10-104 MHz ref: fit + remove R701")
    D0.build_rf(D, R, C, L, tail="ufl", hand0603=True)
    return D

if __name__ == "__main__":
    for name, fn in (("A", build_a), ("B", build_b)):
        D = fn(); n = D.nets()
        single = sorted(k for k, v in n.items() if len(v) == 1)
        by = {}
        for p in D.parts: by[p["by"]] = by.get(p["by"], 0) + 1
        tj = len({(p["value"], p["lcsc"]) for p in D.parts if p["by"] == "jlc"})
        print(f"Board {name}: {len(D.parts)} parts {by}, {len(n)} nets, JLC types {tj}; single-pin nets: {single}")

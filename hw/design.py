#!/usr/bin/env python3
"""
Single source of truth for the ESP32-S31 SDR board: parts, footprints, LCSC numbers, assembly split, nets.
Consumed by build_pcb.py (KiCad board), bom.py (JLC BOM/CPL + hand-solder BOM).

Assembly split (D11): by="jlc" (QFN/DFN/LGA, tiny RF parts, 0402) / "hand" (0603+, SOT/SOIC, connectors) / dnp.
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))

FP = {  # package key -> KiCad footprint
    "R0402": "Resistor_SMD:R_0402_1005Metric", "C0402": "Capacitor_SMD:C_0402_1005Metric", "L0402": "Inductor_SMD:L_0402_1005Metric",
    "R0603": "Resistor_SMD:R_0603_1608Metric", "C0603": "Capacitor_SMD:C_0603_1608Metric", "L0603": "Inductor_SMD:L_0603_1608Metric",
    "C0805": "Capacitor_SMD:C_0805_2012Metric", "FB0603": "Inductor_SMD:L_0603_1608Metric", "LED0603": "LED_SMD:LED_0603_1608Metric",
    "SOT223": "Package_TO_SOT_SMD:SOT-223-3_TabPin2", "SOT23-5": "Package_TO_SOT_SMD:SOT-23-5", "SOT23-6": "Package_TO_SOT_SMD:SOT-23-6",
    "SOT343": "Package_TO_SOT_SMD:SOT-343_SC-70-4", "SOT89": "Package_TO_SOT_SMD:SOT-89-3",
    "SOIC8": "Package_SO:SOIC-8_5.23x5.23mm_P1.27mm", "XTAL3225": "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "TCXO2520": "Oscillator:Oscillator_SMD_SeikoEpson_TG2520SMN-xxx-xxxxxx-4Pin_2.5x2.0mm",
    "QFN32": "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm_ThermalVias", "QFN40": "Package_DFN_QFN:QFN-40-1EP_5x5mm_P0.4mm_EP3.6x3.6mm_ThermalVias",
    "ESP32S31": "esp32_sdr:Espressif_ESP32-S31_QFN-80_8x8mm_P0.35mm_EP6.5mm",
    "USBC": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "HDR1x3": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
}

class Design:
    def __init__(self):
        self.parts = []
        self.refs = set()
    def add(self, ref, value, fp, pins, lcsc="", by="hand", dnp=False, group="", note=""):
        assert ref not in self.refs, ref
        self.refs.add(ref)
        self.parts.append(dict(ref=ref, value=value, footprint=FP.get(fp, fp), pins={str(k): v for k, v in pins.items()},
                               lcsc=lcsc, by=("dnp" if dnp else by), group=group, note=note))
    def nets(self):
        n = {}
        for p in self.parts:
            for pad, net in p["pins"].items():
                if net and net != "NC":
                    n.setdefault(net, []).append((p["ref"], pad))
        return n

# LCSC numbers for common passives (JLC basic where possible). Values in the key.
LCSC = {
    "C0402_100nF": "C1525", "C0402_10nF": "C15195", "C0402_1uF": "C52923", "C0402_100pF": "C1546", "C0402_1nF": "C1523",
    "C0402_2.2pF": "C1555", "C0402_33pF": "C426031", "C0402_15pF": "C1548", "C0402_8.2pF": "C1529",
    "C0603_100nF": "C14663", "C0603_1uF": "C15849", "C0603_4.7uF": "C19666", "C0603_10uF": "C19702", "C0805_10uF": "C15850",
    "C0805_22uF": "C45783", "C0402_10pF": "C85873", "C0402_5.6pF": "C161329", "C0402_12pF": "C85875",
    "C0402_0.6pF": "C76913", "C0402_0.7pF": "C161349", "C0402_1.2pF": "C72135", "C0402_1.4pF": "C161310",
    "C0402_1.6pF": "C161311", "C0402_2.3pF": "C2217357", "C0402_4.3pF": "C161325", "C0402_180pF": "C1600", "C0402_330pF": "C1664",
    "C0402_8.2pF": "C1529", "R0402_22k": "C25768", "R0402_470": "C25117", "R0402_1k": "C11702", "R0402_4.3k": "C25904",
    "R0402_20k": "C25765", "R0402_220": "C25091",
    "L0402_0.8nH": "C76759", "L0402_1.6nH": "C341686", "L0402_2.3nH": "C412340", "L0402_2.8nH": "C412270", "L0402_3.9nH": "C98062",
    "L0402_5.1nH": "C113117", "L0402_6.8nH": "C82919", "L0402_18nH": "C91622", "L0402_22nH": "C86129", "L0402_24nH": "C167472",
    "L0402_33nH": "C113114", "L0402_2.0nH": "C18216", "L0805_1uH": "C440216",
    "R0603_10k": "C25804", "R0603_5.1k": "C23186", "R0603_4.7k": "C23162", "R0603_1k": "C21190", "R0603_330": "C23138",
    "R0603_0": "C21189", "R0603_33": "C23140", "R0603_49.9": "C23184", "R0603_2.49k": "C22861", "R0603_100k": "C25803",
    "R0402_0": "C17168", "R0402_33": "C25105", "R0402_18": "C25113", "R0402_300": "C25102", "R0402_10k": "C25744", "R0402_4.7k": "C25900",
    "R0402_51k": "C25794", "R0402_49.9": "C25120",
    "FB0603_120R": "C1015", "LED0603_G": "C72043",
    "C0603_8.2pF": "C1685", "C0603_180pF": "C124184", "C0603_330pF": "C190577", "C0603_33pF": "C91368",
    "R0603_22k": "C31850", "R0603_470": "C23179", "R0603_51k": "C23196", "R0603_390": "C23151", "R0603_100k": "C25803",
}
def lc(pkg, val): return LCSC.get(f"{pkg}_{val}", "")

def build():
    D = Design()
    def R(ref, val, a, b, pkg="R0603", by=None, dnp=False, group="", note=""):
        D.add(ref, val, pkg, {1: a, 2: b}, lc(pkg, val), by or ("jlc" if pkg.endswith("0402") else "hand"), dnp, group, note)
    def C(ref, val, a, b="GND", pkg="C0603", by=None, dnp=False, group="", note=""):
        D.add(ref, val, pkg, {1: a, 2: b}, lc(pkg, val), by or ("jlc" if pkg.endswith("0402") else "hand"), dnp, group, note)
    def L(ref, val, a, b, pkg="L0402", lcsc="", by=None, dnp=False, group="", note=""):
        D.add(ref, val, pkg, {1: a, 2: b}, lcsc, by or ("jlc" if pkg.endswith("0402") else "hand"), dnp, group, note)

    # ------------------------------------------------------------------ ESP32-S31 (reference schematic, HW design guidelines fig. 1)
    g = "esp32"
    esp = {i: "NC" for i in range(1, 82)}
    esp.update({1: "ESP_ANT", 2: "VDDA34", 3: "VDDA34", 4: "CHIP_PU",
                5: "LDO_EN_HB", 6: "LDO_EN_MB", 7: "SW_V1", 8: "SW_V2", 9: "LDO_EN_LB", 10: "ETH_MDC", 11: "3V3",
                12: "ETH_MDIO", 13: "ETH_PHY_RST_N",
                14: "ETH_TXD0", 15: "ETH_TXD1", 16: "ETH_TXD2", 17: "ETH_TXD3", 18: "VREF_TOUCH",
                19: "ETH_TX_CTL", 20: "ETH_TX_CLK", 21: "ETH_RX_CLK", 22: "ETH_RX_CTL",
                23: "ETH_RXD3", 24: "ETH_RXD2", 25: "ETH_RXD1", 26: "ETH_RXD0",
                30: "V1P8", 34: "V1P8", 35: "V1P8",
                36: "SPI_CS_C", 37: "SPI_Q_C", 38: "SPI_WP_C", 39: "VDD_SPI", 40: "SPI_HD_C", 41: "SPI_CLK_C", 42: "SPI_D_C",
                43: "3V3", 44: "USB_DP", 45: "USB_DM", 54: "3V3",
                58: "RFFC_SCLK", 59: "RFFC_SDATA", 60: "RFFC_ENX", 61: "RFFC_ENBL", 62: "RFFC_RESETX", 63: "VREF_ADC",
                64: "3V3", 65: "RFFC_LD", 66: "LED_STAT", 67: "SW2_V1", 68: "SW2_V2",
                69: "JTAG_TDO", 70: "JTAG_TCK", 71: "JTAG_TDI", 72: "JTAG_TMS", 73: "U0TXD", 74: "U0RXD",
                75: "GPIO60", 76: "BOOT", 77: "3V3", 78: "NC", 79: "XTAL_P", 80: "3V3", 81: "GND"})
    # pins 27-33 (SDIO = GPIO20-25), 46-53 (GPIO33-40), 55-57 (GPIO42-44): internal sample bus -> must stay unconnected
    for p in [27, 28, 29, 31, 32, 33, 46, 47, 48, 49, 50, 51, 52, 53, 55, 56, 57]:
        esp[p] = "NC"
    D.add("U1", "ESP32-S31NRV16", "ESP32S31", esp, "C55601453", "jlc", group=g,
          note="LCSC stock 0 on 2026-11-09: JLC global sourcing")
    C("C101", "10uF", "3V3", pkg="C0805", group=g, note="main entry bulk")
    C("C102", "100nF", "3V3", pkg="C0402", group=g, note="VDDA1/2 (pins 77/80); guideline 10 nF, 100 nF used to save a part type")
    C("C103", "1uF", "3V3", pkg="C0402", group=g, note="VDDA1/2")
    L("L101", "2nH", "3V3", "VDDA34", lcsc="C2986275", group=g, note="VDDA3/4 LC filter (LQG15HS2N0B, 0.1 nH tol; check >=500 mA rating)")
    C("C104", "10uF", "3V3", pkg="C0805", group=g, note="VDDA3/4 rail bulk")
    C("C105", "1uF", "3V3", pkg="C0402", group=g)
    C("C106", "100nF", "3V3", pkg="C0402", group=g)
    C("C107", "100nF", "VDDA34", pkg="C0402", group=g, note="at pins 2/3")
    for i, n in enumerate(["VDDPST1", "VDDPST2", "VDDPST3", "VDDPST4"]):
        C(f"C{108+i}", "100nF", "3V3", pkg="C0402", group=g, note=f"{n} decoupling")
    C("C112", "100nF", "VREF_ADC", pkg="C0402", group=g)
    C("C113", "100nF", "VREF_TOUCH", pkg="C0402", group=g, dnp=True, note="footprint only")
    C("C114", "1uF", "V1P8", pkg="C0402", group=g, note="VDD_LDO_1P8 -> PSRAM")
    C("C115", "100nF", "V1P8", pkg="C0402", group=g)
    C("C116", "100nF", "V1P8", pkg="C0402", group=g)
    C("C117", "1uF", "VDD_SPI", pkg="C0402", group=g)
    C("C118", "100nF", "VDD_SPI", pkg="C0402", group=g)
    R("R101", "10k", "3V3", "CHIP_PU", group=g); C("C119", "1uF", "CHIP_PU", group=g, note="RC delay 10k/1uF")
    # flash (SPI, 0R series footprints per guidelines fig. 5)
    for (sig, fl) in [("CS", "SPI_CS"), ("Q", "SPI_Q"), ("WP", "SPI_WP"), ("HD", "SPI_HD"), ("CLK", "SPI_CLK"), ("D", "SPI_D")]:
        R(f"R1{10 + len([1 for s in D.parts if s['ref'].startswith('R11')])}", "0", f"SPI_{sig}_C", fl, pkg="R0402", group=g)
    D.add("U2", "GD25Q32ESIGR", "SOIC8", {1: "SPI_CS", 2: "SPI_Q", 3: "SPI_WP", 4: "GND", 5: "SPI_D", 6: "SPI_CLK", 7: "SPI_HD", 8: "VDD_SPI"},
          "C2832998", "hand", group=g, note="32 Mbit NOR, 208 mil SOP-8 (hand)")
    R("R120", "10k", "VDD_SPI", "SPI_CS", group=g, dnp=True, note="CS pull-up footprint (ref NC)")
    C("C120", "100nF", "VDD_SPI", group=g, note="at flash")
    # clock: TCXO -> XTAL_P via coupling + 24 nH (mandatory series inductor on XTAL_P)
    L("L102", "24nH", "XTAL_P_C", "XTAL_P", lcsc="C27229", group=g, note="mandatory series inductor (guidelines)")
    C("C121", "100nF", "REFCLK_ESP", "XTAL_P_C", pkg="C0402", group=g, note="AC coupling from TCXO (>=10 nF per Epson)")
    # boot / reset / UART / LED
    D.add("SW1", "RESET", "Button_Switch_SMD:SW_SPST_TL3342", {1: "CHIP_PU", 2: "CHIP_PU", 3: "GND", 4: "GND"}, "C318884", "hand", group=g)
    D.add("SW2", "BOOT", "Button_Switch_SMD:SW_SPST_TL3342", {1: "BOOT", 2: "BOOT", 3: "GND", 4: "GND"}, "C318884", "hand", group=g)
    R("R102", "10k", "3V3", "BOOT", group=g)
    D.add("J5", "UART", "HDR1x3", {1: "GND", 2: "U0TXD", 3: "U0RXD"}, "C49257", "hand", group=g, note="3.3 V UART flashing/console")
    R("R103", "1k", "LED_STAT", "LED_A", group=g)
    D.add("D101", "LED", "LED0603", {1: "GND", 2: "LED_A"}, lc("LED0603", "G"), "hand", group=g)

    # ------------------------------------------------------------------ USB-C (power + HS USB on pins 44/45)
    g = "usb"
    D.add("J4", "USB-C", "USBC", {"A1": "GND", "B12": "GND", "A12": "GND", "B1": "GND", "A4": "VBUS", "B9": "VBUS", "A9": "VBUS", "B4": "VBUS",
                                  "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM",
                                  "A8": "NC", "B8": "NC", "S1": "GND"}, "C165948", "hand", group=g)
    R("R401", "5.1k", "CC1", "GND", group=g); R("R402", "5.1k", "CC2", "GND", group=g)
    D.add("U5", "USBLC6-2SC6", "SOT23-6", {1: "USB_DP", 2: "GND", 3: "USB_DM", 4: "USB_DM", 5: "VBUS", 6: "USB_DP"}, "C7519", "hand", group=g)
    L("FB401", "120R@100MHz", "VBUS", "5V0", pkg="FB0603", lcsc=lc("FB0603", "120R"), group=g)
    C("C401", "22uF", "5V0", pkg="C0805", group=g)

    # ------------------------------------------------------------------ power
    g = "power"
    D.add("U6", "AMS1117-3.3", "SOT223", {1: "GND", 2: "3V3", 3: "5V0"}, "C6186", "hand", group=g, note="3V3 digital (ESP32, flash, switches)")
    C("C601", "22uF", "3V3", pkg="C0805", group=g); C("C602", "10uF", "5V0", pkg="C0805", group=g)
    D.add("U7", "AMS1117-3.3", "SOT223", {1: "GND", 2: "3V3_PHY", 3: "5V0"}, "C6186", "hand", group=g, note="3V3 PHY (~250 mA)")
    C("C603", "22uF", "3V3_PHY", pkg="C0805", group=g); C("C604", "10uF", "5V0", pkg="C0805", group=g)
    # low-noise 3.0 V for RFFC5072 + TCXO
    D.add("U8", "TPS7A2030PDBVR", "SOT23-5", {1: "5V0", 2: "GND", 3: "5V0", 4: "NC", 5: "3V0_RF"}, "C963429", "hand", group=g,
          note="3.0 V low-noise RF rail (RFFC5072 2.7-3.3 V)")
    C("C605", "1uF", "5V0", group=g); C("C606", "4.7uF", "3V0_RF", group=g)
    # LNA / gain-block rails 4.5 V, per-band enable from ESP32 GPIO (only the selected band's LNA is powered)
    for i, (rail, en) in enumerate([("VLNA_LB", "LDO_EN_LB"), ("VLNA_MB", "LDO_EN_MB"), ("VLNA_HB", "LDO_EN_HB"), ("VGB", "5V0")]):
        D.add(f"U{9+i}", "TPS7A2045PDBVR", "SOT23-5", {1: "5V0", 2: "GND", 3: en, 4: "NC", 5: rail}, "C2873627", "hand", group=g)
        C(f"C{607+2*i}", "1uF", "5V0", group=g); C(f"C{608+2*i}", "4.7uF", rail, group=g)
        if en != "5V0":
            R(f"R{601+i}", "100k", en, "GND", group=g, note="LDO off while ESP32 boots")

    # ------------------------------------------------------------------ reference clock (D9/D10)
    g = "clock"
    D.add("Y1", "TG2520SMN 40MHz", "TCXO2520", {1: "NC", 2: "GND", 3: "TCXO_OUT", 4: "3V0_RF"}, "C3007519", "jlc", group=g,
          note="Epson TG2520SMN 40 MHz +/-0.5 ppm: 1 NC, 2 GND, 3 OUT, 4 VCC")
    C("C701", "100nF", "3V0_RF", pkg="C0402", group=g)
    R("R701", "0", "TCXO_OUT", "REFCLK_RF", pkg="R0402", group=g, note="TCXO -> RFFC (remove for external 10 MHz)")
    R("R702", "0", "TCXO_OUT", "REFCLK_ESP", pkg="R0402", group=g, note="TCXO -> ESP32 (remove for external 40 MHz)")
    D.add("J3", "SMA_REF", "Connector_Coaxial:SMA_Amphenol_132289_EdgeMount", {1: "EXT_REF", 2: "GND"}, "", "dnp", dnp=True, group=g,
          note="optional external reference input")
    C("C702", "100nF", "EXT_REF", "EXTREF_AC", pkg="C0402", dnp=True, group=g)
    R("R703", "49.9", "EXTREF_AC", "GND", pkg="R0402", dnp=True, group=g)
    R("R704", "0", "EXTREF_AC", "REFCLK_RF", pkg="R0402", dnp=True, group=g)
    R("R705", "0", "EXTREF_AC", "REFCLK_ESP", pkg="R0402", dnp=True, group=g)

    # ------------------------------------------------------------------ Ethernet PHY (imported from phy_circuit.json)
    phy = json.load(open(os.path.join(HERE, "phy_circuit.json")))
    netmap = {"+3V3": "3V3_PHY", "ETH_PHY_RST_N": "ETH_PHY_RST_N", "ETH_MDC": "ETH_MDC", "ETH_MDIO": "ETH_MDIO"}
    for c in phy["components"]:
        ref = c["ref_hint"]
        pins = {k: netmap.get(v, v) for k, v in c["pins"].items()}
        pk = c.get("package", "")
        fp = c.get("kicad_footprint") or ""
        if not fp:
            if "QFN-40" in pk: fp = "QFN40"
            elif "3225" in pk: fp = "XTAL3225"
            elif "0402" in pk: fp = ("R0402" if ref.startswith("R") else "C0402")
            elif "0603" in pk: fp = ("R0603" if ref.startswith("R") else ("FB0603" if ref.startswith(("FB", "L")) else ("LED0603" if ref.startswith(("D", "LED")) else "C0603")))
            elif "0805" in pk: fp = "C0805"
            elif "1206" in pk: fp = "Capacitor_SMD:C_1206_3216Metric"
            elif "HR911130" in pk or "RJ45" in c.get("part", ""): fp = "esp32_sdr:RJ45_HanRun_HR911130C"
            else: fp = pk
        if any(t in ref for t in ("RJ", "J2")) or "HR911130" in c.get("part", ""):
            fp = "esp32_sdr:RJ45_HanRun_HR911130C"
        by = "dnp" if c.get("dnp") else ("jlc" if fp in ("QFN40", "XTAL3225") or fp.endswith("0402") else "hand")
        D.add(ref, c.get("value", ""), fp, pins, c.get("lcsc", ""), by, c.get("dnp", False), "phy", c.get("note", "")[:120])
    build_rf(D, R, C, L)
    return D

def build_rf(D, R, C, L, tail="esp32", hand0603=False):
    """Mixer-path RF chain (SIGNAL_CHAIN_ANALYSIS s.12), filters from analysis/export/filter_palette.json
    (EM re-optimized values override if em/filters/<name>/result.json exists)."""
    import numpy as np
    sys_path = os.path.join(HERE, "..", "analysis")
    import sys; sys.path.insert(0, sys_path)
    import filters as F
    # final values: EM-in-the-loop optimised + joint palette (em/final_palette.py, em/filters/FINAL_FILTERS.md)
    pal = json.load(open(os.path.join(HERE, "..", "em", "filters", "final_values.json")))
    rf_lcsc = json.load(open(os.path.join(sys_path, "export", "final_rf_lcsc.json")))
    rf_lcsc.update({"L0402_1nH": "C162538", "L0402_2nH": "C2986275"})
    LCSC.update({k: v for k, v in rf_lcsc.items() if v})
    def fmt(v): return ("%g" % v)
    def Lp(ref, v, a, b, group, note=""):
        D.add(ref, fmt(v) + "nH", "L0402", {1: a, 2: b}, lc("L0402", fmt(v) + "nH"), "jlc", group=group, note=note)
    def Cp(ref, v, a, b, group, note=""):
        D.add(ref, fmt(v) + "pF", "C0402", {1: a, 2: b}, lc("C0402", fmt(v) + "pF"), "jlc", group=group, note=note)
    def ladder(prefix, name, n_in, n_out, group):
        """Instantiate a filter ladder; part order = layout order (filter_em.ladder_geometry)."""
        topo = F.FILTERS[name]["topo"]; vals = pal[name]; i = 0; node = n_in; k = 0
        nseries = sum(1 for p, _ in topo if p == "s")
        si = 0
        for bi, (pos, kind) in enumerate(topo):
            if pos == "s":
                si += 1
                nxt = n_out if si == nseries else f"{prefix}_N{si}"
                t = F.PTYPE[kind][0]
                (Lp if t == "L" else Cp)(f"{prefix}{i+1}", vals[i], node, nxt, group, note=f"{name} series {kind}")
                i += 1; node = nxt
            else:
                if kind in ("L", "C"):
                    (Lp if kind == "L" else Cp)(f"{prefix}{i+1}", vals[i], node, "GND", group, note=f"{name} shunt"); i += 1
                else:   # LCs: node - L - mid - C - GND (layout order L then C)
                    mid = f"{prefix}_M{bi}"
                    Lp(f"{prefix}{i+1}", vals[i], node, mid, group, note=f"{name} shunt LCs L"); i += 1
                    Cp(f"{prefix}{i+1}", vals[i + 0], mid, "GND", group, note=f"{name} shunt LCs C"); i += 1
    g = "rf_in"
    D.add("J1", "SMA_MIX", "Connector_Coaxial:SMA_Samtec_SMA-J-P-X-ST-EM1_EdgeMount", {1: "RF_IN_SMA", 2: "GND"}, "C496550", "hand", group=g)
    D.add("D301", "KLXES15AAA1", "Diode_SMD:D_0402_1005Metric", {1: "RF_IN_SMA", 2: "GND"}, "C2892490", "jlc", group=g, note="RF ESD 0.05 pF")
    Cp("C301", 1000, "RF_IN_SMA", "SW1_COM", g, note="DC block (no DC allowed on SP3T)")
    D.parts[-1]["value"] = "1nF"; D.parts[-1]["lcsc"] = "C1523"
    sp3t = lambda ref, com, r1, r2, r3, grp, v1="SW_V1", v2="SW_V2": D.add(ref, "BGS13SN8", "esp32_sdr:Infineon_PG-TSNP-8-1_1.1x1.1mm_P0.4mm",
            {1: "3V3", 2: v2, 3: v1, 4: r3, 5: r1, 6: com, 7: r2, 8: "GND"}, "C3312946", "jlc", group=grp)
    sp3t("U20", "SW1_COM", "LB_IN", "MB_IN", "HB_IN", g)
    C("C302", "100nF", "3V3", pkg="C0402", group=g)
    # ---- LB / MB LNAs (PSA4-5043+, bias per Mini-Circuits TB-653+)
    for band, U, base in (("LB", "U21", 310), ("MB", "U22", 330)):
        g = band.lower()
        C(f"C{base}", "1nF", f"{band}_IN", f"{band}_LNA_I", pkg="C0402", group=g); D.parts[-1]["lcsc"] = "C1523"
        D.add(U, "PSA4-5043+", "SOT343", {1: f"{band}_LNA_O", 2: "GND", 3: f"{band}_LNA_I", 4: "GND"}, "C5240848", "jlc", group=g)
        Lp(f"L{base}", 33, f"{band}_LNA_O", f"{band}_CHK", g, note="RF choke, high SRF")
        D.add(f"L{base+1}", "1uH", "Inductor_SMD:L_0805_2012Metric", {1: f"{band}_CHK", 2: f"VLNA_{band}"}, "C440216", "hand", group=g)
        C(f"C{base+1}", "100pF", f"{band}_CHK", pkg="C0402", group=g)
        C(f"C{base+2}", "100nF", f"VLNA_{band}", pkg="C0402", group=g)
        if band == "LB":
            C(f"C{base+3}", "1nF", "LB_LNA_O", "LB_F_IN", pkg="C0402", group=g); D.parts[-1]["lcsc"] = "C1523"
            ladder("FLB", "LB_LPF", "LB_F_IN", "LB_OUT", g)
        else:   # MB BPF starts with a series C -> acts as DC block
            ladder("FMB", "MB_BPF2", "MB_LNA_O", "MB_OUT", g)
    # ---- HB: pre-HPF, QPL9503 (Qorvo eval values), HPF
    g = "hb"
    ladder("FHP", "HB_PRE", "HB_IN", "HB_PRE_O", g)
    Cp("C350", 10, "HB_PRE_O", "HB_LNA_I", g, note="QPL9503 input match C1")
    Cp("C351", 0.2, "HB_LNA_I", "GND", g, note="QPL9503 input tune (DNP)"); D.parts[-1]["by"] = "dnp"
    D.add("U23", "QPL9503", "Package_DFN_QFN:DFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.6mm",
          {1: "HB_VBIAS", 2: "HB_LNA_I", 3: "NC", 4: "GND", 5: "HB_SD", 6: "GND", 7: "HB_LNA_O", 8: "NC", 9: "GND"}, "C470924", "jlc", group=g)
    R("R350", "4.7k", "VLNA_HB", "HB_VBIAS", pkg="R0402", group=g, note="Qorvo eval 4.3k; 4.7k reuses a part type (slightly lower Idq)")
    C("C352", "100pF", "HB_VBIAS", pkg="C0402", group=g)
    Lp("L350", 18, "HB_LNA_O", "VLNA_HB", g, note="QPL9503 bias choke (Coilcraft 0402CS-18N on eval)")
    C("C353", "100pF", "VLNA_HB", pkg="C0402", group=g); C("C354", "1uF", "VLNA_HB", pkg="C0402", group=g)
    R("R351", "22k", "HB_SD", "GND", pkg="R0402", group=g, note="SD low = enabled")
    Cp("C355", 5.6, "HB_LNA_O", "HB_F_IN", g, note="QPL9503 output C2 (DC block)")
    ladder("FHB", "HB_HPF", "HB_F_IN", "HB_HPF_O", g)
    R("R352", "0", "HB_HPF_O", "HB_OUT", pkg="R0402", group=g, note="0R; replace with application BPF (footprint slot)")
    # ---- band switch out, gain block (GVA-62+) with 0R bypass (D3)
    g = "gain"
    sp3t("U24", "SW2_COM", "MB_OUT", "LB_OUT", "HB_OUT", g, "SW2_V1", "SW2_V2")   # own control: port map differs from U20 (layout)
    C("C360", "100nF", "3V3", pkg="C0402", group=g)
    C("C361", "1nF", "SW2_COM", "GB_I", pkg="C0402", group=g); D.parts[-1]["lcsc"] = "C1523"
    D.add("U25", "GVA-62+", "SOT89", {1: "GB_I", 2: "GND", 3: "GB_O"}, "C5445184", "jlc", group=g)
    Lp("L360", 22, "GB_O", "GB_CHK", g, note="GVA-62+ RF choke")
    D.add("L361", "1uH", "Inductor_SMD:L_0805_2012Metric", {1: "GB_CHK", 2: "VGB"}, "C440216", "hand", group=g)
    C("C362", "100pF", "GB_CHK", pkg="C0402", group=g); C("C363", "100nF", "VGB", pkg="C0402", group=g)
    C("C364", "1nF", "GB_O", "MIX_DRV", pkg="C0402", group=g); D.parts[-1]["lcsc"] = "C1523"
    R("R360", "0", "SW2_COM", "MIX_DRV", pkg="R0402", group=g, dnp=True, note="gain-block bypass (fit + remove C361/C364)")
    # ---- mixer input balun + RFFC5072
    g = "mixer"
    D.add("T1", "H3-TCM2-63WX+", "RF_Mini-Circuits:Mini-Circuits_DB1627", {1: "GND", 2: "GND", 3: "MIX_DRV", 4: "MIX_IN_P", 5: "NC", 6: "MIX_IN_N"},
          "C22383437", "jlc", group=g, note="1:2, no centre tap -> DC blocks on both legs")
    C("C370", "1nF", "MIX_IN_P", "MIX_IPP", pkg="C0402", group=g); D.parts[-1]["lcsc"] = "C1523"
    C("C371", "1nF", "MIX_IN_N", "MIX_IPN", pkg="C0402", group=g); D.parts[-1]["lcsc"] = "C1523"
    rffc = {i: "NC" for i in range(1, 34)}
    rffc.update({1: "RFFC_ENBL_I", 2: "NC", 3: "EXT_LO_DEC", 4: "RFFC_REXT", 5: "3V0_RF", 6: "LF1", 7: "LF2", 8: "LF3",
                 9: "RFFC_MODE", 10: "REF_IN", 12: "GND", 19: "3V0_RF", 22: "3V0_RF", 23: "MIX_IPP", 24: "MIX_IPN",
                 26: "RFFC_LD", 27: "IF_OP_N", 28: "IF_OP_P", 29: "RFFC_RESETX_I", 30: "RFFC_ENX_I", 31: "RFFC_SCLK_I",
                 32: "RFFC_SDATA_I", 33: "GND"})
    D.add("U3", "RFFC5072", "QFN32", rffc, "C3034742", "jlc", group=g, note="LCSC 22 in stock 2026-11-09")
    NP = "R0603" if hand0603 else "R0402"; NC_ = "C0603" if hand0603 else "C0402"
    R("R370", "51k", "RFFC_REXT", "GND", pkg=NP, group=g)
    for i, (pin_net) in enumerate(["3V0_RF", "3V0_RF", "3V0_RF"]):
        C(f"C{372+2*i}", "33pF", "3V0_RF", pkg="C0402", group=g, note=["ANA_VDD1", "DIG_VDD", "ANA_VDD2"][i]); D.parts[-1]["lcsc"] = "C426031"
        C(f"C{373+2*i}", "100nF", "3V0_RF", pkg="C0402", group=g)
    C("C378", "33pF", "EXT_LO_DEC", pkg="C0402", group=g); D.parts[-1]["lcsc"] = "C426031"
    # loop filter (RFFC eval, 52 MHz ref; ~150 kHz BW at 40 MHz)
    C("C380", "8.2pF", "LF1", "LF2", pkg=NC_, group=g)
    R("R380", "22k", "LF1", "LF_A", pkg=NP, group=g); C("C381", "180pF", "LF_A", "LF2", pkg=NC_, group=g)
    R("R381", "470", "LF2", "LF_B", pkg=NP, group=g); C("C382", "330pF", "LF_B", pkg=NC_, group=g)
    R("R382", "470", "LF_B", "LF3", pkg=NP, group=g); C("C383", "330pF", "LF3", pkg=NC_, group=g)
    C("C384", "100nF", "REFCLK_RF", "REF_IN", pkg="C0402", group=g, note="REF_IN AC coupling")
    # control lines: 1k series (3.3 V GPIO into 3.0 V part) + 33 pF
    for sig in ("SCLK", "SDATA", "ENX", "ENBL", "RESETX"):
        R(f"R38{3 + ['SCLK','SDATA','ENX','ENBL','RESETX'].index(sig)}", "1k", f"RFFC_{sig}", f"RFFC_{sig}_I", pkg=NP, group=g)
        C(f"C38{5 + ['SCLK','SDATA','ENX','ENBL','RESETX'].index(sig)}", "33pF", f"RFFC_{sig}_I", pkg=NC_, group=g)
        if not hand0603: D.parts[-1]["lcsc"] = "C426031"
    R("R388", "4.7k", "RFFC_RESETX_I", "3V0_RF", pkg=NP, group=g)
    R("R389", "4.7k", "RFFC_MODE", "GND", pkg=NP, group=g)
    # ---- IF: balun BD2425 (centre-tap DC feed), SAW with 3.9 nH shunts, tee, 3 dB pad, DC block, ESP32 CLC match
    g = "if"
    D.add("T2", "BD2425N50200AHF", "esp32_sdr:Anaren_Xinger_0404_BD2425", {1: "IF_CT", 2: "IF_SE", 3: "IF_OP_P", 4: "IF_OP_N"},
          "C502748", "jlc", group=g)
    R("R390", "0", "3V0_RF", "IF_CT", pkg="R0402", group=g, note="mixer open-collector DC feed via balun centre tap")
    C("C390", "100pF", "IF_CT", pkg="C0402", group=g); C("C391", "100nF", "IF_CT", pkg="C0402", group=g)
    Lp("L390", 3.9, "IF_SE", "GND", g, note="SAW input shunt (Murata: 4.3 nH)")
    D.add("U4", "SAFEA2G45MC0F0AR00", "Filter:Filter_1411-5_1.4x1.1mm", {1: "IF_SE", 2: "GND", 3: "GND", 4: "IF_SAW_O", 5: "GND"},
          "C910550", "jlc", group=g)
    Lp("L391", 3.9, "IF_SAW_O", "GND", g, note="SAW output shunt")
    if tail == "ufl":   # Board B: SAW -> 3 dB pad -> DC block -> U.FL (patch cable to the WROOM-1U antenna connector)
        R("R393", "300", "IF_SAW_O", "GND", pkg="R0402", group=g, note="3 dB pi pad (R1: ESP32 cal-TX protection)")
        R("R394", "18", "IF_SAW_O", "PAD_O", pkg="R0402", group=g)
        R("R395", "300", "PAD_O", "GND", pkg="R0402", group=g)
        C("C392", "33pF", "PAD_O", "IF_OUT", pkg="C0402", group=g, note="DC block (series-resonant near 2.4 GHz)"); D.parts[-1]["lcsc"] = "C426031"
        D.add("J8", "U.FL IF out", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical", {1: "IF_OUT", 2: "GND"}, "C5137195", "jlc", group=g,
              note="IPEX/U.FL gen-1 (BWU.FL-IPEX1); patch cable to WROOM-1U ANT")
    else:
        R("R391", "0", "IF_SAW_O", "ESP_RF_SEL", pkg="R0402", group=g, note="0R tee: MIXER path (fit this OR R392)")
        R("R392", "0", "NAT_RF", "ESP_RF_SEL", pkg="R0402", group=g, dnp=True, note="0R tee: NATIVE ESP32 path")
        D.add("J2", "SMA_NAT", "Connector_Coaxial:SMA_Samtec_SMA-J-P-X-ST-EM1_EdgeMount", {1: "NAT_RF", 2: "GND"}, "C496550", "hand", group=g)
        D.add("D302", "KLXES15AAA1", "Diode_SMD:D_0402_1005Metric", {1: "NAT_RF", 2: "GND"}, "C2892490", "jlc", group=g)
        R("R393", "300", "ESP_RF_SEL", "GND", pkg="R0402", group=g, note="3 dB pi pad (R1: ESP32 cal-TX protection)")
        R("R394", "18", "ESP_RF_SEL", "PAD_O", pkg="R0402", group=g)
        R("R395", "300", "PAD_O", "GND", pkg="R0402", group=g)
        C("C392", "33pF", "PAD_O", "MATCH_I", pkg="C0402", group=g, note="DC block (series-resonant near 2.4 GHz)"); D.parts[-1]["lcsc"] = "C426031"
        Cp("C393", 1.8, "MATCH_I", "GND", g, note="ESP32 CLC match, antenna side (Espressif range 1.2-1.8 pF; tune at bring-up)")
        Lp("L392", 2.7, "MATCH_I", "ESP_ANT", g, note="ESP32 CLC match series L (range 2.0-3.0 nH; tune)")
        Cp("C394", 1.8, "ESP_ANT", "GND", g, note="ESP32 CLC match, chip side (range 1.2-1.8 pF; tune)")

    # test points for spare GPIO / JTAG
    tps = ["RFFC_LD", "3V0_RF", "VGB"] if tail == "ufl" else ["GPIO60", "JTAG_TDO", "JTAG_TCK", "JTAG_TDI", "JTAG_TMS", "RFFC_LD", "3V0_RF", "VGB"]
    for i, n in enumerate(tps):
        D.add(f"TP{i+1}", n, "TestPoint:TestPoint_Pad_D1.0mm", {1: n}, "", "hand", group="test")

if __name__ == "__main__":
    D = build()
    n = D.nets()
    print(len(D.parts), "parts,", len(n), "nets")
    single = sorted(k for k, v in n.items() if len(v) == 1)
    print("single-pin nets (check):", single)

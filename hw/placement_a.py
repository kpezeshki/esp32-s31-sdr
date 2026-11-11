"""Board A (ESP-SDR base, 62 x 46 mm) placement: fixed main parts + automatic satellite placement (placement.place_rest)."""
import os, pcbnew
import build_pcb as BP
import placement as PL

FIXED_A = {   # ref: (x, y, rot)
    "J6": (6.0, 10.0, 0),            # 2x10 RA socket, body over the west edge (pins x = 6.0 / 3.46, y 10..32.9)
    "U1": (19.6, 21.0, 0),           # WROOM-1U: castellations x 10.85 / 28.35; U.FL at top-right (26.4, 12.4)
    # YT8531: MDI pins face east (RJ45); TX pins on top, RX pins on the west side.  Pads span x 32.8-38.4, y 28.2-33.8;
    # leaves a 3 mm RX lane gap to the module (castellations end at x 29.5) and a 2 mm cap column before J201's courtyard (40.5).
    "U201": (35.6, 31.0, 180),
    "Y201": (35.6, 37.6, 0),
    # RGMII 33R series resistors, pinned next to the PHY in pin order (auto-placement anchored them to the module's
    # inner pads and scattered them along the north edge, which made RGMII unroutable).
    # (TX series resistors dropped, D21: TX runs direct from the module to a via row above the PHY's TX pins.)
    # PHY satellites, pinned so decoupling sits at the pins (auto-placement pushed them 10-15 mm away):
    "C209": (39.4, 27.1, 90),        # 100n on 3V3 pin 11 (top-right corner)
    "C211": (31.4, 32.7, 0),         # 100n on 3V3 pins 28/29 (west, below the RX pins)
    "C203": (31.4, 33.8, 0),         # 100n on VDDL pin 30
    "C207": (31.4, 34.9, 0),         # 100n VDDL
    "R201": (37.7, 34.85, 0),        # RBIAS 2.49k at pin 39
    "C204": (39.4, 34.9, 90),        # 100n VDDL pins 38 / 3 (bottom-right corner)
    "C206": (39.4, 36.9, 90), "C205": (39.4, 38.9, 90),   # VDDL, column east of the crystal
    "C201": (32.9, 37.6, 90),        # XI load cap, next to crystal pad 1
    "C202": (38.3, 37.6, 90),        # XO load cap, next to crystal pad 3
    "C208": (39.6, 23.3, 90),        # 10u bulk on PHY_3V3, NE of the TX row
    # RX row (CLK, CTL, RXD0..3) above the TX row, rot 90 = pin 2 (ETH_*, module side) on top.  The 2.2 mm band
    # between the rows carries the PHY-side RX fan-in (PHY west pins -> north through the 29.5-31.5 gap -> band).
    "R213": (30.3, 21.1, 90), "R212": (31.4, 21.1, 90), "R208": (32.5, 21.1, 90),
    "R209": (33.6, 21.1, 90), "R210": (34.7, 21.1, 90), "R211": (35.8, 21.1, 90),
    "J201": (51.2, 31.0, -90),       # RJ45, front face on the east edge
    "J4": (58.4, 6.5, 90),           # USB-C on the east edge
    "U5": (51.0, 6.5, 90), "FB401": (50.5, 11.5, 0), "C401": (53.5, 13.5, 0),
    "U6": (40.0, 7.0, 0), "U7": (40.0, 16.5, 0),
    "J5": (8.5, 42.5, 90), "SW1": (20.5, 41.6, 0), "SW2": (29.1, 41.6, 0), "D101": (37.5, 43.6, 0),
    "H1": (3.0, 3.0, 0), "H2": (3.0, 43.0, 0), "H3": (58.6, 43.4, 0), "H4": (31.5, 3.0, 0),
}

def place_all(B, D):
    PL.FIXED.clear(); PL.FIXED.update(FIXED_A)
    PL.RF_CORRIDORS[:] = []
    for ref, (x, y, r) in FIXED_A.items():     # fixed parts first, so the scripted routes can use their pads ...
        if ref in B.fps: B.place(ref, x, y, r)
    module_escapes(B)
    rgmii_lanes(B)
    PL.place_rest(B, D)                         # ... and auto-placement then treats those routes as obstacles


def module_escapes(B):
    """Deterministic fan-out of the WROOM-1U inner pads (RGMII, USB, RFFC control) to vias, so the autorouter only
    has to connect vias (left to itself it weaves F.Cu between the 0.8 mm-pitch inner pads under the module and
    leaves ~20 connections unrouted).  0.45/0.2 vias at 0.8 mm pitch leave 0.35 mm gaps; stubs are 0.15 mm."""
    def esc(num, dx, dy):
        pad = B.fps["U1"].FindPadByNumber(str(num))
        if pad is None or not pad.GetNetname(): return
        x, y = B.padxy("U1", str(num)); net = pad.GetNetname()
        B.track((x, y), (x + dx, y + dy), 0.15, net=net); B.via(x + dx, y + dy, net=net, d=0.45, drill=0.2)
    top_y = 17.2 - (21.0 - 2.65)          # top inner row (pads 42..49, y = 18.35): vias at y = 17.2
    for n in range(42, 50): esc(n, 0.0, top_y)
    # west inner column (x = 15.5): RXD3..RXD0 (pads 50..53) to a diagonal via staircase x = 13.9 / 13.4 / 12.9 /
    # 12.4 so the In2 RX lanes can drop south without crossing; USB DM/DP (54/55) to x = 14.35.
    for n, xv in ((50, 13.9), (51, 13.4), (52, 12.9), (53, 12.4), (54, 14.35), (55, 14.35)): esc(n, xv - 15.5, 0.0)
    for n in range(56, 62): esc(n, 1.16, 0.0)    # east inner column (x = 20.69): vias at x = 21.85


def rgmii_lanes(B):
    """Scripted module-side RGMII routing (module escape vias -> top pad of each 33R resistor).  The PHY-side
    fan-ins (a few mm) are left to the autorouter.  Lane order was chosen so nothing crosses:
      TX on B.Cu: TXD0..3 go north from the via row to lanes y 16.45/16.10/15.75/15.40, east, then south to vias
        at y 24.55 above their resistors; TX_CLK / TX_CTL go south under the module interior (B.Cu is free there;
        CTL runs at x 18.11, midway between the module's thermal-via columns 17.41 / 18.81) to y 24.55 / 23.95.
      RX on In2: RXD3..0 drop south from the via staircase, RX_CTL / RX_CLK loop round the west side (x 11.9 /
        11.4); all run east along y 24.0 .. 25.75 under the module, turn north in the module-PHY gap
        (x 28.45 .. 30.3), and enter vias at y 19.75 above the RX resistors from the north.
    0.15 mm tracks at >= 0.35 mm pitch, 0.45/0.2 vias; every via-to-foreign-copper gap >= 0.15 mm."""
    W = 0.15
    def eth(ref):
        for p in B.fps[ref].Pads():
            if p.GetNetname().startswith("ETH_"):
                return p.GetNetname(), B.padxy(ref, p.GetNumber())
    def run(net, layer, pts):
        for a, b in zip(pts, pts[1:]): B.track(a, b, W, layer=layer, net=net)
    def via(net, x, y): B.via(x, y, net=net, d=0.45, drill=0.2)
    def mod(n): return B.padxy("U1", str(n))
    BC, I2, FC = pcbnew.B_Cu, pcbnew.In2_Cu, pcbnew.F_Cu
    VY_RX = 19.75
    # ---- TX (B.Cu -> via row y 26.6 at 0.6 mm pitch -> 45 deg F.Cu stubs into the PHY's top pins)
    VY_TX = 26.6
    def phy(n): return B.padxy("U201", str(n))
    def tx_end(net, vx, pin):
        via(net, vx, VY_TX); px, py = phy(pin); dx = px - vx
        run(net, FC, [(vx, VY_TX), (px, VY_TX + abs(dx)), (px, py)])
    # data: north to lanes, east, south through one channel each between the RX resistor vias (x 33.6 / 34.7 /
    # 35.8 at y 19.75), then 45 deg jogs (staggered) into via columns 34.2 / 34.8 / 35.4 / 36.0
    tx = [(42, 18, 16.45, 34.15, 22.60, 34.2), (43, 17, 16.10, 35.25, 22.60, 34.8),
          (44, 16, 15.75, 36.30, 22.60, 35.4), (45, 15, 15.40, 36.65, 23.00, 36.0)]
    for n, pin, ly, xc, yj, vx in tx:
        net = B.fps["U1"].FindPadByNumber(str(n)).GetNetname(); mx = mod(n)[0]
        run(net, BC, [(mx, 17.2), (mx, ly), (xc, ly), (xc, yj), (vx, yj + abs(xc - vx)), (vx, VY_TX)])
        tx_end(net, vx, pin)
    net = B.fps["U1"].FindPadByNumber("47").GetNetname(); mx = mod(47)[0]     # TX_CLK: south under the module
    run(net, BC, [(mx, 17.2), (mx, 24.55), (33.0, 24.55), (33.0, VY_TX)]); tx_end(net, 33.0, 20)
    net = B.fps["U1"].FindPadByNumber("46").GetNetname(); mx = mod(46)[0]     # TX_CTL: x 18.11 between thermal vias
    run(net, BC, [(mx, 17.2), (18.11, 17.61), (18.11, 23.95), (33.6, 23.95), (33.6, VY_TX)]); tx_end(net, 33.6, 19)
    # ---- RX (In2)
    # (via at the module, lane y along the bottom, turn-north x, lane y along the top) per resistor
    rx = [("R211", (13.9, mod(50)[1]), 24.00, 28.45, 17.90),   # RXD3
          ("R210", (13.4, mod(51)[1]), 24.35, 28.80, 18.25),   # RXD2
          ("R209", (12.9, mod(52)[1]), 24.70, 29.15, 18.60),   # RXD1
          ("R208", (12.4, mod(53)[1]), 25.05, 29.50, 18.95)]   # RXD0
    for ref, (vx, vy), yb, xu, yt in rx:
        net, (px, py) = eth(ref)
        run(net, I2, [(vx, vy), (vx, yb), (xu, yb), (xu, yt), (px, yt), (px, VY_RX)]); via(net, px, VY_RX)
        run(net, FC, [(px, VY_RX), (px, py)])
    net, (px, py) = eth("R212"); mx = mod(49)[0]              # RX_CTL: west along y 17.2, south at x 11.9
    run(net, I2, [(mx, 17.2), (11.9, 17.2), (11.9, 25.40), (29.85, 25.40), (29.85, 19.30), (px, 19.30), (px, VY_RX)])
    via(net, px, VY_RX); run(net, FC, [(px, VY_RX), (px, py)])
    net, (px, py) = eth("R213"); mx = mod(48)[0]              # RX_CLK: north to 16.6, west, south at x 11.4
    run(net, I2, [(mx, 17.2), (mx, 16.6), (11.4, 16.6), (11.4, 25.75), (px, 25.75), (px, VY_RX)])
    via(net, px, VY_RX); run(net, FC, [(px, VY_RX), (px, py)])

def zones(B):
    pts = [(0.3, 0.3), (BP.BW - 0.3, 0.3), (BP.BW - 0.3, BP.BH - 0.3), (0.3, BP.BH - 0.3)]
    B.poly_zone(pts, pcbnew.In1_Cu, "GND", name="GND_L2")
    B.poly_zone(pts, pcbnew.In2_Cu, "3V3", name="3V3_L3")
    if not os.environ.get("NO_OUTER_POUR"):
        B.poly_zone(pts, pcbnew.B_Cu, "GND", name="GND_L4"); B.poly_zone(pts, pcbnew.F_Cu, "GND", name="GND_L1")

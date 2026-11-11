# Cost plan vs the $50/board @ qty 5 target (2026-11-09)

Inputs: PART_SELECTION.md (LCSC/JLC prices of 2026-11-09), analysis/bom_cost.py, JLC fee page (pcb-assembly-price, 2026-10-22).

## Where the money goes (LEAN variant, JLC Standard PCBA, qty 5)
| Item | $/board | Note |
|---|---|---|
| RFFC5072TR13 | 15.62 | **31 % of budget.** Only 22 in stock at LCSC. No cheaper integrated PLL+VCO+mixer exists: MAX2871 is $8.6 and ADF4350 $7.9 *without* a mixer, and RFFC2072 ($9.5) stops at 2.7 GHz. |
| ESP32-S31NRV16 + flash | 5.73 | **0 in stock at LCSC** (chip and WROOM-3 module). JLC global sourcing or consignment needed. |
| GbE: YT8531 + 25 MHz xtal + magjack | 3.78 | Plus 3 part types in fees, ≈ $6.7 total. |
| Rest of components | ≈ 6.4 | |
| JLC fixed fees | ≈ 27.9 | Setup $25.56 + stencil $8.21 per order, $1.53 per part type (basic parts too), X-ray, PCB about $15. **The bare ESP32 is 0.35 mm pitch, so Standard PCBA is mandatory** (verified: JLC lists QFN-80 8×8 P0.35). |
| **Total** | **≈ 59.4** | |

The module route (WROOM-3U on Economic PCBA) **does not help**. Economic saves about $4.8/board on setup and stencil, but charges $3.07 per *extended* type instead of $1.53 per type. Every RF part is extended, so the net is about zero.

## Options that reach < $50 @ 5
| # | Option | $/board @5 | Trade-off |
|---|---|---|---|
| A | **JLC bare PCB + stencil, you assemble (LCSC kit)** | **≈ 49 (full design), ≈ 40 (lean)** | You reflow a 0.35 mm QFN80, a 5×5 QFN32 and small DFN/TSLP parts. Excludes LCSC/JLC shipping (about $15–25/order, so +$3–5/board). Keeps GbE, both LNAs, the gain block and the balun. |
| B | JLC assembles everything except the ESP32 and RFFC5072; you hand-place those two | ≈ 50–55 | Standard is still required if JLC places any fine-pitch part. Otherwise Economic with about 25 extended types. Marginal. |
| C | Build qty 10 (LEAN) | ≈ 46.7 | Lean cuts: one LNA (PSA4-5043+, 0.05–4 GHz, so HB to 4 GHz only unless the LNA is QPL9547 at $6.3), no gain block, single-ended mixer drive. NF LB about 2.5–6 dB, HB much worse. |
| D | LEAN, no GbE (20 MS/s over HS-USB) | ≈ 52.5 @5, 41 @10 | Loses half the bandwidth and the GbE requirement. |

## Unverified, could move totals by ±$10/board
- JLC "pre-reflow soldering $0.016/joint". If it applies to all about 600 SMT joints, add about $9.6/board to any JLC-assembled option. It does not apply to option A.
- Whether X-ray is billed per leadless part or per board (±$3–4/board).
- PCB price (about $15 assumed for 5 pcs, 4-layer, impedance stack).
→ A live JLC quote with a real BOM/CPL settles all three. That needs a schematic first.

## Recommendation
Option A if you are comfortable reflowing the QFN80. It is the only path that keeps the full RF chain under $50 at qty 5. Otherwise build qty 10 of the full design with JLC Standard: $59.8 per board, about $10 over target. That is still roughly 10× cheaper than an AD9361 board.

## Hybrid build (D11): JLC places only the hard parts, you hand-solder the rest (2026-11-09)
`analysis/hybrid_cost.py`. JLC still has to use Standard PCBA for the ESP32. JLC places 24 part types: about 12 ICs/RF parts plus about 12 0402 RF passive values. Every non-RF passive is 0603+ and hand-soldered, so it isn't counted. An LCSC shipping charge of $15/order is included for the hand-solder kit.

| Variant | qty | X-ray billing | Components | JLC part types | Fixed/board | **Total/board** |
|---|---|---|---|---|---|---|
| Hybrid, full design | 5 | per board | $42.44 | 24 | $22.38 | **$64.82** |
| Hybrid, full design | 5 | per placement | $42.44 | 24 | $28.94 | **$71.38** |
| Hybrid, full design | 10 | per board | $42.44 | 24 | $12.83 | **$55.27** |
| Hybrid, full design | 10 | per placement | $42.44 | 24 | $16.09 | **$58.53** |
| Hybrid, full design + cost trims | 5 | per board | $39.41 | 24 | $22.38 | **$61.79** |
| Hybrid, full design + cost trims | 5 | per placement | $39.41 | 24 | $28.94 | **$68.35** |
| Hybrid, full design + cost trims | 10 | per board | $39.41 | 24 | $12.83 | **$52.24** |
| Hybrid, full design + cost trims | 10 | per placement | $39.41 | 24 | $16.09 | **$55.50** |

Cost trims: SKY67183 instead of QPL9503 (low stock), a Tokmas GVA-63 clone (unverified), LP5907 LDOs.
**Hybrid saves about $7–11/board compared with full JLC assembly, but it still does not reach $50 at qty 5.** Components alone are about $39–42, and the RFFC5072 is $15.6 of that. The minimum JLC Standard overhead (setup + stencil + PCB) is about $10/board at qty 5 before any per-part fees. At qty 10 the trimmed hybrid is about $52–56.

## HB_PRE: EM co-simulation (Sonnet, 8 ports, layout 5.9 x 2.8 mm)

| Element | Palette value (lumped design) | After EM re-opt (palette only) |
|---|---|---|
| C1 | 1.4 pF | **2.3 pF** |
| L2 | 2.3 nH | **1.9 nH** |
| C3 | 1.6 pF | **1.7 pF** |

| Metric | Lumped model | EM, lumped values | EM, re-optimized |
|---|---|---|---|
| IL max 3.10-6.00 GHz (<= 0.35) | 0.18 | 0.63 | 0.41 |
| RL min 3.10-6.00 GHz (>= 15.0) | 27.90 | 10.90 | 16.03 |
| Rej min 0.03-1.00 GHz (>= 15) | 16.12 | 16.84 | 15.02 |

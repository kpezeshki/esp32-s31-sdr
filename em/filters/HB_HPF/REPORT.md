## HB_HPF: EM co-simulation (Sonnet, 20 ports, layout 10.2 x 4.5 mm)

| Element | Palette value (lumped design) | After EM re-opt (palette only) |
|---|---|---|
| C1 | 1.2 pF | **3.3 pF** |
| L2 | 2.3 nH | **2 nH** |
| C3 | 2.3 pF | **4.3 pF** |
| C4 | 0.7 pF | **1.2 pF** |
| L5 | 2.8 nH | **2.6 nH** |
| C6 | 1.2 pF | **1.7 pF** |
| C7 | 0.6 pF | **1 pF** |
| L8 | 1.6 nH | **1.1 nH** |
| C9 | 0.7 pF | **0.9 pF** |

| Metric | Lumped model | EM, lumped values | EM, re-optimized |
|---|---|---|---|
| IL max 3.10-6.00 GHz (<= 1.6) | 1.63 | 5.38 | 2.99 |
| RL min 3.10-6.00 GHz (>= 13.0) | 12.39 | 2.89 | 8.99 |
| Rej min 2.40-2.48 GHz (>= 47) | 45.79 | 37.53 | 34.45 |
| Rej min 0.03-1.90 GHz (>= 52) | 51.67 | 49.44 | 47.46 |

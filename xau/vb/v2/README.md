# XAU Volatility Breakout V2

VB V2 is developed only on 2015-2023. See `RESEARCH_POLICY.md`.

The first V2 baseline corrects execution and risk issues before adding strategy
logic:

- true H1 data is used for H1 ADX;
- H1 ADX is lagged to the last completed H1 bar at the H4 signal decision;
- entry stop distance uses the completed H4 signal bar ATR;
- position size is calculated from a fixed equity risk budget;
- lots are rounded down to the broker lot step;
- trades below the minimum executable lot are skipped;
- stop gaps fill at the worse bar-open price instead of the stop price.

Run the 2015-2023 corrected baseline:

```bash
.venv/bin/python xau/vb/v2/engine.py
```

Run the predefined development comparison:

```bash
.venv/bin/python xau/vb/v2/research/compare_candidates.py
```

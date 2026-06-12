# Regime Baseline Report: 2025

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `5223.38` / `5325.75`
- Return: `166.29%`
- Profit factor: `5.227`
- Maximum drawdown: `6.22%`
- Trades: `2054`

## Margin

- Peak used margin: `90.66`
- Minimum free margin: `1971.27`
- Minimum margin level: `3659.35%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `1010`
- Total simultaneous-position hours: `820.25`
- Same / opposite direction simultaneous hours: `146.75` / `673.50`

## Example Simultaneous Positions

- `2025-01-27T01:45:00+00:00`: MR long @ 2768.37 (margin 27.68) | VB long @ 2773.52 (margin 27.74)
- `2025-01-27T02:15:00+00:00`: MR long @ 2768.56 (margin 27.69) | VB long @ 2773.52 (margin 27.74)
- `2025-01-27T04:30:00+00:00`: MR long @ 2758.06 (margin 27.58) | VB long @ 2773.52 (margin 27.74)
- `2025-01-27T05:30:00+00:00`: MR long @ 2761.21 (margin 27.61) | VB long @ 2773.52 (margin 27.74)
- `2025-01-27T07:00:00+00:00`: MR long @ 2758.29 (margin 27.58) | VB long @ 2773.52 (margin 27.74)
- `2025-01-27T20:00:00+00:00`: MR long @ 2733.72 (margin 27.34) | VB short @ 2733.51 (margin 27.34)
- `2025-01-27T20:30:00+00:00`: MR long @ 2736.63 (margin 27.37) | VB short @ 2733.51 (margin 27.34)
- `2025-01-27T21:00:00+00:00`: MR long @ 2737.17 (margin 27.37) | VB short @ 2733.51 (margin 27.34)
- `2025-01-27T21:45:00+00:00`: MR long @ 2738.41 (margin 27.38) | VB short @ 2733.51 (margin 27.34)
- `2025-01-27T22:15:00+00:00`: MR long @ 2739.28 (margin 27.39) | VB short @ 2733.51 (margin 27.34)

## Positions At End

- VB: short @ 4421.48

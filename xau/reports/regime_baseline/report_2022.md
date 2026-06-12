# Regime Baseline Report: 2022

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `3026.61` / `3036.53`
- Return: `51.83%`
- Profit factor: `3.502`
- Maximum drawdown: `3.22%`
- Trades: `2179`

## Margin

- Peak used margin: `41.05`
- Minimum free margin: `1979.28`
- Minimum margin level: `5641.84%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `832`
- Total simultaneous-position hours: `680.75`
- Same / opposite direction simultaneous hours: `161.25` / `519.50`

## Example Simultaneous Positions

- `2022-01-27T00:00:00+00:00`: MR long @ 1817.63 (margin 18.18) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T03:45:00+00:00`: MR long @ 1817.17 (margin 18.17) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T04:15:00+00:00`: MR long @ 1815.16 (margin 18.15) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T05:15:00+00:00`: MR long @ 1817.23 (margin 18.17) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T05:45:00+00:00`: MR long @ 1816.21 (margin 18.16) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T06:15:00+00:00`: MR long @ 1815.96 (margin 18.16) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T07:00:00+00:00`: MR long @ 1815.89 (margin 18.16) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T10:00:00+00:00`: MR long @ 1811.05 (margin 18.11) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T13:30:00+00:00`: MR long @ 1810.51 (margin 18.11) | VB short @ 1819.88 (margin 18.20)
- `2022-01-27T15:15:00+00:00`: MR long @ 1807.28 (margin 18.07) | VB short @ 1819.88 (margin 18.20)

## Positions At End

- VB: long @ 1813.82
- MR: short @ 1823.88

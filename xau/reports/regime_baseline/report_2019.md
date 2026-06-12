# Regime Baseline Report: 2019

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `2314.34` / `2366.60`
- Return: `18.33%`
- Profit factor: `1.852`
- Maximum drawdown: `4.71%`
- Trades: `2124`

## Margin

- Peak used margin: `30.52`
- Minimum free margin: `1983.81`
- Minimum margin level: `7215.15%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `807`
- Total simultaneous-position hours: `901.25`
- Same / opposite direction simultaneous hours: `94.25` / `807.00`

## Example Simultaneous Positions

- `2019-01-25T20:00:00+00:00`: MR short @ 1297.57 (margin 12.98) | VB long @ 1297.82 (margin 12.98)
- `2019-01-25T20:45:00+00:00`: MR short @ 1298.29 (margin 12.98) | VB long @ 1297.82 (margin 12.98)
- `2019-01-25T21:45:00+00:00`: MR short @ 1298.05 (margin 12.98) | VB long @ 1297.82 (margin 12.98)
- `2019-01-25T22:15:00+00:00`: MR short @ 1298.50 (margin 12.98) | VB long @ 1297.82 (margin 12.98)
- `2019-01-25T22:45:00+00:00`: MR short @ 1298.93 (margin 12.99) | VB long @ 1297.82 (margin 12.98)
- `2019-01-25T23:30:00+00:00`: MR short @ 1302.74 (margin 13.03) | VB long @ 1297.82 (margin 12.98)
- `2019-01-28T03:30:00+00:00`: MR short @ 1301.28 (margin 13.01) | VB long @ 1297.82 (margin 12.98)
- `2019-01-28T04:00:00+00:00`: MR short @ 1301.58 (margin 13.02) | VB long @ 1297.82 (margin 12.98)
- `2019-01-28T04:45:00+00:00`: MR short @ 1302.48 (margin 13.02) | VB long @ 1297.82 (margin 12.98)
- `2019-01-28T05:15:00+00:00`: MR short @ 1302.30 (margin 13.02) | VB long @ 1297.82 (margin 12.98)

## Positions At End

- VB: long @ 1467.95

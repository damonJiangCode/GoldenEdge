# Regime Baseline Report: 2015

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `2224.28` / `2224.28`
- Return: `11.21%`
- Profit factor: `2.813`
- Maximum drawdown: `0.97%`
- Trades: `1861`

## Margin

- Peak used margin: `23.73`
- Minimum free margin: `1983.86`
- Minimum margin level: `9035.37%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `104`
- Total simultaneous-position hours: `143.00`
- Same / opposite direction simultaneous hours: `59.00` / `84.00`

## Example Simultaneous Positions

- `2015-10-08T08:45:00+00:00`: MR long @ 1143.42 (margin 11.43) | VB long @ 1143.91 (margin 11.44)
- `2015-10-08T09:30:00+00:00`: MR long @ 1142.55 (margin 11.43) | VB long @ 1143.91 (margin 11.44)
- `2015-10-09T12:15:00+00:00`: MR short @ 1152.85 (margin 11.53) | VB long @ 1154.00 (margin 11.54)
- `2015-10-09T13:30:00+00:00`: MR short @ 1155.47 (margin 11.55) | VB long @ 1154.00 (margin 11.54)
- `2015-10-09T14:00:00+00:00`: MR short @ 1154.15 (margin 11.54) | VB long @ 1154.00 (margin 11.54)
- `2015-10-09T14:30:00+00:00`: MR short @ 1153.86 (margin 11.54) | VB long @ 1154.00 (margin 11.54)
- `2015-10-09T15:00:00+00:00`: MR short @ 1153.80 (margin 11.54) | VB long @ 1154.00 (margin 11.54)
- `2015-10-09T18:15:00+00:00`: MR short @ 1157.44 (margin 11.57) | VB long @ 1154.00 (margin 11.54)
- `2015-10-09T18:45:00+00:00`: MR short @ 1157.87 (margin 11.58) | VB long @ 1154.00 (margin 11.54)
- `2015-10-09T19:15:00+00:00`: MR short @ 1158.06 (margin 11.58) | VB long @ 1154.00 (margin 11.54)

## Positions At End

- No open positions.

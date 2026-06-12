# Regime Baseline Report: 2020

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `3035.74` / `3035.74`
- Return: `51.79%`
- Profit factor: `3.374`
- Maximum drawdown: `3.62%`
- Trades: `1804`

## Margin

- Peak used margin: `41.10`
- Minimum free margin: `1983.50`
- Minimum margin level: `6341.56%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `576`
- Total simultaneous-position hours: `392.00`
- Same / opposite direction simultaneous hours: `80.00` / `312.00`

## Example Simultaneous Positions

- `2020-01-27T04:00:00+00:00`: MR short @ 1581.10 (margin 15.81) | VB long @ 1581.29 (margin 15.81)
- `2020-01-27T04:45:00+00:00`: MR short @ 1581.84 (margin 15.82) | VB long @ 1581.29 (margin 15.81)
- `2020-01-27T08:15:00+00:00`: MR short @ 1580.20 (margin 15.80) | VB long @ 1581.29 (margin 15.81)
- `2020-01-27T11:45:00+00:00`: MR short @ 1582.25 (margin 15.82) | VB long @ 1581.29 (margin 15.81)
- `2020-01-27T12:15:00+00:00`: MR short @ 1582.61 (margin 15.83) | VB long @ 1581.29 (margin 15.81)
- `2020-01-27T13:15:00+00:00`: MR short @ 1584.82 (margin 15.85) | VB long @ 1581.29 (margin 15.81)
- `2020-01-27T14:00:00+00:00`: MR short @ 1584.37 (margin 15.84) | VB long @ 1581.29 (margin 15.81)
- `2020-01-28T08:00:00+00:00`: MR long @ 1579.31 (margin 15.79) | VB long @ 1581.29 (margin 15.81)
- `2020-01-28T14:30:00+00:00`: MR long @ 1574.62 (margin 15.75) | VB long @ 1581.29 (margin 15.81)
- `2020-01-28T15:00:00+00:00`: MR long @ 1574.22 (margin 15.74) | VB long @ 1581.29 (margin 15.81)

## Positions At End

- No open positions.

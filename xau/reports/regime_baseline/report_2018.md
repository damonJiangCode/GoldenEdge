# Regime Baseline Report: 2018

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `2223.94` / `2241.33`
- Return: `12.07%`
- Profit factor: `1.855`
- Maximum drawdown: `2.02%`
- Trades: `2306`

## Margin

- Peak used margin: `27.20`
- Minimum free margin: `1945.95`
- Minimum margin level: `7355.28%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `908`
- Total simultaneous-position hours: `690.75`
- Same / opposite direction simultaneous hours: `254.75` / `436.00`

## Example Simultaneous Positions

- `2018-01-30T08:00:00+00:00`: MR long @ 1335.27 (margin 13.35) | VB short @ 1335.10 (margin 13.35)
- `2018-01-30T08:45:00+00:00`: MR long @ 1335.51 (margin 13.36) | VB short @ 1335.10 (margin 13.35)
- `2018-01-30T09:15:00+00:00`: MR long @ 1335.86 (margin 13.36) | VB short @ 1335.10 (margin 13.35)
- `2018-01-30T10:00:00+00:00`: MR long @ 1336.33 (margin 13.36) | VB short @ 1335.10 (margin 13.35)
- `2018-01-30T12:15:00+00:00`: MR short @ 1343.29 (margin 13.43) | VB short @ 1335.10 (margin 13.35)
- `2018-01-30T13:00:00+00:00`: MR short @ 1344.08 (margin 13.44) | VB short @ 1335.10 (margin 13.35)
- `2018-01-30T13:30:00+00:00`: MR short @ 1345.11 (margin 13.45) | VB short @ 1335.10 (margin 13.35)
- `2018-01-30T14:15:00+00:00`: MR short @ 1344.86 (margin 13.45) | VB short @ 1335.10 (margin 13.35)
- `2018-01-30T15:45:00+00:00`: MR short @ 1344.64 (margin 13.45) | VB short @ 1335.10 (margin 13.35)
- `2018-02-01T02:45:00+00:00`: MR short @ 1346.46 (margin 13.46) | VB short @ 1343.38 (margin 13.43)

## Positions At End

- VB: long @ 1262.84

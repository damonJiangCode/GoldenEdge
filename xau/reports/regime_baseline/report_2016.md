# Regime Baseline Report: 2016

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `2363.45` / `2363.45`
- Return: `18.17%`
- Profit factor: `2.690`
- Maximum drawdown: `2.20%`
- Trades: `1957`

## Margin

- Peak used margin: `27.27`
- Minimum free margin: `1988.37`
- Minimum margin level: `8225.20%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `152`
- Total simultaneous-position hours: `172.25`
- Same / opposite direction simultaneous hours: `19.00` / `153.25`

## Example Simultaneous Positions

- `2016-02-24T16:00:00+00:00`: MR short @ 1243.42 (margin 12.43) | VB long @ 1243.71 (margin 12.44)
- `2016-02-24T16:30:00+00:00`: MR short @ 1244.09 (margin 12.44) | VB long @ 1243.71 (margin 12.44)
- `2016-02-24T17:30:00+00:00`: MR short @ 1250.12 (margin 12.50) | VB long @ 1243.71 (margin 12.44)
- `2016-02-24T18:30:00+00:00`: MR short @ 1248.56 (margin 12.49) | VB long @ 1243.71 (margin 12.44)
- `2016-02-24T22:00:00+00:00`: MR long @ 1229.82 (margin 12.30) | VB long @ 1243.71 (margin 12.44)
- `2016-02-24T22:45:00+00:00`: MR long @ 1229.62 (margin 12.30) | VB long @ 1243.71 (margin 12.44)
- `2016-02-24T23:15:00+00:00`: MR long @ 1229.86 (margin 12.30) | VB long @ 1243.71 (margin 12.44)
- `2016-02-24T23:45:00+00:00`: MR long @ 1229.43 (margin 12.29) | VB long @ 1243.71 (margin 12.44)
- `2016-04-20T09:15:00+00:00`: MR long @ 1249.13 (margin 12.49) | VB long @ 1250.95 (margin 12.51)
- `2016-04-20T11:15:00+00:00`: MR long @ 1247.49 (margin 12.47) | VB long @ 1250.95 (margin 12.51)

## Positions At End

- No open positions.

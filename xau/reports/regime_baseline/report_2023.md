# Regime Baseline Report: 2023

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `2992.95` / `2992.95`
- Return: `49.65%`
- Profit factor: `3.764`
- Maximum drawdown: `3.36%`
- Trades: `1857`

## Margin

- Peak used margin: `41.74`
- Minimum free margin: `1979.01`
- Minimum margin level: `5276.44%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `754`
- Total simultaneous-position hours: `989.25`
- Same / opposite direction simultaneous hours: `286.00` / `703.25`

## Example Simultaneous Positions

- `2023-01-26T00:00:00+00:00`: MR short @ 1945.80 (margin 19.46) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T01:30:00+00:00`: MR short @ 1947.46 (margin 19.47) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T02:00:00+00:00`: MR short @ 1948.36 (margin 19.48) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T06:15:00+00:00`: MR short @ 1947.00 (margin 19.47) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T07:00:00+00:00`: MR short @ 1946.62 (margin 19.47) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T08:30:00+00:00`: MR short @ 1947.54 (margin 19.48) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T09:30:00+00:00`: MR long @ 1941.06 (margin 19.41) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T12:00:00+00:00`: MR long @ 1936.94 (margin 19.37) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T12:45:00+00:00`: MR long @ 1937.34 (margin 19.37) | VB long @ 1946.61 (margin 19.47)
- `2023-01-26T13:45:00+00:00`: MR long @ 1936.00 (margin 19.36) | VB long @ 1946.61 (margin 19.47)

## Positions At End

- No open positions.

# Regime Baseline Report: 2017

No Regime selector is applied. VB and MR retain their original engine logic.

## Portfolio Rules

- VB maximum open positions: `1`
- MR maximum open positions: `1`
- Portfolio maximum open positions: `2`
- Leverage: `1:100`
- Single shared account initial balance: `2000`

## Result

- Final balance / equity: `2208.18` / `2208.18`
- Return: `10.41%`
- Profit factor: `1.790`
- Maximum drawdown: `2.73%`
- Trades: `2124`

## Margin

- Peak used margin: `27.08`
- Minimum free margin: `1986.24`
- Minimum margin level: `8118.59%`
- Insufficient shared-margin observations: `0`

## Position Validation

- Maximum simultaneous positions: `2`
- Maximum VB / MR positions: `1` / `1`
- Position-limit violation events: `0`
- Simultaneous-position periods: `695`
- Total simultaneous-position hours: `659.50`
- Same / opposite direction simultaneous hours: `129.50` / `530.00`

## Example Simultaneous Positions

- `2017-02-02T08:00:00+00:00`: MR short @ 1216.23 (margin 12.16) | VB long @ 1216.54 (margin 12.17)
- `2017-02-02T11:15:00+00:00`: MR short @ 1216.52 (margin 12.17) | VB long @ 1216.54 (margin 12.17)
- `2017-02-02T11:45:00+00:00`: MR short @ 1216.54 (margin 12.17) | VB long @ 1216.54 (margin 12.17)
- `2017-02-02T12:45:00+00:00`: MR short @ 1222.32 (margin 12.22) | VB long @ 1216.54 (margin 12.17)
- `2017-02-02T13:15:00+00:00`: MR short @ 1220.92 (margin 12.21) | VB long @ 1216.54 (margin 12.17)
- `2017-02-02T14:15:00+00:00`: MR short @ 1221.86 (margin 12.22) | VB long @ 1216.54 (margin 12.17)
- `2017-02-02T15:30:00+00:00`: MR short @ 1223.13 (margin 12.23) | VB long @ 1216.54 (margin 12.17)
- `2017-02-02T16:00:00+00:00`: MR short @ 1223.58 (margin 12.24) | VB long @ 1216.54 (margin 12.17)
- `2017-02-03T02:45:00+00:00`: MR long @ 1213.39 (margin 12.13) | VB long @ 1216.54 (margin 12.17)
- `2017-02-03T14:30:00+00:00`: MR long @ 1212.13 (margin 12.12) | VB long @ 1216.54 (margin 12.17)

## Positions At End

- No open positions.

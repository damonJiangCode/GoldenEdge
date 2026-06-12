# June 2026 MT5 Regime Baseline

`regime_baseline.py` simulates or executes the no-Regime VB + MR baseline on
one MT5 account.

It reuses the indicator and signal functions from:

- `mt5/2026/may/strategies/VB_H4_V1.py`
- `mt5/2026/jun/strategies/MR_M15_V1.py`

The combined runner owns order placement, position isolation, shared-margin
checks, position reporting, and stop management.

## Safety Rules

- Default mode is dry-run. It calculates and validates orders but never sends
  an entry or stop update.
- Live mode requires an MT5 hedging account.
- VB and MR use separate magic numbers.
- Each strategy may hold at most one position.
- The portfolio may hold at most two managed positions.
- Any foreign account position blocks new entries.
- Every entry must pass both `order_calc_margin` and the broker's
  `order_check`.
- Projected free margin after an order must remain above the configured floor.
- When both strategies signal in the same dry-run cycle, the second simulated
  order includes the first simulated order's reserved margin.

The runner does not close foreign positions and does not automatically liquidate
positions when a validation rule is violated. It fails closed by blocking new
entries and reporting the violation.

Dry-run validates current signals and broker preflights against the live account,
but it does not create persistent virtual positions or simulate their later
exits.

## Required Environment

```powershell
$env:MT5_ACCOUNT = "your-account-number"
$env:MT5_PASSWORD = "your-password"
$env:MT5_SERVER = "your-server"
$env:MT5_PATH = "C:\Program Files\MetaTrader 5\terminal64.exe"
```

Optional settings:

```powershell
$env:REGIME_SYMBOL = "XAUUSD"
$env:REGIME_LOT = "0.01"
$env:REGIME_RUNTIME_SECONDS = "20"
$env:REGIME_MIN_FREE_MARGIN_AFTER_ORDER = "100"
$env:REGIME_VB_MAGIC = "2026061502"
$env:REGIME_MR_MAGIC = "2026061501"
```

## Run

One dry-run cycle:

```powershell
python mt5/2026/jun/regime_baseline.py --once
```

Continuous dry-run simulation:

```powershell
python mt5/2026/jun/regime_baseline.py
```

Live execution:

```powershell
python mt5/2026/jun/regime_baseline.py --live
```

Do not use `--live` until dry-run snapshots show the expected account, symbol,
hedging mode, position ownership, and margin values.

## Runtime Outputs

Files are written under `mt5/2026/jun/logs/`:

- `regime_baseline_events.jsonl`: append-only decisions, signals, margin
  preflights, order results, and stop updates.
- `regime_baseline_snapshot.json`: latest single-account balance, equity,
  margin, free margin, and all current positions.
- `regime_baseline_state_dry_run.json` and `regime_baseline_state_live.json`:
  separate last-consumed-signal and managed-bar state, preventing duplicate
  orders after restart without allowing simulation runs to consume live
  signals.

The snapshot's `positions` section shows every current order with strategy,
magic number, direction, entry price, current price, SL, TP, and floating PnL.

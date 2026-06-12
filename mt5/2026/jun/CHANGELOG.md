# June 2026 MT5 Changelog

## 2026-06-12 - Single-Account Regime Baseline Simulator

### Added

- Added `regime_baseline.py` as the combined MT5 dry-run/live runner for
  VB H4 v1 and MR M15 v1.
- Reused the existing strategy modules for indicators and signal decisions.
- Added one-position-per-strategy and two-position-per-account enforcement.
- Added distinct VB/MR magic-number ownership and fail-closed foreign-position
  detection.
- Added broker-native `order_calc_margin` and `order_check` preflight checks.
- Added a configurable minimum projected free-margin floor.
- Added current account and position snapshots, including balance, equity,
  margin, free margin, strategy, side, entry, SL, TP, and floating PnL.
- Added separate dry-run and live signal state to prevent simulation from
  consuming live signals.
- Added atomic signal consumption before live order attempts to reduce duplicate
  order risk after process failure.
- Added hedging-account enforcement for live mode.
- Added completed-bar-only VB trailing-stop management and MR breakeven
  management.

### Safety Defaults

- Default execution mode is dry-run.
- Real order and stop requests require explicit `--live`.
- Account credentials are read from environment variables and are not stored in
  the combined runner.
- Any unknown account position, duplicate strategy position, failed broker
  preflight, or insufficient projected free margin blocks new orders.

### Verification

- Python static compilation passed.
- Offline MT5-object tests confirmed:
  - one VB plus one MR position is valid;
  - duplicate strategy positions are rejected;
  - foreign account positions are rejected;
  - insufficient projected free margin blocks orders;
  - a full two-signal dry-run cycle calls `order_send` zero times;
  - the second same-cycle simulated order includes the first order's reserved
    margin.

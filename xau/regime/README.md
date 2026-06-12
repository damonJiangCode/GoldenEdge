# XAU Regime Research

This directory contains the control baseline and future Regime-selection
research for the XAU VB v1 and MR v1 strategies.

## Fixed Combination Baseline

`baseline_engine.py` is the no-Regime control group. It directly runs the
existing engines without changing their parameters, entries, exits, costs, or
position handling:

- VB v1 and MR v1 trade one shared account with `2000` initial balance.
- Child-engine balances are attribution ledgers only; they do not represent
  separately funded accounts.
- Both strategies may hold positions at the same time, including opposite
  directions.
- There is no shared margin, Regime filter, strategy selector, conflict
  resolution, or dynamic weighting.
- Account equity is `2000 + VB equity PnL + MR equity PnL`.
- Portfolio margin is monitored at `1:100` by summing both strategy margins.
- Each strategy may hold at most one position; the portfolio may hold at most
  two positions.
- Annual JSON reports include position events that show the currently open VB
  and MR orders after each entry or exit.
- The shared account resets to `2000` at the start of each annual report.

Run the full 2015-2025 baseline:

```bash
.venv/bin/python xau/regime/baseline_engine.py
```

Run one year:

```bash
.venv/bin/python xau/regime/baseline_engine.py --year 2025
```

Outputs are written to `xau/reports/regime_baseline/`:

- `summary.md`, `summary.json`, and `summary.csv`: full-period summaries.
- `report_YEAR.json`: annual portfolio report with aligned equity series and
  child-engine details.
- `trades_YEAR.csv` and `trades_all.csv`: full 55-column unified trade schema.

Annual return and drawdown use portfolio equity, including unrealized PnL from
positions still open at year-end. Profit factor and unified trade summaries use
closed trades only.

Historical results are research data, not pristine OOS. Future Regime models
must be compared against this fixed baseline using the same capital allocation,
years, costs, and reporting rules.

## Robust Optimization Baseline

`robust_baseline.py` audits the fixed-lot baseline before Regime optimization.
It provides two separate views:

- Executable capital view: retain the original `0.01 lot`, but use `10000` per
  strategy sleeve so the maximum observed initial stop risk is about 2% of a
  sleeve.
- Analytical risk-normalized view: scale trades down to a maximum 1% risk and
  apply execution-cost stress scenarios. Fractional lots below `0.01` may not
  be executable and are used only for candidate scoring.

Regime candidates must improve stress performance and stability. They must not
win merely by increasing position size or selecting rules around 2025 results.

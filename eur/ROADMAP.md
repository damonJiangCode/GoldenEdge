# EUR Strategy Optimization Roadmap

## 1. Goal and Principles

Primary goal:
Build a strategy that is stable across multiple years after realistic execution costs, not just high return in one year.

Core principles:

1. Validate the research process before tuning strategy details.
2. Build true edge first, then scale it.
3. Require out-of-sample and walk-forward confirmation before accepting conclusions.

## 2. Priority Order

### Priority 0: Research Infrastructure (must be first)

Scope:

1. Standardize metrics: `Net PnL`, `Max Drawdown`, `Profit Factor`, `Sharpe`, `Trade Count`, `OOS consistency`.
2. Standardize data split: `Train / Validation / Test` plus `Walk-Forward`.
3. Keep one consistent cost model: spread, slippage, commission.
4. Keep experiment traceability: parameters, outputs, and code version.

Why:
Without this layer, optimization is likely to overfit and will not be reproducible.

### Priority 1: Indicator Threshold Optimization

Scope:

1. ADX threshold range (for example `14-28`).
2. RSI threshold pairs (for example `68/32`, `70/30`, `72/28`, `75/25`).
3. Bollinger parameters (`period`, `std`).
4. Confirmation strength (reversion-depth logic).

Method:

1. Coarse grid search for rough regions.
2. Local refinement (Optuna or equivalent).
3. Select robust OOS candidates, not single-year winners.

Why:
This is the fastest low-complexity path for improving the current baseline.

### Priority 2: Exit Logic Optimization (TP/SL)

Scope:

1. Joint ATR multiplier search (`SL` and `TP` together).
2. Time-based stop (force exit after `N` bars).
3. Break-even and/or partial take-profit rules.
4. Validate Friday force-close impact on return and drawdown.

Method:

1. Multi-objective scoring (return, drawdown, stability).
2. Test on fixed signal sets first, then run joint optimization with Priority 1.

Why:
Exit logic often has major impact on drawdown profile and return distribution.

### Priority 3: Execution Logic Optimization

Scope:

1. Entry execution variants (`next open`, pullback/limit style, split entry).
2. Market micro-filters (high spread filter, low-liquidity session filter, news window filter).
3. Signal-structure filters (candle shape, volatility regime, cooldown).

Method:

1. Start with simple, interpretable rules.
2. Add ML gating only after rule-based baseline is well validated.

Why:
Execution changes can reduce false entries but add complexity and hidden failure modes.

### Priority 4: Position Sizing Optimization

Scope:

1. Fixed-risk sizing based on stop distance.
2. Volatility-target sizing.
3. Drawdown-based risk throttling.
4. Fractional Kelly with strict cap.

Method:

1. Apply only after signal edge is proven positive.
2. Use Monte Carlo trade-sequence stress tests for robustness.

Why:
Sizing scales edge; it does not create edge.

## 3. ML and Data Engineering Integration

### A. Data Layer

1. Convert raw CSV to `Parquet`, partitioned by year.
2. Build reusable feature/label datasets.
3. Use `Polars` / `DuckDB` / `Dask` for faster batch research.

Deliverable:
A unified research dataset under `eur/data/processed/`.

### B. Optimization Layer

1. Use constrained multi-objective search.
2. Include drawdown penalty and minimum trade count in objective.
3. Rank by OOS stability, not peak backtest return.

Deliverable:
Trial history plus shortlist of robust candidates.

### C. ML Signal-Quality Layer

1. Build a meta-label model: take or skip each candidate trade.
2. Inputs: ADX, RSI, BB, ATR, spread, session/time, short-horizon volatility.
3. Start with tree-based models and calibrated probabilities.
4. Gate entries by probability threshold.

Deliverable:
A direct comparison: rules-only vs rules-plus-ML-filter.

## 4. Execution Timeline

### Sprint 1

1. Finalize infrastructure and scoring.
2. Run Priority 1 (coarse + local refinement).
3. Keep top robust candidates.

### Sprint 2

1. Run Priority 2 on selected candidates.
2. Add time stop / break-even rules.
3. Keep one primary and one backup configuration.

### Sprint 3

1. Run Priority 3 execution experiments.
2. Add offline ML gating.
3. Run cross-year walk-forward and drawdown stress tests.

### Sprint 4

1. Run Priority 4 sizing optimization.
2. Run Monte Carlo robustness checks.
3. Finalize deployment limits and risk controls.

## 5. Immediate Next Step

Build and maintain one repeatable pipeline:
batch parameter backtest + OOS scoring + automatic ranking.

Once this is stable, all later optimization work becomes faster and comparable.

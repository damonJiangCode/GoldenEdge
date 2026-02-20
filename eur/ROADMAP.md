# EUR Strategy Optimization Roadmap

## 1) Goal and Principles

The goal is not "best return in one year," but "stable positive performance across multiple years after realistic costs."

Core principles:
1. Validate the research process first, then optimize strategy details.
2. Build true edge first, then scale that edge.
3. Every conclusion must pass out-of-sample and walk-forward validation.

---

## 2) Priority Order (and Why)

### Priority 0: Research Infrastructure (must come first)

Scope:
1. Fix evaluation metrics: `Net PnL`, `Max Drawdown`, `Profit Factor`, `Sharpe`, `Trade Count`, `OOS consistency`.
2. Fix data split: `Train / Validation / Test` + `Walk-Forward`.
3. Fix execution cost model: spread/slippage/commission applied consistently.
4. Fix experiment logging: parameters, results, and code version must be traceable.

Why:
Without this layer, parameter tuning and AI optimization will overfit and become non-reproducible.

### Priority 1: Optimize Indicator Thresholds (your direction 1)

Scope:
1. ADX threshold range, e.g. `14~28`.
2. RSI thresholds, e.g. `(68/32), (70/30), (72/28), (75/25)`.
3. Bollinger parameters: `period` and `std`.
4. Confirmation strength: parameterize the current "reversion depth" rule.

Method:
1. Coarse grid search to find useful regions.
2. Bayesian optimization (Optuna) for local refinement.
3. Pick robust out-of-sample sets, not single-year winners.

Why:
This is the most direct and lowest-cost source of improvement for the current strategy.

### Priority 2: Optimize TP/SL Logic (your direction 4)

Scope:
1. Joint search of ATR stop/target multipliers (e.g. `SL 0.8~1.5`, `TP 1.2~3.0`).
2. Time stop (force close after N bars).
3. Partial take profit or break-even trailing after 1R.
4. Keep Friday force-close and test its return/DD impact.

Method:
1. Multi-objective optimization: return, drawdown, and stability.
2. Test on fixed signal sets first, then run joint optimization with Priority 1.

Why:
Exit logic usually has a bigger effect on return distribution and drawdown shape.

### Priority 3: Optimize Order Execution Logic (your direction 2)

Scope:
1. Entry trigger variants: `next open`, pullback limit entry, split entry.
2. Micro filters: high-spread filter, low-liquidity session filter, news window filter.
3. Signal structure enhancements: confirmation candle shape, volatility filter, cooldown.

Method:
1. Start with rule-based, interpretable experiments.
2. Then add ML gating (see Section 4).

Why:
Execution logic can reduce false entries, but complexity is higher and can hide root causes if done too early.

### Priority 4: Optimize Position Sizing (your direction 3)

Scope:
1. Fixed-risk sizing (units based on stop distance).
2. Volatility-target sizing.
3. Drawdown protection (auto risk reduction beyond DD thresholds).
4. Fractional Kelly with hard cap.

Method:
1. Apply only after signal edge is proven positive.
2. Use Monte Carlo trade sequence reshuffling for robustness checks.

Why:
Sizing is a multiplier, not an edge generator. Scaling a negative edge only accelerates drawdown.

---

## 3) How to Integrate ML and "Big Data" Tools

### A. Data Layer (Big Data)

1. Convert historical CSV files to `Parquet`, partition by `year`.
2. Build reusable feature and label datasets.
3. Use `Polars/DuckDB` (or Dask) for fast batch backtests.

Deliverable:
A unified data asset in `eur/data/processed/` for all experiments.

### B. Optimization Layer (Auto Search)

1. Use Optuna for constrained multi-objective parameter search.
2. Objective should include drawdown penalty and minimum trade count.
3. Rank by out-of-sample stability, not single-run peak return.

Deliverable:
`eur/research/results/optuna_trials.csv` + top robust parameter sets.

### C. ML Enhancement Layer (Signal Quality Filter)

1. Build a binary meta-labeling model: "take this trade or skip".
2. Features: ADX/RSI/BB/ATR, spread, session/time features, short-horizon volatility features.
3. Start with XGBoost/LightGBM and output `p(win)`.
4. Allow entries only when `p(win)` is above threshold.

Deliverable:
Comparison of "rules-only" vs "rules + ML filter" strategies.

---

## 4) Recommended Execution Timeline

### Sprint 1 (first)

1. Build experiment framework: unified scoring, unified split, unified outputs.
2. Run Priority 1 search (coarse grid + Optuna).
3. Keep top 3 robust parameter candidates.

### Sprint 2

1. Run Priority 2 (TP/SL) on candidate parameter sets.
2. Add time stop and break-even trailing.
3. Keep 1 primary set and 1 backup set.

### Sprint 3

1. Run Priority 3 execution logic experiments.
2. Add ML gating (offline backtest first, not live).
3. Run cross-year walk-forward and drawdown stress tests.

### Sprint 4

1. Run Priority 4 position sizing optimization.
2. Perform Monte Carlo robustness validation.
3. Finalize deployable parameters and risk limits.

---

## 5) The First Next Step Right Now

Do one thing first:
Build a "batch parameter backtest + out-of-sample scoring + automatic ranking" pipeline.

Once this exists, all four optimization directions can move quickly with comparable, reproducible results.

# Out-of-Sample 001 — Framework 001 on 2026 Data

## 1. Research Question

Framework 001 is frozen and has completed historical validation. This report evaluates only 2026 data to test whether the framework behaves normally on previously unseen data.

No parameters, rules, filters, universe definitions, or sizing logic are changed.

## 2. Fixed Framework

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Signal: 126 trading-day cross-sectional momentum
- Selection: month-end ranking, next trading day execution, Top5 ETFs
- Weighting: inverse volatility using 126 trading-day daily return volatility
- Cost: 5 bps transaction cost applied to turnover
- Constraints: long only, no leverage, no shorting, no MA filter

## 3. Data And Initialization

- Evaluation window requested: `2026-01-01` to latest available 2026 trading date
- Latest available data date: `2026-06-23`
- OOS return measurement: `2026-01-01` through `2026-06-23`
- First active OOS trading date: `2026-01-02`
- First 2026 holding was initialized from the `2025-12-31` month-end signal, effective `2026-01-02`.
- Initial Framework 001 holdings: `SLV, GLD, IWM, QQQ, SPY`
- 2025 and earlier data are used only for momentum and volatility warm-up.
- No 2025 returns are included in OOS performance.

## 4. OOS Performance

| Strategy | Start Date | End Date | CAGR | Total Return | Sharpe | MaxDD | Volatility | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Framework 001 / IV Framework | 2026-01-02 | 2026-06-23 | 19.77% | 9.34% | 1.11 | -8.66% | 18.84% | 501.35% |
| Equal Weight Top5 Momentum | 2026-01-02 | 2026-06-23 | 19.25% | 9.38% | 0.84 | -13.78% | 27.35% | 371.86% |
| SPY Buy & Hold | 2026-01-02 | 2026-06-23 | 17.64% | 8.15% | 1.25 | -8.88% | 14.24% | 0.00% |
| Original 12 Equal Weight | 2026-01-02 | 2026-06-23 | 20.09% | 9.34% | 1.45 | -6.60% | 13.85% | 127.01% |

## 5. Relative Performance

Positive MaxDD Improvement means Framework 001 has a shallower drawdown.

| Comparison | CAGR Difference | Sharpe Difference | MaxDD Improvement | Total Return Difference |
| --- | --- | --- | --- | --- |
| Framework vs Equal Weight Top5 Momentum | 0.52% | 0.27 | 5.12% | -0.04% |
| Framework vs SPY Buy & Hold | 2.14% | -0.14 | 0.22% | 1.19% |
| Framework vs Original 12 Equal Weight | -0.32% | -0.34 | -2.06% | -0.00% |

## 6. Monthly Holdings

| Rebalance Date | Effective Date | ETF | Momentum Rank | Momentum Return | Volatility | Weight |
| --- | --- | --- | --- | --- | --- | --- |
| 2025-12-31 | 2026-01-02 | SLV | 1 | 93.80% | 2.36% | 9.22% |
| 2025-12-31 | 2026-01-02 | GLD | 2 | 28.15% | 1.25% | 17.43% |
| 2025-12-31 | 2026-01-02 | IWM | 3 | 12.06% | 1.20% | 18.18% |
| 2025-12-31 | 2026-01-02 | QQQ | 4 | 11.80% | 0.93% | 23.36% |
| 2025-12-31 | 2026-01-02 | SPY | 5 | 10.54% | 0.69% | 31.81% |
| 2026-01-30 | 2026-02-02 | SLV | 1 | 126.41% | 3.81% | 6.31% |
| 2026-01-30 | 2026-02-02 | GLD | 2 | 46.87% | 1.65% | 14.53% |
| 2026-01-30 | 2026-02-02 | IWM | 3 | 19.08% | 1.19% | 20.12% |
| 2026-01-30 | 2026-02-02 | EFA | 4 | 17.19% | 0.70% | 34.44% |
| 2026-01-30 | 2026-02-02 | QQQ | 5 | 10.33% | 0.98% | 24.60% |
| 2026-02-27 | 2026-03-02 | SLV | 1 | 142.90% | 4.50% | 6.20% |
| 2026-02-27 | 2026-03-02 | GLD | 2 | 54.70% | 1.91% | 14.61% |
| 2026-02-27 | 2026-03-02 | EFA | 3 | 17.03% | 0.71% | 39.37% |
| 2026-02-27 | 2026-03-02 | IWM | 4 | 11.48% | 1.16% | 24.04% |
| 2026-02-27 | 2026-03-02 | USO | 5 | 9.73% | 1.77% | 15.78% |
| 2026-03-31 | 2026-04-01 | USO | 1 | 70.60% | 2.68% | 9.88% |
| 2026-03-31 | 2026-04-01 | SLV | 2 | 60.33% | 4.81% | 5.51% |
| 2026-03-31 | 2026-04-01 | GLD | 3 | 22.08% | 2.14% | 12.38% |
| 2026-03-31 | 2026-04-01 | EFA | 4 | 6.34% | 0.99% | 26.77% |
| 2026-03-31 | 2026-04-01 | DBA | 5 | 5.18% | 0.58% | 45.47% |
| 2026-04-30 | 2026-05-01 | USO | 1 | 106.04% | 3.21% | 8.82% |
| 2026-04-30 | 2026-05-01 | SLV | 2 | 56.11% | 4.79% | 5.91% |
| 2026-04-30 | 2026-05-01 | GLD | 3 | 16.27% | 2.03% | 13.94% |
| 2026-04-30 | 2026-05-01 | IWM | 4 | 12.23% | 1.25% | 22.57% |
| 2026-04-30 | 2026-05-01 | DBA | 5 | 11.01% | 0.58% | 48.76% |
| 2026-05-29 | 2026-06-01 | USO | 1 | 86.41% | 3.40% | 9.34% |
| 2026-05-29 | 2026-06-01 | SLV | 2 | 46.41% | 4.94% | 6.44% |
| 2026-05-29 | 2026-06-01 | QQQ | 3 | 21.56% | 1.08% | 29.37% |
| 2026-05-29 | 2026-06-01 | IWM | 4 | 19.09% | 1.21% | 26.37% |
| 2026-05-29 | 2026-06-01 | EFA | 5 | 13.70% | 1.12% | 28.48% |

## 7. Monthly Portfolio Return

| Month | Framework Return | EW Top5 Return | SPY Return | Original 12 EW Return |
| --- | --- | --- | --- | --- |
| 2026-01 | 5.42% | 7.46% | 1.47% | 4.80% |
| 2026-02 | 3.17% | 4.84% | -0.86% | 3.07% |
| 2026-03 | 1.58% | 2.30% | -4.94% | -0.19% |
| 2026-04 | 3.79% | 3.93% | 10.51% | 4.79% |
| 2026-05 | -1.52% | -1.94% | 5.26% | 0.84% |
| 2026-06 | -3.18% | -6.89% | -2.78% | -4.04% |

## 8. Asset Class Exposure

Average daily held weights during 2026 OOS period.

| Strategy | Equity | Commodity | Bond |
| --- | --- | --- | --- |
| Framework 001 / IV Framework | 56.17% | 43.83% | 0.00% |
| Equal Weight Top5 Momentum | 41.65% | 58.35% | 0.00% |
| SPY Buy & Hold | 100.00% | 0.00% | 0.00% |
| Original 12 Equal Weight | 33.40% | 33.65% | 32.94% |

## 9. Turnover Detail

| Rebalance Date | Effective Date | Turnover | Estimated Cost |
| --- | --- | --- | --- |
| 2025-12-31 | 2026-01-02 | 100.00% | 0.05% |
| 2026-01-30 | 2026-02-02 | 77.12% | 0.04% |
| 2026-02-27 | 2026-03-02 | 49.31% | 0.02% |
| 2026-03-31 | 2026-04-01 | 92.16% | 0.05% |
| 2026-04-30 | 2026-05-01 | 58.67% | 0.03% |
| 2026-05-29 | 2026-06-01 | 124.10% | 0.06% |

## 10. Diagnostics

1. **Did Framework 001 produce positive OOS return in 2026?** Yes. Framework 001 total return is `9.34%` through `2026-06-23`.
2. **Did it outperform Equal Weight Top5 on Sharpe?** Yes. Framework Sharpe is `1.11` versus EW Top5 `0.84`.
3. **Did it reduce MaxDD versus Equal Weight Top5?** Yes. Framework MaxDD is `-8.66%` versus EW Top5 `-13.78%`.
4. **Did it outperform SPY on CAGR or mainly on risk?** Framework CAGR is `19.77%` versus SPY `17.64%`, and MaxDD is `-8.66%` versus SPY `-8.88%`. SPY has the higher Sharpe so far: `1.25` versus Framework `1.11`.
5. **Did the 2026 holdings behave consistently with the framework thesis?** Yes. The holdings rotated through the strongest cross-asset momentum names while inverse-vol sizing kept lower-volatility assets at larger weights and high-volatility assets smaller.
6. **Were any 2026 results abnormal relative to historical validation?** The OOS result is healthy versus the direct EW Top5 momentum benchmark, but not a clean sweep: Original 12 Equal Weight has higher Sharpe and shallower drawdown so far.
7. **Was the first 2026 holding initialized correctly using 2025 warm-up data?** Yes. The `2025-12-31` month-end signal established the first OOS position effective `2026-01-02`, matching live trading mechanics.
8. **Are there any missing data, stale price, or alignment warnings?** No. All 12 Original ETF files loaded successfully, and the common sample extends through `2026-06-23`.

## 11. Final Conclusion

Framework 001 behaves normally on 2026 out-of-sample data so far. The result is positive and risk control is clearly better than Equal Weight Top5 Momentum, but Framework 001 is not the strongest 2026 risk-adjusted portfolio among the reported benchmarks because Original 12 Equal Weight currently has higher Sharpe and shallower MaxDD.

The OOS period is still partial-year and should not be over-interpreted, but current evidence does not indicate a framework break.

The result is preserved without optimization, rule changes, universe changes, or new filters.

## 12. Output Files

- `metrics/oos_001_performance.csv`
- `metrics/oos_001_relative_performance.csv`
- `metrics/oos_001_monthly_holdings.csv`
- `metrics/oos_001_monthly_returns.csv`
- `metrics/oos_001_asset_class_exposure.csv`
- `metrics/oos_001_turnover_detail.csv`
- `outputs/oos_001_daily_details.csv`
- `outputs/oos_001_daily_weights.csv`

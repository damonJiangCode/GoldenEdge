# Research 002 — Absolute Momentum Integration in Framework 001

## 1. Research Question

Framework 001 uses the Original 12 ETF universe, 126-day cross-sectional momentum, monthly Top5 selection, and 126-day inverse-volatility weighting. This study tests whether adding a fixed absolute momentum filter improves the framework.

This is not parameter optimization. The absolute momentum rule is fixed at `126-day return > 0`.

## 2. Fixed Design

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Sample: `2008-02-01` to `2025-12-31`
- Cross-sectional momentum: 126 trading days
- Absolute momentum filter: 126-day return > 0
- Rebalance: monthly, month-end signal, next trading day execution
- Weighting: 126-day inverse volatility
- Transaction cost: 5 bps on turnover
- Constraints: long only, no leverage, no shorting, no MA filter

## 3. Strategies

- `Framework001`: baseline Top5 cross-sectional momentum with inverse volatility.
- `Filter Before Ranking (Reweight)`: remove non-positive momentum ETFs before ranking; reweight qualifying holdings to 100%.
- `Filter Before Ranking (Cash)`: remove non-positive momentum ETFs before ranking; if fewer than 5 qualify, hold proportional cash.
- `Filter After Ranking (Reweight)`: rank Top5 first, then remove non-positive Top5 members; reweight remaining holdings to 100%.
- `Filter After Ranking (Cash)`: rank Top5 first, then remove non-positive Top5 members; if fewer than 5 remain, hold proportional cash.

If no ETF passes the absolute momentum filter, the filtered portfolio is held in cash for that rebalance period.

## 4. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Framework001 | 10.32% | 0.97 | -17.22% | 10.75% | 59.92% | 476.93% | 13244.10% |
| Filter Before Ranking (Reweight) | 10.74% | 0.96 | -18.05% | 11.33% | 59.50% | 517.58% | 12882.50% |
| Filter Before Ranking (Cash) | 10.50% | 0.97 | -17.22% | 10.90% | 61.00% | 494.61% | 12458.69% |
| Filter After Ranking (Reweight) | 10.74% | 0.96 | -18.05% | 11.33% | 59.50% | 517.58% | 12882.50% |
| Filter After Ranking (Cash) | 10.50% | 0.97 | -17.22% | 10.90% | 61.00% | 494.61% | 12458.69% |

## 5. Relative Change vs Framework001

Positive MaxDD Change means shallower drawdown.

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Filter Before Ranking (Reweight) | 0.42% | -0.01 | -0.83% |
| Filter Before Ranking (Cash) | 0.19% | 0.00 | -0.00% |
| Filter After Ranking (Reweight) | 0.42% | -0.01 | -0.83% |
| Filter After Ranking (Cash) | 0.19% | 0.00 | -0.00% |

## 6. Absolute Momentum Diagnostics

| Strategy | Average ETFs with Positive Momentum | Average Holdings | Average Cash Weight | Maximum Cash Weight | Months with Cash | Months with Fewer than Five Holdings | Average Effective Positions | Average HHI | Average Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Framework001 | 7.73 | 5.00 | 0.00% | 0.00% | 0 | 0 | 3.93 | 0.29 | 61.60% |
| Filter Before Ranking (Reweight) | 7.73 | 4.74 | 1.40% | 100.00% | 3 | 27 | 3.94 | 0.29 | 60.48% |
| Filter Before Ranking (Cash) | 7.73 | 4.74 | 5.21% | 100.00% | 27 | 27 | 4.03 | 0.28 | 58.49% |
| Filter After Ranking (Reweight) | 7.73 | 4.74 | 1.40% | 100.00% | 3 | 27 | 3.94 | 0.29 | 60.48% |
| Filter After Ranking (Cash) | 7.73 | 4.74 | 5.21% | 100.00% | 27 | 27 | 4.03 | 0.28 | 58.49% |

## 7. Asset Class Exposure

Average daily weight.

| Strategy | Equity | Commodity | Bond | Cash |
| --- | --- | --- | --- | --- |
| Framework001 | 40.93% | 22.86% | 36.21% | 0.00% |
| Filter Before Ranking (Reweight) | 42.04% | 24.89% | 31.67% | 1.40% |
| Filter Before Ranking (Cash) | 41.47% | 23.56% | 29.76% | 5.21% |
| Filter After Ranking (Reweight) | 42.04% | 24.89% | 31.67% | 1.40% |
| Filter After Ranking (Cash) | 41.47% | 23.56% | 29.76% | 5.21% |

## 8. ETF Selection Frequency

| Strategy | ETF | Selection Count | Selection Percent |
| --- | --- | --- | --- |
| Framework001 | SPY | 134 | 62.33% |
| Framework001 | QQQ | 146 | 67.91% |
| Framework001 | IWM | 111 | 51.63% |
| Framework001 | EFA | 83 | 38.60% |
| Framework001 | GLD | 103 | 47.91% |
| Framework001 | SLV | 94 | 43.72% |
| Framework001 | USO | 81 | 37.67% |
| Framework001 | DBA | 66 | 30.70% |
| Framework001 | TLT | 83 | 38.60% |
| Framework001 | IEF | 71 | 33.02% |
| Framework001 | SHY | 42 | 19.53% |
| Framework001 | LQD | 61 | 28.37% |
| Filter Before Ranking (Reweight) | SPY | 132 | 61.40% |
| Filter Before Ranking (Reweight) | QQQ | 143 | 66.51% |
| Filter Before Ranking (Reweight) | IWM | 108 | 50.23% |
| Filter Before Ranking (Reweight) | EFA | 82 | 38.14% |
| Filter Before Ranking (Reweight) | GLD | 97 | 45.12% |
| Filter Before Ranking (Reweight) | SLV | 91 | 42.33% |
| Filter Before Ranking (Reweight) | USO | 76 | 35.35% |
| Filter Before Ranking (Reweight) | DBA | 64 | 29.77% |
| Filter Before Ranking (Reweight) | TLT | 80 | 37.21% |
| Filter Before Ranking (Reweight) | IEF | 66 | 30.70% |
| Filter Before Ranking (Reweight) | SHY | 27 | 12.56% |
| Filter Before Ranking (Reweight) | LQD | 53 | 24.65% |
| Filter Before Ranking (Cash) | SPY | 132 | 61.40% |
| Filter Before Ranking (Cash) | QQQ | 143 | 66.51% |
| Filter Before Ranking (Cash) | IWM | 108 | 50.23% |
| Filter Before Ranking (Cash) | EFA | 82 | 38.14% |
| Filter Before Ranking (Cash) | GLD | 97 | 45.12% |
| Filter Before Ranking (Cash) | SLV | 91 | 42.33% |
| Filter Before Ranking (Cash) | USO | 76 | 35.35% |
| Filter Before Ranking (Cash) | DBA | 64 | 29.77% |
| Filter Before Ranking (Cash) | TLT | 80 | 37.21% |
| Filter Before Ranking (Cash) | IEF | 66 | 30.70% |
| Filter Before Ranking (Cash) | SHY | 27 | 12.56% |
| Filter Before Ranking (Cash) | LQD | 53 | 24.65% |
| Filter After Ranking (Reweight) | SPY | 132 | 61.40% |
| Filter After Ranking (Reweight) | QQQ | 143 | 66.51% |
| Filter After Ranking (Reweight) | IWM | 108 | 50.23% |
| Filter After Ranking (Reweight) | EFA | 82 | 38.14% |
| Filter After Ranking (Reweight) | GLD | 97 | 45.12% |
| Filter After Ranking (Reweight) | SLV | 91 | 42.33% |
| Filter After Ranking (Reweight) | USO | 76 | 35.35% |
| Filter After Ranking (Reweight) | DBA | 64 | 29.77% |
| Filter After Ranking (Reweight) | TLT | 80 | 37.21% |
| Filter After Ranking (Reweight) | IEF | 66 | 30.70% |
| Filter After Ranking (Reweight) | SHY | 27 | 12.56% |
| Filter After Ranking (Reweight) | LQD | 53 | 24.65% |
| Filter After Ranking (Cash) | SPY | 132 | 61.40% |
| Filter After Ranking (Cash) | QQQ | 143 | 66.51% |
| Filter After Ranking (Cash) | IWM | 108 | 50.23% |
| Filter After Ranking (Cash) | EFA | 82 | 38.14% |
| Filter After Ranking (Cash) | GLD | 97 | 45.12% |
| Filter After Ranking (Cash) | SLV | 91 | 42.33% |
| Filter After Ranking (Cash) | USO | 76 | 35.35% |
| Filter After Ranking (Cash) | DBA | 64 | 29.77% |
| Filter After Ranking (Cash) | TLT | 80 | 37.21% |
| Filter After Ranking (Cash) | IEF | 66 | 30.70% |
| Filter After Ranking (Cash) | SHY | 27 | 12.56% |
| Filter After Ranking (Cash) | LQD | 53 | 24.65% |

## 9. Interpretation

1. **Does Absolute Momentum improve CAGR?** 4/4 filtered variants improved CAGR versus Framework001. The highest filtered CAGR is `10.74%` from `Filter Before Ranking (Reweight)`, versus baseline `10.32%`. The improvement is real but modest.
2. **Does Absolute Momentum improve Sharpe?** 2/4 filtered variants improved Sharpe. The best filtered Sharpe is `0.97` from `Filter Before Ranking (Cash)`, versus baseline `0.97`. The Sharpe gain is marginal.
3. **Does Absolute Momentum reduce MaxDD?** 0/4 filtered variants improved MaxDD. The shallowest filtered MaxDD is `-17.22%` from `Filter Before Ranking (Cash)`, versus baseline `-17.22%`. Absolute Momentum does not materially improve drawdown in this test.
4. **Is filtering before ranking better than filtering after ranking?** No. Before-ranking and after-ranking are mathematically equivalent here because both use the same 126-day return signal; before-ranking average Sharpe is `0.96` and after-ranking average Sharpe is `0.96`.
5. **Is Cash better than Reweight when fewer than five ETFs qualify?** Yes on risk-adjusted behavior. Cash variants average Sharpe `0.97` versus reweight variants `0.96`. Reweight variants have higher CAGR but worse Sharpe and deeper MaxDD.
6. **Which strategy provides the best overall risk-adjusted performance?** `Filter Before Ranking (Cash)` has the highest filtered Sharpe. Its most frequent ETFs are: QQQ, SPY, IWM, GLD, SLV.
7. **Does Absolute Momentum mainly improve downside protection or return generation?** It does not clearly improve downside protection. Reweight mainly raises CAGR by concentrating into fewer positive-momentum assets, while Cash slightly improves Sharpe by reducing exposure when breadth is weak.
8. **Does Absolute Momentum materially reduce diversification?** Moderately. Filtered variants average `4.74` holdings versus 5.00 for baseline, with 27 months below five holdings.
9. **Should Absolute Momentum become part of the next framework version?** Not yet as a fully justified Framework002 component. The Cash implementation is a candidate for further validation, but the improvement over Framework001 is too small and does not reduce MaxDD.

## 10. Final Conclusion

Absolute Momentum is evaluated as a fixed integration layer, not optimized. In this test, it does not provide enough improvement to justify changing Framework001.

The Cash implementation is superior to Reweight on risk-adjusted behavior, but its advantage over baseline is tiny: it slightly improves CAGR and Sharpe while leaving MaxDD essentially unchanged. Reweight produces higher CAGR but worsens Sharpe and MaxDD, which is not an attractive framework evolution.

Filtering before ranking and filtering after ranking are equivalent under this design because both the cross-sectional ranking and absolute filter use the same 126-day return signal. The real implementation choice is therefore Cash versus Reweight, and Cash is the cleaner version.

Final classification: Absolute Momentum Cash is a weak candidate for further validation, not a confirmed Framework002 upgrade. Framework001 remains unchanged.

## 11. Output Files

- `metrics/performance.csv`
- `metrics/relative_change.csv`
- `metrics/absolute_momentum_diagnostics.csv`
- `metrics/asset_class_exposure.csv`
- `metrics/selection_frequency.csv`
- `outputs/monthly_holding_diagnostics.csv`
- `outputs/target_weights_by_rebalance.csv`
- `outputs/daily_details.csv`
- `outputs/daily_weights.csv`

# Research 004 — Momentum Ensemble in Framework001

## 1. Research Question

Framework001 currently uses a single 126-day cross-sectional momentum signal. This study tests one predefined ensemble signal based on average rank across 63-day, 126-day, and 252-day momentum.

No horizon optimization is performed. The inverse-volatility sizing rule is unchanged.

## 2. Fixed Design

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Sample: `2008-02-01` to `2025-12-31`
- Rebalance: monthly
- Signal date: month-end
- Execution: next trading day
- Transaction cost: 5 bps
- Constraints: long only, no leverage, no shorting, no MA filter
- Weighting: 126-day inverse volatility

## 3. Strategies

- `Framework001 Baseline`: Top5 by 126-day momentum rank, then 126-day inverse-volatility weighting.
- `Momentum Ensemble`: Top5 by lowest average rank across 63-day, 126-day, and 252-day momentum ranks, then 126-day inverse-volatility weighting.

## 4. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Framework001 Baseline | 10.32% | 0.97 | -17.22% | 10.75% | 59.92% | 476.93% | 13244.10% |
| Momentum Ensemble | 10.21% | 0.96 | -14.06% | 10.75% | 72.62% | 467.24% | 13385.44% |

## 5. Relative Change vs Framework001

Positive MaxDD Change means shallower drawdown.

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Momentum Ensemble | -0.10% | -0.01 | 3.16% |

## 6. Ensemble Diagnostics

| Metric | Display Value |
| --- | --- |
| Average Rank63 of selected ETFs | 3.89 |
| Average Rank126 of selected ETFs | 3.34 |
| Average Rank252 of selected ETFs | 3.73 |
| Average Ensemble Rank | 3.65 |
| Average Turnover | 62.26% |
| Average Effective Positions | 3.90 |
| Average HHI | 0.29 |

## 7. Selection Overlap

| Metric | Display Value |
| --- | --- |
| Average Overlap Count | 4.35 |
| Average Overlap Percent | 87.07% |
| Months with Same Top5 | 94 |
| Months with 4/5 Overlap | 104 |
| Months with 3/5 or Less Overlap | 17 |

## 8. Asset Class Exposure

Average daily portfolio weight.

| Strategy | Equity | Commodity | Bond |
| --- | --- | --- | --- |
| Framework001 Baseline | 40.93% | 22.86% | 36.21% |
| Momentum Ensemble | 40.21% | 23.35% | 36.44% |

## 9. ETF Selection Frequency

| ETF | Framework001 Baseline Selection Percent | Momentum Ensemble Selection Percent |
| --- | --- | --- |
| SPY | 62.33% | 67.44% |
| QQQ | 67.91% | 72.09% |
| IWM | 51.63% | 51.16% |
| EFA | 38.60% | 37.21% |
| GLD | 47.91% | 52.09% |
| SLV | 43.72% | 43.26% |
| USO | 37.67% | 33.95% |
| DBA | 30.70% | 30.23% |
| TLT | 38.60% | 33.49% |
| IEF | 33.02% | 29.77% |
| SHY | 19.53% | 17.67% |
| LQD | 28.37% | 31.63% |

## 10. Interpretation

1. **Does Momentum Ensemble improve CAGR?** No. Ensemble CAGR is `10.21%` versus baseline `10.32%`.
2. **Does Momentum Ensemble improve Sharpe?** No. Ensemble Sharpe is `0.96` versus baseline `0.97`.
3. **Does Momentum Ensemble reduce MaxDD?** Yes. Ensemble MaxDD is `-14.06%` versus baseline `-17.22%`.
4. **Does Ensemble reduce turnover?** No. Ensemble turnover is `13385.44%` versus baseline `13244.10%`.
5. **Does Ensemble materially change holdings versus 126-day momentum?** Average overlap is `4.35/5`, or `87.07%`. Same Top5 occurred in `94` months; 3/5 or less overlap occurred in `17` months.
6. **Does Ensemble create more stable selections or just dilute the 126-day signal?** The answer depends on whether lower turnover comes with better Sharpe and MaxDD. Here, the relative table is the decisive evidence.
7. **Which assets benefit most from Ensemble selection?** Largest selection-frequency increases are: SPY, QQQ, GLD.
8. **Should Ensemble replace 126-day momentum in Framework001?** The ensemble improves one risk metric but not enough dimensions to replace the simpler 126-day signal.

## 11. Final Conclusion

The ensemble improves one risk metric but not enough dimensions to replace the simpler 126-day signal.

This study only tests the predefined 63/126/252 average-rank ensemble. It does not search other horizon combinations, does not change inverse-volatility sizing, and does not introduce filters.

Framework001 should only be updated if the ensemble delivers a meaningful improvement across CAGR, Sharpe, MaxDD, and turnover. Otherwise, the single 126-day signal remains the cleaner framework component.

## 12. Output Files

- `metrics/performance.csv`
- `metrics/relative_change.csv`
- `metrics/ensemble_diagnostics.csv`
- `metrics/selection_overlap.csv`
- `metrics/asset_class_exposure.csv`
- `metrics/selection_frequency.csv`
- `outputs/monthly_holding_diagnostics.csv`
- `outputs/selection_overlap_by_rebalance.csv`
- `outputs/daily_weights.csv`
- `outputs/daily_details.csv`

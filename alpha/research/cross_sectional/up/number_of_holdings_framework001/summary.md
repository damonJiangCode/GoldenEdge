# Research 003 — Number of Holdings in Framework001

## 1. Research Question

Framework001 currently uses monthly Top5 cross-sectional momentum selection with 126-day inverse-volatility weighting. This study tests whether changing the selected ETF count to Top3 or Top7 improves the framework.

Only the number of holdings changes. Universe, signal window, rebalance schedule, inverse-volatility window, costs, and constraints remain fixed.

## 2. Fixed Design

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Sample: `2008-02-01` to `2025-12-31`
- Cross-sectional momentum: 126 trading days
- Rebalance: monthly, month-end signal, next trading day execution
- Weighting: 126-day inverse volatility
- Transaction cost: 5 bps
- Constraints: long only, no leverage, no shorting, no MA filter

## 3. Strategies

- `Top3`: Top3 cross-sectional momentum with inverse-volatility weighting.
- `Framework001 (Top5)`: current baseline.
- `Top7`: Top7 cross-sectional momentum with inverse-volatility weighting.

## 4. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Top3 | 10.02% | 0.70 | -30.15% | 15.27% | 33.22% | 447.51% | 14617.81% |
| Framework001 (Top5) | 10.32% | 0.97 | -17.22% | 10.75% | 59.92% | 476.93% | 13244.10% |
| Top7 | 6.73% | 0.87 | -15.24% | 7.85% | 44.15% | 220.59% | 11968.36% |

## 5. Relative Change vs Framework001

Positive MaxDD Change means shallower drawdown.

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Top3 | -0.30% | -0.27 | -12.93% |
| Top7 | -3.59% | -0.10 | 1.97% |

## 6. Portfolio Diagnostics

| Strategy | Average Holdings | Average Effective Positions | Average HHI | Average Turnover |
| --- | --- | --- | --- | --- |
| Top3 | 3.00 | 2.72 | 0.38 | 67.99% |
| Framework001 (Top5) | 5.00 | 3.93 | 0.29 | 61.60% |
| Top7 | 7.00 | 4.23 | 0.30 | 55.67% |

## 7. Position Weight Diagnostics

Average weight by momentum rank.

| Strategy | Rank1 | Rank2 | Rank3 | Rank4 | Rank5 | Rank6 | Rank7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Top3 | 28.01% | 34.54% | 37.45% | NA | NA | NA | NA |
| Framework001 (Top5) | 14.17% | 17.36% | 18.88% | 22.75% | 26.83% | NA | NA |
| Top7 | 8.10% | 10.00% | 10.98% | 13.70% | 16.73% | 21.49% | 19.00% |

## 8. Asset Class Exposure

Average daily portfolio weight.

| Strategy | Equity | Commodity | Bond |
| --- | --- | --- | --- |
| Top3 | 47.19% | 32.30% | 20.51% |
| Framework001 (Top5) | 40.93% | 22.86% | 36.21% |
| Top7 | 27.76% | 17.48% | 54.76% |

## 9. ETF Selection Frequency

Selection Percent = selected rebalances / total rebalances.

| ETF | Top3 | Framework001 (Top5) | Top7 |
| --- | --- | --- | --- |
| SPY | 33.95% | 62.33% | 80.93% |
| QQQ | 54.42% | 67.91% | 80.93% |
| IWM | 33.49% | 51.63% | 64.19% |
| EFA | 15.81% | 38.60% | 58.14% |
| GLD | 30.70% | 47.91% | 61.40% |
| SLV | 34.88% | 43.72% | 52.56% |
| USO | 26.51% | 37.67% | 46.05% |
| DBA | 18.60% | 30.70% | 47.44% |
| TLT | 27.44% | 38.60% | 51.16% |
| IEF | 13.95% | 33.02% | 46.51% |
| SHY | 5.58% | 19.53% | 45.12% |
| LQD | 4.65% | 28.37% | 65.58% |

## 10. Interpretation

1. **Does reducing holdings to Top3 improve CAGR?** No. Top3 CAGR is `10.02%` versus Top5 `10.32%`.
2. **Does Top3 sacrifice diversification for concentration?** Yes. Top3 effective positions average `2.72` versus Top5 `3.93`.
3. **Does increasing holdings to Top7 reduce volatility?** Yes. Top7 volatility is `7.85%` versus Top5 `10.75%`.
4. **Does Top7 dilute momentum enough to reduce returns?** Yes. Top7 CAGR is `6.73%` versus Top5 `10.32%`.
5. **Which holding count produces the highest Sharpe?** `Framework001 (Top5)` with Sharpe `0.97`.
6. **Which holding count produces the shallowest MaxDD?** `Top7` with MaxDD `-15.24%`.
7. **Which holding count provides the best overall balance between CAGR, Sharpe, and MaxDD?** Top5 remains the strongest overall choice.
8. **Should Framework001 migrate to Top3 or Top7?** A migration is justified only if the improvement is meaningful across risk-adjusted return and drawdown. Marginal or one-dimensional improvement is not enough to change the frozen framework.

## 11. Final Conclusion

This study compares only Top3, Top5, and Top7. It does not search other holding counts.

Top5 remains the strongest overall choice. Framework001 should remain unchanged unless Top3 or Top7 shows a materially better and more balanced profile across CAGR, Sharpe, and MaxDD.

## 12. Output Files

- `metrics/performance.csv`
- `metrics/relative_change.csv`
- `metrics/portfolio_diagnostics.csv`
- `metrics/position_weight_diagnostics.csv`
- `metrics/asset_class_exposure.csv`
- `metrics/selection_frequency.csv`
- `outputs/monthly_holdings.csv`
- `outputs/daily_weights.csv`
- `outputs/daily_details.csv`

# Walk Forward Validation 001 — Cross-Asset Momentum Framework V1

## 1. Research Question

Framework 001 has been frozen as Original 12 ETF, 126-day cross-sectional momentum, monthly Top5 selection, and 126-day inverse-volatility weighting. This validation asks whether the frozen framework remains effective across separate historical periods, rather than depending only on full-sample performance.

No parameter is optimized in this report. The same rules are applied in every segment.

## 2. Fixed Framework

| Component | Definition |
| --- | --- |
| Universe | Original 12 ETF |
| Equity | SPY, QQQ, IWM, EFA |
| Commodity | GLD, SLV, USO, DBA |
| Bond | TLT, IEF, SHY, LQD |
| Signal | 126 trading-day momentum |
| Selection | Monthly rebalance; month-end signal; next trading day execution; Top5 momentum ETFs |
| Weighting | Inverse Volatility; 126 trading-day daily-return volatility; normalized to 100% |
| Cost | 5 bps transaction cost applied to turnover |
| Constraints | Long only; no leverage; no shorting; no MA filter |

Momentum and volatility are calculated using data available through the signal date. Segment evaluation uses one continuous simulation and then slices calendar periods, so later segments inherit live portfolio weights from earlier dates rather than forcing artificial re-entry trades at each segment start. Warm-up uses prior available history; if prior data is insufficient, trading begins only after both momentum and volatility are valid.

## 3. Walk Forward Windows

| Segment | Start | End |
| --- | --- | --- |
| WF1 | 2008-02-01 | 2012-12-31 |
| WF2 | 2013-01-01 | 2016-12-31 |
| WF3 | 2017-01-01 | 2020-12-31 |
| WF4 | 2021-01-01 | 2025-12-31 |
| Full | 2008-02-01 | 2025-12-31 |

## 4. Segment Performance

| Segment | Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WF1 | Inverse Vol Framework | 10.35% | 0.83 | -13.13% | 12.72% | 0.79 | 61.22% | 3415.25% |
| WF1 | Equal Weight Top5 Momentum | 8.33% | 0.57 | -29.06% | 15.79% | 0.29 | 46.62% | 2594.59% |
| WF1 | SPY Buy & Hold | 2.66% | 0.24 | -51.48% | 26.27% | 0.05 | 15.59% | 0.00% |
| WF1 | Original 12 Equal Weight | 5.33% | 0.45 | -31.37% | 13.72% | 0.17 | 29.33% | 336.27% |
| WF2 | Inverse Vol Framework | 9.02% | 1.20 | -5.83% | 7.89% | 1.55 | 44.16% | 2562.12% |
| WF2 | Equal Weight Top5 Momentum | 9.31% | 1.04 | -11.01% | 9.46% | 0.85 | 45.54% | 1756.60% |
| WF2 | SPY Buy & Hold | 13.53% | 1.10 | -13.02% | 12.82% | 1.04 | 70.21% | 0.00% |
| WF2 | Original 12 Equal Weight | 0.07% | 0.08 | -17.42% | 7.52% | 0.00 | 1.32% | 144.08% |
| WF3 | Inverse Vol Framework | 8.22% | 0.79 | -17.22% | 10.90% | 0.48 | 37.63% | 3573.56% |
| WF3 | Equal Weight Top5 Momentum | 9.64% | 0.80 | -23.09% | 12.57% | 0.42 | 44.47% | 2264.99% |
| WF3 | SPY Buy & Hold | 15.70% | 0.84 | -33.72% | 20.06% | 0.47 | 80.35% | 0.00% |
| WF3 | Original 12 Equal Weight | 8.51% | 0.88 | -22.09% | 9.96% | 0.39 | 38.95% | 151.78% |
| WF4 | Inverse Vol Framework | 12.66% | 1.18 | -11.39% | 10.50% | 1.11 | 80.37% | 3693.20% |
| WF4 | Equal Weight Top5 Momentum | 13.47% | 1.01 | -19.90% | 13.33% | 0.68 | 87.65% | 2757.73% |
| WF4 | SPY Buy & Hold | 14.69% | 0.87 | -24.50% | 17.12% | 0.60 | 95.39% | 0.00% |
| WF4 | Original 12 Equal Weight | 9.18% | 0.92 | -17.78% | 10.09% | 0.52 | 54.88% | 176.52% |
| Full | Inverse Vol Framework | 10.32% | 0.97 | -17.22% | 10.75% | 0.60 | 476.94% | 13244.12% |
| Full | Equal Weight Top5 Momentum | 10.36% | 0.81 | -29.06% | 13.16% | 0.36 | 478.53% | 9373.90% |
| Full | SPY Buy & Hold | 11.32% | 0.64 | -51.48% | 19.94% | 0.22 | 593.26% | 0.00% |
| Full | Original 12 Equal Weight | 5.95% | 0.59 | -31.37% | 10.72% | 0.19 | 182.02% | 808.66% |

## 5. Relative Performance vs Equal Weight Top5

Positive MaxDD Improvement means the IV Framework has a shallower drawdown than Equal Weight Top5 in that segment.

| Segment | IV Framework Sharpe - EW Top5 Sharpe | IV Framework MaxDD Improvement vs EW Top5 | IV Framework CAGR - EW Top5 CAGR |
| --- | --- | --- | --- |
| WF1 | 0.26 | 15.92% | 2.02% |
| WF2 | 0.16 | 5.18% | -0.29% |
| WF3 | -0.01 | 5.87% | -1.42% |
| WF4 | 0.17 | 8.52% | -0.81% |
| Full | 0.15 | 11.84% | -0.04% |

## 6. Consistency Summary

| Metric | Value |
| --- | --- |
| Number of segments | 4 |
| Segments with positive CAGR | 4 |
| Segments with Sharpe > 0 | 4 |
| Segments where IV Sharpe > EW Top5 Sharpe | 3 |
| Segments where IV MaxDD is shallower than EW Top5 MaxDD | 4 |
| Worst segment CAGR | 8.22% |
| Worst segment Sharpe | 0.79 |
| Worst segment MaxDD | -17.22% |

## 7. Rank and Weight Diagnostics

| Segment | Avg Rank1 Weight | Avg Rank5 Weight | Avg Effective Positions | Avg HHI |
| --- | --- | --- | --- | --- |
| WF1 | 13.72% | 27.19% | 3.83 | 0.29 |
| WF2 | 15.79% | 27.31% | 3.95 | 0.29 |
| WF3 | 12.38% | 27.98% | 3.88 | 0.29 |
| WF4 | 14.74% | 25.19% | 4.05 | 0.28 |
| Full | 14.17% | 26.83% | 3.93 | 0.29 |

## 8. Asset Class Exposure

Average daily held weights for the IV Framework within each segment.

| Segment | Equity | Commodity | Bond |
| --- | --- | --- | --- |
| WF1 | 29.94% | 26.39% | 43.67% |
| WF2 | 44.06% | 12.78% | 43.16% |
| WF3 | 46.16% | 14.40% | 39.44% |
| WF4 | 45.08% | 34.25% | 20.67% |
| Full | 40.93% | 22.86% | 36.21% |

## 9. Key Segment Read

- **WF1 2008-2012:** IV Framework CAGR 10.35%, Sharpe 0.83, MaxDD -13.13%. This segment includes the financial crisis and early recovery; inverse-vol sizing materially improved drawdown versus Equal Weight Top5 by 15.92%.
- **WF2 2013-2016:** IV Framework CAGR 9.02%, Sharpe 1.20. SPY delivered stronger CAGR in this steady equity bull period, but the framework still produced strong risk-adjusted results with shallow drawdown.
- **WF3 2017-2020:** IV Framework CAGR 8.22%, Sharpe 0.79. Performance remained positive through the Covid crash window, with MaxDD -17.22%.
- **WF4 2021-2025:** IV Framework CAGR 12.66%, Sharpe 1.18. This period includes the 2022 stock-bond bear market followed by 2023-2025 recovery; the framework's commodity and bond rotation helped keep realized drawdown controlled.

## 10. Interpretation Questions

1. **Does the frozen framework work across all walk-forward segments?** Yes. The IV Framework has positive CAGR and positive Sharpe in all four walk-forward segments.
2. **Does Inverse Vol improve Sharpe consistently versus Equal Weight Top5?** Mostly, but not perfectly. IV Sharpe is higher than Equal Weight Top5 in 3/4 segments; WF3 is essentially flat but slightly lower.
3. **Does Inverse Vol reduce MaxDD consistently versus Equal Weight Top5?** Yes. IV MaxDD is shallower in 4/4 segments.
4. **Which period is the weakest?** `WF3` with CAGR 8.22%, Sharpe 0.79, and MaxDD -17.22%.
5. **Which period is the strongest?** `WF2` with CAGR 9.02%, Sharpe 1.20, and MaxDD -5.83%.
6. **Is performance mainly from one historical segment, or distributed across time?** It is distributed across all four segments: every walk-forward segment is profitable. WF4 has the highest CAGR, WF2 has the highest Sharpe, and WF3 is the weakest segment.
7. **Does the framework remain superior to SPY on risk-adjusted metrics?** Mixed but favorable. IV Sharpe beats SPY in 3/4 walk-forward segments and in the full sample (0.97 vs 0.64).
8. **Does the framework beat SPY in CAGR, or mainly in Sharpe and MaxDD?** Mainly Sharpe and MaxDD. IV beats SPY CAGR in 1/4 walk-forward segments; full-sample CAGR is 10.32% vs SPY 11.32%.
9. **Does asset class exposure change meaningfully across segments?** Yes. Across WF segments, Equity exposure range is 16.22%, Commodity range is 21.47%, and Bond range is 23.00%. The framework is not a static allocation; it rotates materially across asset classes.
10. **Is the framework ready for the next validation step?** Yes. Walk-forward evidence is strong enough to proceed, but not sufficient for live deployment. The next stage should test regimes, path dependence, and sampling uncertainty.

## 11. Final Conclusion

Framework 001 shows enough time-segment robustness to proceed to further validation. The key evidence is not that it maximizes CAGR in every period; it does not. The stronger evidence is that the frozen framework produces positive CAGR in every walk-forward segment, improves MaxDD versus Equal Weight Top5 in all four segments, improves Sharpe in three of four segments, and keeps full-sample risk-adjusted performance above SPY while using the same unchanged rules.

The weakest evidence is benchmark-relative return during the 2013-2016 equity bull market, where SPY's CAGR is difficult to beat with a diversified cross-asset allocation. That does not break the framework thesis, but it clarifies the thesis: Framework 001 is primarily a risk-adjusted cross-asset momentum framework, not a pure SPY-CAGR maximizer.

Proceed to the next validation stage:

- Regime Analysis
- Bootstrap
- Monte Carlo
- Paper Trading Simulation

## 12. Output Files

- Metrics: `alpha/validation/metrics/walk_forward_001_segment_performance.csv`
- Relative performance: `alpha/validation/metrics/walk_forward_001_relative_performance.csv`
- Consistency: `alpha/validation/metrics/walk_forward_001_consistency_summary.csv`
- Rank/weight diagnostics: `alpha/validation/metrics/walk_forward_001_rank_weight_diagnostics.csv`
- Asset-class exposure: `alpha/validation/metrics/walk_forward_001_asset_class_exposure.csv`
- Daily details: `alpha/validation/outputs/walk_forward_001_daily_details.csv`
- Daily weights: `alpha/validation/outputs/walk_forward_001_daily_weights.csv`

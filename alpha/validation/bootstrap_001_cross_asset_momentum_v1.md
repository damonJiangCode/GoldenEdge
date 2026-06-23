# Bootstrap Validation 001 — Cross-Asset Momentum Framework V1

## 1. Research Question

Framework 001 has completed Walk Forward Validation and Regime Analysis. This validation asks whether the frozen framework's historical performance is statistically stable under bootstrap uncertainty, rather than being created by a few special months or one lucky historical path.

No parameter is optimized. No strategy rule is changed.

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

## 3. Bootstrap Design

- Source returns: Framework 001 daily net returns from `walk_forward_001_daily_details.csv`
- Sample length: 4508 trading days
- Calendar month blocks available: 215
- Simulations: 10,000 per method
- Random seed: `20260623`
- Daily Bootstrap: resample daily returns with replacement.
- Monthly-Block Bootstrap: resample calendar months with replacement, preserving within-month daily return order, then truncate to the full sample length.
- Paired comparisons: each simulation uses the same sampled days or months for all strategies, preserving cross-strategy comparison fairness.

Daily bootstrap tests return distribution stability. Monthly-block bootstrap partially preserves short-term autocorrelation and clustered volatility. CAGR values in this report use 252-trading-day annualization for both historical and simulated paths, so they can differ slightly from prior calendar-year CAGR tables.

## 4. Historical Reference

| Strategy | Historical CAGR | Historical Sharpe | Historical MaxDD | Historical Volatility |
| --- | --- | --- | --- | --- |
| Inverse Vol Framework | 10.29% | 0.97 | -17.22% | 10.75% |
| Equal Weight Top5 Momentum | 10.31% | 0.81 | -29.06% | 13.16% |
| SPY Buy & Hold | 11.43% | 0.64 | -51.48% | 19.94% |
| Original 12 Equal Weight | 5.97% | 0.59 | -31.37% | 10.72% |

## 5. Daily Bootstrap Summary

For MaxDD, the 5th percentile is the worse drawdown tail.

| Strategy | CAGR Median | CAGR 5th Percentile | CAGR 95th Percentile | Sharpe Median | Sharpe 5th Percentile | Sharpe 95th Percentile | MaxDD Median | MaxDD 5th Percentile | MaxDD 95th Percentile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Inverse Vol Framework | 10.28% | 5.73% | 15.01% | 0.96 | 0.57 | 1.37 | -20.09% | -30.83% | -13.89% |
| Equal Weight Top5 Momentum | 10.28% | 4.78% | 16.12% | 0.81 | 0.42 | 1.21 | -26.17% | -40.10% | -17.91% |
| SPY Buy & Hold | 11.45% | 3.12% | 20.54% | 0.64 | 0.25 | 1.04 | -40.39% | -60.42% | -27.92% |
| Original 12 Equal Weight | 5.95% | 1.60% | 10.53% | 0.59 | 0.20 | 1.00 | -24.71% | -39.68% | -16.30% |

## 6. Monthly-Block Bootstrap Summary

| Strategy | CAGR Median | CAGR 5th Percentile | CAGR 95th Percentile | Sharpe Median | Sharpe 5th Percentile | Sharpe 95th Percentile | MaxDD Median | MaxDD 5th Percentile | MaxDD 95th Percentile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Inverse Vol Framework | 10.31% | 6.29% | 14.55% | 0.97 | 0.62 | 1.34 | -18.47% | -27.40% | -13.77% |
| Equal Weight Top5 Momentum | 10.30% | 5.32% | 15.65% | 0.81 | 0.46 | 1.19 | -24.59% | -37.33% | -17.30% |
| SPY Buy & Hold | 11.46% | 4.82% | 18.48% | 0.65 | 0.33 | 1.01 | -36.66% | -52.86% | -27.72% |
| Original 12 Equal Weight | 6.01% | 1.78% | 10.33% | 0.60 | 0.21 | 1.00 | -25.74% | -40.96% | -17.71% |

## 7. Probability Diagnostics

| Method | Strategy | P(CAGR > 0) | P(Sharpe > 0) | P(MaxDD worse than -20%) | P(MaxDD worse than -30%) | P(MaxDD worse than -40%) |
| --- | --- | --- | --- | --- | --- | --- |
| Daily Bootstrap | Inverse Vol Framework | 100.00% | 100.00% | 50.68% | 6.16% | 0.42% |
| Daily Bootstrap | Equal Weight Top5 Momentum | 99.95% | 99.98% | 87.02% | 29.89% | 5.10% |
| Daily Bootstrap | SPY Buy & Hold | 99.03% | 99.72% | 99.98% | 90.71% | 51.52% |
| Daily Bootstrap | Original 12 Equal Weight | 98.91% | 99.41% | 79.00% | 24.31% | 4.73% |
| Monthly-Block Bootstrap | Inverse Vol Framework | 100.00% | 100.00% | 36.13% | 2.27% | 0.11% |
| Monthly-Block Bootstrap | Equal Weight Top5 Momentum | 99.99% | 100.00% | 82.04% | 20.55% | 2.91% |
| Monthly-Block Bootstrap | SPY Buy & Hold | 99.83% | 99.99% | 99.74% | 83.54% | 34.25% |
| Monthly-Block Bootstrap | Original 12 Equal Weight | 99.02% | 99.57% | 84.38% | 29.28% | 5.90% |

## 8. Framework vs Benchmark Probability

| Method | Comparison | P(Framework Sharpe > Benchmark Sharpe) | P(Framework MaxDD shallower than Benchmark MaxDD) | P(Framework CAGR > Benchmark CAGR) |
| --- | --- | --- | --- | --- |
| Daily Bootstrap | Framework vs Equal Weight Top5 | 96.04% | 97.13% | 49.99% |
| Daily Bootstrap | Framework vs SPY | 89.13% | 99.04% | 40.45% |
| Daily Bootstrap | Framework vs Original 12 Equal Weight | 95.95% | 76.01% | 96.29% |
| Monthly-Block Bootstrap | Framework vs Equal Weight Top5 | 96.36% | 97.12% | 48.57% |
| Monthly-Block Bootstrap | Framework vs SPY | 93.10% | 99.53% | 36.57% |
| Monthly-Block Bootstrap | Framework vs Original 12 Equal Weight | 97.59% | 88.99% | 98.49% |

## 9. Interpretation Questions

1. **Is Framework 001 statistically stable under bootstrap resampling?** Yes for positive return and Sharpe stability. In monthly-block bootstrap, Framework 001 has P(CAGR > 0) = 100.00% and P(Sharpe > 0) = 100.00%.
2. **How often does Framework 001 have positive CAGR?** Daily bootstrap: 100.00%; monthly-block bootstrap: 100.00%.
3. **How often does Framework 001 suffer MaxDD worse than -30%?** Daily bootstrap: 6.16%; monthly-block bootstrap: 2.27%.
4. **Does Framework 001 preserve its Sharpe advantage over Equal Weight Top5?** Yes. P(Framework Sharpe > EW Sharpe) is 96.04% in daily bootstrap and 96.36% in monthly-block bootstrap.
5. **Does Framework 001 preserve its MaxDD advantage over SPY?** Yes. P(Framework MaxDD shallower than SPY) is 99.53% in monthly-block bootstrap.
6. **Does Framework 001 beat SPY in CAGR consistently, or mainly in Sharpe/MaxDD?** Mainly Sharpe and MaxDD. P(Framework CAGR > SPY CAGR) is only 36.57% under monthly-block bootstrap, while Sharpe and MaxDD probabilities are much stronger.
7. **Does monthly-block bootstrap produce materially worse outcomes than daily bootstrap?** No. In this sample it is not materially worse for Framework 001. Framework median MaxDD changes from -20.09% in daily bootstrap to -18.47% in monthly-block bootstrap, and the 5th percentile MaxDD changes from -30.83% to -27.40%. The conclusion is therefore not dependent on the iid daily bootstrap assumption.
8. **Are the historical results near the bootstrap median or unusually lucky?** Historical CAGR 10.29% is at the 49.75% percentile of monthly-block bootstrap CAGR, Sharpe 0.97 is at the 49.68% percentile, and MaxDD -17.22% is at the 62.71% percentile. The historical result is favorable but not a one-in-a-thousand outlier.
9. **Which benchmark is hardest to beat?** SPY is hardest on CAGR. SPY remains the hardest benchmark for raw CAGR, while Equal Weight Top5 is the more relevant benchmark for testing whether Inverse Vol sizing adds value.
10. **Does this support proceeding to Monte Carlo or Paper Trading?** Yes. Bootstrap uncertainty does not break the framework thesis, but it also confirms that live expectations should emphasize Sharpe and drawdown control rather than persistent SPY CAGR dominance.

## 10. Final Conclusion

Framework 001 remains statistically credible under bootstrap uncertainty. The strongest evidence is high positive-CAGR probability, persistent Sharpe advantage over Equal Weight Top5, and strong MaxDD advantage versus SPY and Equal Weight Top5.

The caveat is unchanged from Walk Forward and Regime Analysis: Framework 001 is not a reliable SPY-CAGR maximizer. Its edge is mainly risk-adjusted performance and drawdown control. Monthly-block bootstrap does not weaken the result in this test; it confirms that the Sharpe and drawdown advantages survive a resampling method that keeps within-month return ordering intact.

Proceed to the next validation stage:

- Monte Carlo Path Simulation
- Paper Trading Simulation
- Live Readiness Checklist

## 11. Output Files

- Historical reference: `alpha/validation/metrics/bootstrap_001_historical_reference.csv`
- Daily bootstrap summary: `alpha/validation/metrics/bootstrap_001_daily_summary.csv`
- Monthly-block bootstrap summary: `alpha/validation/metrics/bootstrap_001_monthly_block_summary.csv`
- Probability diagnostics: `alpha/validation/metrics/bootstrap_001_probability_diagnostics.csv`
- Framework vs benchmark probabilities: `alpha/validation/metrics/bootstrap_001_framework_vs_benchmark.csv`
- Bootstrap simulation metrics: `alpha/validation/outputs/bootstrap_001_simulation_metrics.csv`

# Monte Carlo Path Simulation 001 — Cross-Asset Momentum Framework V1

## 1. Research Question

Framework 001 has completed Walk Forward Validation, Regime Analysis, and Bootstrap Validation. Bootstrap tested distribution stability. This Monte Carlo report tests path risk: what happens if the same return behavior appears in a different order?

The focus is not average return. The focus is worst paths, drawdown risk, wealth dispersion, and sequence risk.

No parameter is optimized. No Framework rule is changed.

## 2. Fixed Framework

| Component | Definition |
| --- | --- |
| Universe | Original 12 ETF |
| Signal | 126-day Cross-Sectional Momentum |
| Selection | Monthly Top5 |
| Weighting | 126-day Inverse Volatility |
| Cost | 5 bps transaction cost |
| Constraints | Long only; no leverage; no shorting; no MA filter |
| Source Returns | `alpha/validation/outputs/walk_forward_001_daily_details.csv` |

## 3. Monte Carlo Design

- Source series: Framework 001 actual historical daily net returns
- Sample length: 4508 trading days
- Simulations: 10,000 per method
- Random seed: `20260623`

### Method A — Return Shuffle Monte Carlo

Randomly shuffles all daily returns. It preserves every historical return value and only changes order. This directly tests sequence risk. Since the return set is unchanged, final wealth, CAGR, Sharpe, and volatility are effectively fixed; MaxDD changes.

### Method B — Block Monte Carlo

Samples contiguous 21-trading-day return blocks with replacement until the simulated path reaches the full sample length. This preserves short-term trend and volatility clustering inside each block.

### Method C — Stationary Bootstrap Monte Carlo

Uses random-length blocks with average length 21 trading days. At each day, the path either continues the prior block or restarts from a random historical day. This creates more natural block boundaries than fixed blocks.

## 4. Historical Reference

| Metric | Historical |
| --- | --- |
| CAGR | 10.29% |
| Sharpe | 0.97 |
| MaxDD | -17.22% |
| Volatility | 10.75% |
| Total Return | 476.94% |
| Final Wealth | 5.77x |

## 5. Final Wealth Distribution

| Method | Percentile | Final Wealth Multiple |
| --- | --- | --- |
| Return Shuffle | 1% | 5.77 |
| Return Shuffle | 5% | 5.77 |
| Return Shuffle | 25% | 5.77 |
| Return Shuffle | 50% | 5.77 |
| Return Shuffle | 75% | 5.77 |
| Return Shuffle | 95% | 5.77 |
| Return Shuffle | 99% | 5.77 |
| Block Monte Carlo | 1% | 2.13 |
| Block Monte Carlo | 5% | 2.88 |
| Block Monte Carlo | 25% | 4.29 |
| Block Monte Carlo | 50% | 5.71 |
| Block Monte Carlo | 75% | 7.43 |
| Block Monte Carlo | 95% | 11.17 |
| Block Monte Carlo | 99% | 14.68 |
| Stationary Bootstrap | 1% | 2.30 |
| Stationary Bootstrap | 5% | 2.98 |
| Stationary Bootstrap | 25% | 4.41 |
| Stationary Bootstrap | 50% | 5.80 |
| Stationary Bootstrap | 75% | 7.54 |
| Stationary Bootstrap | 95% | 11.25 |
| Stationary Bootstrap | 99% | 14.82 |

## 6. CAGR Distribution

| Method | Percentile | CAGR |
| --- | --- | --- |
| Return Shuffle | 1% | 10.29% |
| Return Shuffle | 5% | 10.29% |
| Return Shuffle | 25% | 10.29% |
| Return Shuffle | 50% | 10.29% |
| Return Shuffle | 75% | 10.29% |
| Return Shuffle | 95% | 10.29% |
| Return Shuffle | 99% | 10.29% |
| Block Monte Carlo | 1% | 4.32% |
| Block Monte Carlo | 5% | 6.09% |
| Block Monte Carlo | 25% | 8.48% |
| Block Monte Carlo | 50% | 10.23% |
| Block Monte Carlo | 75% | 11.86% |
| Block Monte Carlo | 95% | 14.44% |
| Block Monte Carlo | 99% | 16.20% |
| Stationary Bootstrap | 1% | 4.76% |
| Stationary Bootstrap | 5% | 6.30% |
| Stationary Bootstrap | 25% | 8.65% |
| Stationary Bootstrap | 50% | 10.32% |
| Stationary Bootstrap | 75% | 11.96% |
| Stationary Bootstrap | 95% | 14.49% |
| Stationary Bootstrap | 99% | 16.26% |

## 7. MaxDD Distribution

For MaxDD, `1% Worst` and `5% Worst` represent the most severe drawdown tails.

| Method | Percentile | MaxDD |
| --- | --- | --- |
| Return Shuffle | 1% Worst | -34.28% |
| Return Shuffle | 5% Worst | -28.72% |
| Return Shuffle | Median | -19.80% |
| Return Shuffle | 95% | -14.59% |
| Return Shuffle | 99% | -13.12% |
| Block Monte Carlo | 1% Worst | -35.57% |
| Block Monte Carlo | 5% Worst | -29.34% |
| Block Monte Carlo | Median | -19.27% |
| Block Monte Carlo | 95% | -13.48% |
| Block Monte Carlo | 99% | -11.72% |
| Stationary Bootstrap | 1% Worst | -33.66% |
| Stationary Bootstrap | 5% Worst | -27.66% |
| Stationary Bootstrap | Median | -18.78% |
| Stationary Bootstrap | 95% | -13.26% |
| Stationary Bootstrap | 99% | -11.62% |

## 8. Probability Diagnostics

| Method | Metric | Probability |
| --- | --- | --- |
| Return Shuffle | CAGR > 0 | 100.00% |
| Return Shuffle | CAGR > 5% | 100.00% |
| Return Shuffle | CAGR > 10% | 100.00% |
| Return Shuffle | Sharpe > 0.5 | 100.00% |
| Return Shuffle | Sharpe > 1.0 | 0.00% |
| Return Shuffle | MaxDD worse than -20% | 48.25% |
| Return Shuffle | MaxDD worse than -30% | 3.52% |
| Return Shuffle | MaxDD worse than -40% | 0.13% |
| Return Shuffle | MaxDD worse than -50% | 0.00% |
| Block Monte Carlo | CAGR > 0 | 100.00% |
| Block Monte Carlo | CAGR > 5% | 98.04% |
| Block Monte Carlo | CAGR > 10% | 53.84% |
| Block Monte Carlo | Sharpe > 0.5 | 98.09% |
| Block Monte Carlo | Sharpe > 1.0 | 43.96% |
| Block Monte Carlo | MaxDD worse than -20% | 43.95% |
| Block Monte Carlo | MaxDD worse than -30% | 4.22% |
| Block Monte Carlo | MaxDD worse than -40% | 0.33% |
| Block Monte Carlo | MaxDD worse than -50% | 0.02% |
| Stationary Bootstrap | CAGR > 0 | 100.00% |
| Stationary Bootstrap | CAGR > 5% | 98.66% |
| Stationary Bootstrap | CAGR > 10% | 55.28% |
| Stationary Bootstrap | Sharpe > 0.5 | 98.70% |
| Stationary Bootstrap | Sharpe > 1.0 | 44.36% |
| Stationary Bootstrap | MaxDD worse than -20% | 38.57% |
| Stationary Bootstrap | MaxDD worse than -30% | 2.69% |
| Stationary Bootstrap | MaxDD worse than -40% | 0.10% |
| Stationary Bootstrap | MaxDD worse than -50% | 0.00% |

## 9. Worst 10 Simulations

Worst paths are ranked by lowest final wealth for Block and Stationary methods. Return Shuffle has invariant final wealth, so it is ranked by deepest MaxDD.

| Rank Type | Method | Simulation | CAGR | MaxDD | Final Wealth |
| --- | --- | --- | --- | --- | --- |
| Worst 10 | Return Shuffle | 8081 | 10.29% | -48.57% | 5.77 |
| Worst 10 | Return Shuffle | 1794 | 10.29% | -44.44% | 5.77 |
| Worst 10 | Return Shuffle | 9817 | 10.29% | -42.99% | 5.77 |
| Worst 10 | Return Shuffle | 5513 | 10.29% | -42.44% | 5.77 |
| Worst 10 | Return Shuffle | 395 | 10.29% | -41.74% | 5.77 |
| Worst 10 | Return Shuffle | 1793 | 10.29% | -41.67% | 5.77 |
| Worst 10 | Return Shuffle | 5578 | 10.29% | -41.58% | 5.77 |
| Worst 10 | Return Shuffle | 7084 | 10.29% | -41.48% | 5.77 |
| Worst 10 | Return Shuffle | 7551 | 10.29% | -41.23% | 5.77 |
| Worst 10 | Return Shuffle | 4202 | 10.29% | -41.19% | 5.77 |
| Worst 10 | Block Monte Carlo | 6552 | 0.01% | -43.76% | 1.00 |
| Worst 10 | Block Monte Carlo | 5012 | 1.04% | -33.44% | 1.20 |
| Worst 10 | Block Monte Carlo | 4430 | 1.86% | -34.17% | 1.39 |
| Worst 10 | Block Monte Carlo | 564 | 1.89% | -42.08% | 1.40 |
| Worst 10 | Block Monte Carlo | 5871 | 2.02% | -44.17% | 1.43 |
| Worst 10 | Block Monte Carlo | 2316 | 2.16% | -32.09% | 1.47 |
| Worst 10 | Block Monte Carlo | 9710 | 2.17% | -37.31% | 1.47 |
| Worst 10 | Block Monte Carlo | 8036 | 2.18% | -42.42% | 1.47 |
| Worst 10 | Block Monte Carlo | 2909 | 2.47% | -24.76% | 1.55 |
| Worst 10 | Block Monte Carlo | 6039 | 2.58% | -24.40% | 1.58 |
| Worst 10 | Stationary Bootstrap | 9448 | 1.16% | -35.30% | 1.23 |
| Worst 10 | Stationary Bootstrap | 676 | 2.15% | -28.56% | 1.46 |
| Worst 10 | Stationary Bootstrap | 1604 | 2.17% | -29.34% | 1.47 |
| Worst 10 | Stationary Bootstrap | 3546 | 2.19% | -39.73% | 1.47 |
| Worst 10 | Stationary Bootstrap | 8275 | 2.31% | -38.75% | 1.50 |
| Worst 10 | Stationary Bootstrap | 9801 | 2.50% | -24.93% | 1.55 |
| Worst 10 | Stationary Bootstrap | 701 | 2.74% | -32.45% | 1.62 |
| Worst 10 | Stationary Bootstrap | 6689 | 2.79% | -28.35% | 1.64 |
| Worst 10 | Stationary Bootstrap | 4599 | 2.89% | -31.56% | 1.66 |
| Worst 10 | Stationary Bootstrap | 4421 | 2.98% | -26.68% | 1.69 |

## 10. Best 10 Simulations

Best paths are ranked by highest final wealth for Block and Stationary methods. Return Shuffle has invariant final wealth, so it is ranked by shallowest MaxDD.

| Rank Type | Method | Simulation | CAGR | MaxDD | Final Wealth |
| --- | --- | --- | --- | --- | --- |
| Best 10 | Return Shuffle | 5060 | 10.29% | -10.36% | 5.77 |
| Best 10 | Return Shuffle | 5479 | 10.29% | -10.86% | 5.77 |
| Best 10 | Return Shuffle | 8615 | 10.29% | -10.89% | 5.77 |
| Best 10 | Return Shuffle | 2808 | 10.29% | -11.13% | 5.77 |
| Best 10 | Return Shuffle | 4588 | 10.29% | -11.30% | 5.77 |
| Best 10 | Return Shuffle | 5759 | 10.29% | -11.50% | 5.77 |
| Best 10 | Return Shuffle | 6776 | 10.29% | -11.52% | 5.77 |
| Best 10 | Return Shuffle | 2214 | 10.29% | -11.62% | 5.77 |
| Best 10 | Return Shuffle | 4922 | 10.29% | -11.70% | 5.77 |
| Best 10 | Return Shuffle | 8434 | 10.29% | -11.82% | 5.77 |
| Best 10 | Block Monte Carlo | 9849 | 20.49% | -15.05% | 28.07 |
| Best 10 | Block Monte Carlo | 8083 | 20.23% | -11.32% | 27.01 |
| Best 10 | Block Monte Carlo | 333 | 20.00% | -14.88% | 26.10 |
| Best 10 | Block Monte Carlo | 917 | 18.94% | -14.67% | 22.26 |
| Best 10 | Block Monte Carlo | 6271 | 18.87% | -12.04% | 22.04 |
| Best 10 | Block Monte Carlo | 4040 | 18.86% | -16.87% | 22.00 |
| Best 10 | Block Monte Carlo | 6602 | 18.83% | -16.81% | 21.90 |
| Best 10 | Block Monte Carlo | 7263 | 18.70% | -16.47% | 21.46 |
| Best 10 | Block Monte Carlo | 836 | 18.44% | -12.36% | 20.65 |
| Best 10 | Block Monte Carlo | 4407 | 18.39% | -16.60% | 20.49 |
| Best 10 | Stationary Bootstrap | 3917 | 21.74% | -13.66% | 33.74 |
| Best 10 | Stationary Bootstrap | 7264 | 19.89% | -16.35% | 25.68 |
| Best 10 | Stationary Bootstrap | 2737 | 19.63% | -11.48% | 24.69 |
| Best 10 | Stationary Bootstrap | 7181 | 19.11% | -14.62% | 22.85 |
| Best 10 | Stationary Bootstrap | 9759 | 18.94% | -14.59% | 22.26 |
| Best 10 | Stationary Bootstrap | 9922 | 18.75% | -9.76% | 21.64 |
| Best 10 | Stationary Bootstrap | 4664 | 18.65% | -17.47% | 21.30 |
| Best 10 | Stationary Bootstrap | 6137 | 18.31% | -13.54% | 20.24 |
| Best 10 | Stationary Bootstrap | 6674 | 18.17% | -14.91% | 19.82 |
| Best 10 | Stationary Bootstrap | 8763 | 18.09% | -13.72% | 19.57 |

## 11. Historical Percentile

Percentile is calculated as `P(simulated metric <= historical metric)`. For MaxDD, a higher percentile means the historical drawdown was shallower than more simulated paths.

| Method | Metric | Historical Percentile |
| --- | --- | --- |
| Return Shuffle | CAGR | 54.45% |
| Return Shuffle | Sharpe | 99.99% |
| Return Shuffle | MaxDD | 75.56% |
| Return Shuffle | Final Wealth | 45.02% |
| Block Monte Carlo | CAGR | 50.96% |
| Block Monte Carlo | Sharpe | 50.21% |
| Block Monte Carlo | MaxDD | 68.13% |
| Block Monte Carlo | Final Wealth | 50.96% |
| Stationary Bootstrap | CAGR | 49.60% |
| Stationary Bootstrap | Sharpe | 49.20% |
| Stationary Bootstrap | MaxDD | 66.47% |
| Stationary Bootstrap | Final Wealth | 49.60% |

## 12. Interpretation Questions

1. **Is Framework 001 sensitive to return order?** Yes for drawdown, not for final wealth under pure shuffle. Return Shuffle keeps CAGR fixed near 10.29%, but MaxDD median becomes -19.80% versus historical -17.22%. Sequence affects the pain path more than the endpoint.
2. **How bad is the worst path?** The worst simulated path is `Block Monte Carlo` simulation 6552, with CAGR 0.01%, MaxDD -43.76%, and final wealth 1.00x.
3. **Is historical MaxDD close to an extreme value?** No. Under Stationary Bootstrap, historical MaxDD percentile is 66.47%. The historical drawdown is favorable, but not implausibly lucky.
4. **Is historical CAGR close to an extreme lucky value?** No. Under Stationary Bootstrap, historical CAGR percentile is 49.60%.
5. **Which Monte Carlo method is strictest?** `Block Monte Carlo` is strictest by P(MaxDD worse than -30%). The three probabilities are Shuffle 3.52%, Block 4.22%, Stationary 2.69%.
6. **Does sequence risk constitute the main risk?** Sequence risk is real but not thesis-breaking. It mainly appears as deeper drawdowns, especially when losses cluster. It does not destroy long-run wealth in the tested simulations.
7. **Is long-term wealth distribution stable?** Yes. Stationary Bootstrap 5th percentile final wealth is 2.98x, and P(CAGR > 0) is 100.00%.
8. **Does Framework have acceptable tail risk?** Yes for a research framework. Stationary Bootstrap 1% worst MaxDD is -33.66%. That is painful but still materially below catastrophic equity-crisis drawdowns observed in SPY-based references.
9. **Are Bootstrap and Monte Carlo conclusions consistent?** Yes. Both show the same profile: positive long-term return stability, strong drawdown control relative to raw equity exposure, and no guarantee of SPY-CAGR dominance.
10. **Is Framework ready for Live Readiness?** Yes as a validated research framework. It should now move into live-readiness work: execution assumptions, monitoring, reconciliation, paper trading, and failure procedures.

## 13. Final Conclusion

Framework 001 passes Monte Carlo path-risk validation. Return order changes can materially alter drawdowns, but the framework's long-term wealth distribution remains stable across shuffle, fixed-block, and stationary-bootstrap simulations.

The main risk is not that the framework only worked because of one lucky ordering of returns. The main risk is practical: tolerating drawdowns that can be worse than the historical path, especially under clustered-loss paths. That is a live-readiness and risk-budget question, not a failure of the research framework.

Status update:

**Framework 001 is marked as a Validated Research Framework.**

The project should now enter:

`alpha/live_readiness/`

Next work:

- Monte Carlo path review against investor risk limits
- Paper Trading Simulation
- Execution and slippage assumptions
- Monitoring and reconciliation checklist
- Live failure procedures

## 14. Output Files

- Historical reference: `alpha/validation/metrics/monte_carlo_001_historical_reference.csv`
- Final wealth distribution: `alpha/validation/metrics/monte_carlo_001_final_wealth_distribution.csv`
- CAGR distribution: `alpha/validation/metrics/monte_carlo_001_cagr_distribution.csv`
- MaxDD distribution: `alpha/validation/metrics/monte_carlo_001_maxdd_distribution.csv`
- Probability diagnostics: `alpha/validation/metrics/monte_carlo_001_probability_diagnostics.csv`
- Worst paths: `alpha/validation/metrics/monte_carlo_001_worst_10.csv`
- Best paths: `alpha/validation/metrics/monte_carlo_001_best_10.csv`
- Historical percentiles: `alpha/validation/metrics/monte_carlo_001_historical_percentiles.csv`
- Simulation metrics: `alpha/validation/outputs/monte_carlo_001_simulation_metrics.csv`

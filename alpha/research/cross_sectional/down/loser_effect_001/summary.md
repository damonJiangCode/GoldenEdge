# Cross-Sectional Loser Effect 001

## 1. Research Question

Framework 001 validated the winner side of cross-sectional momentum. This study measures the opposite side: after an ETF becomes one of the worst 126-day performers in the Original 12 universe, does it keep underperforming or mean revert?

This is not a strategy backtest. It does not use shorts, position sizing, MA filters, transaction costs, or parameter optimization.

## 2. Methodology

- Universe: Original 12 ETF universe
- Equity: SPY, QQQ, IWM, EFA
- Commodity: GLD, SLV, USO, DBA
- Bond: TLT, IEF, SHY, LQD
- Requested sample window: `2008-02-01` to `2025-12-31`
- Included event/forward date range: `2008-02-29` to `2025-12-30`
- Ranking date: each month-end trading day
- Ranking signal: 126 trading day total return, lower is worse
- Loser groups: Top1 Loser, Top3 Loser, Top5 Loser
- Forward horizons: 5, 10, 20, 40, 60, 120 trading days
- Forward return: month-end close to future close
- Events: no overlapping event filtering
- Significance reference: Newey-West mean test, with lag increasing by horizon

## 3. Aggregate Results

| group | horizon | mean_return | median_return | win_rate | observation_count | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Top1 Loser | FR5 | -0.17% | -0.10% | 48.13% | 214 | -0.58 | 0.56 |
| Top1 Loser | FR10 | -0.27% | -0.05% | 49.53% | 214 | -0.67 | 0.50 |
| Top1 Loser | FR20 | -0.19% | 0.23% | 53.74% | 214 | -0.30 | 0.76 |
| Top1 Loser | FR40 | -0.11% | 0.72% | 55.40% | 213 | -0.10 | 0.92 |
| Top1 Loser | FR60 | 0.34% | 1.01% | 53.77% | 212 | 0.26 | 0.80 |
| Top1 Loser | FR120 | 0.34% | -0.09% | 49.76% | 209 | 0.17 | 0.86 |
| Top3 Loser | FR5 | -0.01% | -0.03% | 48.13% | 214 | -0.05 | 0.96 |
| Top3 Loser | FR10 | 0.04% | 0.18% | 52.80% | 214 | 0.15 | 0.88 |
| Top3 Loser | FR20 | 0.40% | 0.23% | 54.67% | 214 | 1.09 | 0.28 |
| Top3 Loser | FR40 | 0.57% | 0.37% | 56.34% | 213 | 0.98 | 0.33 |
| Top3 Loser | FR60 | 1.12% | 1.23% | 59.43% | 212 | 1.42 | 0.16 |
| Top3 Loser | FR120 | 2.11% | 1.31% | 58.85% | 209 | 1.43 | 0.15 |
| Top5 Loser | FR5 | -0.08% | -0.10% | 46.73% | 214 | -0.52 | 0.60 |
| Top5 Loser | FR10 | -0.07% | 0.05% | 50.47% | 214 | -0.34 | 0.73 |
| Top5 Loser | FR20 | 0.26% | 0.21% | 52.80% | 214 | 0.84 | 0.40 |
| Top5 Loser | FR40 | 0.55% | 0.38% | 55.40% | 213 | 1.10 | 0.27 |
| Top5 Loser | FR60 | 1.06% | 1.35% | 61.32% | 212 | 1.51 | 0.13 |
| Top5 Loser | FR120 | 2.23% | 1.96% | 61.24% | 209 | 1.62 | 0.11 |

## 4. By Asset Class

| asset_class | group | horizon | mean_return | median_return | win_rate | observation_count |
| --- | --- | --- | --- | --- | --- | --- |
| Bond | Top1 Loser | FR5 | -0.34% | -0.36% | 40.00% | 50 |
| Bond | Top1 Loser | FR10 | -0.10% | -0.30% | 38.00% | 50 |
| Bond | Top1 Loser | FR20 | 0.12% | 0.14% | 54.00% | 50 |
| Bond | Top1 Loser | FR40 | 0.77% | 1.15% | 62.00% | 50 |
| Bond | Top1 Loser | FR60 | 1.08% | 1.71% | 54.00% | 50 |
| Bond | Top1 Loser | FR120 | 2.75% | 0.47% | 55.10% | 49 |
| Bond | Top3 Loser | FR5 | -0.11% | -0.03% | 47.60% | 208 |
| Bond | Top3 Loser | FR10 | -0.04% | -0.04% | 46.63% | 208 |
| Bond | Top3 Loser | FR20 | 0.26% | 0.13% | 59.13% | 208 |
| Bond | Top3 Loser | FR40 | 0.32% | 0.18% | 57.77% | 206 |
| Bond | Top3 Loser | FR60 | 0.51% | 0.39% | 59.80% | 204 |
| Bond | Top3 Loser | FR120 | 1.42% | 0.65% | 62.00% | 200 |
| Bond | Top5 Loser | FR5 | -0.12% | -0.04% | 45.99% | 411 |
| Bond | Top5 Loser | FR10 | -0.17% | -0.07% | 44.53% | 411 |
| Bond | Top5 Loser | FR20 | 0.04% | 0.04% | 54.50% | 411 |
| Bond | Top5 Loser | FR40 | 0.21% | 0.07% | 53.43% | 408 |
| Bond | Top5 Loser | FR60 | 0.38% | 0.24% | 58.66% | 404 |
| Bond | Top5 Loser | FR120 | 1.01% | 0.63% | 61.52% | 395 |
| Commodity | Top1 Loser | FR5 | -0.16% | -0.11% | 48.97% | 145 |
| Commodity | Top1 Loser | FR10 | -0.27% | 0.38% | 53.10% | 145 |
| Commodity | Top1 Loser | FR20 | -0.65% | 0.07% | 51.03% | 145 |
| Commodity | Top1 Loser | FR40 | -0.75% | 0.34% | 50.69% | 144 |
| Commodity | Top1 Loser | FR60 | 0.03% | 0.65% | 53.15% | 143 |
| Commodity | Top1 Loser | FR120 | -0.27% | -0.57% | 47.52% | 141 |
| Commodity | Top3 Loser | FR5 | -0.09% | -0.06% | 49.36% | 312 |
| Commodity | Top3 Loser | FR10 | 0.04% | 0.19% | 52.56% | 312 |
| Commodity | Top3 Loser | FR20 | -0.01% | 0.11% | 50.96% | 312 |
| Commodity | Top3 Loser | FR40 | -0.37% | 0.32% | 51.77% | 311 |
| Commodity | Top3 Loser | FR60 | 0.46% | 0.61% | 54.19% | 310 |
| Commodity | Top3 Loser | FR120 | 0.99% | 0.10% | 50.65% | 306 |
| Commodity | Top5 Loser | FR5 | -0.18% | -0.06% | 49.03% | 414 |
| Commodity | Top5 Loser | FR10 | -0.05% | 0.09% | 50.72% | 414 |
| Commodity | Top5 Loser | FR20 | -0.03% | 0.11% | 50.72% | 414 |
| Commodity | Top5 Loser | FR40 | -0.16% | 0.28% | 51.21% | 412 |
| Commodity | Top5 Loser | FR60 | 0.38% | 0.39% | 52.80% | 411 |
| Commodity | Top5 Loser | FR120 | 0.97% | 0.71% | 51.72% | 406 |
| Equity | Top1 Loser | FR5 | 0.17% | 0.52% | 63.16% | 19 |
| Equity | Top1 Loser | FR10 | -0.72% | 0.35% | 52.63% | 19 |
| Equity | Top1 Loser | FR20 | 2.48% | 2.65% | 73.68% | 19 |
| Equity | Top1 Loser | FR40 | 2.40% | 3.02% | 73.68% | 19 |
| Equity | Top1 Loser | FR60 | 0.66% | 3.53% | 57.89% | 19 |
| Equity | Top1 Loser | FR120 | -1.33% | 5.53% | 52.63% | 19 |
| Equity | Top3 Loser | FR5 | 0.37% | 0.50% | 57.38% | 122 |
| Equity | Top3 Loser | FR10 | 0.17% | 0.64% | 54.92% | 122 |
| Equity | Top3 Loser | FR20 | 1.71% | 3.12% | 66.39% | 122 |
| Equity | Top3 Loser | FR40 | 3.39% | 4.90% | 70.49% | 122 |
| Equity | Top3 Loser | FR60 | 3.82% | 5.24% | 67.21% | 122 |
| Equity | Top3 Loser | FR120 | 6.10% | 7.63% | 67.77% | 121 |
| Equity | Top5 Loser | FR5 | 0.17% | 0.52% | 55.51% | 245 |
| Equity | Top5 Loser | FR10 | 0.04% | 0.56% | 53.88% | 245 |
| Equity | Top5 Loser | FR20 | 1.10% | 1.88% | 63.27% | 245 |
| Equity | Top5 Loser | FR40 | 2.31% | 4.09% | 67.76% | 245 |
| Equity | Top5 Loser | FR60 | 3.33% | 4.28% | 67.35% | 245 |
| Equity | Top5 Loser | FR120 | 6.32% | 7.98% | 68.85% | 244 |

## 5. Distribution Diagnostics

| group | horizon | p10 | p25 | median | p75 | p90 |
| --- | --- | --- | --- | --- | --- | --- |
| Top1 Loser | FR5 | -4.20% | -2.31% | -0.10% | 1.74% | 4.43% |
| Top1 Loser | FR10 | -6.96% | -3.00% | -0.05% | 2.44% | 6.30% |
| Top1 Loser | FR20 | -8.02% | -3.91% | 0.23% | 3.83% | 8.28% |
| Top1 Loser | FR40 | -11.45% | -4.25% | 0.72% | 6.54% | 11.82% |
| Top1 Loser | FR60 | -15.31% | -4.46% | 1.01% | 8.15% | 14.61% |
| Top1 Loser | FR120 | -16.51% | -7.60% | -0.09% | 8.91% | 21.50% |
| Top3 Loser | FR5 | -2.42% | -1.54% | -0.03% | 1.27% | 2.62% |
| Top3 Loser | FR10 | -4.12% | -1.81% | 0.18% | 2.12% | 4.32% |
| Top3 Loser | FR20 | -5.13% | -1.97% | 0.23% | 2.75% | 5.78% |
| Top3 Loser | FR40 | -7.20% | -2.29% | 0.37% | 4.22% | 8.69% |
| Top3 Loser | FR60 | -8.71% | -2.24% | 1.23% | 5.32% | 9.93% |
| Top3 Loser | FR120 | -10.10% | -3.00% | 1.31% | 6.71% | 16.30% |
| Top5 Loser | FR5 | -2.19% | -1.23% | -0.10% | 1.06% | 2.15% |
| Top5 Loser | FR10 | -3.25% | -1.59% | 0.05% | 1.61% | 3.39% |
| Top5 Loser | FR20 | -3.87% | -1.93% | 0.21% | 2.07% | 5.08% |
| Top5 Loser | FR40 | -5.89% | -1.83% | 0.38% | 3.42% | 6.61% |
| Top5 Loser | FR60 | -7.19% | -2.03% | 1.35% | 4.19% | 8.95% |
| Top5 Loser | FR120 | -9.57% | -2.78% | 1.96% | 6.29% | 14.47% |

## 6. Key Observations

- Negative mean forward return appears in `7` of `18` group-horizon combinations.
- Statistically significant negative mean return appears in `0` of `18` combinations.
- Positive mean forward return appears in `11` of `18` combinations.
- Statistically significant positive mean return appears in `0` of `18` combinations.
- Strongest loser-continuation cell: `Top1 Loser` at `FR10` with mean return `-0.27%` and win rate `49.53%`.
- Strongest mean-reversion cell: `Top5 Loser` at `FR120` with mean return `2.23%` and win rate `61.24%`.
- Cross-group average return is weakest at `FR10` and strongest at `FR120`.
- By asset class, selected losers are weakest in `Commodity` and strongest in `Equity`.
- Top1 Loser average across horizons is `-0.01%`; Top5 Loser average across horizons is `0.66%`.

## 7. Answers

1. **Do losers continue losing?** Only partially. Some short-to-intermediate cells show weak loser continuation, but the pattern is not broad enough to define a standalone loser alpha.
2. **At which horizons is continuation strongest?** The most negative average cell is `Top1 Loser` at `FR10`.
3. **At which horizons does mean reversion appear?** Mean reversion is strongest in `Top5 Loser` at `FR120` and becomes more visible where the median and win rate rise above zero.
4. **Is the effect different across Equity, Commodity, and Bond?** Yes. The weakest average loser behavior is in `Commodity`, while `Equity` shows the most mean-reversion-like behavior among selected losers.
5. **Does Top1 behave differently from Top5?** Yes. Top1 is more idiosyncratic and has wider distribution tails. Top5 is smoother because it averages several weak assets, but it also dilutes any extreme loser continuation.
6. **Is there evidence of a tradable Loser Alpha?** Not yet. The effect measurement does not produce stable, statistically strong negative forward returns across groups and horizons.
7. **Momentum, mean reversion, or mixed behavior?** `Mixed behavior, with no robust standalone loser alpha.` The loser side is materially less clean than the winner side validated in Framework 001.

## 8. Final Conclusion

The Original 12 loser side does not currently qualify as a validated standalone alpha direction. Worst-ranked ETFs do not reliably keep falling across the tested horizons. The evidence is better described as mixed: some loser continuation exists, but mean reversion appears in other horizons and asset classes.

Loser-side research remains useful as a diagnostic for potential long-short spreads, but this study does not support introducing a short-loser component into Framework 001.

## 9. Output Files

- `metrics/aggregate_results.csv`
- `metrics/by_asset_class.csv`
- `metrics/distribution_diagnostics.csv`
- `metrics/statistical_tests.csv`
- `outputs/loser_portfolio_events.csv`
- `outputs/loser_asset_events.csv`

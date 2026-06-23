# Bottom Loser Continuation Study

## 1. Research Question

过去 126 个交易日表现最差的资产，未来是否继续表现最差？本研究是 event-study validation，不构建或优化交易策略。

- Universe: current 12 ETF Mixed Asset Universe
- Sample: `2007-08-01` to `2025-12-31`
- Ranking frequency: monthly, at month end
- Momentum lookback: 126 trading days
- Forward horizons: 5/15/30/45/60 trading days
- Portfolios: Bottom1/Bottom3/Bottom5 and matched Top1/Top3/Top5
- Forward return starts from the ranking-date close; no transaction cost is applied
- t-statistic and two-sided p-value use Newey-West standard errors to address overlapping forward returns

## 2. Bottom Portfolio Future Returns

| portfolio | horizon | sample_count | mean | median | std | win_rate | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bottom1 | FR5 | 221 | -0.20% | -0.09% | 4.36% | 48.42% | -0.67 | 0.50 |
| Bottom1 | FR15 | 221 | -0.46% | 0.07% | 8.48% | 51.13% | -0.80 | 0.42 |
| Bottom1 | FR30 | 220 | -0.04% | 0.49% | 11.13% | 53.18% | -0.05 | 0.96 |
| Bottom1 | FR45 | 219 | 0.17% | 0.90% | 13.16% | 53.88% | 0.16 | 0.87 |
| Bottom1 | FR60 | 219 | 0.30% | 0.72% | 14.85% | 53.88% | 0.24 | 0.81 |
| Bottom3 | FR5 | 221 | -0.03% | -0.03% | 2.53% | 48.42% | -0.18 | 0.86 |
| Bottom3 | FR15 | 221 | 0.01% | 0.18% | 4.90% | 52.94% | 0.02 | 0.98 |
| Bottom3 | FR30 | 220 | 0.48% | 0.20% | 6.31% | 54.55% | 0.99 | 0.33 |
| Bottom3 | FR45 | 219 | 0.81% | 0.80% | 7.64% | 56.16% | 1.24 | 0.21 |
| Bottom3 | FR60 | 219 | 1.09% | 1.25% | 8.62% | 59.36% | 1.41 | 0.16 |
| Bottom5 | FR5 | 221 | -0.09% | -0.10% | 2.17% | 47.06% | -0.60 | 0.55 |
| Bottom5 | FR15 | 221 | -0.06% | -0.01% | 3.97% | 49.77% | -0.24 | 0.81 |
| Bottom5 | FR30 | 220 | 0.36% | 0.41% | 5.29% | 52.73% | 0.86 | 0.39 |
| Bottom5 | FR45 | 219 | 0.83% | 0.99% | 6.44% | 59.36% | 1.49 | 0.14 |
| Bottom5 | FR60 | 219 | 1.11% | 1.46% | 7.26% | 61.64% | 1.63 | 0.10 |

## 3. Bottom vs Equal Weight Universe

`Bottom excess = Bottom portfolio forward return - 12 ETF Equal Weight forward return`

| portfolio | horizon | sample_count | avg_excess | win_rate | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- |
| Bottom1 | FR5 | 221 | -0.28% | 46.15% | -1.10 | 0.27 |
| Bottom1 | FR15 | 221 | -0.77% | 47.06% | -1.59 | 0.11 |
| Bottom1 | FR30 | 220 | -0.83% | 48.18% | -1.17 | 0.24 |
| Bottom1 | FR45 | 219 | -1.05% | 47.95% | -1.18 | 0.24 |
| Bottom1 | FR60 | 219 | -1.27% | 48.86% | -1.25 | 0.21 |
| Bottom3 | FR5 | 221 | -0.11% | 44.34% | -0.90 | 0.37 |
| Bottom3 | FR15 | 221 | -0.30% | 45.70% | -1.36 | 0.17 |
| Bottom3 | FR30 | 220 | -0.31% | 43.18% | -0.96 | 0.34 |
| Bottom3 | FR45 | 219 | -0.41% | 46.12% | -0.96 | 0.34 |
| Bottom3 | FR60 | 219 | -0.48% | 47.03% | -0.99 | 0.32 |
| Bottom5 | FR5 | 221 | -0.17% | 43.44% | -1.80 | 0.07 |
| Bottom5 | FR15 | 221 | -0.37% | 42.08% | -2.52 | 0.01 |
| Bottom5 | FR30 | 220 | -0.43% | 40.91% | -1.86 | 0.06 |
| Bottom5 | FR45 | 219 | -0.39% | 41.55% | -1.22 | 0.22 |
| Bottom5 | FR60 | 219 | -0.45% | 42.92% | -1.24 | 0.22 |

## 4. Winner-Loser Spread

`Spread = matched Top N forward return - Bottom N forward return`

| portfolio_size | horizon | sample_count | spread_mean | spread_win_rate | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | FR5 | 221 | 0.13% | 51.58% | 0.33 | 0.74 |
| 1 | FR15 | 221 | 0.98% | 51.13% | 1.42 | 0.16 |
| 1 | FR30 | 220 | 0.73% | 48.64% | 0.70 | 0.48 |
| 1 | FR45 | 219 | 0.94% | 50.68% | 0.74 | 0.46 |
| 1 | FR60 | 219 | 1.31% | 53.88% | 0.88 | 0.38 |
| 3 | FR5 | 221 | 0.26% | 54.75% | 1.04 | 0.30 |
| 3 | FR15 | 221 | 0.82% | 52.49% | 2.12 | 0.03 |
| 3 | FR30 | 220 | 0.85% | 54.55% | 1.41 | 0.16 |
| 3 | FR45 | 219 | 0.91% | 53.88% | 1.16 | 0.25 |
| 3 | FR60 | 219 | 0.98% | 52.51% | 1.08 | 0.28 |
| 5 | FR5 | 221 | 0.36% | 56.56% | 1.95 | 0.05 |
| 5 | FR15 | 221 | 0.87% | 58.82% | 3.02 | 0.00 |
| 5 | FR30 | 220 | 1.00% | 58.64% | 2.19 | 0.03 |
| 5 | FR45 | 219 | 0.90% | 55.71% | 1.45 | 0.15 |
| 5 | FR60 | 219 | 0.99% | 56.16% | 1.39 | 0.17 |

## 5. Winner-Only Continuation

Winner-only continuation is evaluated against the same Equal Weight Universe:

| portfolio_size | horizon | sample_count | avg_excess | win_rate | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | FR5 | 221 | -0.15% | 44.34% | -0.59 | 0.55 |
| 1 | FR15 | 221 | 0.22% | 47.51% | 0.56 | 0.58 |
| 1 | FR30 | 220 | -0.11% | 45.91% | -0.19 | 0.85 |
| 1 | FR45 | 219 | -0.11% | 44.75% | -0.17 | 0.87 |
| 1 | FR60 | 219 | 0.05% | 48.86% | 0.06 | 0.95 |
| 3 | FR5 | 221 | 0.14% | 52.94% | 1.01 | 0.31 |
| 3 | FR15 | 221 | 0.52% | 56.56% | 2.48 | 0.01 |
| 3 | FR30 | 220 | 0.54% | 56.82% | 1.64 | 0.10 |
| 3 | FR45 | 219 | 0.50% | 52.05% | 1.18 | 0.24 |
| 3 | FR60 | 219 | 0.50% | 55.25% | 0.98 | 0.33 |
| 5 | FR5 | 221 | 0.19% | 54.30% | 1.99 | 0.05 |
| 5 | FR15 | 221 | 0.50% | 56.56% | 3.33 | 0.00 |
| 5 | FR30 | 220 | 0.57% | 60.91% | 2.41 | 0.02 |
| 5 | FR45 | 219 | 0.51% | 55.71% | 1.59 | 0.11 |
| 5 | FR60 | 219 | 0.54% | 55.71% | 1.46 | 0.15 |

## 6. Answers

1. **Are Bottom portfolios negative on average?** 6/15 portfolio-horizon combinations have negative mean forward return, but only 0/15 are significantly below zero.
2. **Do Bottom portfolios underperform Equal Weight?** 15/15 have negative average excess; 1/15 are negative with p-value < 0.05.
3. **Does underperformance change with horizon?** Bottom underperformance strengthens monotonically as the horizon increases. This is an economic-magnitude pattern; statistical significance does not strengthen monotonically.
4. **Is Winner-Loser statistically stronger than Winner-only?** No overall. Spread has both a higher t-statistic and lower p-value in only 6/15 matched comparisons. Significant positive spread exists in 3/15 combinations, versus 4/15 significant positive Winner-only excess combinations.
5. **Classification:** `Winner Continuation primarily, with limited relative loser weakness`. Bottom 的负收益没有统计显著性，相对弱势仅 1/15 显著；Winner-only 相对 Equal Weight 则有更广泛的显著证据。

## 7. Interpretation Guardrails

- Bottom future return being positive does not disprove relative loser weakness; broad market drift can lift both winners and losers.
- Bottom underperforming Equal Weight does not mean losers are profitable shorts after financing, borrow costs, and implementation constraints.
- Winner-Loser spread can be significant even when neither leg is attractive as a standalone trade.
- Top3/Top5 spreads at FR15, and Top5 at FR30, justify further long-short implementation research; they do not establish a robust short-loser strategy across horizons.
- The same monthly observations overlap at longer horizons. Newey-West correction reduces, but does not eliminate, regime dependence and multiple-comparison risk.
- This study does not test alternative lookbacks, ranking frequencies, or portfolio sizes beyond the fixed specification.

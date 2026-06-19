# Cross-Sectional Momentum Summary

## 1. 研究问题

如果每个月买过去表现最好的资产，未来是否能够获得高于基准的收益和风险调整收益？
这里验证的是跨资产横截面动量，不是单个资产内部的 Time-Series Momentum。

## 2. 实验设计

- Price: `Adj Close`
- Universe: 12 ETFs across equity, commodity, and bond
- Common sample: `2007-08-01` to `2025-12-31`
- Rebalance: 每个月最后一个交易日排名，下一交易日开始持仓
- Momentum windows: `mom_63`, `mom_126`
- Strategies: `Top1`, `Top3`, `Top5`
- Weighting: selected assets equal weight
- Trading cost: 5 bps applied to turnover
- Benchmarks: `SPY Buy & Hold`, `Equal Weight All Assets monthly rebalance`

## 3. 结果表

| momentum_window | strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover | Number of Rebalances |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mom_63 | Top1 | 6.45% | 0.36 | -67.53% | 27.12% | 0.10 | 211.95% | 21400.00% | 221 |
| mom_63 | Top3 | 8.62% | 0.58 | -37.31% | 16.49% | 0.23 | 355.35% | 17898.48% | 221 |
| mom_63 | Top5 | 8.42% | 0.67 | -29.41% | 13.30% | 0.29 | 341.51% | 13688.53% | 221 |
| mom_126 | Top1 | 6.30% | 0.36 | -48.56% | 26.83% | 0.13 | 204.00% | 19700.00% | 221 |
| mom_126 | Top3 | 11.00% | 0.71 | -31.30% | 16.70% | 0.35 | 582.82% | 13094.76% | 221 |
| mom_126 | Top5 | 11.36% | 0.88 | -29.06% | 13.20% | 0.39 | 623.86% | 9708.32% | 221 |
| Benchmark | Benchmark_SPY | 10.76% | 0.61 | -55.19% | 19.94% | 0.19 | 560.12% | 0.00% | 0 |
| Benchmark | Benchmark_EqualWeight | 6.44% | 0.64 | -31.37% | 10.70% | 0.21 | 215.95% | 735.33% | 221 |

## 4. 总体结论

- Sharpe 最好的策略: `mom_126_Top5`，CAGR=11.36%，Sharpe=0.88，MaxDD=-29.06%。
- CAGR 最好的策略: `mom_126_Top5`，CAGR=11.36%。
- Top1/Top3/Top5 中，按平均 Sharpe 排名最好的是 `Top5`。
- 3个月 vs 6个月动量中，按平均 Sharpe 排名更好的是 `mom_126`。
- 显著优于 SPY 的策略数量: 0 / 6。
- 显著优于 Equal Weight 的策略数量: 1 / 6。
- 最佳策略的优势来源: 更高收益；更低回撤。

## 5. Top N 对比

| top_n | avg_CAGR | avg_Sharpe | avg_MaxDD |
| --- | --- | --- | --- |
| 5.00 | 9.89% | 0.78 | -29.23% |
| 3.00 | 9.81% | 0.65 | -34.31% |
| 1.00 | 6.38% | 0.36 | -58.04% |

## 6. Momentum Window 对比

| momentum_window | avg_CAGR | avg_Sharpe | avg_MaxDD |
| --- | --- | --- | --- |
| mom_126 | 9.56% | 0.65 | -36.31% |
| mom_63 | 7.83% | 0.54 | -44.75% |

## 7. 是否优于 Benchmark

| strategy_label | benchmark | monthly_observations | avg_monthly_excess | annualized_excess | win_rate_vs_benchmark | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mom_63_Top1 | Benchmark_SPY | 221 | -0.16% | -1.94% | 47.96% | -0.30 | 0.76 |
| mom_63_Top1 | Benchmark_EqualWeight | 221 | 0.23% | 2.80% | 49.77% | 0.50 | 0.62 |
| mom_63_Top3 | Benchmark_SPY | 221 | -0.17% | -1.98% | 46.15% | -0.49 | 0.63 |
| mom_63_Top3 | Benchmark_EqualWeight | 221 | 0.23% | 2.75% | 53.39% | 0.92 | 0.36 |
| mom_63_Top5 | Benchmark_SPY | 221 | -0.22% | -2.58% | 42.53% | -0.78 | 0.44 |
| mom_63_Top5 | Benchmark_EqualWeight | 221 | 0.18% | 2.13% | 56.56% | 1.02 | 0.31 |
| mom_126_Top1 | Benchmark_SPY | 221 | -0.20% | -2.40% | 44.80% | -0.40 | 0.69 |
| mom_126_Top1 | Benchmark_EqualWeight | 221 | 0.19% | 2.32% | 47.96% | 0.45 | 0.66 |
| mom_126_Top3 | Benchmark_SPY | 221 | 0.01% | 0.17% | 47.06% | 0.04 | 0.97 |
| mom_126_Top3 | Benchmark_EqualWeight | 221 | 0.41% | 5.00% | 57.01% | 1.78 | 0.08 |
| mom_126_Top5 | Benchmark_SPY | 221 | 0.00% | 0.03% | 44.34% | 0.01 | 0.99 |
| mom_126_Top5 | Benchmark_EqualWeight | 221 | 0.40% | 4.86% | 61.09% | 2.53 | 0.01 |

## 8. 哪些资产最常进入组合

下面是最佳策略 `mom_126_Top5` 的资产入选统计：

| symbol | Average Rank | Selection Count | Selection Percentage |
| --- | --- | --- | --- |
| QQQ | 4.25 | 150 | 67.87% |
| SPY | 5.09 | 136 | 61.54% |
| IWM | 6.05 | 111 | 50.23% |
| GLD | 5.92 | 108 | 48.87% |
| SLV | 6.78 | 95 | 42.99% |
| USO | 7.37 | 87 | 39.37% |
| EFA | 6.62 | 86 | 38.91% |
| TLT | 7.01 | 86 | 38.91% |
| IEF | 7.12 | 73 | 33.03% |
| DBA | 7.41 | 70 | 31.67% |
| LQD | 6.77 | 61 | 27.60% |
| SHY | 7.62 | 42 | 19.00% |

完整资产统计见 `metrics/asset_selection_summary.csv`。

## 9. 解释

- Top 资产继续上涨，只说明横截面动量方向有效；它还必须在扣除 turnover cost 后优于 benchmark，才更接近可投资策略。
- 显著优于 benchmark 这里用月度超额收益做单样本 t-test；由于月度样本仍可能存在状态依赖，结论应作为研究证据，不应当作最终投资确认。
- 如果收益提升主要来自更低回撤，策略可能更像风险切换；如果主要来自更高 CAGR，才更像纯粹的 winner continuation。
- Equal Weight 是很强的基准，因为它已经吃到了跨资产分散收益；能否超过它，比超过 SPY 更能说明横截面动量是否真的增值。

## 10. 最终回答

这个实验直接回答：“跨资产横截面动量是否能把之前发现的 Momentum Alpha 转化成一个真正的投资组合策略？”

判断标准不是单看 Top 组合是否赚钱，而是看它是否在同一期间、同一资产池、扣除成本后，稳定优于 `SPY` 和 `Equal Weight`，并且 Sharpe / MaxDD 没有明显恶化。基于当前结果，最佳策略是 `mom_126_Top5`，但是否足够进入下一阶段，需要优先看它相对 Equal Weight 的显著性和回撤改善。

## 11. Data Warnings

- 无数据 warning。

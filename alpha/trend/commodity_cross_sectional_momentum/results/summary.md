# Commodity-Only Cross-Sectional Momentum Summary

## 1. 研究问题

Commodity ETF 内部是否存在稳定的 Cross-Sectional Momentum Alpha，并且是否比 Equity ETF Universe 更强、更稳定？

本研究只验证预先固定的 `mom_126/mom_168` 与 `Top1/Top3`，不继续搜索参数。

## 2. Universe And Sample

- Commodity ETFs: 14
- Earliest Start Date: `2004-11-18`
- Common Start Date: `2011-09-19`
- Common End Date: `2025-12-31`
- Strategy sample after 168-day lookback: `2012-06-01` to `2025-12-31`
- Monthly rebalance; month-end ranking; next trading day execution
- Equal Weight; transaction cost 5 bps

## 3. Commodity Strategy Results

| momentum_window | strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover | Number of Rebalances |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mom_126 | Top1 | -0.96% | 0.15 | -67.55% | 36.31% | -0.01 | -12.82% | 14400.00% | 163 |
| mom_126 | Top3 | 7.34% | 0.42 | -54.61% | 22.82% | 0.13 | 158.78% | 10520.60% | 163 |
| mom_168 | Top1 | -10.82% | -0.13 | -90.20% | 37.62% | -0.12 | -79.98% | 15700.00% | 163 |
| mom_168 | Top3 | 2.53% | 0.21 | -60.52% | 23.52% | 0.04 | 34.42% | 10118.21% | 163 |

## 4. Benchmarks

| strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Benchmark_CommodityEqualWeight | 0.37% | 0.10 | -61.57% | 15.45% | 0.01 | 3.80% | 744.04% |
| Benchmark_SPY | 15.14% | 0.91 | -33.72% | 16.80% | 0.45 | 561.20% | 0.00% |
| Benchmark_QQQ | 19.67% | 0.96 | -35.12% | 20.67% | 0.56 | 1016.16% | 0.00% |

## 5. Benchmark Comparison

| strategy_label | benchmark | monthly_observations | avg_monthly_excess | annualized_excess | win_rate_vs_benchmark | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mom_126_Top1 | Benchmark_CommodityEqualWeight | 163 | 0.33% | 4.09% | 53.37% | 0.45 | 0.65 |
| mom_126_Top1 | Benchmark_SPY | 163 | -0.80% | -9.22% | 46.01% | -1.01 | 0.31 |
| mom_126_Top1 | Benchmark_QQQ | 163 | -1.17% | -13.14% | 44.79% | -1.42 | 0.16 |
| mom_126_Top3 | Benchmark_CommodityEqualWeight | 163 | 0.67% | 8.35% | 55.83% | 1.83 | 0.07 |
| mom_126_Top3 | Benchmark_SPY | 163 | -0.47% | -5.46% | 42.33% | -0.95 | 0.35 |
| mom_126_Top3 | Benchmark_QQQ | 163 | -0.83% | -9.53% | 44.79% | -1.51 | 0.13 |
| mom_168_Top1 | Benchmark_CommodityEqualWeight | 163 | -0.65% | -7.49% | 48.47% | -0.98 | 0.33 |
| mom_168_Top1 | Benchmark_SPY | 163 | -1.78% | -19.42% | 44.17% | -2.35 | 0.02 |
| mom_168_Top1 | Benchmark_QQQ | 163 | -2.15% | -22.94% | 43.56% | -2.67 | 0.01 |
| mom_168_Top3 | Benchmark_CommodityEqualWeight | 163 | 0.27% | 3.31% | 49.08% | 0.72 | 0.47 |
| mom_168_Top3 | Benchmark_SPY | 163 | -0.87% | -9.90% | 43.56% | -1.62 | 0.11 |
| mom_168_Top3 | Benchmark_QQQ | 163 | -1.23% | -13.79% | 41.10% | -2.07 | 0.04 |

- Commodity Equal Weight: 3/4 个固定规格的平均月度超额为正，方向不完全一致，但没有规格在 5% 水平显著。
- 按最终复合收益计算，只有 2/4 个规格的 CAGR 高于 Commodity Equal Weight。算术月度超额为正不保证复合财富更高。
- Commodity 策略平均 Sharpe 为 0.17，SPY/QQQ 分别为 0.91/0.96。

## 6. Top1 vs Top3

| strategy | avg_CAGR | avg_Sharpe | avg_MaxDD |
| --- | --- | --- | --- |
| Top3 | 4.93% | 0.32 | -57.56% |
| Top1 | -5.89% | 0.01 | -78.87% |

按两个固定 window 的平均 Sharpe，`Top3` 更好。Top1 集中度更高，应同时检查其回撤和换手。

## 7. 126 vs 168

| momentum_window | avg_CAGR | avg_Sharpe | avg_MaxDD |
| --- | --- | --- | --- |
| mom_126 | 3.19% | 0.29 | -61.08% |
| mom_168 | -4.15% | 0.04 | -75.36% |

按 Top1/Top3 的平均 Sharpe，`mom_126` 更好。重点是两个 window 的 Alpha 方向是否一致，不是挑选单点最优。

## 8. Commodity vs Equity: Matched Top3 Comparison

为了公平比较，只比较双方共有的 `Top3 × mom_126/mom_168`，并使用完全相同的 `2016-07-01` 至 `2025-12-31` 样本。

| strategy_label | commodity_CAGR | equity_CAGR | difference_CAGR | commodity_Sharpe | equity_Sharpe | difference_Sharpe | commodity_MaxDD | equity_MaxDD | difference_MaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mom_126_Top3 | 14.30% | 9.74% | 4.56% | 0.67 | 0.58 | 0.09 | -30.86% | -29.92% | -0.94% |
| mom_168_Top3 | 8.15% | 14.09% | -5.94% | 0.44 | 0.78 | -0.33 | -53.35% | -30.20% | -23.14% |

### Stability

| universe | avg_CAGR | std_CAGR | min_CAGR | avg_Sharpe | std_Sharpe | min_Sharpe | avg_MaxDD | worst_MaxDD | avg_monthly_excess_vs_equal_weight | positive_excess_count | significant_positive_excess_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Commodity | 11.23% | 3.08% | 8.15% | 0.55 | 0.11 | 0.44 | -42.10% | -53.35% | 0.66% | 2 | 0 |
| Equity | 11.92% | 2.18% | 9.74% | 0.68 | 0.10 | 0.58 | -30.06% | -30.20% | -0.02% | 1 | 0 |

- Commodity 强度是否高于 Equity: 否。
- Commodity 稳定性是否高于 Equity: 否。
- 强度要求平均 Sharpe 与相对各自 Equal Weight 的平均月度超额同时更高。
- 稳定性要求两个 window 的 Sharpe 离散度更低，且最差 Sharpe 更高。

## 9. Asset Selection Analysis

| momentum_window | strategy | symbol | category | Average Rank | Selection Count | Selection Percentage |
| --- | --- | --- | --- | --- | --- | --- |
| mom_126 | Top1 | PALL | PreciousMetal | 6.63 | 37 | 22.70% |
| mom_126 | Top1 | XOP | Energy | 6.94 | 25 | 15.34% |
| mom_126 | Top1 | SLV | PreciousMetal | 7.10 | 23 | 14.11% |
| mom_126 | Top1 | UNG | Energy | 9.24 | 23 | 14.11% |
| mom_126 | Top1 | GLD | PreciousMetal | 6.26 | 16 | 9.82% |
| mom_126 | Top1 | CORN | Agriculture | 8.18 | 8 | 4.91% |
| mom_126 | Top1 | PPLT | PreciousMetal | 7.58 | 8 | 4.91% |
| mom_126 | Top1 | USO | Energy | 7.57 | 7 | 4.29% |
| mom_126 | Top3 | GLD | PreciousMetal | 6.26 | 67 | 41.10% |
| mom_126 | Top3 | PALL | PreciousMetal | 6.63 | 62 | 38.04% |
| mom_126 | Top3 | XOP | Energy | 6.94 | 51 | 31.29% |
| mom_126 | Top3 | SLV | PreciousMetal | 7.10 | 50 | 30.67% |
| mom_126 | Top3 | USO | Energy | 7.57 | 47 | 28.83% |
| mom_126 | Top3 | UNG | Energy | 9.24 | 39 | 23.93% |
| mom_126 | Top3 | DBO | Energy | 7.37 | 35 | 21.47% |
| mom_126 | Top3 | PPLT | PreciousMetal | 7.58 | 33 | 20.25% |
| mom_168 | Top1 | PALL | PreciousMetal | 6.55 | 37 | 22.70% |
| mom_168 | Top1 | UNG | Energy | 9.36 | 24 | 14.72% |
| mom_168 | Top1 | XOP | Energy | 6.87 | 23 | 14.11% |
| mom_168 | Top1 | SLV | PreciousMetal | 7.01 | 22 | 13.50% |
| mom_168 | Top1 | GLD | PreciousMetal | 6.10 | 13 | 7.98% |
| mom_168 | Top1 | DBO | Energy | 7.55 | 10 | 6.13% |
| mom_168 | Top1 | PPLT | PreciousMetal | 7.56 | 8 | 4.91% |
| mom_168 | Top1 | SOYB | Agriculture | 7.19 | 7 | 4.29% |
| mom_168 | Top3 | GLD | PreciousMetal | 6.10 | 70 | 42.94% |
| mom_168 | Top3 | XOP | Energy | 6.87 | 63 | 38.65% |
| mom_168 | Top3 | PALL | PreciousMetal | 6.55 | 62 | 38.04% |
| mom_168 | Top3 | SLV | PreciousMetal | 7.01 | 49 | 30.06% |
| mom_168 | Top3 | USO | Energy | 7.76 | 41 | 25.15% |
| mom_168 | Top3 | UNG | Energy | 9.36 | 38 | 23.31% |
| mom_168 | Top3 | DBO | Energy | 7.55 | 36 | 22.09% |
| mom_168 | Top3 | DBA | Agriculture | 6.79 | 30 | 18.40% |

完整结果见 `asset_selection_summary.csv`。

## 10. 最终结论

Commodity ETF 内部 Momentum Alpha 的方向性证据为：3/4 个固定规格的平均月度超额为正，方向不完全一致，但没有规格在 5% 水平显著。

从可投资的复合结果看，证据更弱：只有 2/4 个规格的 CAGR 高于 Commodity Equal Weight，Top1 的高波动和严重回撤造成明显复利损耗。因此不支持“Commodity 内部存在稳定、可直接组合化的 Momentum Alpha”。

在同期、同 window、同 Top3 规则下，Commodity 相对 Equity 的强度判断为 `not stronger`，稳定性判断为 `not more stable`。Commodity 策略平均 Sharpe 为 0.17，SPY/QQQ 分别为 0.91/0.96。

Commodity Top3 相对自身 Equal Weight 的月度超额比 Equity Top3 更明显，但这一选择效应被更高波动、更深回撤和更低 Sharpe 抵消，不足以得出 Commodity Universe 更适合构建策略的结论。

是否更适合构建策略，不只取决于绝对收益；还必须同时满足相对 Commodity Equal Weight 的超额方向一致、风险调整收益足够高，以及结果不被个别 Commodity ETF 反复主导。

## 11. 注意事项

- `XOP` 是能源股 ETF，而非商品期货 ETF；它按当前数据 Universe 要求保留。
- 多个农产品和能源 ETF 存在期货展期损益，Momentum 结果包含期限结构效应。
- 月度 t-test 未解决市场状态依赖和多重比较问题。
- 本实验没有搜索其他 window、Top N 或调仓频率。

## 12. Data Warnings

- 无数据 warning。

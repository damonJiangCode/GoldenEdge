# Equity-Only Cross-Sectional Momentum Summary

## 1. 研究问题

Momentum Alpha 在股票 ETF 内部是否比 Mixed Asset Universe 更强、更稳定、更适合构建策略组合？

本研究只验证固定的 `mom_126/mom_168` 与 `Top3/Top5`，不继续搜索参数。

## 2. 实验设计

- Equity universe: 自动读取 `alpha/data/equity/` 下全部 24 只 ETF
- Common sample: `2016-07-01` to `2025-12-31`
- Rebalance: 月末排名，下一交易日开始持仓
- Weighting: Equal Weight
- Transaction cost: 5 bps applied to turnover
- Momentum windows: `126`, `168`
- Portfolios: `Top3`, `Top5`
- Benchmarks: SPY Buy & Hold, Equity Universe monthly Equal Weight
- Mixed Asset 对照在同一期间用相同 window、Top N、权重、调仓与成本重新计算

## 3. Equity-Only Results

| momentum_window | strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover | Number of Rebalances |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mom_126 | Top3 | 9.74% | 0.58 | -29.92% | 19.39% | 0.33 | 142.20% | 9534.95% | 114 |
| mom_126 | Top5 | 12.06% | 0.72 | -30.35% | 18.16% | 0.40 | 195.18% | 7168.65% | 114 |
| mom_168 | Top3 | 14.09% | 0.78 | -30.20% | 19.46% | 0.47 | 249.25% | 7926.24% | 114 |
| mom_168 | Top5 | 13.92% | 0.80 | -32.11% | 18.57% | 0.43 | 244.46% | 6559.26% | 114 |

## 4. Benchmarks

| strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Benchmark_SPY | 15.07% | 0.87 | -33.72% | 18.10% | 0.45 | 280.14% | 0.00% |
| Benchmark_EqualWeightEquity | 12.28% | 0.76 | -35.70% | 17.25% | 0.34 | 201.27% | 225.64% |

## 5. Benchmark Comparison

| strategy_label | benchmark | monthly_observations | avg_monthly_excess | annualized_excess | win_rate_vs_benchmark | t_statistic | p_value |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mom_126_Top3 | Benchmark_SPY | 114 | -0.39% | -4.63% | 41.23% | -1.84 | 0.07 |
| mom_126_Top3 | Benchmark_EqualWeightEquity | 114 | -0.18% | -2.17% | 42.11% | -0.83 | 0.41 |
| mom_126_Top5 | Benchmark_SPY | 114 | -0.23% | -2.71% | 44.74% | -1.32 | 0.19 |
| mom_126_Top5 | Benchmark_EqualWeightEquity | 114 | -0.02% | -0.20% | 45.61% | -0.09 | 0.93 |
| mom_168_Top3 | Benchmark_SPY | 114 | -0.07% | -0.85% | 45.61% | -0.32 | 0.75 |
| mom_168_Top3 | Benchmark_EqualWeightEquity | 114 | 0.14% | 1.71% | 48.25% | 0.64 | 0.52 |
| mom_168_Top5 | Benchmark_SPY | 114 | -0.09% | -1.11% | 50.88% | -0.52 | 0.60 |
| mom_168_Top5 | Benchmark_EqualWeightEquity | 114 | 0.12% | 1.43% | 51.75% | 0.67 | 0.51 |

- 显著优于 Equity Equal Weight: 0 / 4。
- 显著优于 SPY: 0 / 4。
- 2/4 个策略的 CAGR 更高，4/4 个策略的 MaxDD 更低，改善更多来自更低回撤。

## 6. Top3 vs Top5

| strategy | avg_CAGR | avg_Sharpe | avg_MaxDD |
| --- | --- | --- | --- |
| Top5 | 12.99% | 0.76 | -31.23% |
| Top3 | 11.92% | 0.68 | -30.06% |

按两个固定 window 的平均 Sharpe，`Top5` 更好。这里只是固定规格比较，不用于继续扩大参数搜索。

## 7. 126 vs 168

| momentum_window | avg_CAGR | avg_Sharpe | avg_MaxDD |
| --- | --- | --- | --- |
| mom_168 | 14.00% | 0.79 | -31.16% |
| mom_126 | 10.90% | 0.65 | -30.13% |

按 Top3/Top5 的平均 Sharpe，`mom_168` 更好。重点仍是两个邻近窗口的方向是否一致，而不是挑选单点最优。

## 8. Equity vs Mixed Asset: Matched Sample

| strategy_label | equity_CAGR | mixed_CAGR | difference_CAGR | equity_Sharpe | mixed_Sharpe | difference_Sharpe | equity_MaxDD | mixed_MaxDD | difference_MaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mom_126_Top3 | 9.74% | 11.46% | -1.72% | 0.58 | 0.77 | -0.19 | -29.92% | -28.13% | -1.79% |
| mom_126_Top5 | 12.06% | 10.76% | 1.30% | 0.72 | 0.87 | -0.15 | -30.35% | -23.09% | -7.26% |
| mom_168_Top3 | 14.09% | 10.69% | 3.40% | 0.78 | 0.72 | 0.05 | -30.20% | -29.99% | -0.21% |
| mom_168_Top5 | 13.92% | 11.50% | 2.42% | 0.80 | 0.92 | -0.13 | -32.11% | -20.08% | -12.03% |

### Universe Stability

| universe | avg_CAGR | std_CAGR | min_CAGR | avg_Sharpe | std_Sharpe | min_Sharpe | avg_MaxDD | worst_MaxDD | avg_monthly_excess_vs_equal_weight | positive_excess_count | significant_positive_excess_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Equity | 12.45% | 1.76% | 9.74% | 0.72 | 0.08 | 0.58 | -30.65% | -32.11% | 0.02% | 2 | 0 |
| Mixed | 11.10% | 0.38% | 10.69% | 0.82 | 0.08 | 0.72 | -25.32% | -29.99% | 0.26% | 4 | 0 |

- 强度判断：Equity-only 没有同时表现出更高平均 Sharpe 和更高等权基准超额。
- 稳定性判断：Equity-only 没有同时表现出更低 Sharpe 离散度和更高最差 Sharpe。
- “更强”要求平均 Sharpe 与相对各自 Equal Weight 的平均月度超额同时更高。
- “更稳定”要求四个固定规格的 Sharpe 离散度更低，同时最差 Sharpe 更高。

## 9. Asset Selection Analysis

各策略最常入选的 ETF：

| momentum_window | strategy | symbol | category | Average Rank | Selection Count | Selection Percentage |
| --- | --- | --- | --- | --- | --- | --- |
| mom_126 | Top3 | XLK | Sector | 7.58 | 47 | 41.23% |
| mom_126 | Top3 | QQQ | Core | 8.89 | 33 | 28.95% |
| mom_126 | Top3 | XLF | Sector | 11.07 | 30 | 26.32% |
| mom_126 | Top3 | XLE | Sector | 14.82 | 29 | 25.44% |
| mom_126 | Top3 | XLU | Sector | 13.29 | 24 | 21.05% |
| mom_126 | Top3 | MTUM | StyleFactor | 10.77 | 22 | 19.30% |
| mom_126 | Top3 | IWF | StyleFactor | 9.13 | 19 | 16.67% |
| mom_126 | Top3 | IWM | Core | 13.91 | 16 | 14.04% |
| mom_126 | Top5 | XLK | Sector | 7.58 | 61 | 53.51% |
| mom_126 | Top5 | QQQ | Core | 8.89 | 52 | 45.61% |
| mom_126 | Top5 | IWF | StyleFactor | 9.13 | 42 | 36.84% |
| mom_126 | Top5 | XLF | Sector | 11.07 | 38 | 33.33% |
| mom_126 | Top5 | MTUM | StyleFactor | 10.77 | 37 | 32.46% |
| mom_126 | Top5 | XLE | Sector | 14.82 | 31 | 27.19% |
| mom_126 | Top5 | XLU | Sector | 13.29 | 31 | 27.19% |
| mom_126 | Top5 | EEM | Core | 14.32 | 27 | 23.68% |
| mom_168 | Top3 | XLK | Sector | 7.14 | 47 | 41.23% |
| mom_168 | Top3 | QQQ | Core | 8.56 | 37 | 32.46% |
| mom_168 | Top3 | XLF | Sector | 10.86 | 33 | 28.95% |
| mom_168 | Top3 | XLU | Sector | 13.18 | 30 | 26.32% |
| mom_168 | Top3 | XLE | Sector | 14.97 | 27 | 23.68% |
| mom_168 | Top3 | IWF | StyleFactor | 8.79 | 26 | 22.81% |
| mom_168 | Top3 | MTUM | StyleFactor | 10.32 | 24 | 21.05% |
| mom_168 | Top3 | IWM | Core | 14.63 | 15 | 13.16% |
| mom_168 | Top5 | XLK | Sector | 7.14 | 68 | 59.65% |
| mom_168 | Top5 | QQQ | Core | 8.56 | 51 | 44.74% |
| mom_168 | Top5 | IWF | StyleFactor | 8.79 | 50 | 43.86% |
| mom_168 | Top5 | XLF | Sector | 10.86 | 41 | 35.96% |
| mom_168 | Top5 | MTUM | StyleFactor | 10.32 | 38 | 33.33% |
| mom_168 | Top5 | XLU | Sector | 13.18 | 35 | 30.70% |
| mom_168 | Top5 | XLE | Sector | 14.97 | 30 | 26.32% |
| mom_168 | Top5 | XLY | Sector | 12.34 | 27 | 23.68% |

完整结果见 `asset_selection_summary.csv`。

## 10. 最终结论

在 `2016-07-01` 至 `2025-12-31` 的公平配对样本中，Equity-only Momentum 相比 Mixed Asset Momentum：强度上没有同时表现出更高平均 Sharpe 和更高等权基准超额，稳定性上没有同时表现出更低 Sharpe 离散度和更高最差 Sharpe。

Equity ETF 内部的证据也不足以确认稳定 Momentum Alpha：`mom_126` 的 Top3/Top5 相对 Equity Equal Weight 均为负超额，`mom_168` 的两个组合虽为正超额，但 p-value 均高于 0.50。这个 Alpha 没有在两个预先固定的中期窗口上保持方向一致。

这个判断区分了三件事：策略绝对收益为正、策略优于自身等权 Universe、以及超额收益达到统计显著。只有后两项才能支持 Universe 内部的横截面 Momentum Alpha；短样本和 ETF 高度重叠仍限制结论强度。

## 11. 注意事项

- 共同样本由历史最短的 Equity ETF 决定，明显短于原 Mixed Asset 全样本研究。
- SPY、VTI、QQQ、IWF、XLK 等持仓暴露高度重叠，24 个 ETF 不等于 24 个独立股票风险来源。
- 月度 t-test 未解决市场状态依赖和多重比较问题，应视为研究证据而不是最终投资确认。
- 本实验没有搜索其他 momentum window、Top N 或调仓频率。

## 12. Data Warnings

- 无数据 warning。

# Cross-Sectional Momentum Window Robustness Test

## 1. 研究目标

本实验不寻找新的最佳 momentum window。唯一目标是判断：Top5 横截面 Momentum Alpha 是否在一段邻近参数区间内稳定存在，还是主要来自 126 日这个孤立峰值。

## 2. 固定实验条件

- Universe: 当前 12 ETF
- Common sample: `2008-02-01` to `2025-12-31`
- Rebalance: Monthly，月末排名，下一交易日开始持仓
- Portfolio: Top5, Equal Weight
- Transaction cost: 5 bps applied to turnover
- Benchmarks: SPY Buy & Hold, Equal Weight All Assets monthly rebalance
- 唯一变化参数: momentum window = `42, 63, 84, 105, 126, 147, 168, 189, 210, 252` trading days
- 所有 window 使用完全相同的回测起止日期

## 3. Robustness Score

对每个 window，计算其 Sharpe 与左右直接相邻测试 window 的平均绝对差：

`Robustness Score = 100 × max(0, 1 - neighbor_sharpe_MAE / 0.20)`

分数越高，表示该 window 与邻近参数的 Sharpe 越接近。该分数只衡量局部平滑度，不衡量收益高低，也不用于挑选最佳参数。

## 4. Window Results

| momentum_window | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover | Robustness Score |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 9.21% | 0.74 | -27.87% | 13.02% | 0.33 | 382.76% | 16195.97% | 31.84 |
| 63 | 7.40% | 0.60 | -29.41% | 13.23% | 0.25 | 257.79% | 13358.87% | 60.07 |
| 84 | 7.66% | 0.63 | -28.74% | 13.02% | 0.27 | 271.07% | 12431.09% | 71.72 |
| 105 | 8.95% | 0.72 | -21.77% | 13.08% | 0.41 | 360.31% | 10311.07% | 54.12 |
| 126 | 10.36% | 0.81 | -29.06% | 13.16% | 0.36 | 478.69% | 9318.20% | 60.06 |
| 147 | 9.37% | 0.75 | -31.47% | 13.11% | 0.30 | 392.64% | 8418.26% | 77.82 |
| 168 | 8.98% | 0.72 | -30.06% | 13.01% | 0.30 | 362.27% | 8039.68% | 89.77 |
| 189 | 8.66% | 0.70 | -26.70% | 12.90% | 0.32 | 338.06% | 8095.78% | 82.53 |
| 210 | 9.32% | 0.76 | -26.81% | 12.80% | 0.35 | 388.15% | 7349.57% | 65.76 |
| 252 | 8.44% | 0.67 | -28.77% | 13.33% | 0.29 | 322.61% | 6952.29% | 57.39 |

## 5. Stable Plateau Test

平台区预先定义为至少 3 个连续 window，并同时满足：Sharpe 极差不超过 0.15、CAGR 极差不超过 2%、MaxDD 极差不超过 10%。

识别到 `105-252` 交易日的平台区，共 7 个连续 window。区间内 CAGR 为 8.44%-10.36%，Sharpe 为 0.67-0.81，MaxDD 为 -31.47%--21.77%。

没有 window 的 Sharpe 同时比左右相邻 window 高出 0.15，未发现孤立尖峰。

对原参数的局部检查：126 日 Sharpe 为 0.81；105/147 日 Sharpe 分别为 0.72/0.75，其 Robustness Score 为 60.06。

## 6. Window Length And Risk/Return

- 窗口每增加 21 个交易日，CAGR 线性趋势约上升 0.05%，但该趋势不具有统计显著性（p=0.584）。
- 窗口每增加 21 个交易日，Sharpe 线性趋势约上升 0.00，但该趋势不具有统计显著性（p=0.591）。
- 窗口每增加 21 个交易日，MaxDD 线性趋势约下降 0.05%，但该趋势不具有统计显著性（p=0.879）。
- 窗口每增加 21 个交易日，Turnover 线性趋势约下降 870.34 个百分点，但该趋势具有统计显著性（p=0.000）。

这些线性趋势只用于描述方向，不代表窗口长度与绩效之间存在稳定因果关系。

## 7. Benchmark Context

| strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Benchmark_SPY | 11.32% | 0.64 | -51.48% | 19.94% | 0.22 | 593.26% | 0.00% |
| Benchmark_EqualWeight | 5.95% | 0.59 | -31.37% | 10.72% | 0.19 | 182.15% | 715.45% |

- 月度平均超额收益为正的 window：相对 SPY 为 0/10，相对 Equal Weight 为 10/10。
- 正超额且 p-value < 0.05 的 window：相对 SPY 为 0/10，相对 Equal Weight 为 1/10。
- Benchmark 检验用于提供经济意义背景；平台判断本身不以某一个显著性结果作为参数筛选条件。

## 8. 最终结论

Top5 策略的风险收益形态在一段连续参数区间内稳定存在，126 日不是孤立尖峰。但严格的 benchmark-relative Alpha 只得到部分支持：相对 Equal Weight 的经济超额在所有 window 上方向一致，统计显著性却没有形成平台；相对 SPY 则没有稳定超额收益。

在不选择单点最优参数的前提下，`105-252` 交易日是当前样本中的稳定风险收益平衡区间。

这项结论只说明参数邻域稳定性。它不能替代 out-of-sample、walk-forward、资产池敏感性和更高交易成本测试。

## 9. Data Warnings

- 无数据 warning。

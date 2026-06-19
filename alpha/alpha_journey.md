# Alpha Journey

## 2026-06-16

### 假设

200MA 长期趋势过滤可能在 ETF 上降低回撤、提高风险调整后收益。

### 实验

- 标的：`SPY`, `QQQ`, `GLD`, `TLT`
- 数据：日线 `Adj Close`
- 规则：`Adj Close > MA200` 下一交易日持有，否则空仓
- 不做空，不加杠杆
- 交易成本：每次换仓 5 bps
- 信号延迟 1 天，避免未来函数

### 结果

| Asset | 200MA CAGR | BuyHold CAGR | 200MA Sharpe | BuyHold Sharpe | 200MA MaxDD | BuyHold MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 8.16% | 10.87% | 0.74 | 0.64 | -21.54% | -55.19% |
| QQQ | 11.91% | 15.56% | 0.82 | 0.78 | -27.12% | -53.40% |
| GLD | 7.45% | 10.80% | 0.55 | 0.66 | -35.06% | -45.56% |
| TLT | -0.06% | 3.14% | 0.05 | 0.28 | -47.33% | -48.35% |

### 结论

200MA 对 `SPY/QQQ` 有明显风控价值：回撤大幅下降，Sharpe 略升，但 CAGR 下降。对 `GLD/TLT` 不理想。它更像风险控制工具，不是独立收益 Alpha。

## 2026-06-16

### 假设

如果 200MA 风控思想真实存在，它应该对参数、交易成本、空仓处理方式有一定鲁棒性。

### 实验

- 参数：MA `50/100/150/200/250/300`
- 成本：`0/2/5/10/20/50 bps`
- 空仓替代：`SHY`
- 标的：`SPY`, `QQQ`, `GLD`, `TLT`

### 结果

- `SPY`：多数参数/成本组合通过。
- `QQQ`：部分参数/成本组合通过。
- `GLD/TLT`：整体不通过。
- 空仓持有 `SHY` 会改善 CAGR，但不改变主要结论。

### 结论

200MA 的有效方向仍然是股票 ETF 风控，尤其是 `SPY`。不能证明它是稳定收益增强 Alpha。

## 2026-06-16

### 假设

200MA 风控效果可能也存在于其他股票 ETF。

### 实验

- 标的：`IWM`, `EFA`, `EEF`
- 规则：MA200 vs Buy-and-Hold
- 空仓收益：0
- 交易成本：5 bps

### 结果

| Asset | 200MA CAGR | BuyHold CAGR | 200MA Sharpe | BuyHold Sharpe | 200MA MaxDD | BuyHold MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| IWM | 5.07% | 8.78% | 0.41 | 0.47 | -28.21% | -58.64% |
| EFA | 4.31% | 6.24% | 0.40 | 0.39 | -28.80% | -61.04% |
| EEF | 0.89% | 79.20% | 0.19 | 1.50 | -23.23% | -23.19% |

### 结论

`EFA` 有类似风控价值。`IWM` 虽降低回撤，但 Sharpe/CAGR 变差。`EEF` 样本太短，忽略。

## 2026-06-16

### 假设

创 52 周新高后，未来收益可能高于普通时期，即：

`E(Return | NewHigh) > E(Return | NotNewHigh)`

### 实验

- 标的：`SPY`, `QQQ`
- 数据：日线 `Adj Close`
- NewHigh：创 252 日新高
- 未来收益：`20d/60d/120d`
- 比较：`NewHigh` vs `NotNewHigh` vs `AllDays`

### 结果

SPY:

| Horizon | NewHigh Mean | NotNewHigh Mean | AllDays Mean |
|---:|---:|---:|---:|
| 20d | 0.35% | 1.05% | 0.95% |
| 60d | 1.62% | 2.98% | 2.78% |
| 120d | 4.65% | 5.84% | 5.66% |

QQQ:

| Horizon | NewHigh Mean | NotNewHigh Mean | AllDays Mean |
|---:|---:|---:|---:|
| 20d | 0.63% | 1.44% | 1.33% |
| 60d | 2.19% | 4.24% | 3.96% |
| 120d | 6.70% | 8.28% | 8.05% |

### 结论

52 周新高后没有表现出更高未来收益。简单“创 52 周新高后买入”的趋势 Alpha 不成立。

## 2026-06-16

### 假设

52 周新高实验结果反直觉，可能来自定义错误、未来函数、样本重叠或事件定义不合理。

### 实验

- 检查未来函数
- 使用严格定义：`close > rolling_max(close.shift(1), 252)`
- 测试首次突破 52 周新高
- 测试非重叠事件
- 补充 t-test 和 event study

### 结果

- 没有未来函数。
- 原始定义偏宽，但不是主要问题。
- 连续创新高导致样本重叠。
- 严格 NewHigh 和 FirstBreakout 仍然跑输 NotNewHigh。
- 去重后显著性下降，但结果没有反转。

### 结论

负结果不是代码错误导致。该实验测的是“新高事件后的条件收益”，不是完整趋势交易策略。若继续研究，需要做明确 entry/exit 的 event-study/backtest。

## 2026-06-16

### 假设

创 52 周新高后可能不是趋势延续，而是存在均值回归。

### 实验

- 标的：`SPY`, `QQQ`
- 严格事件：`close > rolling_max(close.shift(1), 252)`
- 未来收益：`20d/60d/120d`
- 比较：`NewHigh` vs `NotNewHigh`
- 如果支持反转，再测试 NewHigh 后做空 `20d/60d/120d`

### 结果

| Asset | Horizon | NewHigh Mean | NotNewHigh Mean | NewHigh WinRate |
|---|---:|---:|---:|---:|
| SPY | 20d | 0.34% | 1.05% | 65.06% |
| SPY | 60d | 1.62% | 2.98% | 73.77% |
| SPY | 120d | 4.63% | 5.84% | 77.69% |
| QQQ | 20d | 0.63% | 1.44% | 63.96% |
| QQQ | 60d | 2.19% | 4.24% | 67.24% |
| QQQ | 120d | 6.69% | 8.28% | 83.98% |

做空 NewHigh:

| Asset | Horizon | Short Mean | Short Median | Short WinRate |
|---|---:|---:|---:|---:|
| SPY | 20d | -0.34% | -1.07% | 34.94% |
| SPY | 60d | -1.62% | -2.96% | 26.23% |
| SPY | 120d | -4.63% | -5.72% | 22.31% |
| QQQ | 20d | -0.63% | -1.33% | 36.04% |
| QQQ | 60d | -2.19% | -2.97% | 32.76% |
| QQQ | 120d | -6.69% | -7.97% | 16.02% |

### 结论

NewHigh 后收益低于 NotNewHigh，但仍然是正收益、高胜率。  
这不是可做空的均值回归 Alpha。分类：`C. 趋势延续和均值回归都不明显`。

## 2026-06-17

### 假设

MA200 趋势过滤在股票、商品和债券 ETF 上是否具有一致的风险收益改善效果。

### 实验

- 资产池：12 只 ETF，覆盖 Equity、Commodity、Bond
- 价格：日线 `Adj Close`
- 规则：价格高于 MA200 时持有，信号延迟 1 天
- 仓位：`100%` 或 `0%`，不做空、不加杠杆
- 成本：每次仓位变化 5 bps

### 结果

- 12/12 资产的 MaxDD 都有改善。
- 5/12 资产的 Sharpe 提高，3/12 资产的 CAGR 提高。
- Equity 平均 MaxDD 改善 36.47%，但 CAGR 平均下降 1.46%。
- Commodity 平均 CAGR 提高 0.98%，MaxDD 改善 17.95%。
- Bond 的 CAGR 和 Sharpe 平均都变差。

### 结论

MA200 在跨资产样本上再次表现为风险过滤器，而不是稳定的收益 Alpha。它值得作为组合层的风险开关继续测试，但不应单独作为收益来源。

## 2026-06-17

### 假设

资产首次突破过去 52 周最高收盘价后，中长期未来收益可能高于随机时期。

### 实验

- 资产池：12 只 ETF
- 事件：`Adj Close > Adj Close.shift(1).rolling(252).max()` 的首次突破
- 未来收益：`FR20`, `FR60`, `FR120`
- 对照组：从非事件日中进行 1000 次等样本 bootstrap
- 统计：双侧经验 p-value 和 Cohen's d

### 结果

| Horizon | Event Mean | Random Mean | Difference | p-value | Cohen's d |
|---|---:|---:|---:|---:|---:|
| FR20 | 0.61% | 0.52% | 0.09% | 0.44 | 0.02 |
| FR60 | 2.02% | 1.55% | 0.47% | 0.02 | 0.05 |
| FR120 | 3.95% | 3.13% | 0.83% | 0.01 | 0.06 |

- Commodity 的突破效果最强，三个 horizon 均显著高于随机对照。
- Equity 没有稳定的突破后超额收益。
- Bond 的 FR120 反而显著弱于随机对照。

### 结论

扩大到跨资产样本并改用首次突破事件后，52 周新高在 `FR60/FR120` 上有统计证据，但效应量很小，且主要由 Commodity 驱动。这修正了早期只看 SPY/QQQ 时的负面判断，但仍不足以直接确认为可交易策略。

## 2026-06-17

### 假设

对单个资产而言，过去收益最强的历史状态，未来收益应高于过去收益最弱的历史状态。

### 实验

- Momentum windows：`63/126/252` 交易日
- Forward horizons：`20/60/120` 交易日
- 每个 symbol 内部按 momentum 分为 Q1 至 Q5
- 核心比较：Top 20% vs Bottom 20%
- 统计：Welch t-test 和 Cohen's d
- 本实验只验证预测能力，不是策略回测

### 结果

- Top 组未来平均收益为正：98/108 个检验组合。
- Top 组高于 Bottom 组：61/108 个检验组合。
- Top > Bottom 且 `p < 0.05`：46/108 个检验组合。
- 总体最强组合是 `mom_63 -> FR120`，Top-Bottom 平均差为 1.29%。
- Equity 最强是 `mom_126 -> FR120`，平均差 2.64%。
- Commodity 最强是 `mom_63 -> FR120`，平均差 2.72%。
- `mom_252` 总体不稳定，在 FR60/FR120 上平均差为负。

### 结论

时间序列分位数检验给出了中等强度的 Momentum Alpha 证据，尤其是 3/6 个月动量对 6/12 个月未来收益的预测。但方向一致性并不完整，效应量偏小，而且重叠 forward return 会带来统计依赖。因此它值得进入组合实验，但还不能单凭这一步宣称可投资。

## 2026-06-17

### 假设

在 12 个资产之间，每月持有过去表现最强的资产，能否把 Momentum Alpha 转化为扣除成本后的组合收益。

### 实验

- 共同样本：`2007-08-01` 至 `2025-12-31`
- 每月最后一个交易日排名，下一交易日开始持仓
- Momentum windows：`mom_63`, `mom_126`
- 组合：`Top1`, `Top3`, `Top5` 等权
- 成本：按仓位变化扣除 5 bps
- 基准：SPY Buy & Hold、12 资产月度等权组合

### 结果

| Strategy | CAGR | Sharpe | MaxDD | Total Return |
|---|---:|---:|---:|---:|
| mom_126 Top5 | 11.36% | 0.88 | -29.06% | 623.86% |
| SPY | 10.76% | 0.61 | -55.19% | 560.12% |
| Equal Weight | 6.44% | 0.64 | -31.37% | 215.95% |

- `mom_126 Top5` 同时是 CAGR 和 Sharpe 最高的动量组合。
- Top5 平均优于 Top3 和 Top1；`mom_126` 平均优于 `mom_63`。
- 6 个策略中，没有一个在月度超额收益上显著优于 SPY。
- `mom_126 Top5` 显著优于 Equal Weight：年化超额约 4.86%，`p = 0.01`。
- 最佳策略相比 SPY 同时有更高 CAGR 和更低回撤，但 CAGR 优势极小且不显著。
- 最常入选的资产是 QQQ（67.87%）、SPY（61.54%）、IWM（50.23%）和 GLD（48.87%）。

### 结论

跨资产横截面动量已经从预测性验证走到了可执行的月度组合原型。`mom_126 Top5` 在扣除成本后明显优于全资产等权基准，并大幅改善 SPY 的回撤；但它没有统计上显著优于 SPY。因此当前答案是“有希望，但尚未完成确认”，应进入样本外和稳健性阶段，而不是继续优化参数。

## 2026-06-17

### 假设

`mom_126 Top5` 的表现应该来自一段稳定的 momentum window 参数区间，而不是 126 日这个孤立尖峰。

### 实验

- 固定：12 ETF、Monthly Rebalance、Top5、Equal Weight、5 bps 成本
- 唯一变量：Momentum window = `42/63/84/105/126/147/168/189/210/252`
- 所有 window 使用共同样本：`2008-02-01` 至 `2025-12-31`
- 平台标准：至少 3 个连续 window，Sharpe 极差不超过 0.15、CAGR 极差不超过 2 个百分点、MaxDD 极差不超过 10 个百分点
- Robustness Score 衡量每个 window 与左右相邻 window 的 Sharpe 接近程度，不用于选取最优参数

### 结果

| Window | CAGR | Sharpe | MaxDD | Robustness Score |
|---:|---:|---:|---:|---:|
| 84 | 7.66% | 0.63 | -28.74% | 71.72 |
| 105 | 8.95% | 0.72 | -21.77% | 54.12 |
| 126 | 10.36% | 0.81 | -29.06% | 60.06 |
| 147 | 9.37% | 0.75 | -31.47% | 77.82 |
| 168 | 8.98% | 0.72 | -30.06% | 89.77 |
| 189 | 8.66% | 0.70 | -26.70% | 82.53 |
| 210 | 9.32% | 0.76 | -26.81% | 65.76 |
| 252 | 8.44% | 0.67 | -28.77% | 57.39 |

- 预设规则识别出 `105-252` 交易日的连续稳定平台。
- 平台内 CAGR 为 8.44%-10.36%，Sharpe 为 0.67-0.81，MaxDD 为 -31.47% 至 -21.77%。
- 没有 window 的 Sharpe 同时比左右相邻 window 高出 0.15，未发现孤立尖峰。
- 随着 window 增大，换手率显著下降；CAGR、Sharpe 和 MaxDD 没有显著线性趋势。
- 相对 Equal Weight，10/10 个 window 的月度平均超额收益为正，但只有 1/10 统计显著。
- 相对 SPY，0/10 个 window 的月度平均超额收益为正。

### 结论

Top5 策略的风险收益形态在 `105-252` 日的连续参数区间内稳定存在，126 日不是孤立尖峰。但严格的 benchmark-relative Alpha 只得到部分支持：相对 Equal Weight 的经济超额方向稳定，显著性不稳定；相对 SPY 没有稳定超额收益。

## 2026-06-18

### 假设

如果横截面 Momentum Alpha 在同类资产内更纯粹，那么在 24 只 Equity ETF 内部排名应该比 Mixed Asset Universe 更强、更稳定。

### 实验

- Universe：自动读取 24 只 Equity ETF
- 固定 window：`mom_126`, `mom_168`
- 组合：`Top3`, `Top5`，月度调仓、等权、5 bps 成本
- 基准：SPY、Equity Equal Weight
- 公平比较：Mixed Asset 在相同 `2016-07-01` 至 `2025-12-31` 样本和相同规则下重新计算

### 结果

| Strategy | CAGR | Sharpe | MaxDD |
|---|---:|---:|---:|
| mom_126 Top3 | 9.74% | 0.58 | -29.92% |
| mom_126 Top5 | 12.06% | 0.72 | -30.35% |
| mom_168 Top3 | 14.09% | 0.78 | -30.20% |
| mom_168 Top5 | 13.92% | 0.80 | -32.11% |

- Top5 平均优于 Top3，`mom_168` 平均优于 `mom_126`。
- 0/4 策略显著优于 Equity Equal Weight，0/4 显著优于 SPY。
- `mom_126` 的 Top3/Top5 相对 Equity Equal Weight 均为负超额；`mom_168` 虽为正超额，但 p-value 均高于 0.50。
- Equity 四个规格平均 Sharpe 为 0.72，低于同期 Mixed 的 0.82。
- Equity 最差 Sharpe 为 0.58，低于 Mixed 的 0.72；平均 MaxDD 也更深。

### 结论

Equity-only Momentum 没有比 Mixed Asset Momentum 更强或更稳定。它的绝对收益不差，但超额收益没有在 126/168 两个固定 window 上保持一致，改善更多来自较低回撤，而不是稳定 Alpha。

## 2026-06-18

### 假设

Commodity ETF 的价格趋势可能比 Equity ETF 更持久，因此 Commodity 内部的横截面 Momentum 可能更明显。

### 实验

- Universe：14 只 Commodity ETF
- 数据共同区间：`2011-09-19` 至 `2025-12-31`
- 策略样本：`2012-06-01` 至 `2025-12-31`
- 固定 window：`mom_126`, `mom_168`
- 组合：`Top1`, `Top3`，月度调仓、等权、5 bps 成本
- 基准：Commodity Equal Weight、SPY、QQQ
- Commodity vs Equity 只比较同期、同 window、同 Top3 规则

### 结果

| Strategy | CAGR | Sharpe | MaxDD |
|---|---:|---:|---:|
| mom_126 Top1 | -0.96% | 0.15 | -67.55% |
| mom_126 Top3 | 7.34% | 0.42 | -54.61% |
| mom_168 Top1 | -10.82% | -0.13 | -90.20% |
| mom_168 Top3 | 2.53% | 0.21 | -60.52% |

- Top3 明显优于 Top1，`mom_126` 优于 `mom_168`。
- 3/4 规格的平均月度超额相对 Commodity Equal Weight 为正，但 0/4 统计显著。
- 只有 2/4 规格的最终 CAGR 高于 Commodity Equal Weight；Top1 存在严重波动拖累和复利损耗。
- Commodity 策略平均 Sharpe 为 0.17，远低于 SPY 的 0.91 和 QQQ 的 0.96。
- 同期 Top3 比较中，Commodity 平均 Sharpe 为 0.55，Equity 为 0.68；Commodity 的回撤和参数离散度都更大。

### 结论

Commodity Top3 相对自身 Equal Weight 有一定选择效应，但被高波动、深回撤和低 Sharpe 抵消。Top1 组合不可用，两个 window 之间也不稳定。因此 Commodity Universe 没有比 Equity 或 Mixed Asset Universe 更适合构建横截面 Momentum 策略。

## 2026-06-18

### 假设

Mixed Asset `mom_126 Top5` 的高 Sharpe 应该来自多个资产的广泛贡献，而不是少数长期赢家撑起全部收益。

### 实验

- 策略：12 ETF Mixed Asset `mom_126 Top5`
- 样本：`2007-08-01` 至 `2025-12-31`
- 资产日度贡献：期初组合净值 × 期初权重 × 资产收益
- 5 bps 成本按各资产绝对调仓额分摊
- 资产贡献之和与组合最终 Total Return 精确对账
- 移除测试：从 Universe 删除前 1/2/3 大贡献资产后，重新排名、建仓和计算成本

### 结果

| Symbol | Selection % | Total Contribution | Contribution % |
|---|---:|---:|---:|
| QQQ | 67.87% | 136.49% | 21.88% |
| GLD | 48.87% | 113.46% | 18.19% |
| SLV | 42.99% | 89.04% | 14.27% |
| SPY | 61.54% | 56.57% | 9.07% |
| EFA | 38.91% | 51.42% | 8.24% |

- 前三大贡献资产是 `QQQ`, `GLD`, `SLV`，合计贡献净收益的 54.34%。
- 所有 12 只 ETF 在全样本中的净贡献都为正。

| Scenario | CAGR | Sharpe | MaxDD |
|---|---:|---:|---:|
| Baseline | 11.36% | 0.88 | -29.06% |
| Remove QQQ | 10.05% | 0.83 | -26.51% |
| Remove QQQ, GLD | 8.40% | 0.75 | -25.72% |
| Remove QQQ, GLD, SLV | 6.26% | 0.65 | -21.07% |

- 移除前三大贡献资产后，策略保留 55.09% CAGR 和 73.56% Sharpe。
- 移除贡献资产后 MaxDD 反而改善，说明主要赢家同时也带来了更高风险。

### 结论

Mixed Asset Momentum 不是由单一 ETF 驱动：移除 QQQ 后 CAGR 和 Sharpe 仍保留 88.45%/94.47%，移除前三大贡献资产后策略仍有 6.26% CAGR 和 0.65 Sharpe。但前三大贡献占 54.34%，说明赢家集中度不可忽略。当前最合理的判断是：收益具有一定 Cross-Asset breadth，同时存在中等程度的核心赢家依赖。

## 2026-06-18

### 假设

Mixed Asset Momentum 的优势可能来自特定资产类别，也可能来自 Equity、Commodity、Bond 在收益与风险上的互补和跨类别轮动。

### 实验

- 基准：12 ETF Mixed Asset `mom_126 Top5`
- 固定月度调仓、等权、5 bps 成本
- 从 Universe 中分别删除全部 Equity、Commodity、Bond
- 删除后重新计算 momentum 排名、Top5 持仓、换手和成本
- `Remove Equity/Commodity/Bond` 分别等价于 `Commodity + Bond` / `Equity + Bond` / `Equity + Commodity`

### 结果

| Scenario | CAGR | Sharpe | MaxDD | CAGR Retention | Sharpe Retention |
|---|---:|---:|---:|---:|---:|
| Baseline | 11.36% | 0.88 | -29.06% | 100.00% | 100.00% |
| Remove Equity | 6.37% | 0.61 | -24.05% | 56.07% | 69.42% |
| Remove Commodity | 8.71% | 0.86 | -24.61% | 76.67% | 97.87% |
| Remove Bond | 9.35% | 0.62 | -47.04% | 82.33% | 70.22% |

| Asset Class | Historical PnL Contribution |
|---|---:|
| Equity | 45.42% |
| Commodity | 42.54% |
| Bond | 12.04% |

- Equity 的历史 PnL 贡献最高，删除后 CAGR 和 Sharpe 损失也最大，是主要收益引擎。
- Commodity 贡献 42.54% 历史 PnL，但删除后仍保留 97.87% Sharpe，且 MaxDD 改善，更像收益增强而非必要的风险调整 Alpha 来源。
- Bond 只贡献 12.04% PnL，但删除后 MaxDD 恶化 17.98 个百分点、波动率上升 3.53 个百分点，是主要风险分散器。
- 完整 Mixed Universe 的 CAGR 和 Sharpe 都高于任何双类别 Universe，支持跨类别轮动有增值。

### 结论

- **Strong Evidence:** Equity 是主要收益引擎；Bond 是主要风险分散器。
- **Moderate Evidence:** Commodity 提供重要收益增强，跨类别排名和轮动提高完整组合的 CAGR/Sharpe。
- **Weak Evidence:** Commodity 是不可替代的风险调整 Alpha 来源。

当前最准确的结构性解释是：`Equity Trend + Commodity Return Enhancement + Bond Diversification + Cross-Class Rotation`。

## 当前总判断

### 已经学到的事

- `MA200`：对降低回撤有高度一致性，但不是稳定的收益 Alpha。
- `52 Week High`：中长期事件效应存在，但很小且集中在 Commodity。
- `Time-Series Momentum Validation`：过去 3/6 个月的强势对未来中长期收益有一定预测力，但跨资产一致性有限。
- `Cross-Sectional Momentum`：Top5 在 `105-252` 日形成稳定参数平台；收益不是由单一 ETF 驱动，但 QQQ/GLD/SLV 合计贡献 54.34%，存在中等赢家集中度。类别归因显示 Equity 负责核心收益、Commodity 增强收益、Bond 提供关键分散，完整 Universe 轮动优于所有双类别组合。
- `Equity-only Momentum`：绝对收益可以，但相对 Equity Equal Weight 的 Alpha 在 126/168 上不一致，强度和稳定性都弱于 Mixed Asset。
- `Commodity-only Momentum`：Top3 有局部选择效应，但高波动、深回撤和低 Sharpe 使其难以组合化，也弱于 Mixed Asset。

### 当前结论

目前最值得继续推进的主线仍是 `Mixed Asset medium-term cross-sectional momentum + Top5 monthly portfolio`。参数邻域和单一资产类别敏感性已经测试：Alpha 并没有在 Equity-only 或 Commodity-only 中变得更强，说明跨资产分散本身可能是组合效果的重要来源。

MA200 更适合作为后续的风险过滤模块，52 周新高则保留为 Commodity 子研究。

下一阶段的目标不是寻找更好的回测参数，而是判断当前结果是否能离开全样本后仍然存活：

1. 固定 Top5 和中期 momentum 规则，做 chronological out-of-sample split，不在样本外重新挑选 window。
2. 使用 rolling/expanding walk-forward 检查不同时期的稳定性。
3. 压力测试更高交易成本，并拆分换手的实际影响。
4. 做市场状态分段，检查 Equity 收益、Commodity 增强和 Bond 分散角色是否在不同 regime 中稳定。
5. 在主策略稳健性确认后，再独立测试 MA200 风险过滤是否增值。

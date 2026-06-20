# Asset Rotation vs Category Rotation Test

## 1. Research Question

在固定 Expanded 45 ETF、`mom_126` 和月度调仓框架下，比较统一资产排名与先控制或轮动资产类别的结构。本实验不优化任何参数。

## 2. Fixed Design

- Sample: `2016-05-02` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps; no MA filter
- Global Top5: 45 ETF 统一排名，Top5 每只 20%
- Category Balanced: Equity Top2、Commodity Top2、Bond Top1，每只 20%
- Category Winner Class Mean / Top3 Mean: 按两种预先指定的类别动量选 Top2 类别，各类别 Top2 ETF，共四个 25% 槽位
- Currency 不强制配置；类别内不足两个 ETF 时缺失槽位保留现金

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 11.34% | 0.89 | -23.09% | 12.87% | 0.49 | 180.25% | 5459.03% |
| Expanded Global Top5 | 7.52% | 0.46 | -39.59% | 20.64% | 0.19 | 101.44% | 9520.29% |
| Category Balanced | 11.77% | 0.77 | -22.43% | 16.11% | 0.52 | 191.73% | 9135.53% |
| Category Winner (Class Mean) | 9.57% | 0.71 | -18.66% | 14.31% | 0.51 | 141.77% | 8778.86% |
| Category Winner (Top3 Mean) | 8.45% | 0.52 | -28.73% | 19.05% | 0.29 | 118.24% | 10010.69% |

## 4. Asset Class Exposure

| Strategy | Equity | Commodity | Bond | Currency | Cash |
| --- | --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 47.28% | 34.82% | 17.89% | 0.00% | -0.00% |
| Expanded Global Top5 | 50.80% | 45.58% | 2.73% | 0.89% | -0.00% |
| Category Balanced | 40.01% | 40.09% | 19.90% | 0.00% | -0.00% |
| Category Winner (Class Mean) | 39.62% | 19.49% | 18.52% | 11.19% | 11.18% |
| Category Winner (Top3 Mean) | 46.51% | 45.78% | 4.66% | 1.53% | 1.52% |

## 5. Selection Statistics

`Average Turnover` 是发生调仓时的平均双边绝对权重变化。

| Strategy | Distinct Assets Selected | Average Holdings | Average Turnover | Number of Rebalances |
| --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 12 | 5.00 | 47.06% | 116 |
| Expanded Global Top5 | 40 | 5.00 | 82.07% | 116 |
| Category Balanced | 39 | 5.00 | 78.75% | 116 |
| Category Winner (Class Mean) | 38 | 3.55 | 75.68% | 116 |
| Category Winner (Top3 Mean) | 38 | 3.94 | 86.30% | 116 |

## 6. Category Contribution

Contribution 使用期初组合财富加权的资产类别毛 PnL，百分比在四类资产之间归一化，不包含交易成本归属。

| Strategy | Asset Class | Total Gross PnL Contribution | Contribution Percent |
| --- | --- | --- | --- |
| Category Balanced | Equity | 0.77 | 38.53% |
| Category Balanced | Commodity | 1.11 | 55.73% |
| Category Balanced | Bond | 0.11 | 5.74% |
| Category Balanced | Currency | 0.00 | 0.00% |
| Category Winner (Class Mean) | Equity | 0.46 | 30.71% |
| Category Winner (Class Mean) | Commodity | 0.96 | 64.67% |
| Category Winner (Class Mean) | Bond | 0.06 | 4.24% |
| Category Winner (Class Mean) | Currency | 0.01 | 0.38% |
| Category Winner (Top3 Mean) | Equity | 0.57 | 45.77% |
| Category Winner (Top3 Mean) | Commodity | 0.63 | 50.12% |
| Category Winner (Top3 Mean) | Bond | 0.06 | 4.57% |
| Category Winner (Top3 Mean) | Currency | -0.01 | -0.46% |

## 7. Interpretation

1. **Category Balanced 是否优于 Expanded Global Top5？** 是。Sharpe 0.77 vs 0.46；MaxDD -22.43% vs -39.59%。
2. **Category Winner 是否优于 Expanded Global Top5？** Class Mean 是，Top3 Mean 是；对应 Sharpe 为 0.71/0.52。
3. **Bond 权重恢复后 MaxDD 是否改善？** Category Balanced 的 Bond 权重增加 17.18%，MaxDD 改善 17.15%。
4. **Expanded 劣化是否主要来自 Bond 被挤出？** 恢复固定 Bond 配置后风险收益显著改善，Bond 被挤出是重要原因；但类别内重复和高波动资产竞争仍会影响结果，不能归因于单一因素。
5. **Alpha 更像来自什么？** Category Balanced 与至少一个 Category Winner 版本都改善 Global Top5，证据更支持资产选择与类别结构共同作用。
6. **最接近 Original 12 的结构？** 按 CAGR、Sharpe、MaxDD 相对 Original 的预设归一化距离，`Category Balanced` 最接近；该距离只用于结构比较，不用于参数优化。

## 8. Final Conclusion

当前核心 Alpha 更接近资产级 Momentum 与资产类别结构的结合。Expanded Universe 的失效更可能来自统一排名让大量相关、高波动 ETF 竞争有限 Top5 槽位，并挤出防守性类别，而不是 Momentum 信号本身完全消失。

# Expanded Universe Momentum Test

## 1. Research Question

在固定 `mom_126 Top5` 策略下，检验 Universe 从原始 12 ETF 扩展至 45 ETF 后，Cross-Sectional Momentum 的核心风险收益特征是否仍然存在。本实验不优化任何参数。

## 2. Fixed Design and Sample

- Monthly rebalance; month-end signal effective next trading day
- Momentum window: 126 trading days
- Top5 equal weight; transaction cost 5 bps; no MA filter
- Common data sample: `2015-10-08` to `2025-12-31` (2573 trading days)
- First 126 common-sample trading days are momentum warm-up
- Strategy comparison sample: `2016-05-02` to `2025-12-31` (2432 trading days)
- Both Universes use identical rebalance dates and performance sample
- Descriptive similarity guide: Sharpe difference <= 0.15 and MaxDD difference <= 5 percentage points

## 3. Performance Comparison

| Universe | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Original 12 ETF Universe | 11.34% | 0.89 | -23.09% | 12.87% | 0.49 | 180.25% | 5459.03% |
| Expanded ETF Universe | 7.52% | 0.46 | -39.59% | 20.64% | 0.19 | 101.44% | 9520.29% |

## 4. Relative Change

| Metric | Expanded - Original |
| --- | --- |
| CAGR | -3.83% |
| Sharpe | -0.44 |
| MaxDD | -16.50% |
| Volatility | 7.77% |
| Calmar | -0.30 |
| Turnover | 4061.26% |

## 5. Selection Statistics

| Metric | Original | Expanded |
| --- | --- | --- |
| Average Eligible Assets | 12.00 | 45.00 |
| Average Distinct Assets Held | 5.00 | 5.00 |
| Average Annual Turnover | 565.66% | 986.48% |
| Number of Assets Ever Selected | 12.00 | 40.00 |
| Percent of Universe Ever Selected | 100.00% | 88.89% |
| Number of Rebalances | 116.00 | 116.00 |

`Average Distinct Assets Held` 是每个调仓期实际 Top5 持仓数；资产广度主要由 `Number of Assets Ever Selected` 和 `Percent of Universe Ever Selected` 判断。

## 6. Asset Class Exposure

以下为持有期间日初实际权重的长期均值。

| Asset Class | Original 12 ETF Universe Weight | Expanded ETF Universe Weight |
| --- | --- | --- |
| Equity | 47.28% | 50.80% |
| Commodity | 34.82% | 45.58% |
| Bond | 17.89% | 2.73% |
| Currency | 0.00% | 0.89% |

## 7. Expanded Universe Top Holdings Frequency

| Symbol | Selection Count | Selection Percent | Original 12 ETF |
| --- | --- | --- | --- |
| XLK | 43 | 37.07% | False |
| SLV | 34 | 29.31% | True |
| PALL | 33 | 28.45% | False |
| QQQ | 32 | 27.59% | True |
| USO | 32 | 27.59% | True |
| XOP | 31 | 26.72% | False |
| GLD | 27 | 23.28% | True |
| DBO | 26 | 22.41% | False |
| UNG | 25 | 21.55% | False |
| XLF | 23 | 19.83% | False |
| MTUM | 22 | 18.97% | False |
| IWF | 20 | 17.24% | False |
| XLE | 19 | 16.38% | False |
| XLU | 19 | 16.38% | False |
| PPLT | 16 | 13.79% | False |

## 8. Interpretation

1. **Expanded Universe 是否保持类似 Sharpe？** 否。Expanded 为 0.46，Original 为 0.89。
2. **是否保持类似 MaxDD？** 否。Expanded 为 -39.59%，Original 为 -23.09%。
3. **收益变化？** CAGR 恶化：Expanded 7.52% vs Original 11.34%。
4. **是否出现新的长期赢家？** 是，Top15 中新增标的包括 XLK, PALL, XOP, DBO, UNG, XLF, MTUM, IWF, XLE, XLU, PPLT。
5. **Top5 是否仍由原始 12 ETF 主导？** 原始 12 ETF 占 Expanded 全部入选槽位的 28.62%；已不占多数。
6. **是否提高资产广度？** 是。曾入选资产数从 12 增至 40。
7. **更支持哪种解释？** 扩展后核心风险收益特征未同时保持，当前证据仍显示策略对 Universe 构造敏感。

名义广度增加并不等同于独立风险来源增加。Expanded Universe 包含多组高度重叠的宽基、行业、风格和单一商品 ETF；同时 Bond 实际权重从 17.89% 降至 2.73%。年化换手增加对应的直接成本差约为 0.21%，不足以单独解释 CAGR 的全部下降，主要变化来自持仓构成、波动率和回撤。

## 9. Final Conclusion

扩展到 45 ETF 后，Cross-Sectional Momentum 的核心风险收益特征没有完整保持。这一结论仅比较固定策略在两个 Universe 中的表现，不包含参数搜索。

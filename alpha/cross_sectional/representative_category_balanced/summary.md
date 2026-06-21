# Representative Cluster Universe + Category Balanced Test

## 1. Research Question

检验在固定 9 ETF Representative Universe 中加入 Equity Top2、Commodity Top2、Bond Top1 的类别席位，是否进一步修复 Global Top5 的风险收益特征。本实验不优化参数。

## 2. Fixed Design

- Sample: `2016-05-02` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps; no MA filter
- Representative Global: 9 ETF 统一排名 Top5，每只 20%
- Category Balanced: Equity Top2、Commodity Top2、Bond Top1，每只 20%
- 类别不足时保留现金，不跨类别补仓
- Representative ETFs are fixed and cannot be replaced

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 11.34% | 0.89 | -23.09% | 12.87% | 0.49 | 180.25% | 5459.03% |
| Representative Global Top5 | 7.93% | 0.67 | -20.91% | 12.71% | 0.38 | 109.47% | 4052.77% |
| Representative Category Balanced | 9.81% | 0.79 | -22.79% | 13.04% | 0.43 | 147.53% | 2258.44% |

## 4. Relative Change vs Original

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Representative Global Top5 | -3.41% | -0.23 | 2.17% |
| Representative Category Balanced | -1.53% | -0.11 | 0.30% |

## 5. Asset Class Exposure

| Strategy | Equity | Commodity | Bond | Currency | Cash |
| --- | --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 47.28% | 34.82% | 17.89% | 0.00% | -0.00% |
| Representative Global Top5 | 29.50% | 53.13% | 8.28% | 9.09% | -0.00% |
| Representative Category Balanced | 40.03% | 40.07% | 19.89% | 0.00% | -0.00% |

## 6. Selection Statistics

`Average Turnover` 是全部预定调仓月的平均双边绝对权重变化。

| Strategy | Distinct Assets Selected | Average Holdings | Average Turnover | Number of Rebalances |
| --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 12 | 5.00 | 47.06% | 116 |
| Representative Global Top5 | 9 | 5.00 | 34.94% | 116 |
| Representative Category Balanced | 8 | 5.00 | 19.47% | 116 |

## 7. Category Balanced ETF Selection Frequency

| ETF | Selection Count | Selection Percent |
| --- | --- | --- |
| IEF | 116 | 100.00% |
| SPY | 116 | 100.00% |
| XLU | 116 | 100.00% |
| GLD | 64 | 55.17% |
| PALL | 57 | 49.14% |
| DBC | 43 | 37.07% |
| DBA | 35 | 30.17% |
| UNG | 33 | 28.45% |
| UUP | 0 | 0.00% |

## 8. Interpretation

1. **Category Balanced 是否优于 Representative Global Top5？** 整体风险收益更优，但并非每个单项风险指标都改善。CAGR 9.81% vs 7.93%，Sharpe 0.79 vs 0.67；MaxDD 变化 -1.87%，总 Turnover 从 4052.77% 降至 2258.44%。
2. **Sharpe 是否进一步恢复？** 变化为 +0.12；Balanced 与 Original 的 Sharpe 差为 -0.11。
3. **Bond 权重是否恢复？** 从 8.28% 增至 19.89%，变化 11.61%。
4. **Commodity 是否被过度压制？** Commodity 从 53.13% 调整为 40.07%，变化 -13.05%；Original 为 34.82%。类别结构仍保留 40% Commodity 目标权重，不属于完全压制。
5. **主要问题是去重不足还是类别失衡？** Global 版本已经完成去重但仍有 5/9 Commodity 代表竞争 Top5；Balanced 只改变类别席位。风险调整表现继续改善，说明完成去重后的主要剩余问题是类别排名机会失衡。
6. **是否更接近 Original 12？** 是，满足预设的 CAGR、Sharpe、MaxDD 接近标准。

## 9. Final Conclusion

在已去重的 Representative Universe 中，类别平衡进一步修复了 CAGR、Sharpe、Calmar 和换手，并使整体表现满足接近 Original 12 的预设标准；代价是 MaxDD 相对 Representative Global 小幅变深。Universe 设计需要同时控制相关性重复和各资产类别的排名席位，只做聚类去重仍不足。该结论只适用于固定代表池和预先指定的类别席位，不包含参数优化。

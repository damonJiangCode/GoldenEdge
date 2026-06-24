# Representative Cluster Universe Momentum Test

## 1. Research Question

在固定 `mom_126 Top5` 策略下，检验使用 9 个风险簇代表 ETF 是否能修复 Expanded 45 ETF Global Top5 的风险收益恶化。本实验不优化参数。

## 2. Fixed Design

- Sample: `2016-05-02` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; Top5 equal weight
- Transaction cost: 5 bps; no MA filter
- Representative Universe: SPY, DBA, DBC, GLD, IEF, PALL, UNG, UUP, XLU
- Descriptive closeness to Original: CAGR difference <= 2 percentage points, Sharpe difference <= 0.15, MaxDD difference <= 5 percentage points

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 11.34% | 0.89 | -23.09% | 12.87% | 0.49 | 180.25% | 5459.03% |
| Expanded 45 ETF Global Top5 | 7.52% | 0.46 | -39.59% | 20.64% | 0.19 | 101.44% | 9520.29% |
| Representative 9 ETF Top5 | 7.93% | 0.67 | -20.91% | 12.71% | 0.38 | 109.47% | 4052.77% |

## 4. Relative Change vs Original 12

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Expanded 45 ETF Global Top5 | -3.83% | -0.44 | -16.50% |
| Representative 9 ETF Top5 | -3.41% | -0.23 | 2.17% |

## 5. Asset Class Exposure

| Strategy | Equity | Commodity | Bond | Currency | Cash |
| --- | --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 47.28% | 34.82% | 17.89% | 0.00% | -0.00% |
| Expanded 45 ETF Global Top5 | 50.80% | 45.58% | 2.73% | 0.89% | -0.00% |
| Representative 9 ETF Top5 | 29.50% | 53.13% | 8.28% | 9.09% | -0.00% |

## 6. Selection Statistics

`Average Turnover` 是全部预定调仓月的平均双边绝对权重变化。

| Strategy | Distinct Assets Selected | Average Holdings | Average Turnover | Number of Rebalances |
| --- | --- | --- | --- | --- |
| Original 12 ETF Top5 | 12 | 5.00 | 47.06% | 116 |
| Expanded 45 ETF Global Top5 | 40 | 5.00 | 82.07% | 116 |
| Representative 9 ETF Top5 | 9 | 5.00 | 34.94% | 116 |

## 7. Representative ETF Selection Frequency

| Symbol | Selection Count | Selection Percent |
| --- | --- | --- |
| SPY | 94 | 81.03% |
| GLD | 79 | 68.10% |
| XLU | 77 | 66.38% |
| PALL | 68 | 58.62% |
| DBA | 63 | 54.31% |
| DBC | 62 | 53.45% |
| UUP | 53 | 45.69% |
| IEF | 48 | 41.38% |
| UNG | 36 | 31.03% |

## 8. Interpretation

1. **Representative Universe 是否优于 Expanded Global Top5？** 是。Sharpe 0.67 vs 0.46；MaxDD -20.91% vs -39.59%。
2. **是否接近 Original 12？** 否，未同时满足 CAGR、Sharpe 和 MaxDD 接近标准。
3. **Sharpe 是否恢复？** 部分恢复。相对 Expanded 到 Original 的 Sharpe 缺口，Representative 恢复了 48.16%；MaxDD 改善 18.68%，Volatility 变化 -7.93%。
4. **Bond 是否恢复合理权重？** Bond 长期权重从 2.73% 回升至 8.28%，但仍低于 Original 的 17.89%，只属于部分恢复。
5. **Expanded 失败是否主要来自重复风险来源？** 去重后 Sharpe 和 MaxDD 同时改善，重复 ETF 和不均衡排名机会是重要原因；但代表池自身类别构成仍会影响结果，不能作为唯一因果解释。
6. **Clustering 是否提高有效广度？** Representative Top5 曾使用 9/9 个风险簇代表。去重让每个簇最多拥有一个排名席位，降低了大型相关簇凭 ticker 数量占据 Top5 的机会；但 9 个代表中 5 个属于 Commodity，类别数量仍不均衡，因此有效广度只得到部分改善。

## 9. Final Conclusion

使用风险簇代表 ETF 后，回撤和波动特征明显恢复，但 CAGR 与 Sharpe 未恢复到 Original 12 水平。去重是必要的 Universe 改进，却不是充分条件；还需要关注各资产类别拥有的簇数量和排名机会是否均衡。该结论只适用于固定 9 ETF 代表池和既定策略，不包含参数优化。

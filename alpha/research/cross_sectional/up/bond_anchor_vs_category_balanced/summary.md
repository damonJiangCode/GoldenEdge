# Bond Anchor vs Category Balanced Test

## 1. Research Question

在固定 Representative Universe 中，检验只固定 20% IEF 风险锚、其余资产统一排名，是否优于固定 Equity/Commodity/Bond 类别席位。本实验不优化任何参数。

## 2. Fixed Design

- Sample: `2016-05-02` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps; no MA filter
- Category Balanced: Equity Top2, Commodity Top2, Bond Top1
- Bond Anchor Global: IEF 20% plus global Top4 from the other 8 ETFs
- Bond Anchor Commodity Cap: same anchor, but at most two Commodity ETFs in Top4
- All positions are 20%; Representative Universe is unchanged

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Original 12 ETF Top5 (Reference) | 11.34% | 0.89 | -23.09% | 12.87% | 0.49 | 180.25% | 5459.03% |
| Representative Category Balanced | 9.81% | 0.79 | -22.79% | 13.04% | 0.43 | 147.53% | 2258.44% |
| Bond Anchor Global Top4 | 7.97% | 0.70 | -19.93% | 11.98% | 0.40 | 110.20% | 3619.71% |
| Bond Anchor Commodity Cap | 9.24% | 0.80 | -22.79% | 12.00% | 0.41 | 135.38% | 2999.37% |

## 4. Relative Change vs Category Balanced

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Original 12 ETF Top5 (Reference) | 1.53% | 0.11 | -0.30% |
| Bond Anchor Global Top4 | -1.84% | -0.08 | 2.85% |
| Bond Anchor Commodity Cap | -0.57% | 0.01 | 0.00% |

## 5. Asset Class Exposure

| Strategy | Equity | Commodity | Bond | Currency | Cash |
| --- | --- | --- | --- | --- | --- |
| Original 12 ETF Top5 (Reference) | 47.28% | 34.82% | 17.89% | 0.00% | 0.00% |
| Representative Category Balanced | 40.03% | 40.07% | 19.89% | 0.00% | 0.00% |
| Bond Anchor Global Top4 | 26.62% | 46.27% | 19.89% | 7.22% | 0.00% |
| Bond Anchor Commodity Cap | 31.79% | 38.50% | 19.89% | 9.82% | 0.00% |

## 6. Selection Statistics

`Average Turnover` 是全部预定调仓月的平均双边绝对权重变化。

| Strategy | Distinct Assets Selected | Average Holdings | Average Turnover | Number of Rebalances |
| --- | --- | --- | --- | --- |
| Original 12 ETF Top5 (Reference) | 12 | 5.00 | 47.06% | 116 |
| Representative Category Balanced | 8 | 5.00 | 19.47% | 116 |
| Bond Anchor Global Top4 | 9 | 5.00 | 31.20% | 116 |
| Bond Anchor Commodity Cap | 9 | 5.00 | 25.86% | 116 |

## 7. ETF Selection Frequency

### Representative Category Balanced

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

### Bond Anchor Global Top4

| ETF | Selection Count | Selection Percent |
| --- | --- | --- |
| IEF | 116 | 100.00% |
| SPY | 90 | 77.59% |
| GLD | 70 | 60.34% |
| PALL | 64 | 55.17% |
| XLU | 64 | 55.17% |
| DBA | 51 | 43.97% |
| DBC | 49 | 42.24% |
| UUP | 42 | 36.21% |
| UNG | 34 | 29.31% |

### Bond Anchor Commodity Cap

| ETF | Selection Count | Selection Percent |
| --- | --- | --- |
| IEF | 116 | 100.00% |
| SPY | 99 | 85.34% |
| XLU | 85 | 73.28% |
| GLD | 63 | 54.31% |
| UUP | 57 | 49.14% |
| PALL | 55 | 47.41% |
| DBC | 38 | 32.76% |
| DBA | 34 | 29.31% |
| UNG | 33 | 28.45% |

## 8. Interpretation

1. **Bond Anchor 是否优于 Category Balanced？** Global Top4 没有在 CAGR 与 Sharpe 上同时更高：7.97%/0.70 vs 9.81%/0.79。
2. **固定 Bond 是否提高 Sharpe？** 三种 Representative 结构都约有20% Bond；结构差异来自剩余80%的排名方式。Global Anchor 相对 Balanced 的 Sharpe 变化为 -0.08。
3. **Commodity 是否再次过多？** Global Anchor 的 Commodity 平均权重为 46.27%，Category Balanced 为 40.07%。
4. **Commodity Cap 是否改善风险收益？** 整体改善：CAGR、Sharpe、Calmar 均高于 Global Anchor，但 MaxDD 更深。Cap 后 Commodity 权重为 38.50%，Sharpe/MaxDD 为 0.80/-22.79%，Global Anchor 为 0.70/-19.93%。
5. **更适合固定类别还是固定 Bond？** 固定 Category Balanced 仍最接近 Original，并具有更高 CAGR 和 Calmar；Bond Anchor + Commodity Cap 的 Sharpe 和波动率略优，但没有形成全面优势。单独固定 Bond 不足以替代类别约束。
6. **最接近 Original 12？** 按 CAGR、Sharpe、MaxDD 的预设归一化距离，`Representative Category Balanced` 最接近 Original；该距离只用于结构比较，不用于参数优化。

## 9. Final Conclusion

固定 Bond 本身没有优于当前 Category Balanced；风险锚不能替代对剩余资产类别排名机会的控制。Commodity Cap 使 Anchor 结构重新接近 Balanced，说明未来 Position Sizing 应把固定风险锚与 Alpha sleeve 的类别集中上限分开设计。本实验不选择新参数。

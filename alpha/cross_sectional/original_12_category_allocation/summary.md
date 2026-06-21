# Original 12 ETF Category Allocation Test

## 1. Research Question

比较 Original 12 ETF 中自由竞争 Top5 与固定 `3-1-1`、`2-2-1`、`1-3-1` 类别席位，检验成功是否隐含稳定类别配置。本实验不优化参数。

## 2. Fixed Design

- Sample: `2008-02-01` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps
- No MA filter; five equal-weight 20% holdings
- Initial portfolio is established from cash on the sample start date

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Original Top5 | 10.36% | 0.81 | -29.06% | 13.16% | 0.36 | 478.53% | 9373.90% |
| 3-1-1 | 9.07% | 0.70 | -38.91% | 13.95% | 0.23 | 378.37% | 8677.20% |
| 2-2-1 | 8.68% | 0.72 | -36.59% | 12.77% | 0.24 | 345.28% | 9682.24% |
| 1-3-1 | 7.07% | 0.60 | -34.14% | 12.81% | 0.21 | 239.00% | 9099.46% |

## 4. Relative Change vs Original Top5

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| 3-1-1 | -1.29% | -0.11 | -9.85% |
| 2-2-1 | -1.68% | -0.09 | -7.53% |
| 1-3-1 | -3.29% | -0.21 | -5.08% |

## 5. Asset Class Exposure

| Strategy | Equity | Commodity | Bond |
| --- | --- | --- | --- |
| Original Top5 | 44.15% | 31.98% | 23.87% |
| 3-1-1 | 60.07% | 19.99% | 19.94% |
| 2-2-1 | 40.06% | 40.00% | 19.94% |
| 1-3-1 | 20.03% | 60.01% | 19.95% |

## 6. Selection Statistics

Lower Selection Concentration HHI means selection slots are distributed more broadly across the 12 ETFs.

| Strategy | Distinct Assets Selected | Average Holdings | Average Turnover | Selection Concentration HHI | Number of Rebalances |
| --- | --- | --- | --- | --- | --- |
| Original Top5 | 12 | 5.00 | 43.60% | 0.09 | 215 |
| 3-1-1 | 12 | 5.00 | 40.36% | 0.12 | 215 |
| 2-2-1 | 12 | 5.00 | 45.03% | 0.10 | 215 |
| 1-3-1 | 12 | 5.00 | 42.32% | 0.12 | 215 |

## 7. Category Contribution

Contribution uses beginning-wealth-weighted gross PnL and is normalized across the three asset classes; transaction costs are not assigned to a class.

| Strategy | Equity Contribution | Commodity Contribution | Bond Contribution |
| --- | --- | --- | --- |
| Original Top5 | 46.67% | 40.55% | 12.77% |
| 3-1-1 | 68.77% | 26.24% | 5.00% |
| 2-2-1 | 45.37% | 49.93% | 4.71% |
| 1-3-1 | 24.50% | 68.08% | 7.42% |

## 8. Average Category Slots

| Strategy | Average Equity Slots | Average Commodity Slots | Average Bond Slots |
| --- | --- | --- | --- |
| Original Top5 | 2.20 | 1.60 | 1.20 |
| 3-1-1 | 3.00 | 1.00 | 1.00 |
| 2-2-1 | 2.00 | 2.00 | 1.00 |
| 1-3-1 | 1.00 | 3.00 | 1.00 |

## 9. ETF Selection Frequency

### Original Top5

| ETF | Selection Count | Selection Percent |
| --- | --- | --- |
| QQQ | 146 | 67.91% |
| SPY | 134 | 62.33% |
| IWM | 111 | 51.63% |
| GLD | 103 | 47.91% |
| SLV | 94 | 43.72% |
| EFA | 83 | 38.60% |
| TLT | 83 | 38.60% |
| USO | 81 | 37.67% |
| IEF | 71 | 33.02% |
| DBA | 66 | 30.70% |
| LQD | 61 | 28.37% |
| SHY | 42 | 19.53% |

### 3-1-1

| ETF | Selection Count | Selection Percent |
| --- | --- | --- |
| SPY | 194 | 90.23% |
| QQQ | 187 | 86.98% |
| IWM | 148 | 68.84% |
| EFA | 116 | 53.95% |
| TLT | 83 | 38.60% |
| USO | 65 | 30.23% |
| GLD | 62 | 28.84% |
| SLV | 61 | 28.37% |
| SHY | 57 | 26.51% |
| LQD | 55 | 25.58% |
| DBA | 27 | 12.56% |
| IEF | 20 | 9.30% |

### 2-2-1

| ETF | Selection Count | Selection Percent |
| --- | --- | --- |
| QQQ | 164 | 76.28% |
| GLD | 132 | 61.40% |
| SPY | 129 | 60.00% |
| SLV | 103 | 47.91% |
| DBA | 101 | 46.98% |
| USO | 94 | 43.72% |
| IWM | 90 | 41.86% |
| TLT | 83 | 38.60% |
| SHY | 57 | 26.51% |
| LQD | 55 | 25.58% |
| EFA | 47 | 21.86% |
| IEF | 20 | 9.30% |

### 1-3-1

| ETF | Selection Count | Selection Percent |
| --- | --- | --- |
| GLD | 188 | 87.44% |
| DBA | 175 | 81.40% |
| SLV | 162 | 75.35% |
| USO | 120 | 55.81% |
| QQQ | 108 | 50.23% |
| TLT | 83 | 38.60% |
| SHY | 57 | 26.51% |
| LQD | 55 | 25.58% |
| IWM | 52 | 24.19% |
| SPY | 29 | 13.49% |
| EFA | 26 | 12.09% |
| IEF | 20 | 9.30% |

## 10. Original Top5 Slot Dynamics

| Equity Slots | Commodity Slots | Bond Slots | Month Count | Month Percent |
| --- | --- | --- | --- | --- |
| 3.00 | 2.00 | 0.00 | 41.00 | 19.07% |
| 4.00 | 1.00 | 0.00 | 36.00 | 16.74% |
| 0.00 | 2.00 | 3.00 | 18.00 | 8.37% |
| 2.00 | 3.00 | 0.00 | 17.00 | 7.91% |
| 2.00 | 2.00 | 1.00 | 14.00 | 6.51% |
| 3.00 | 1.00 | 1.00 | 12.00 | 5.58% |
| 3.00 | 0.00 | 2.00 | 10.00 | 4.65% |
| 0.00 | 4.00 | 1.00 | 10.00 | 4.65% |
| 0.00 | 1.00 | 4.00 | 10.00 | 4.65% |
| 4.00 | 0.00 | 1.00 | 8.00 | 3.72% |
| 1.00 | 1.00 | 3.00 | 8.00 | 3.72% |
| 2.00 | 1.00 | 2.00 | 7.00 | 3.26% |
| 1.00 | 2.00 | 2.00 | 6.00 | 2.79% |
| 1.00 | 0.00 | 4.00 | 6.00 | 2.79% |
| 2.00 | 0.00 | 3.00 | 5.00 | 2.33% |
| 0.00 | 3.00 | 2.00 | 4.00 | 1.86% |
| 1.00 | 3.00 | 1.00 | 2.00 | 0.93% |
| 1.00 | 4.00 | 0.00 | 1.00 | 0.47% |

Original Top5 is exactly `2-2-1` in 6.51% of rebalance months and has exactly one Bond slot in 21.40%. The most common structure is `3-2-0` at 19.07%.

## 11. Interpretation

1. **Original Top5 是否优于所有约束方案？** 是，CAGR 与 Sharpe 均高于全部固定结构。
2. **2-2-1 是否最接近 Original？** 按 CAGR、Sharpe、MaxDD 的预设归一化距离，`2-2-1` 最接近。
3. **Equity 席位增加是否提高 CAGR？** 在三个固定结构中呈单调提高。
4. **Commodity 席位增加的影响？** 在固定结构中 CAGR 单调下降，同时 MaxDD 单调改善；更多 Commodity 在本样本中牺牲收益并降低部分尾部风险。
5. **固定一席 Bond 是否稳定风险？** 没有证据表明固定一席足够。三个固定结构的 MaxDD 都比 Original 更深；Original 虽平均有 1.20 席 Bond，但只有 21.40% 的月份恰好一席，风险控制来自动态类别轮动而非固定一席。
6. **成功来自 Momentum 还是类别平衡？** 两者共同作用，但 Momentum 驱动的动态类别轮动更关键。Original 长期平均接近均衡结构，却显著优于机械固定配额。
7. **Original 平均席位最接近？** `2-2-1`；Original 平均为 Equity 2.20、Commodity 1.60、Bond 1.20。
8. **长期核心 ETF？** Original Top5: QQQ, SPY, IWM; 3-1-1: SPY, QQQ, IWM; 2-2-1: QQQ, GLD, SPY; 1-3-1: GLD, DBA, SLV。
9. **约束提高广度还是集中？** HHI 最低的是 `Original Top5`。全部策略都曾选择12只ETF，但固定配额提高了选择集中度，未提高实际广度。
10. **是否隐含稳定类别模式？** 只存在长期平均倾向，不存在稳定固定模式。Original 恰好2-2-1仅占 6.51%，最常见结构也只有 19.07%；平均值掩盖了显著的月度类别轮动。

## 12. Final Conclusion

Original 12 的成功部分来自长期平均类别平衡，但更关键的是 Momentum 允许类别席位随市场状态动态变化。`2-2-1` 在风险收益上最接近，`2-2-1` 在平均席位上最接近；然而固定该结构会显著损失收益并加深回撤。目标应是保留自由排名产生的动态类别轮动，而不是把长期平均机械固化。

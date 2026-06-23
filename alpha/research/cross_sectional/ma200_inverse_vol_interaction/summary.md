# MA200 x Inverse Vol Interaction Test

## 1. Research Question

在固定 Original 12 ETF `mom_126 Top5` 信号下，检验 MA200 与 Inverse Volatility 是否提供独立或互补的风险控制价值。本实验不优化任何参数。

## 2. Fixed Design

- Sample: `2008-02-01` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum and volatility windows: 126 trading days
- MA window: 200 trading days
- Transaction cost: 5 bps
- Processing order: select Momentum Top5 first, then apply MA200 to those five assets
- Cash variants retain 20% total exposure per surviving asset; IV Cash allocates surviving exposure `count / 5` using inverse-vol proportions
- Reweight variants normalize surviving assets to 100%; zero survivors means full cash

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Equal Weight | 10.36% | 0.81 | -29.06% | 13.16% | 0.36 | 478.53% | 9373.90% |
| EW + MA200 Cash | 9.73% | 0.81 | -18.13% | 12.38% | 0.54 | 422.18% | 9045.41% |
| EW + MA200 Reweight | 8.70% | 0.65 | -33.72% | 14.25% | 0.26 | 341.17% | 11098.20% |
| Inverse Vol | 10.32% | 0.97 | -17.22% | 10.75% | 0.60 | 476.94% | 13244.12% |
| IV + MA200 Cash | 9.53% | 0.91 | -17.65% | 10.57% | 0.54 | 407.91% | 12224.31% |
| IV + MA200 Reweight | 8.66% | 0.73 | -33.68% | 12.42% | 0.26 | 339.61% | 13782.89% |

## 4. Relative Change vs Equal Weight

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| EW + MA200 Cash | -0.63% | -0.00 | 10.93% |
| EW + MA200 Reweight | -1.66% | -0.16 | -4.66% |
| Inverse Vol | -0.04% | 0.15 | 11.84% |
| IV + MA200 Cash | -0.83% | 0.10 | 11.41% |
| IV + MA200 Reweight | -1.70% | -0.08 | -4.62% |

## 5. Exposure Statistics

| Strategy | Avg Holdings | Avg Cash Allocation | Percent Months Below 5 Assets |
| --- | --- | --- | --- |
| Equal Weight | 5.00 | 0.00% | 0.00% |
| EW + MA200 Cash | 4.56 | 8.84% | 23.26% |
| EW + MA200 Reweight | 4.56 | 0.93% | 23.26% |
| Inverse Vol | 5.00 | 0.00% | 0.00% |
| IV + MA200 Cash | 4.56 | 8.84% | 23.26% |
| IV + MA200 Reweight | 4.56 | 0.93% | 23.26% |

## 6. Position Concentration

Cash is included as an explicit position in HHI when present. HHI and Effective Positions are calculated at each rebalance and then averaged.

| Strategy | Average HHI | Effective Positions |
| --- | --- | --- |
| Equal Weight | 0.20 | 5.00 |
| EW + MA200 Cash | 0.23 | 4.74 |
| EW + MA200 Reweight | 0.25 | 4.57 |
| Inverse Vol | 0.29 | 3.93 |
| IV + MA200 Cash | 0.28 | 3.99 |
| IV + MA200 Reweight | 0.31 | 3.80 |

## 7. Turnover Impact

| Strategy | Annual Turnover | Cost Drag Estimate |
| --- | --- | --- |
| Equal Weight | 524.01% | 0.26% |
| EW + MA200 Cash | 505.64% | 0.25% |
| EW + MA200 Reweight | 620.40% | 0.31% |
| Inverse Vol | 740.35% | 0.37% |
| IV + MA200 Cash | 683.35% | 0.34% |
| IV + MA200 Reweight | 770.47% | 0.39% |

## 8. Interpretation

1. **MA200 是否独立提高 Sharpe？** 否；完全投资的 EW Reweight 未同时改善 Sharpe 与 MaxDD，MA Cash 的优势主要依赖降低风险暴露。
2. **Inverse Vol 是否独立提高 Sharpe？** 是。Inverse Vol Sharpe/MaxDD 为 0.97/-17.22%，Equal Weight 为 0.81/-29.06%。
3. **两者是否互补？** Cash组合 没有同时进一步改善 Sharpe 与 MaxDD；Reweight组合 没有同时进一步改善。互补性必须相对单独 Inverse Vol 判断，而不是只相对 Equal Weight。
4. **MA200 改善来自趋势还是现金？** EW Cash vs Reweight 的 Sharpe/MaxDD 为 0.81/-18.13% vs 0.65/-33.72%；Cash 版本同时更优，主要证据指向现金降风险机制。
5. **Reweight 与 Cash 哪种更优？** Cash 在 EW 和 IV 两组中都明显优于对应 Reweight；EW系列最高Sharpe仍是 `Equal Weight`。Reweight 的平均0.93%现金来自2个零通过资产月份，并非日常保留现金。
6. **Inverse Vol 是否仍优于所有 Equal Weight 版本？** 是，以 Sharpe 比较。
7. **哪种最符合保留收益并控制风险？** 在 CAGR 不低于 Equal Weight 1个百分点的固定方案中，`Inverse Vol` 的 Sharpe 最高；该筛选只总结预先指定方案，不进行参数搜索。

## 9. Final Conclusion

在当前 Original 12 ETF Momentum Framework 中，**MA200 与 Inverse Vol 没有显示增量互补性**。MA200 Cash 能显著降低 Equal Weight 回撤，但不提高 Sharpe，其价值主要来自现金降风险；MA200 Reweight 在 EW 和 IV 下都恶化表现。Inverse Vol 单独保留最高 CAGR、最高 Sharpe和最浅MaxDD，因此是六个固定方案中最完整的风险控制机制。当前证据不支持把 MA200 叠加到 Inverse Vol，也不支持过滤后重新归一化。本实验不测试其它 MA、Vol窗口或仓位方法。

# MA200 Filter + Cross-Sectional Momentum Test

## 1. Research Question

在固定的 12 ETF Mixed Asset `mom_126 Top5` 框架下，MA200 是否能够降低回撤、提高 Sharpe 和改善风险调整后收益？本实验不搜索其他 MA 或 momentum 参数。

## 2. Fixed Design

- Sample: `2007-08-01` to `2025-12-31`
- Monthly rebalance; signal at month end; holdings effective next trading day
- Momentum window: 126 trading days
- Portfolio: Top5 equal weight
- Transaction cost: 5 bps
- MA filter: month-end `Adj Close > SMA200`
- Version A: eligible 少于 5 时，每只仍持有 20%，剩余资金为零收益现金
- Version B: eligible 少于 5 时，在全部 eligible 资产中等权满仓
- eligible 为 0 时，两种版本均为全现金

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 11.36% | 0.88 | -29.06% | 13.20% | 0.39 | 623.86% | 9708.32% |
| MA200 Version A | 11.29% | 0.91 | -17.82% | 12.59% | 0.63 | 615.24% | 9544.84% |
| MA200 Version B | 10.30% | 0.77 | -32.77% | 14.02% | 0.31 | 506.89% | 10753.91% |

## 4. Relative Change vs Baseline

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| MA200 Version A | -0.07% | 0.03 | 11.23% |
| MA200 Version B | -1.06% | -0.11 | -3.71% |

## 5. Exposure Statistics

| Metric | MA200 Version A | MA200 Version B |
| --- | --- | --- |
| Average Eligible Assets | 7.90 | 7.90 |
| Minimum Eligible Assets | 0.00 | 0.00 |
| Maximum Eligible Assets | 12.00 | 12.00 |
| Average Portfolio Holdings | 4.71 | 4.71 |
| Average Cash Allocation | 5.70% | 0.90% |
| Percent Months Below 5 Assets | 11.31% | 11.31% |

## 6. Asset Class Exposure

以下为日初实际风险资产权重的全样本均值；Version A 的行合计可能低于 100%，差额为现金。

| Asset Class | Baseline Weight | MA200 Version A Weight | MA200 Version B Weight | Baseline Risk Share | MA200 Version A Risk Share | MA200 Version B Risk Share |
| --- | --- | --- | --- | --- | --- | --- |
| Equity | 43.76% | 42.85% | 43.65% | 43.76% | 45.43% | 44.05% |
| Commodity | 32.57% | 29.84% | 31.82% | 32.57% | 31.64% | 32.11% |
| Bond | 23.67% | 21.64% | 23.63% | 23.67% | 22.94% | 23.84% |

## 7. Interpretation

1. **MA200 是否提高 Sharpe？** Version A: 0.91 vs 0.88; Version B: 0.77 vs 0.88。
2. **MA200 是否降低 MaxDD？** Version A: -17.82%; Version B: -32.77%; Baseline: -29.06%。
3. **收益变化主要来自什么？** 最佳过滤版本 `MA200 Version A` 的 CAGR 为 11.29%、波动率为 12.59%。Version A 通过平均现金仓位降低风险暴露，避开弱趋势资产基本抵消了现金拖累。
4. **是否减少 Commodity/Bond 暴露？** 最佳过滤版本相对 baseline 的 Commodity/Bond 总权重变化为 -2.73% / -2.04%；其中一部分来自现金仓位。
5. **是否提高 Equity Concentration？** Equity 总权重变化为 -0.91%，但在已投资风险资产中的占比变化为 1.67%。
6. **是否足以证明策略增强？** MA200 是有价值的条件性风险过滤器：只有当不合格仓位保留为现金时，它才在几乎保留 CAGR 的同时提高 Sharpe 并大幅降低 MaxDD。Version B 的恶化说明改善来自趋势过滤与降低风险暴露的组合，不是过滤后集中持仓本身。

## 8. Final Conclusion

MA200 是有价值的条件性风险过滤器：只有当不合格仓位保留为现金时，它才在几乎保留 CAGR 的同时提高 Sharpe 并大幅降低 MaxDD。Version B 的恶化说明改善来自趋势过滤与降低风险暴露的组合，不是过滤后集中持仓本身。

该结论只适用于固定的 MA200、mom_126、Top5 和当前 12 ETF Universe。两种现金处理方式同时给出，是为了判断改善是否来自过滤本身，而不是某一种低 eligible 权重规则。

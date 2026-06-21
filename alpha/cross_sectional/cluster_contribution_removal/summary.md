# Cluster Contribution & Removal Test

## 1. Research Question

识别 Representative Category Balanced 框架中各风险簇的直接收益贡献、删除敏感度和组合职责。本实验不优化任何参数。

## 2. Fixed Baseline and Removal Rules

- Sample: `2016-05-02` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum: 126 trading days; transaction cost: 5 bps
- Category slots remain Equity Top2, Commodity Top2, Bond Top1 at 20% each
- A removed cluster is excluded before ranking; unavailable category slots remain cash
- Baseline CAGR/Sharpe/MaxDD: 9.81% / 0.79 / -22.79%
- Small-impact diagnostic: absolute CAGR <= 0.5 percentage points, Sharpe <= 0.05, MaxDD <= 2 percentage points

## 3. Performance

| Scenario | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 9.81% | 0.79 | -22.79% | 13.04% | 0.43 | 147.53% | 2258.44% |
| Remove Equity | 4.73% | 0.51 | -19.05% | 10.10% | 0.25 | 56.13% | 2084.27% |
| Remove Bond | 9.63% | 0.78 | -23.52% | 12.96% | 0.41 | 143.67% | 2178.20% |
| Remove Agriculture | 10.18% | 0.80 | -22.27% | 13.32% | 0.46 | 154.97% | 1792.16% |
| Remove Energy | 10.03% | 0.81 | -22.79% | 12.95% | 0.44 | 152.23% | 1992.20% |
| Remove Precious Metals | 7.25% | 0.60 | -23.05% | 13.08% | 0.31 | 96.53% | 2382.34% |
| Remove Palladium | 7.81% | 0.72 | -18.36% | 11.45% | 0.43 | 107.27% | 1990.37% |
| Remove Natural Gas | 11.49% | 1.03 | -22.79% | 11.21% | 0.50 | 186.52% | 1774.94% |
| Remove USD | 9.81% | 0.79 | -22.79% | 13.04% | 0.43 | 147.53% | 2258.44% |

## 4. Relative Change vs Baseline

正的 MaxDD Change 表示回撤改善。

| Scenario | Cluster | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- | --- |
| Remove Equity | Equity | -5.08% | -0.28 | 3.74% |
| Remove Bond | Bond | -0.19% | -0.01 | -0.74% |
| Remove Agriculture | Agriculture | 0.37% | 0.01 | 0.52% |
| Remove Energy | Energy / Broad Commodity | 0.21% | 0.02 | 0.00% |
| Remove Precious Metals | Precious Metals | -2.57% | -0.19 | -0.27% |
| Remove Palladium | Palladium | -2.00% | -0.07 | 4.42% |
| Remove Natural Gas | Natural Gas | 1.67% | 0.24 | 0.00% |
| Remove USD | US Dollar | 0.00% | 0.00 | 0.00% |

## 5. Baseline Direct Gross PnL Contribution

Contribution 使用期初组合财富加权的毛 PnL，在风险簇之间归一化；交易成本不归属于单个簇。它与删除后替代效应不同。

| Cluster | Total Gross PnL Contribution | Contribution Percent |
| --- | --- | --- |
| Equity | 0.73 | 49.04% |
| Precious Metals | 0.42 | 28.26% |
| Palladium | 0.26 | 17.50% |
| Energy / Broad Commodity | 0.19 | 12.85% |
| Agriculture | 0.15 | 10.17% |
| Bond | 0.02 | 1.19% |
| US Dollar | 0.00 | 0.00% |
| Natural Gas | -0.28 | -19.01% |

## 6. Contribution Importance Rankings

Positive impact means removal damaged the corresponding metric. Negative impact means removal improved it.

### CAGR Impact

| Rank | Cluster | Impact |
| --- | --- | --- |
| 1 | Equity | 5.08% |
| 2 | Precious Metals | 2.57% |
| 3 | Palladium | 2.00% |
| 4 | Bond | 0.19% |
| 5 | US Dollar | 0.00% |
| 6 | Energy / Broad Commodity | -0.21% |
| 7 | Agriculture | -0.37% |
| 8 | Natural Gas | -1.67% |

### Sharpe Impact

| Rank | Cluster | Impact |
| --- | --- | --- |
| 1 | Equity | 0.28 |
| 2 | Precious Metals | 0.19 |
| 3 | Palladium | 0.07 |
| 4 | Bond | 0.01 |
| 5 | US Dollar | 0.00 |
| 6 | Agriculture | -0.01 |
| 7 | Energy / Broad Commodity | -0.02 |
| 8 | Natural Gas | -0.24 |

### Risk Impact

Risk Impact is positive when removal makes MaxDD more negative.

| Rank | Cluster | Impact |
| --- | --- | --- |
| 1 | Bond | 0.74% |
| 2 | Precious Metals | 0.27% |
| 3 | Energy / Broad Commodity | 0.00% |
| 4 | Natural Gas | 0.00% |
| 5 | US Dollar | 0.00% |
| 6 | Agriculture | -0.52% |
| 7 | Equity | -3.74% |
| 8 | Palladium | -4.42% |

## 7. Scenario Exposure and Cash

| Scenario | Equity | Commodity | Bond | Currency | Cash |
| --- | --- | --- | --- | --- | --- |
| Baseline | 40.03% | 40.07% | 19.89% | 0.00% | 0.00% |
| Remove Equity | 0.00% | 40.16% | 19.93% | 0.00% | 39.91% |
| Remove Bond | 40.02% | 40.07% | 0.00% | 0.00% | 19.91% |
| Remove Agriculture | 40.02% | 40.10% | 19.89% | 0.00% | 0.00% |
| Remove Energy | 40.03% | 40.08% | 19.89% | 0.00% | 0.00% |
| Remove Precious Metals | 40.07% | 40.01% | 19.92% | 0.00% | 0.00% |
| Remove Palladium | 40.05% | 40.04% | 19.90% | 0.00% | 0.00% |
| Remove Natural Gas | 40.02% | 40.09% | 19.89% | 0.00% | 0.00% |
| Remove USD | 40.03% | 40.07% | 19.89% | 0.00% | 0.00% |

## 8. Interpretation

1. **主要收益引擎？** 按删除后 CAGR 下降，`Equity` 排名第一。
2. **对 Sharpe 最重要？** `Equity` 删除后造成最大 Sharpe 损失。
3. **主要风险缓冲器？** `Bond` 删除后造成最大 MaxDD 恶化。
4. **删除后影响很小？** 按预设三项 small-impact 标准：Bond, Agriculture, Energy / Broad Commodity, US Dollar。其中 US Dollar 在当前规则中从未配置，影响严格为零；Agriculture 和 Energy 可被其它 Commodity 代表替代。
5. **可简化的 Satellite Clusters？** Natural Gas 是最强的简化候选：Baseline 直接贡献为负，删除后 CAGR 和 Sharpe 均明显上升。该结论仍需样本外验证，不能据此直接永久删除。US Dollar 在当前无 Currency 席位的规则下可从交易 Universe 移除但不改变策略。Bond 虽在 small-impact 范围内，却是排名第一的回撤缓冲器，不应按小收益影响机械删除。
6. **框架依赖哪些风险来源？** Equity、Precious Metals 和 Palladium 承担主要收益；Equity 与 Precious Metals 对 Sharpe 最重要；Bond 提供幅度有限但方向明确的回撤保护。Equity/Bond 整类删除还会产生 40%/20% 现金，因此它们的影响同时包含资产缺失和降风险暴露；Commodity 单簇删除主要衡量同类别替代能力。

## 9. Final Conclusion

当前框架中不可替代性应按三个维度分别判断：`Equity` 是主要 CAGR 来源，`Equity` 对风险调整表现最重要，`Bond` 是主要回撤缓冲器。Precious Metals 和 Palladium 也是重要收益来源；Natural Gas 是样本内主要拖累，US Dollar 在当前规则下没有组合职责。删除测试是条件敏感度分析，不应把样本内负面贡献机械解释成永久移除建议。

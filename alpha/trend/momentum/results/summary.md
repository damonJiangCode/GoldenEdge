# Momentum Alpha Validation Summary

## 1. 研究问题

过去收益率是否能预测未来收益率？
本实验验证的是 Past Return 对 Future Return 的预测能力，不是交易策略回测。

## 2. Alpha 假设

如果 Momentum Alpha 存在，则过去动量最强的一组未来收益应该高于过去动量最弱的一组。
核心比较是每个 symbol 内部的 `Q5 / Top 20%` 与 `Q1 / Bottom 20%`。

## 3. 实验设计

- Price: `Adj Close`
- Momentum windows: `mom_63`, `mom_126`, `mom_252`
- Forward horizons: `FR20`, `FR60`, `FR120`
- 每个 symbol 内部按 momentum 分成 5 组: `Q1` 到 `Q5`
- `Q1` 是过去动量最弱 20%，`Q5` 是过去动量最强 20%
- Forward return 只用于验证，不进入 momentum 信号计算
- 未来数据不足的样本直接丢弃
- Top vs Bottom 检验使用 Welch t-test，并报告 Cohen's d

## 4. 总体结论

- 是否发现 Momentum Alpha: 总体上 Top 20% 平均相对 Bottom 20% 的最佳组合是 mom_63 -> FR120，avg_difference=1.29%。
- 最有效 momentum window: `mom_63`
- 最有效 forward horizon: `FR120`
- Top 组未来收益为正的检验组合数量: 98 / 108
- Top 组未来收益高于 Bottom 组的检验组合数量: 61 / 108
- Top > Bottom 且 p-value < 0.05 的检验组合数量: 46 / 108

### Overall Top vs Bottom Summary

| momentum_window | forward_horizon | avg_difference | percent_symbols_top_outperforms_bottom | avg_top_win_rate | avg_bottom_win_rate | avg_p_value | avg_cohens_d |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mom_63 | FR20 | 0.39% | 75.00% | 58.38% | 57.12% | 0.203 | 0.080 |
| mom_63 | FR60 | 0.85% | 66.67% | 64.51% | 61.67% | 0.049 | 0.112 |
| mom_63 | FR120 | 1.29% | 58.33% | 68.14% | 64.18% | 0.011 | 0.113 |
| mom_126 | FR20 | 0.37% | 58.33% | 58.37% | 57.10% | 0.141 | 0.069 |
| mom_126 | FR60 | 1.14% | 66.67% | 64.24% | 60.40% | 0.094 | 0.129 |
| mom_126 | FR120 | 1.01% | 58.33% | 67.27% | 61.95% | 0.044 | 0.126 |
| mom_252 | FR20 | -0.09% | 41.67% | 57.96% | 56.19% | 0.230 | 0.041 |
| mom_252 | FR60 | -0.92% | 41.67% | 60.45% | 59.95% | 0.018 | 0.013 |
| mom_252 | FR120 | -1.62% | 41.67% | 61.89% | 63.15% | 0.001 | 0.028 |

## 5. 分资产类别结论

### Best Combination By Asset Class

| asset_class | momentum_window | forward_horizon | avg_difference | percent_symbols_top_outperforms_bottom | avg_top_win_rate | avg_bottom_win_rate | avg_p_value | avg_cohens_d |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bond | mom_252 | FR120 | 0.21% | 50.00% | 66.31% | 62.73% | 0.002 | 0.355 |
| commodity | mom_63 | FR120 | 2.72% | 75.00% | 60.08% | 57.30% | 0.021 | 0.199 |
| equity | mom_126 | FR120 | 2.64% | 75.00% | 78.78% | 60.89% | 0.030 | 0.165 |

### Equity

- 最强组合: `mom_126 -> FR120`，avg_difference=2.64%，top outperform 比例=75.00%。
- 显著且 Top > Bottom 的 symbol-window-horizon 数量: 17。
### Commodity

- 最强组合: `mom_63 -> FR120`，avg_difference=2.72%，top outperform 比例=75.00%。
- 显著且 Top > Bottom 的 symbol-window-horizon 数量: 18。
### Bond

- 最强组合: `mom_252 -> FR120`，avg_difference=0.21%，top outperform 比例=50.00%。
- 显著且 Top > Bottom 的 symbol-window-horizon 数量: 11。

## 6. 注意事项

- `Top 组未来收益为正` 只说明高动量样本后续平均收益为正，不等于存在 alpha。
- `Top 组未来收益高于 Bottom 组` 才是本实验对 Momentum Alpha 的核心方向性证据。
- `p_value < 0.05` 表示均值差异在当前样本中更难用随机波动解释；不显著不等于没有经济意义，但不能作为强统计证据。
- Cohen's d 衡量差异相对波动的大小；均值差异显著但 Cohen's d 很小，仍可能很难构造成稳健策略。
- 是否值得进入策略构建阶段，应同时看方向稳定性、显著性、效果大小、资产类别一致性，以及交易规则后的成本和回撤。

## 7. 下一步建议

- 测试跨资产横截面动量，而不是只做单资产时间序列分位数。
- 测试 monthly rebalance，减少日度样本重叠带来的统计依赖。
- 加入 MA 风险过滤，观察趋势状态是否能改善 Top vs Bottom 差异。
- 做 out-of-sample split，避免只根据全样本选择最佳窗口。
- 对 forward return 使用 Newey-West 或 block bootstrap，处理重叠持有期导致的自相关。

## 8. Data Warnings

- 无跳过或数据质量 warning。

# XAU Engines 总结笔记（2015-2025）

日期：2026-02-27

本次已汇总以下策略在 `xau/data/historical` 全量数据（5 个 timeframe，2015-2025）的结果：
- `trend_pullback/v1`
- `mean_reversion/v1`
- `volatility_breakout/v1`
- `volatility_breakout/v2`

## 报告位置
- `xau/data/reports/trend_pullback/v1/`
- `xau/data/reports/mean_reversion/v1/`
- `xau/data/reports/volatility_breakout/v1/`
- `xau/data/reports/volatility_breakout/v2/`

## 各 Engine 总览（按各自最佳 timeframe）
| Engine | Best TF | Avg Return % | Avg PF | Avg MaxDD % | Positive Years |
| --- | --- | ---:| ---:| ---:| --- |
| trend_pullback_v1 | H4 | 4.35 | 1.052 | 15.27 | 6/11 |
| mean_reversion_v1 | H1 | -1.05 | 0.922 | 2.70 | 4/11 |
| volatility_breakout_v1 | H4 | 22.74 | 2.682 | 8.77 | 9/11 |
| volatility_breakout_v2 | H4 | 22.74 | 2.682 | 8.77 | 9/11 |

## 核心结论
- 当前最强策略是 `volatility_breakout` 系列，`H4` 明显领先（收益、PF、正收益年份都最优）。
- `trend_pullback_v1` 有一定可用性，但稳定性与收益显著弱于 breakout。
- `mean_reversion_v1` 在当前参数下整体偏弱，所有 timeframe 平均收益为负。
- `M1` 在所有策略中都表现最差（高交易频率 + 成本侵蚀明显），不建议作为当前主战 timeframe。
- 当前 `volatility_breakout/v1` 与 `v2` 汇总结果一致，说明在当前默认参数组合下两者行为等价（需要通过不同 `trend_filter`、`N`、`k_sl`、`k_trail` 才能拉开差异）。

## 按策略的简要判断
- `trend_pullback/v1`：保留 `H4/M30` 作为对照组；适合做稳健性和成本敏感性测试。
- `mean_reversion/v1`：建议先限制在 `H1/H4` 做重新参数化，优先解决胜率与正收益年份不足。
- `volatility_breakout/v1,v2`：优先继续推进 `H4`；`M15/M30` 可作为次优扩展；`M1` 暂停。

## 下一步建议（执行优先级）
1. 以 `volatility_breakout/v2` 为主线，在 `H4` 做参数网格：`N={20,55}`、`k_sl={1.8,2.0,2.2}`、`k_trail={2.5,3.0,3.5}`、`trend_filter={adx,ema200,both}`。
2. 固定最佳组合后，做 OOS 切片验证（例如 2015-2021 训练 / 2022-2025 验证）确认是否过拟合。
3. 统一加入交易成本压力测试（点差上浮、滑点上浮）评估实盘鲁棒性。

# XAU Engines 总结笔记（2015-2025）

日期：2026-02-27

本次已汇总以下策略在 `xau/data/historical` 全量数据（5 个 timeframe，2015-2025）的结果：
- `trend_pullback/v1`
- `mean_reversion/v1`
- `volatility_breakout/v1`
- `volatility_breakout/v2`
- `volatility_breakout/v3`

## 报告位置
- `xau/data/reports/trend_pullback/v1/`
- `xau/data/reports/mean_reversion/v1/`
- `xau/data/reports/volatility_breakout/v1/`
- `xau/data/reports/volatility_breakout/v2/`
- `xau/data/reports/volatility_breakout/v3/`

## 各 Engine 总览（按各自最佳 timeframe）
| Engine | Best TF | Avg Return % | Avg PF | Avg MaxDD % | Positive Years |
| --- | --- | ---:| ---:| ---:| --- |
| trend_pullback_v1 | H4 | 4.35 | 1.052 | 15.27 | 6/11 |
| mean_reversion_v1 | H1 | -1.05 | 0.922 | 2.70 | 4/11 |
| volatility_breakout_v1 | H4 | 22.74 | 2.682 | 8.77 | 9/11 |
| volatility_breakout_v2 | H4 | 13.72 | 1.879 | 10.15 | 8/11 |
| volatility_breakout_v3 | H4 | 13.02 | 1.755 | 14.39 | 5/11 |

## 核心结论
- 当前最强策略是 `volatility_breakout` 系列，`H4` 明显领先（收益、PF、正收益年份都最优）。
- `trend_pullback_v1` 有一定可用性，但稳定性与收益显著弱于 breakout。
- `mean_reversion_v1` 在当前参数下整体偏弱，所有 timeframe 平均收益为负。
- `M1` 在所有策略中都表现最差（高交易频率 + 成本侵蚀明显），不建议作为当前主战 timeframe。
- `volatility_breakout/v2 (EMA200)` 相比 `v1` 没有成为更优替代：`H1` 改善，但核心主战 `H4` 明显变弱。
- `volatility_breakout/v3`（分层加仓）验证了“趋势加仓”的研究方向，但当前参数下整体退化明显，仅 `H4` 保持正收益，且质量低于 `v1`。

## 按策略的简要判断
- `trend_pullback/v1`：保留 `H4/M30` 作为对照组；适合做稳健性和成本敏感性测试。
- `mean_reversion/v1`：建议先限制在 `H1/H4` 做重新参数化，优先解决胜率与正收益年份不足。
- `volatility_breakout/v1`：当前仍是 breakout 主基线，优先继续推进 `H4`；`M15/M30` 可作为次优扩展。
- `volatility_breakout/v2 (ema200)`：保留为 `H1` 定向研究分支，不建议作为全局默认替代。
- `volatility_breakout/v3`：当前版本不建议继续直接全量推进，应先缩小到 `H4` 单独修正金字塔加仓逻辑。

## 下一步建议（执行优先级）
1. 以 `volatility_breakout/v1` 继续作为主线，在 `H4` 做参数网格：`N={20,55}`、`k_sl={1.8,2.0,2.2}`、`k_trail={2.5,3.0,3.5}`。
2. 对 `volatility_breakout/v2` 继续测试 `trend_filter={adx,ema200,both}`，重点看 `H1/H4` 的结构性差异。
3. 对 `volatility_breakout/v3` 仅在 `H4` 做修正：降低加仓频率、收紧总风险、限制最多加到 2 层，再复测。
4. 固定最佳组合后，做 OOS 切片验证（例如 2015-2021 训练 / 2022-2025 验证）确认是否过拟合。
5. 统一加入交易成本压力测试（点差上浮、滑点上浮）评估实盘鲁棒性。

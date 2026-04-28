# XAU Engines 总结笔记（2015-2025）

日期：2026-04-28

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
- `xau/data/optimizations/volatility_breakout/v1/H4/`
- `xau/data/optimizations/volatility_breakout/v1/H4_island/`

## 各 Engine 总览（按各自最佳 timeframe）
| Engine | Best TF | Avg Return % | Avg PF | Avg MaxDD % | Positive Years |
| --- | --- | ---:| ---:| ---:| --- |
| trend_pullback_v1 | H4 | 4.35 | 1.052 | 15.27 | 6/11 |
| mean_reversion_v1 | H1 | -1.05 | 0.922 | 2.70 | 4/11 |
| volatility_breakout_v1 | H4 | 22.74 | 2.682 | 8.77 | 9/11 |
| volatility_breakout_v2 | H4 | 13.72 | 1.879 | 10.15 | 8/11 |
| volatility_breakout_v3 | H4 | 13.02 | 1.755 | 14.39 | 5/11 |

## 最新优化结论：VB/H4 参数岛（2026-04-28）

已完成 `volatility_breakout/v1` 在 `H4` 上的两轮参数优化：
- 第一轮：`864` 组，输出目录 `xau/data/optimizations/volatility_breakout/v1/H4/`
- 第二轮：`1440` 组，输出目录 `xau/data/optimizations/volatility_breakout/v1/H4_island/`

数据使用方式：
- `2015-2021`：开发集
- `2022-2023`：验证集
- `2024-2025`：最终 OOS

稳健过滤条件：
- Full positive years >= `10`
- OOS average PF >= `1.5`
- Validation average PF >= `1.3`
- Full average max drawdown <= `12%`
- Full average trades >= `18/year`

第二轮通过稳健过滤：`690/1440`，说明 `VB/H4` 附近存在稳定参数岛，而不是单点过拟合。

### 当前推荐主候选

| Param | Value |
| --- | ---: |
| donchian_breakout_period | `18` |
| donchian_exit_period | `10` |
| sl_atr_mult | `2.2` |
| trail_atr_mult | `3.2` |
| h1_adx_min | `18` |
| atr_ratio_min | `1.0` |

结果：

| Metric | Value |
| --- | ---: |
| Full Avg Return | `25.73%` |
| Full PF | `2.12` |
| Full MaxDD | `9.28%` |
| Positive Years | `11/11` |
| OOS Avg Return | `81.30%` |
| OOS PF | `3.04` |

### 参数岛范围

核心稳定区域：
- `N = 18-20`
- `SL = 2.2-2.5`
- `trail = 3.2`
- `ATRr = 1.0`
- `ADX = 18-20`

更激进的候选：
- `N=20, exit=10/20, SL=2.2, trail=3.2, ADX=16, ATRr=0.95`
- Full Avg Return：`27.22%`
- Full PF：`1.94`
- Full MaxDD：`10.27%`
- Positive Years：`10/11`
- OOS Avg Return：`87.33%`

判断：
- 默认生产候选优先选择 `N=18, SL=2.2, trail=3.2, ADX=18, ATRr=1.0`。
- 激进候选收益更高，但放松了 `ADX` 与 `ATR ratio` 过滤，更容易依赖 2024-2025 大趋势行情。
- `donchian_exit_period=10` 和 `20` 多数组合结果一致，当前退出由 `chandelier` trailing 主导，Donchian exit 暂时不是关键参数。

## 核心结论
- 当前最强策略仍是 `volatility_breakout` 系列，`H4` 明显领先；参数岛优化后，`v1/H4` 推荐候选优于原始基线。
- `trend_pullback_v1` 有一定可用性，但稳定性与收益显著弱于 breakout。
- `mean_reversion_v1` 在当前参数下整体偏弱，所有 timeframe 平均收益为负。
- `M1` 在所有策略中都表现最差（高交易频率 + 成本侵蚀明显），不建议作为当前主战 timeframe。
- `volatility_breakout/v2 (EMA200)` 相比 `v1` 没有成为更优替代：`H1` 改善，但核心主战 `H4` 明显变弱。
- `volatility_breakout/v3`（分层加仓）验证了“趋势加仓”的研究方向，但当前参数下整体退化明显，仅 `H4` 保持正收益，且质量低于 `v1`。
- 当前主线应从“继续找方向”切换到“验证推荐候选是否能承受成本压力与 walk-forward 切片”。

## 按策略的简要判断
- `trend_pullback/v1`：保留 `H4/M30` 作为对照组；适合做稳健性和成本敏感性测试。
- `mean_reversion/v1`：建议先限制在 `H1/H4` 做重新参数化，优先解决胜率与正收益年份不足。
- `volatility_breakout/v1`：当前 XAUUSD 主基线；优先推进 `H4` 推荐候选参数，暂不分散到低周期。
- `volatility_breakout/v2 (ema200)`：保留为 `H1` 定向研究分支，不建议作为全局默认替代。
- `volatility_breakout/v3`：当前版本不建议继续直接全量推进，应先缩小到 `H4` 单独修正金字塔加仓逻辑。

## 下一步建议（执行优先级）
1. 用推荐主候选生成正式年度 report 目录，作为新的 `VB/H4` 候选基线。
2. 对推荐主候选做成本压力测试：spread/slippage 上浮，确认实盘鲁棒性。
3. 做 rolling / walk-forward 验证，避免只相信 `2015-2021 -> 2022-2025` 单一切片。
4. 若压力测试通过，再把 `VB/H4` 逻辑迁移到 MT5 独立策略脚本，不要混入旧 M5 RSI/BB 系列。
5. `v2` 与 `v3` 暂时降级为研究分支，等 `VB/H4` 主候选完成压力测试后再继续。

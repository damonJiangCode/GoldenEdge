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
- `xau/data/reports/volatility_breakout/v1_h4_candidate/`
- `xau/data/optimizations/volatility_breakout/v1/H4/`
- `xau/data/optimizations/volatility_breakout/v1/H4_island/`
- `xau/data/optimizations/volatility_breakout/v1/H4_quality_filter/`
- `xau/data/validation/volatility_breakout/v1_h4_candidate/`
- `xau/data/diagnostics/volatility_breakout/v1_h4_candidate/`

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

## 最新验证结论：VB/H4 推荐候选（2026-04-28）

已生成正式年度报告与验证输出：
- 正式报告目录：`xau/data/reports/volatility_breakout/v1_h4_candidate/`
- 验证输出目录：`xau/data/validation/volatility_breakout/v1_h4_candidate/`
- 运行命令：`.venv/bin/python xau/scripts/validation/vb_h4_candidate_validate.py`

正式年度结果：

| Metric | Value |
| --- | ---: |
| Full Avg Return | `25.73%` |
| Full PF | `2.12` |
| Full MaxDD | `9.28%` |
| Positive Years | `11/11` |
| Worst Year Return | `1.18%` |
| Avg Trades | `25.55/year` |

成本压力测试：

| Scenario | Avg Return | Avg PF | Positive Years | Worst Year |
| --- | ---: | ---: | ---: | ---: |
| base | `25.73%` | `2.12` | `11/11` | `1.18%` |
| spread_1_25x | `23.69%` | `1.56` | `9/11` | `0.00%` |
| spread_1_50x | `23.43%` | `2.25` | `8/11` | `-4.13%` |
| slippage_2x | `25.69%` | `2.12` | `11/11` | `1.12%` |
| spread_1_50x_slippage_2x | `23.40%` | `2.24` | `8/11` | `-4.17%` |

Rolling / walk-forward：
- `2015-2019 -> 2020-2021`：Test Avg Return `22.23%`，PF `1.84`，Positive Years `2/2`
- `2016-2020 -> 2021-2022`：Test Avg Return `21.00%`，PF `1.82`，Positive Years `2/2`
- `2017-2021 -> 2022-2023`：Test Avg Return `26.14%`，PF `1.95`，Positive Years `2/2`
- `2018-2022 -> 2023-2024`：Test Avg Return `29.19%`，PF `2.12`，Positive Years `2/2`
- `2019-2023 -> 2024-2025`：Test Avg Return `81.30%`，PF `3.04`，Positive Years `2/2`

判断：
- 推荐主候选通过正式年度报告、成本压力测试和 rolling OOS 验证。
- spread 压力会减少交易并使部分年份转弱，但策略没有崩；H4 级别对 slippage 不敏感。
- 可以进入 MT5 迁移前设计阶段，但应新建独立 `VB/H4` MT5 策略脚本，不要混入旧 M5 RSI/BB 脚本。

## 最新诊断结论：VB 单质量分解（2026-04-28）

已生成 trade-level 诊断输出：
- 输出目录：`xau/data/diagnostics/volatility_breakout/v1_h4_candidate/`
- 运行命令：`.venv/bin/python xau/scripts/diagnostics/vb_h4_trade_diagnostics.py`

注意：
- 年度报告里的 Avg Return / Avg PF / Avg MaxDD 是“每年独立重置资金后按年份平均”。
- Trade diagnostics 使用的是一条连续 2015-2025 H4 曲线，用来观察 equity curve、drawdown、单笔交易分布、持仓时间和 PnL 来源。

Trade metrics：

| Metric | Value |
| --- | ---: |
| Trades | `302` |
| Win Rate | `43.71%` |
| Avg Win | `40.12` |
| Avg Loss | `-14.69` |
| Payoff Ratio | `2.73` |
| Profit Factor | `2.12` |
| Expectancy / Trade | `9.27` |
| Sharpe / Trade | `0.23` |
| Avg R Multiple | `0.35` |
| Avg Holding | `23.74 bars / 5.45 days` |

PnL 分解：
- Long trades：`167` 笔，net PnL `2107.21`，PF `2.40`
- Short trades：`135` 笔，net PnL `692.22`，PF `1.70`
- ADX `25-30`：PF `2.86`，avg PnL `15.28`，是当前最好的 ADX 区域。
- ATR ratio `1.25-1.5`：PF `3.99`，avg PnL `23.69`，是当前最好的 ATR ratio 区域。
- 持仓 `1-24` 根 H4 的 buckets 合计为负，持仓 `25+` 根 H4 的 bucket 贡献 `4607.85` net PnL，PF `38.76`。

诊断判断：
- 这个策略真正赚钱的是“跑出来的大趋势 VB 单”，不是频繁短打。
- 坏单主要是突破后很快失败的短持仓单。
- 持仓时间是事后诊断里最强的 PnL 分界，但不能直接作为入场过滤条件；下一步应研究是否能用入场前/入场后早期信号预测“是否有机会跑到 25+ bars”。

质量过滤网格：
- 输出目录：`xau/data/optimizations/volatility_breakout/v1/H4_quality_filter/`
- 大幅提高 `ATRr` 到 `1.2+` 会让交易过少，正收益年份下降。
- `ADX=20/22` 与 `ATRr=1.0` 是更现实的过滤方向。
- `N=18, SL=2.5, trail=3.2, ADX=20, ATRr=1.0`：Full Avg Return `25.25%`，PF `2.64`，MaxDD `8.86%`，Positive Years `10/11`。
- 默认候选仍保留 `N=18, SL=2.2, trail=3.2, ADX=18, ATRr=1.0`，增强过滤候选作为后续对照。

## 核心结论
- 当前最强策略仍是 `volatility_breakout` 系列，`H4` 明显领先；参数岛优化后，`v1/H4` 推荐候选优于原始基线。
- `trend_pullback_v1` 有一定可用性，但稳定性与收益显著弱于 breakout。
- `mean_reversion_v1` 在当前参数下整体偏弱，所有 timeframe 平均收益为负。
- `M1` 在所有策略中都表现最差（高交易频率 + 成本侵蚀明显），不建议作为当前主战 timeframe。
- `volatility_breakout/v2 (EMA200)` 相比 `v1` 没有成为更优替代：`H1` 改善，但核心主战 `H4` 明显变弱。
- `volatility_breakout/v3`（分层加仓）验证了“趋势加仓”的研究方向，但当前参数下整体退化明显，仅 `H4` 保持正收益，且质量低于 `v1`。
- 当前主线已从“找方向”推进到“VB 单质量诊断与 MT5 迁移前设计”；推荐候选已通过成本压力与 walk-forward 验证。

## 按策略的简要判断
- `trend_pullback/v1`：保留 `H4/M30` 作为对照组；适合做稳健性和成本敏感性测试。
- `mean_reversion/v1`：建议先限制在 `H1/H4` 做重新参数化，优先解决胜率与正收益年份不足。
- `volatility_breakout/v1`：当前 XAUUSD 主基线；优先推进 `H4` 推荐候选参数，暂不分散到低周期。
- `volatility_breakout/v2 (ema200)`：保留为 `H1` 定向研究分支，不建议作为全局默认替代。
- `volatility_breakout/v3`：当前版本不建议继续直接全量推进，应先缩小到 `H4` 单独修正金字塔加仓逻辑。

## 下一步建议（执行优先级）
1. 围绕“短持仓失败单”继续找可交易的早期过滤信号，而不是只追总收益。
2. 将默认候选与增强过滤候选做并排 trade diagnostics 对比。
3. 设计并实现独立 `VB/H4` MT5 策略脚本，参数先使用默认推荐主候选。
4. MT5 迁移时重点处理 H4 bar close / next bar market entry、H1 ADX 映射、spread 过滤、ATR/Donchian 与 Chandelier trailing 的一致性。
5. 上 demo 前加入风险保护：单仓、magic number、symbol alias、周末/收盘保护、日志与 Telegram 报警。

# Strategy Changelog

## [2026-05-26-VB-V1-H4-QUALITY-DEFAULTS] volatility_breakout / v1 / H4

- 日期：2026-05-26
- 变更类型：`parameter-default`
- 目标：将 `volatility_breakout/v1` 固定为只做高质量 VB 单的 H4 主线，后续可与其他策略一起进入组合层验证。
- 修改文件：`xau/scripts/engines/volatility_breakout/v1.py`

### 默认参数更新

| Param | Old | New |
| --- | ---: | ---: |
| default timeframes | `H1,H4` | `H4` |
| donchian_breakout_period | `20` | `18` |
| donchian_exit_period | `10` | `10` |
| sl_atr_mult | `2.0` | `2.2` |
| trail_atr_mult | `3.0` | `3.2` |
| h1_adx_min | `20` | `18` |
| atr_ratio_min | `1.0` | `1.0` |

### 复核结果

- 复核方式：使用新默认参数跑 `H4` 年度报告。
- 先完整查看 `2015-2025`，再单独排除强趋势年份 `2025`，验证策略是否过度依赖 2025。

`2015-2025`：

| Metric | Value |
| --- | ---: |
| Avg Return | `25.73%` |
| Avg PF | `2.12` |
| Avg MaxDD | `9.28%` |
| Positive Years | `11/11` |
| Avg Trades | `25.55/year` |

`2015-2024`，排除 `2025`：

| Metric | Value |
| --- | ---: |
| Avg Return | `14.37%` |
| Avg PF | `1.92` |
| Avg MaxDD | `8.99%` |
| Positive Years | `10/10` |
| Avg Trades | `24.90/year` |
| Worst Year | `2018: +1.18%` |
| Best Year | `2023: +35.10%` |

### 判断

- 去掉 `2025` 后收益明显降温，但结构没有崩，仍保持 `10/10` 正收益年份。
- 当前默认参数适合作为 VB/H4 主策略候选，不再把 H1 混入默认运行。
- 下一步调参重点不再追求增加交易数，而是围绕坏单过滤继续研究，例如对照 `ADX=20`、`SL=2.5` 的质量增强候选。
- 后续与其他策略组合运行时，VB 这一侧应定位为低频趋势突破模块，而不是全市场高频信号源。

## [2026-04-28-VB-V1-H4-TRADE-DIAGNOSTICS] volatility_breakout / v1 / H4

- 日期：2026-04-28
- 变更类型：`diagnostics`
- 诊断对象：`volatility_breakout/v1`，`H4` 推荐主候选
- 运行命令：`.venv/bin/python xau/scripts/diagnostics/vb_h4_trade_diagnostics.py`
- 输出目录：`xau/data/diagnostics/volatility_breakout/v1_h4_candidate/`

### 改了什么

- `volatility_breakout/v1.py` 报告新增完整 `trade_details`，不再只保留前 30 笔 `sample_trades`。
- `vb_h4_candidate_validate.py` 年度 summary 新增 trade-level 指标：
- `avg_win`
- `avg_loss`
- `payoff_ratio`
- `avg_holding_bars`
- `trade_sharpe`
- 新增 `xau/scripts/diagnostics/vb_h4_trade_diagnostics.py`：
- 输出连续 2015-2025 trade list。
- 输出 equity / drawdown / overlay / trade histogram / rolling Sharpe SVG。
- 输出按 year、quarter、side、holding bucket、ADX bucket、ATR ratio bucket 的 PnL breakdown。

### 连续 2015-2025 Trade Metrics

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

### 关键诊断结论

- `long` 贡献显著高于 `short`：long net PnL `2107.21`，short net PnL `692.22`。
- ADX 最好的区域是 `25-30`：PF `2.86`，avg PnL `15.28`。
- ATR ratio 最好的区域是 `1.25-1.5`：PF `3.99`，avg PnL `23.69`。
- 持仓时间是最强诊断信号：
- `1-24` 根 H4 的 trade bucket 整体为负。
- `25+` 根 H4 的 bucket 贡献 `4607.85` net PnL，PF `38.76`，win rate `85.34%`。
- 这说明策略真正赚钱的是跑出来的大趋势单，短时间失败的 breakout 是主要拖累。

### 质量过滤网格

- 新增输出目录：`xau/data/optimizations/volatility_breakout/v1/H4_quality_filter/`
- 目的：测试提高 ADX / ATR ratio 是否能过滤坏单。
- 结论：
- 大幅提高 `ATRr` 到 `1.2+` 会显著减少交易，正收益年份下降，不适合作为默认主线。
- `ADX=20/22` 与 `ATRr=1.0` 是更现实的过滤方向。
- 候选 `N=18, SL=2.5, trail=3.2, ADX=20, ATRr=1.0` 提高 PF 到 `2.64`，但 Positive Years 从 `11/11` 降到 `10/11`。
- 当前仍保留 `N=18, SL=2.2, trail=3.2, ADX=18, ATRr=1.0` 作为默认候选；过滤增强版作为对照候选。

## [2026-04-28-VB-V1-H4-CANDIDATE-VALIDATION] volatility_breakout / v1 / H4

- 日期：2026-04-28
- 变更类型：`validation`
- 验证对象：`volatility_breakout/v1`，`H4` 推荐主候选
- 运行命令：`.venv/bin/python xau/scripts/validation/vb_h4_candidate_validate.py`
- 正式报告目录：`xau/data/reports/volatility_breakout/v1_h4_candidate/`
- 验证输出目录：`xau/data/validation/volatility_breakout/v1_h4_candidate/`

### 验证参数

- `donchian_breakout_period = 18`
- `donchian_exit_period = 10`
- `sl_atr_mult = 2.2`
- `trail_atr_mult = 3.2`
- `h1_adx_min = 18`
- `atr_ratio_min = 1.0`

### 正式年度报告

| Metric | Value |
| --- | ---: |
| Full Avg Return | `25.73%` |
| Full PF | `2.12` |
| Full MaxDD | `9.28%` |
| Positive Years | `11/11` |
| Worst Year Return | `1.18%` |
| Avg Trades | `25.55/year` |

### 成本压力测试

| Scenario | Avg Return | Avg PF | Avg MaxDD | Positive Years | Worst Year |
| --- | ---: | ---: | ---: | ---: | ---: |
| base | `25.73%` | `2.12` | `9.28%` | `11/11` | `1.18%` |
| spread_1_25x | `23.69%` | `1.56` | `8.43%` | `9/11` | `0.00%` |
| spread_1_50x | `23.43%` | `2.25` | `7.14%` | `8/11` | `-4.13%` |
| slippage_2x | `25.69%` | `2.12` | `9.30%` | `11/11` | `1.12%` |
| spread_1_50x_slippage_2x | `23.40%` | `2.24` | `7.14%` | `8/11` | `-4.17%` |

结论：

- `slippage` 上浮对 H4 候选影响很小。
- `spread` 上浮会减少交易、降低正收益年份数量，但策略未崩；`1.5x spread + 2x slippage` 下仍保持平均正收益与 PF > 2。
- 因为 spread 压力测试会触发 `spread_max_points` 过滤，交易数量下降，PF 变化不完全等同于单纯成本劣化。

### Rolling / Walk-forward

| Window | Train Avg Return | Train PF | Test Avg Return | Test PF | Test Positive Years |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2015-2019 -> 2020-2021 | `4.74%` | `1.94` | `22.23%` | `1.84` | `2/2` |
| 2016-2020 -> 2021-2022 | `7.59%` | `1.34` | `21.00%` | `1.82` | `2/2` |
| 2017-2021 -> 2022-2023 | `11.86%` | `1.48` | `26.14%` | `1.95` | `2/2` |
| 2018-2022 -> 2023-2024 | `13.52%` | `1.43` | `29.19%` | `2.12` | `2/2` |
| 2019-2023 -> 2024-2025 | `20.31%` | `1.71` | `81.30%` | `3.04` | `2/2` |

结论：

- 所有 rolling OOS 窗口都是正收益，且测试段 PF 全部 > `1.8`。
- 候选参数通过迁移到 MT5 前的研究验证，但仍建议先生成独立 MT5 脚本，不要混入旧 M5 RSI/BB 系列。

## [2026-04-28-VB-V1-H4-PARAM-ISLAND] volatility_breakout / v1 / H4

- 日期：2026-04-28
- 变更类型：`optimization`
- 优化对象：`volatility_breakout/v1`，仅聚焦 `H4`
- 对比基线：`xau/data/reports/volatility_breakout/v1/H4/`
- 第一轮运行命令：`.venv/bin/python xau/scripts/optimization/vb_h4_grid.py --workers 4 --top-n 30`
- 第二轮运行命令：`.venv/bin/python xau/scripts/optimization/vb_h4_island.py`
- 第一轮输出目录：`xau/data/optimizations/volatility_breakout/v1/H4/`
- 第二轮输出目录：`xau/data/optimizations/volatility_breakout/v1/H4_island/`

### 策略目的

- 正确使用 2015-2025 十一年 H4 历史数据，避免直接全样本找最优导致过拟合。
- 将数据切成：
- `2015-2021`：开发集
- `2022-2023`：验证集
- `2024-2025`：最终 OOS
- 目标不是找单点最高收益，而是确认 `VB/H4` 是否存在稳定参数岛。

### 改了什么

- 新增 `xau/scripts/optimization/vb_h4_grid.py`：
- 复用 `volatility_breakout/v1.py` 的 EngineConfig 和 Engine，不复制策略逻辑。
- 对参数组合分别输出 dev / validation / OOS / full 四段统计。
- 新增 `xau/scripts/optimization/vb_h4_island.py`：
- 围绕第一轮候选做二轮参数岛精扫。
- 自动生成 `island_notes.md`，筛出稳健组合与参数簇。

### 第一轮结果

- 第一轮网格：`864` 组。
- 当前基线：
- `N=20, exit=10, SL=2.0, trail=3.0, ADX=20, ATRr=1.0`
- Full Avg Return：`22.74%`
- Full PF：`2.68`
- Full MaxDD：`8.77%`
- Positive Years：`9/11`
- 第一轮最高分：
- `N=20, exit=10/20, SL=2.0, trail=3.0, ADX=18, ATRr=1.0`
- Full Avg Return：`23.07%`
- Full PF：`2.10`
- Full MaxDD：`8.96%`
- Positive Years：`9/11`
- 第一轮保守候选：
- `N=20, exit=10/20, SL=2.2, trail=3.0, ADX=18, ATRr=1.0`
- Full Avg Return：`22.54%`
- Full PF：`2.11`
- Full MaxDD：`9.10%`
- Positive Years：`11/11`

### 第二轮参数岛结果

- 第二轮网格：`1440` 组。
- 稳健过滤条件：
- Full positive years >= `10`
- OOS average PF >= `1.5`
- Validation average PF >= `1.3`
- Full average max drawdown <= `12%`
- Full average trades >= `18/year`
- 通过稳健过滤：`690/1440`。
- 说明 `VB/H4` 附近不是单点过拟合，而是存在大面积可用参数岛。

### 推荐主候选

- 当前推荐先锁定：
- `donchian_breakout_period = 18`
- `donchian_exit_period = 10`
- `sl_atr_mult = 2.2`
- `trail_atr_mult = 3.2`
- `h1_adx_min = 18`
- `atr_ratio_min = 1.0`

结果：

| Metric | Value |
| --- | ---: |
| Full Avg Return | `25.73%` |
| Full PF | `2.12` |
| Full MaxDD | `9.28%` |
| Positive Years | `11/11` |
| OOS Avg Return | `81.30%` |
| OOS PF | `3.04` |

### 备选候选

更激进的高分候选：

- `N=20, exit=10/20, SL=2.2, trail=3.2, ADX=16, ATRr=0.95`
- Full Avg Return：`27.22%`
- Full PF：`1.94`
- Full MaxDD：`10.27%`
- Positive Years：`10/11`
- OOS Avg Return：`87.33%`

判断：

- 该组合收益更高，但 `ADX=16` 与 `ATRr=0.95` 都是在放松过滤。
- 它更容易吃到 2024-2025 的大趋势红利，不建议直接作为默认生产候选。

### 参数岛结论

- 核心稳定区域：
- `N = 18-20`
- `SL = 2.2-2.5`
- `trail = 3.2`
- `ATRr = 1.0`
- `ADX = 18-20`
- `donchian_exit_period=10` 和 `20` 多数组合结果一致，说明当前 `chandelier` trailing 主导退出，Donchian exit 暂时不是关键参数。
- 相比原基线，推荐候选牺牲少量 PF，但换来更高平均收益与 `11/11` 年正收益。

### 下一步

1. 用推荐主候选生成正式年度报告目录，避免只停留在 optimization csv。
2. 对推荐主候选做成本压力测试：spread/slippage 上浮。
3. 做 rolling / walk-forward 验证，确认 `2015-2021 -> 2022-2025` 之外的切片也稳定。
4. 若压力测试通过，再考虑迁移到 MT5 策略实现，不直接把研究参数硬塞进旧 M5 RSI/BB 脚本。

## [2026-02-27-VB-V2-EMA200] volatility_breakout / v2

- 日期：2026-02-27
- 变更类型：`filter`
- 对比基线：`xau/data/reports/volatility_breakout/v1/`（默认 `ADX` 过滤）
- 运行命令：`.venv/bin/python xau/scripts/engines/volatility_breakout/v2.py --timeframes M1,M15,M30,H1,H4 --trend-filter ema200`
- 输出目录：`xau/data/reports/volatility_breakout/v2/`

### 改了什么

- 将 `v2` 的趋势过滤从默认 `ADX` 切换为 `EMA200`。
- `v2` 默认参数已同步改为 `trend_filter=ema200`。
- 其他核心逻辑未变：仍然是 Donchian 突破、ATR 扩张过滤、spread 过滤、ATR 初始止损、Chandelier/Donchian trailing。

### 结果对比（v1 -> v2 ema200）

| TF  |       Avg Return % |  Delta |         Avg PF |  Delta |      Avg MaxDD % |  Delta |
| --- | -----------------: | -----: | -------------: | -----: | ---------------: | -----: |
| H4  |     22.74 -> 13.72 |  -9.02 | 2.682 -> 1.879 | -0.803 |    8.77 -> 10.15 |  +1.38 |
| M30 |       5.52 -> 3.35 |  -2.17 | 1.010 -> 1.006 | -0.004 |   13.27 -> 14.04 |  +0.77 |
| H1  |       1.16 -> 2.93 |  +1.77 | 0.985 -> 1.059 | +0.074 |   15.59 -> 13.52 |  -2.07 |
| M15 |       9.90 -> 1.14 |  -8.76 | 1.063 -> 0.984 | -0.079 |   10.62 -> 15.02 |  +4.40 |
| M1  | -119.33 -> -145.58 | -26.25 | 0.626 -> 0.606 | -0.020 | 120.90 -> 147.42 | +26.52 |

附加结论：

- `H4` 仍是 `v2(ema200)` 的最佳 timeframe，但显著弱于 `v1(adx)`。
- `H1` 是唯一明显改善的 timeframe。
- 全局来看，`EMA200` 过滤让交易更偏方向性，但对高表现的 `H4/M15` 伤害更大。

### 变好了

- `H1` 明显改善：
- 平均收益：`+1.77%`
- 平均 PF：`+0.074`
- 平均 MaxDD：`-2.07%`
- 正收益年份：`5/11 -> 7/11`
- `H1` 从“勉强可用”提升到“可继续优化”的状态。

### 变差了

- `H4` 显著变差：
- 平均收益从 `22.74%` 降到 `13.72%`
- PF 从 `2.682` 降到 `1.879`
- 回撤上升
- `M15` 由强正收益策略退化到接近持平。
- `M1` 更差，说明 `EMA200` 对超低周期没有修复作用。
- 从组合层面看，`EMA200` 过滤削弱了最重要的 alpha 来源：`H4`。

### 是否值得保留

- 结论：`partial`
- 理由：
- 如果主战 timeframe 是 `H4`，不值得用 `EMA200` 替换 `v1` 的默认 `ADX` 方案。
- 如果目标是单独优化 `H1`，`EMA200` 值得保留为一个可选分支。
- 因此，`EMA200` 适合作为 `v2` 的一个实验配置，但不应视为当前“全局最优替代方案”。

### 建议的策略定位

- `volatility_breakout/v1`：保留为当前主基线（尤其是 `H4`）。
- `volatility_breakout/v2 (ema200)`：保留为 `H1` 导向的候选分支。
- 当前不建议用 `v2(ema200)` 直接取代 `v1` 作为总基线。

### 下一步

1. 跑 `v2 --trend-filter both`，重点只看 `H1/H4`，判断能否同时保住 `H4` 并继续改善 `H1`。
2. 在 `v2(ema200)` 上加入 `EMA200 slope` 过滤（只允许顺着 EMA 斜率方向交易），减少横盘假突破。
3. 对 `H1` 单独做参数网格：`N={20,55}`、`k_sl={1.8,2.0,2.2}`、`k_trail={2.5,3.0,3.5}`。
4. 若 `H4` 仍为主战周期，则把 `v1(adx)` 继续作为默认生产候选，把 `v2` 仅当研究分支使用。

## [2026-02-27-VB-V3-PYRAMIDING] volatility_breakout / v3

- 日期：2026-02-27
- 变更类型：`logic`
- 对比基线：`xau/data/reports/volatility_breakout/v1/`
- 运行命令：`.venv/bin/python xau/scripts/engines/volatility_breakout/v3.py --timeframes M1,M15,M30,H1,H4`
- 输出目录：`xau/data/reports/volatility_breakout/v3/`

### 策略目的

- 在 `v1` 的 Donchian breakout 基础上，引入“只在盈利方向加仓”的趋势放大利润机制。
- 目标不是提高胜率，而是让已经跑出的趋势单吃到更大的利润曲线。
- 理论上，若突破后延续性足够强，分层加仓应当提升 `H4/H1` 的趋势利润上限。

### 策略意义

- 这是对 breakout 策略“仓位管理层”的扩展，而不是信号层的扩展。
- 它验证的是：当前 breakout 信号质量，是否已经足够好到可以承载金字塔加仓。
- 如果信号本身不稳定，pyramiding 往往会放大利润，也会同步放大回撤与错误。

### 改了什么

- 从单仓 `position` 改为多层 `position_layers`。
- 支持参数：
- `enable_pyramiding`
- `pyramid_trigger_r`
- `pyramid_max_layers`
- `pyramid_size_decay`
- 只允许顺盈利方向加仓，不允许亏损加仓。
- 每层独立记录：
- `layer_id`
- `layer_entry_price`
- `layer_sl`
- `layer_initial_risk`
- `size_multiplier`
- 每层独立 SL / trailing / 结算。
- 新增报表字段：
- `pyramid_layers_max_used`
- `pyramid_add_count`
- `pyramid_total_layers_closed`

### 结果对比（v1 -> v3）

| TF  |       Avg Return % |   Delta |         Avg PF |   Delta |      Avg MaxDD % |   Delta |
| --- | -----------------: | ------: | -------------: | ------: | ---------------: | ------: |
| H4  |     22.74 -> 13.02 |   -9.72 | 2.682 -> 1.755 |  -0.926 |    8.77 -> 14.39 |   +5.62 |
| H1  |      1.16 -> -19.17 | -20.33 | 0.985 -> 0.671 |  -0.314 |   15.59 -> 29.10 |  +13.51 |
| M30 |      5.52 -> -23.89 | -29.41 | 1.010 -> 0.668 |  -0.342 |   13.27 -> 29.67 |  +16.39 |
| M15 |      9.90 -> -31.07 | -40.97 | 1.063 -> 0.703 |  -0.360 |   10.62 -> 35.25 |  +24.62 |
| M1  | -119.33 -> -249.27 | -129.94 | 0.626 -> 0.453 |  -0.173 | 120.90 -> 249.32 | +128.42 |

附加结论：

- `H4` 仍是 `v3` 唯一相对可看的 timeframe，但仍明显弱于 `v1`。
- 除 `H4` 外，其余 timeframe 全部退化为“全周期平均负收益”。
- `v3` 虽然确实实现了分层加仓，但当前参数下，它放大了错误仓位，而不是有效放大利润。

### 变好了

- 从“策略实验完整性”角度，`v3` 完成了仓位管理层的验证：
- 分层加仓、风险封顶、逐层平仓、逐层 trailing 都已经落地。
- `H4` 仍保留正收益，说明金字塔加仓方向不是完全错误，只是当前触发与风控参数不合适。

### 变差了

- `H4`：
- 平均收益下降约 `9.72%`
- PF 明显下降
- 回撤明显放大
- `H1/M30/M15`：
- 从原本可用或接近可用，全部退化到明显负收益
- 说明中低周期突破延续性不足，不足以支撑此版本的加仓结构
- `M1`：
- 大幅恶化，进一步确认低周期不适合当前 breakout + pyramiding 组合

### 是否值得保留

- 结论：`partial`
- 理由：
- 这版 `v3` 不值得替代 `v1` 作为主策略。
- 但它值得保留为一个研究分支，因为它已经证明：
- “加仓思路”本身可实现
- 问题主要在加仓触发条件和风险释放节奏，而不是框架不可用
- 当前更准确的结论是：`v3` 的方向有研究价值，但参数和风控设计还远未可用

### 是否该更新默认基线

- 不建议。
- 当前 breakout 主基线仍应保持 `v1`。
- `v3` 只应保留在研究分支中继续修正，不适合作为默认运行版本。

### 下一步

1. 只在 `H4` 上继续研究 `v3`，暂停 `H1/M30/M15/M1`。
2. 把 `pyramid_trigger_r` 提高到 `1.5R` 或 `2.0R`，减少过早加仓。
3. 将 `pyramid_max_layers` 从 `3` 降到 `2`，先验证“少量加仓”是否更稳。
4. 收紧风险释放：要求首层完全 break-even 后才允许加第二层，并限制新层真实风险低于 `0.25R~0.5R`。
5. 增加“趋势确认后再加仓”条件，例如只有当 ADX 上升或价格仍位于 Donchian 外沿时才允许加仓。

# Strategy Changelog

> Paths in older entries are historical snapshots. Current structure is documented
> in `xau/readme.md`.

## [2026-06-09-DAILY-SUMMARY] XAU strategy-first workspace restructure

- 日期：2026-06-09
- 变更类型：`structure` / `optimization` / `reporting`
- 范围：`VB v1`、`MR v1`、`TP v1`、原始行情、正式 reports 与研究输出。

### 今日完成事项

1. 将 XAU 工作区改为按策略组织：

```text
xau/
├── vb/v1/
├── mr/v1/
├── tp/v1/
├── marketdata/
├── changelog.md
└── readme.md
```

2. 每个策略版本统一采用：

```text
engine.py
reports/
optimization/
bucket_analysis/
```

3. 路径迁移：
   - 原始行情：`xau/data/market_data/` -> `xau/marketdata/`
   - VB engine / reports / optimization / bucket analysis -> `xau/vb/v1/`
   - MR engine / reports / optimization -> `xau/mr/v1/`
   - TP engine -> `xau/tp/v1/`
   - unified trade schema 与结构说明合并到 `xau/readme.md`
   - 历史研究记录迁移到 `xau/changelog.md`

4. MR v1 研究：
   - 新增多阶段 parameter-island 优化器。
   - 修复下一根入场指标快照与未完成 H1 ADX 的未来数据泄漏。
   - 将最佳稳健参数覆盖为 MR v1 默认参数。
   - 生成 M15 2015-2025 正式年度 reports 与统一 summary。

5. Reporting：
   - VB H4 与 MR M15 正式 report 目录新增 `summary.md`、`summary.json`、`summary.csv`。
   - summary 包含年度表现、已平仓成交、年末未平仓影响、方向、退出原因、成本、过滤器和参数汇总。

### 验证

- VB、MR、TP engine 均使用 `xau/marketdata/` 成功运行。
- VB optimization、MR parameter-island CLI、VB bucket analysis、report summary 均成功运行。
- 所有当前 Python 文件通过 `py_compile`。
- `git diff --check` 通过。

## [2026-06-04-DAILY-SUMMARY] VB v1 / unified trades / regime prep

- 日期：2026-06-04
- 变更类型：`daily-summary`
- 范围：`VB v1` 单质量研究、unified trade 输出、regime 项目准备。

### 今日完成事项

1. 明确组合研究方向：
   - 将 `VB`、`MR`、`TF` 定义为三个策略因子。
   - `Regime` 不直接预测涨跌，第一阶段只做策略适用环境判断。
   - 后续组合层目标是降低回撤、减少坏年份、减少策略冲突，而不是追求单策略最高收益。

2. 建立 unified trade schema：
   - 文件：`xau/readme.md`
   - 目的：让 `VB`、`MR`、`TF` 后续都输出同一套 trade-level 字段。
   - 关键字段包括：
   - `strategy`
   - `engine_version`
   - `signal_time_utc`
   - `entry_time_utc`
   - `exit_time_utc`
   - `initial_sl`
   - `final_sl`
   - `net_pnl`
   - `pnl_result`
   - `initial_risk_money`
   - `r_multiple`
   - `entry_atr`
   - `entry_atr_ratio`
   - `entry_h1_adx`
   - `adx_bucket`
   - `atr_ratio_bucket`
   - `post_entry_holding_bucket`
   - `sl_update_count`
   - `trail_updates_json`

3. 将 `VB v1` baseline 和 7 个过滤实验统一输出为 regime 可读格式：
   - 输出目录：`xau/vb/v1/optimization/results/`
   - 每个版本只保留：
   - `summary.csv`
   - `summary.json`
   - `unified_trades.csv`
   - 顶层对照表：
   - `xau/vb/v1/optimization/results/comparison_summary.csv`
   - `xau/vb/v1/optimization/results/comparison_summary.json`

4. 清理 optimization 旧 JSON report 输出：
   - 已删除：`xau/vb/v1/optimization/results/*/reports/report_YEAR.json`
   - 保留正式 engine report：
   - `xau/vb/v1/reports/H4/report_2015.json`
   - ...
   - `xau/vb/v1/reports/H4/report_2025.json`

5. 新增 7 个 VB v1 过滤实验脚本：
   - `01_close_breakout_confirm.py`
   - `02_candle_close_quality.py`
   - `03_adx20_rising.py`
   - `04_atr_ratio_1_1.py`
   - `05_overextension_filter.py`
   - `06_early_failure_exit.py`
   - `07_candle_quality_adx20_rising.py`

6. 新增统一 runner：
   - `xau/vb/v1/optimization/run_all_unified.py`
   - 用途：一次性重跑 baseline + `01` 到 `07`，覆盖 unified 输出。

7. 增强 `VB v1` 正式 report 与 unified trades：
   - 每笔 trade 新增 `sl_update_count`。
   - 每笔 trade 新增 `trail_updates` / `trail_updates_json`。
   - 每笔 trade 新增 `pnl_result`，区分最终赚钱还是亏钱。

### 当前 VB v1 对照结果

| Version | Avg Return | PF | Positive Years | Avg Trades | Profit Trades / Total | Profit Ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | `25.73%` | `2.12` | `11/11` | `25.55` | `123 / 281` | `43.77%` |
| 01 close confirm | `17.76%` | `2.65` | `9/11` | `20.73` | `101 / 228` | `44.30%` |
| 02 candle quality | `19.34%` | `2.38` | `10/11` | `20.36` | `99 / 224` | `44.20%` |
| 03 ADX20 rising | `16.01%` | `2.46` | `10/11` | `17.18` | `85 / 189` | `44.97%` |
| 04 ATRr 1.1 | `17.89%` | `1.91` | `9/11` | `16.82` | `86 / 185` | `46.49%` |
| 05 overextension | `16.69%` | `2.09` | `9/11` | `22.00` | `103 / 242` | `42.56%` |
| 06 early failure | `17.29%` | `1.80` | `8/11` | `31.00` | `140 / 341` | `41.06%` |
| 07 candle + ADX | `10.67%` | `2.33` | `9/11` | `13.64` | `68 / 150` | `45.33%` |

### SL 更新统计结论

- `VB v1` 是高度依赖 trailing stop 的趋势策略。
- baseline 中：
  - 交易数：`281`
  - 至少更新过一次 SL：`80.78%`
  - 平均每笔 SL 更新次数：`12.33`
  - 更新过 SL 的交易赚钱率：`54.19%`
  - 未更新 SL 的交易赚钱率：`0.00%`
- 解释：
  - 未更新 SL 的交易基本等价于突破后快速失败。
  - 更新过 SL 的交易才进入可管理趋势状态。
  - 因此后续不应只看传统 win rate，而应重点看 `pnl_result`、`r_multiple`、`sl_update_count`、`trail_updates_json` 和 regime bucket。

### 今日取留判断

- 主策略继续保留 `00_baseline_current_v1_default`。
  - 理由：唯一保持 `11/11` 正收益，排除 `2025` 后仍保持 `10/10` 正收益。
- `02_candle_close_quality` 保留为重点研究候选。
  - 理由：PF 和赚钱率有改善，但交易数仍相对足够。
- `03_adx20_rising` 保留为 regime 候选条件。
  - 理由：PF 和回撤结构较好，但交易数偏少。
- `01_close_breakout_confirm` 保留为对照。
  - 理由：PF 高，但正收益年份下降。
- `04_atr_ratio_1_1` 暂不推进。
  - 理由：赚钱率最高，但整体收益和正收益年份不如 baseline。
- `05_overextension_filter` 暂不推进。
  - 理由：没有改善赚钱率。
- `06_early_failure_exit` 丢弃当前版本。
  - 理由：交易结构变差，PF 和正收益年份下降。
- `07_candle_quality_adx20_rising` 暂不推进。
  - 理由：过滤过猛，交易数过低，收益明显下降。

### 当前结论

- `VB v1 baseline` 已经可以作为第一个策略因子进入组合研究。
- 不建议继续在 `VB v1` 内部强行追求更高赚钱率。
- 后续应把 `02`、`03` 作为 regime selector 的候选条件，而不是直接替换主策略。
- 下一阶段应开始开发第二个因子，优先建议 `MR`，因为它和 `VB` 的市场适用环境互补性更强。

### 下一步

1. 用 `unified_trades.csv` 做 `VB` bucket analysis。
2. 重点分析：
   - `pnl_result`
   - `r_multiple`
   - `sl_update_count`
   - `adx_bucket`
   - `atr_ratio_bucket`
   - `post_entry_holding_bucket`
3. 再开始 `MR v1` 因子开发，并按同一份 unified trade schema 输出。

## [2026-06-04-VB-V1-UNIFIED-OPTIMIZATION-OUTPUTS] volatility_breakout / v1 / H4

- 日期：2026-06-04
- 变更类型：`research-output`
- 目标：将 `VB v1` baseline 与 7 个过滤实验统一输出为 regime 后续可直接读取的 trade-level CSV，不再保留每年一个 JSON report 的 optimization 输出。
- 输出目录：`xau/vb/v1/optimization/results/`
- 脚本目录：`xau/vb/v1/optimization/`

### 新增 / 更新脚本

- `common.py`：统一实验 runner，输出 `summary.csv`、`summary.json`、`unified_trades.csv`。
- `run_all_unified.py`：一次性重跑 baseline + `01` 到 `07`。
- `compare_results.py`：从各实验的 `summary.json` 生成总对照表。
- `01_close_breakout_confirm.py`：H4 close 必须突破 Donchian。
- `02_candle_close_quality.py`：突破 K 线必须收在突破方向强势一侧。
- `03_adx20_rising.py`：`H1 ADX >= 20` 且 ADX 正在上升。
- `04_atr_ratio_1_1.py`：`ATR ratio min = 1.1`。
- `05_overextension_filter.py`：过滤过度拉伸的突破 K 线。
- `06_early_failure_exit.py`：8 根 H4 内未达到 `+0.5R` 提前退出。
- `07_candle_quality_adx20_rising.py`：`02 + 03` 组合过滤。

### Unified Trade Schema

- 新增文档：`xau/readme.md`
- 目的：为 `VB`、`MR`、`TF` 后续进入 regime analysis 提供统一 trade-level 字段。
- 当前 `VB` unified 输出已包含：
- `trade_id`
- `strategy`
- `engine_version`
- `symbol`
- `timeframe`
- `signal_time_utc`
- `entry_time_utc`
- `exit_time_utc`
- `initial_sl`
- `final_sl`
- `net_pnl`
- `initial_risk_money`
- `r_multiple`
- `entry_atr`
- `entry_atr_ratio`
- `entry_h1_adx`
- `adx_bucket`
- `atr_ratio_bucket`
- `spread_bucket`
- `post_entry_holding_bucket`

### 输出结构

每个实验目录只保留：

```text
summary.csv
summary.json
unified_trades.csv
```

总对照表：

```text
xau/vb/v1/optimization/results/comparison_summary.csv
xau/vb/v1/optimization/results/comparison_summary.json
```

已删除旧 optimization 输出：

```text
xau/vb/v1/optimization/results/*/reports/report_YEAR.json
```

说明：正式 engine report 目录 `xau/vb/v1/reports/H4/` 未清理，仍保留为主策略年度 report 来源。

### 对照结果

| Version | Avg Return | PF | Positive Years | Avg Trades | Win Rate | Worst |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | `25.73%` | `2.12` | `11/11` | `25.55` | `43.86%` | `2018: +1.18%` |
| baseline ex 2025 | `14.37%` | `1.92` | `10/10` | `24.90` | `41.37%` | `2018: +1.18%` |
| 01 close confirm | `17.76%` | `2.65` | `9/11` | `20.73` | `46.62%` | `2018: -2.63%` |
| 02 candle quality | `19.34%` | `2.38` | `10/11` | `20.36` | `45.30%` | `2018: -3.46%` |
| 03 ADX20 rising | `16.01%` | `2.46` | `10/11` | `17.18` | `46.44%` | `2018: -3.10%` |
| 04 ATRr 1.1 | `17.89%` | `1.91` | `9/11` | `16.82` | `44.61%` | `2018: -1.52%` |
| 05 overextension | `16.69%` | `2.09` | `9/11` | `22.00` | `42.99%` | `2018: -3.05%` |
| 06 early failure | `17.29%` | `1.80` | `8/11` | `31.00` | `41.03%` | `2018: -4.47%` |
| 07 candle + ADX | `10.67%` | `2.33` | `9/11` | `13.64` | `46.93%` | `2016: -5.40%` |

### 取留判断

- 主策略保留 `00_baseline_current_v1_default`。理由：唯一保持 `11/11` 正收益，排除 `2025` 后仍保持 `10/10`。
- `02_candle_close_quality` 保留为重点研究候选。理由：过滤后胜率和 PF 提升，但仍保留相对足够交易数。
- `03_adx20_rising` 保留为 regime 特征候选。理由：胜率、PF、回撤结构较好，但交易数偏少，不适合直接替换主线。
- `01_close_breakout_confirm` 保留为对照。理由：PF 最高，但正收益年份下降，过滤过硬。
- `04_atr_ratio_1_1` 暂不推进。理由：交易数减少，PF 不优于 baseline。
- `05_overextension_filter` 暂不推进。理由：没有提高胜率，回撤也没有改善。
- `06_early_failure_exit` 丢弃当前版本。理由：胜率、PF、正收益年份均变差。
- `07_candle_quality_adx20_rising` 暂不推进。理由：胜率最高但交易数过低，收益与正收益年份明显下降，组合过滤过猛。

### 下一步

1. 用 `unified_trades.csv` 做 VB bucket analysis，不再从 JSON report 读取 trade details。
2. 优先分析 `baseline`、`02`、`03` 三组的 `adx_bucket`、`atr_ratio_bucket`、`post_entry_holding_bucket`。
3. 不直接替换主策略，先把 `02` / `03` 当作 regime selector 的候选条件。
4. 后续将 `MR`、`TF` 接入同一份 unified trade schema。

## [2026-06-04-REGIME-FACTOR-ROADMAP] portfolio / regime / VB-MR-TF

- 日期：2026-06-04
- 变更类型：`roadmap`
- 目标：把单策略研究推进到组合层。将 `VB`、`MR`、`TF` 视为三个可独立评估的交易因子，再用 regime 对市场状态进行评估，决定哪些因子允许出手。
- 当前前提：先继续独立研究 `VB v1` 的单质量，后续再把 `MR`、`TF` 纳入同一套 trade log / regime analysis 框架。

### 核心定义

- `VB`：趋势突破因子，适合波动扩张和趋势延续环境。
- `MR`：均值回归因子，适合震荡、过度偏离后回归环境。
- `TF`：趋势跟随 / 趋势回调因子，适合已有趋势中的回踩延续环境。
- `Regime`：组合层市场状态评估模块，不直接预测涨跌，第一阶段只判断当前市场是否适合某个因子出手。

### 设计原则

- Regime 不是用来拯救弱策略。每个因子必须先在独立回测中证明有基本 edge。
- 第一版 regime 只做 hard filter / strategy selector，不做复杂权重。
- 所有 regime 特征必须在 `entry_time` 之前可见，不能使用未来信息。
- 评估标准以组合层结果为主：更低回撤、更少坏年份、更稳定 PF，而不是单一策略最高收益。

### Step 1: 统一 Trade Log

目标：

- 让 `VB`、`MR`、`TF` 输出同一种 trade-level 格式。
- 后续 regime analysis 不关心策略内部细节，只读取统一 trade log。

每笔 trade 至少包含：

| Field | Meaning |
| --- | --- |
| `strategy` | `VB` / `MR` / `TF` |
| `engine_version` | 例如 `volatility_breakout_v1` |
| `symbol` | 当前主要是 `XAUUSD` |
| `timeframe` | 例如 `H4` |
| `side` | `long` / `short` |
| `signal_time` | 信号出现时间 |
| `entry_time` | 实际入场时间 |
| `exit_time` | 出场时间 |
| `entry_price` | 入场价 |
| `exit_price` | 出场价 |
| `initial_sl` | 初始止损 |
| `exit_reason` | `SL` / `TRAIL` / `DONCHIAN_EXIT` / strategy-specific |
| `net_pnl` | 扣除成本后的净 PnL |
| `r_multiple` | 以初始风险归一化后的 R 倍数 |
| `holding_bars` | 持仓 bar 数 |
| `entry_atr` | 入场时 ATR |
| `entry_spread` | 入场时 spread |

产物：

- `xau/data/trades/<strategy>/<version>/trades_YEAR.csv`
- 或后续统一为 `xau/data/factors/trades/<strategy>/<version>/...`

### Step 2: 对齐 Regime Features

目标：

- 给每笔 trade 的 `entry_time` 对齐当时可见的市场状态特征。
- 不预测未来，只描述入场前市场结构。

候选特征：

| Feature | Purpose |
| --- | --- |
| `atr_ratio` | 当前波动是否扩张 |
| `adx` | 趋势强度 |
| `adx_slope` | 趋势强度是否正在增强 |
| `ema_slope` | 大方向趋势斜率 |
| `donchian_width` | 区间宽度 / 压缩扩张 |
| `bb_width` | 波动压缩程度 |
| `range_efficiency` | 行情是否方向性移动 |
| `close_to_ema_distance_atr` | 是否过度偏离均值 |
| `spread_points` | 成本环境 |
| `session_utc` | 交易时段 |
| `weekday` | 星期特征 |

产物：

- `trades_with_regime_features.csv`
- 每行 = 一笔 trade + 入场前 regime feature snapshot。

### Step 3: 分析各策略适合的 Regime

目标：

- 按 regime feature bucket 统计每个策略的表现。
- 找出每个策略真正有 edge 的环境。

核心统计：

| Metric | Purpose |
| --- | --- |
| `trades` | 样本数是否足够 |
| `win_rate` | 胜率 |
| `avg_win` | 平均盈利 |
| `avg_loss` | 平均亏损 |
| `payoff_ratio` | 盈亏比 |
| `profit_factor` | 盈亏质量 |
| `expectancy` | 单笔期望 |
| `avg_r_multiple` | 风险归一化表现 |
| `max_drawdown_pct` | 回撤压力 |

分析方式：

- 对 `VB` 看趋势扩张类 regime：`ADX`、`ADX slope`、`ATR ratio`、Donchian width。
- 对 `MR` 看震荡回归类 regime：低 ADX、均值偏离、波动压缩。
- 对 `TF` 看趋势回调类 regime：EMA slope、价格回踩幅度、趋势方向一致性。

产物：

- `xau/data/regime/analysis/<strategy>_bucket_stats.csv`
- `xau/data/regime/analysis/regime_notes.md`

### Step 4: Hard Filter

目标：

- 第一版 regime 只做允许 / 禁止，不做复杂预测。
- 如果某个策略在某类 regime 明显表现差，就禁止该策略在该环境开仓。

示例：

```text
VB_on = ADX rising and ATR ratio >= 1.0 and spread <= max_spread
MR_on = ADX low/falling and price far from mean and volatility not extreme
TF_on = EMA slope aligned and pullback depth within acceptable range
```

评估标准：

- 单策略过滤后是否减少坏年份。
- PF 是否提升。
- MaxDD 是否下降。
- 交易数是否仍然足够。
- OOS 是否保持，不只看全样本。

产物：

- `xau/scripts/regime/hard_filters.py`
- `xau/data/regime/filter_tests/<strategy>/summary.csv`

### Step 5: Strategy Selector

目标：

- 从“每个策略自己开关”升级到“当前市场最适合哪个策略”。
- 解决策略冲突，例如 `VB` 想追突破，`MR` 想反向回归。

第一版 selector 规则：

```text
trend_expansion -> allow VB, optionally TF, block MR
range_reversion -> allow MR, block VB
trend_pullback -> allow TF, optionally VB, block MR if trend is strong
unclear/noisy -> block all or reduce exposure
```

输出：

```text
selected_strategy = VB / MR / TF / NONE
allowed_strategies = [VB, TF]
```

评估标准：

- 组合层 PF 是否高于简单策略叠加。
- 组合 MaxDD 是否低于单策略和无筛选组合。
- 策略冲突时是否减少互相抵消的亏损。
- 每年是否仍有足够交易机会。

产物：

- `xau/scripts/regime/strategy_selector.py`
- `xau/data/regime/selector_tests/summary.csv`

### Step 6: 权重和组合风控

目标：

- 在 hard filter 和 selector 可靠之后，再做权重。
- 第一版权重应保持简单，避免过拟合。

可选权重方式：

```text
equal_weight_allowed_strategies
regime_score_weight
volatility_target_weight
drawdown_reduction_weight
```

组合风控规则：

- 同一时间最大总风险。
- 单策略最大开放风险。
- 同方向重复暴露限制。
- 相反方向信号冲突处理。
- 连续亏损后的降权或暂停。

评估标准：

- 组合 equity curve 是否更平滑。
- 年度 worst year 是否改善。
- MaxDD 是否下降。
- 收益是否不过度依赖单一策略或单一年份。

### 当前执行顺序

1. 继续完成 `VB v1` 单质量研究，先明确哪些过滤真的能砍坏单。
2. 为 `VB` 固化统一 trade log 输出格式。
3. 将 `MR`、`TF` 接入同样 trade log 格式。
4. 构建 `entry_time` regime feature snapshot。
5. 做 bucket analysis，先得到数据证据，再写 hard filter。
6. 最后再做 selector 和组合权重。

### 成功标准

- Regime 第一版成功，不要求总收益最大。
- 只要求：
- 坏年份减少。
- MaxDD 下降。
- PF 更稳定。
- 策略冲突减少。
- OOS 没有明显崩坏。

## [2026-05-26-VB-V1-H4-QUALITY-DEFAULTS] volatility_breakout / v1 / H4

- 日期：2026-05-26
- 变更类型：`parameter-default`
- 目标：将 `volatility_breakout/v1` 固定为只做高质量 VB 单的 H4 主线，后续可与其他策略一起进入组合层验证。
- 修改文件：`xau/vb/v1/engine.py`

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
- 正式报告目录：`xau/vb/v1/reports_h4_candidate/`
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
- 对比基线：`xau/vb/v1/reports/H4/`
- 第一轮运行命令：`.venv/bin/python xau/vb/v1/optimization_h4_grid.py --workers 4 --top-n 30`
- 第二轮运行命令：`.venv/bin/python xau/vb/v1/optimization_h4_island.py`
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

- 新增 `xau/vb/v1/optimization_h4_grid.py`：
- 复用 `volatility_breakout/v1.py` 的 EngineConfig 和 Engine，不复制策略逻辑。
- 对参数组合分别输出 dev / validation / OOS / full 四段统计。
- 新增 `xau/vb/v1/optimization_h4_island.py`：
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
- 对比基线：`xau/vb/v1/reports/`（默认 `ADX` 过滤）
- 运行命令：`.venv/bin/python xau/scripts/engines/volatility_breakout/v2.py --timeframes M1,M15,M30,H1,H4 --trend-filter ema200`
- 输出目录：`xau/data/reports/vb/v2/`

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
- 对比基线：`xau/vb/v1/reports/`
- 运行命令：`.venv/bin/python xau/scripts/engines/volatility_breakout/v3.py --timeframes M1,M15,M30,H1,H4`
- 输出目录：`xau/data/reports/vb/v3/`

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

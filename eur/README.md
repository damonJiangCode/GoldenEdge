# EUR 回测工作区说明

这个目录是 EURUSD M15 回测与优化的独立工作区。  
目标不是追求某一年最高收益，而是看策略在多年数据上的稳定性（特别是样本外表现）。

## 1. 目录结构（你最常看这几块）

- `eur/data/historical/`
  - 历史数据，当前是 `M15_2017.csv ... M15_2025.csv`
- `eur/scripts/backtest/engine_1.py`
  - 单次回测引擎（基准策略）
- `eur/scripts/backtest/run_yearly_backtests.py`
  - 按年批量跑回测（2017-2025），并自动出汇总
- `eur/scripts/backtest/optimize_base_strategy.py`
  - 网格参数优化（按 Train/Validation/Test 打分）
- `eur/data/backtest/runs/`
  - 每次“按年批跑”的结果目录
- `eur/data/backtest/optimizations/`
  - 每次“参数优化”的结果目录
- `eur/data/backtest/samples/`
  - 样例/模板输出（单次回测默认写到这里）

## 2. 数据要求（CSV 必须有这些列）

`engine_1.py` 读取 CSV 时要求以下列名存在：

- `time`
- `open`
- `high`
- `low`
- `close`
- `tick_volume`
- `spread`

说明：
- `time` 会转成 UTC 时间并排序去重
- 缺失/无效价格会被清理
- `spread` 的单位按 MT point 处理（EURUSD: `1 point = 0.00001`）

## 3. 三个脚本分别做什么

### A) 单文件回测：`engine_1.py`

用途：对单个年份或单个 CSV 直接跑一次策略。

示例：
```bash
.venv/bin/python eur/scripts/backtest/engine_1.py \
  --input eur/data/historical/M15_2025.csv \
  --output eur/data/backtest/samples/EUR_simple_backtest_report.json
```

常用参数：
- `--initial-balance` 初始资金（默认 1000）
- `--lot-size` 手数（默认 0.005）
- `--slippage-pips` 滑点
- `--commission-per-lot-per-side` 手续费
- `--confirm-use-rsi` 是否启用 RSI 二次确认（开关）

---

### B) 按年批跑：`run_yearly_backtests.py`

用途：把 2017-2025 每年跑一遍，并自动汇总。

示例（你现在常用）：
```bash
.venv/bin/python eur/scripts/backtest/run_yearly_backtests.py \
  --run-dir eur/data/backtest/runs/2026-02-21-base
```

默认数据分组（可改）：
- Train: 2017-2021
- Validation: 2022-2023
- Test: 2024-2025

输出结构：
- `reports/EUR_M15_YYYY_report.json`：每年一份详细报告
- `summary/yearly_summary.csv`：年度总表（最常用于横向比较）
- `summary/yearly_summary.json`：机器可读汇总
- `summary/README.md`：本次运行摘要（总收益、OOS consistency 等）
- `config/run_config.json`：本次参数和代码版本（`code_version`）

---

### C) 参数优化：`optimize_base_strategy.py`

用途：在给定参数网格里批量试验，按 Train/Validation/Test 综合打分，找“更稳”的组合。

示例（首轮小网格）：
```bash
PYTHONUNBUFFERED=1 .venv/bin/python -u eur/scripts/backtest/optimize_base_strategy.py \
  --run-dir eur/data/backtest/optimizations/2026-02-21-priority0-opt1 \
  --adx-grid 19,21 \
  --rsi-grid 70:30,72:28 \
  --atr-sl-grid 0.8,1.0 \
  --atr-tp-grid 1.8,2.2 \
  --confirm-rsi-grid false,true
```

输出结构：
- `trials/trials_all.csv`：所有参数组合 + 分数（已排序）
- `summary/top10.csv`：前 10 组合
- `summary/best_params.json`：最佳参数摘要
- `summary/best_yearly_results.csv`：最佳参数的逐年表现
- `config/run_config.json`：网格范围、分组设置、评分公式、代码版本

## 4. 关键指标怎么理解（大白话）

- `return_pct`：这一年的收益率（正数赚钱，负数亏钱）
- `max_drawdown_pct`：最大回撤（越小越稳）
- `profit_factor`：总盈利 / 总亏损（>1 通常更健康）
- `sharpe_per_trade`：每笔交易收益稳定性（越高越好）
- `trades`：交易次数（太少可能不可靠）
- `oos_consistency`：样本外（Validation+Test）里正收益年份占比

## 5. 怎么看“改动前后谁更好”

每次你改策略后，按下面流程：

1. 新建一个 run 目录名（建议带日期和标签）  
   例：`eur/data/backtest/runs/2026-02-22-v2`

2. 跑批量按年回测  
```bash
.venv/bin/python eur/scripts/backtest/run_yearly_backtests.py \
  --run-dir eur/data/backtest/runs/2026-02-22-v2
```

3. 对比两份 `yearly_summary.csv`  
   重点看：
- Validation/Test 的 `return_pct` 是否改善
- `max_drawdown_pct` 是否下降
- `profit_factor` 是否上升
- `oos_consistency` 是否提高

结论标准建议：
- 如果只在 Train 变好，而 Validation/Test 变差，基本是过拟合
- 如果 Validation/Test 同时改善，才算有效优化

## 6. 当前已完成的基础设施（Priority 0）

已经落地的内容：
- 统一指标：Net PnL / MaxDD / ProfitFactor / Sharpe / TradeCount
- 固定分组：Train / Validation / Test
- 成本模型统一：spread/slippage/commission 一致使用
- 实验可追踪：每次输出记录参数与 `code_version`

## 7. 常见注意事项

- 请优先用 `.venv/bin/python` 运行（系统 Python 可能缺少 `numpy/pandas`）
- 不要用单一年份评估策略是否有效
- 参数网格先粗后细：先大范围找方向，再局部细化
- 保留每次 run/optimization 目录，方便之后回看和复盘

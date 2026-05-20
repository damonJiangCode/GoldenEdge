# XAU Workspace

这个目录现在只保留两类核心资产：

- `data/market_data/`: XAU 历史行情 CSV。
- `scripts/engines/`: 可运行的策略回测 engine。

`research/changelog.md` 和 `research/notes.md` 是研究记录。之前的 optimization、diagnostics、validation、reports 已经清理掉；engine 运行时会按需要重新生成 `data/reports/...` 输出目录。

## Data Format

所有 engine 都读取 CSV，并要求至少包含这些列：

```text
time, open, high, low, close, tick_volume, spread
```

约定：

- `time` 会按 UTC 解析。
- `spread` 是 points，不是价格差；默认 `point_value=0.01`。
- 默认数据目录是 `xau/data/market_data/`。
- 如果不传 `--input`，多数 engine 会自动扫描 `data/market_data` 下的 CSV。

## Engines Overview

当前有三组策略：

```text
scripts/engines/
  volatility_breakout/
    v1.py
    v2.py
    v3.py
  trend_pullback/
    v1.py
    v3.py
  mean_reversion/
    v1.py
```

### Volatility Breakout

路径：`scripts/engines/volatility_breakout/`

核心思想：用 Donchian 通道找突破，用 ATR 扩张过滤假突破，再用止损和 trailing stop 管理出场。

共同逻辑：

- 入场：当前 bar 的 `high/low` 触发 Donchian 上/下轨突破，下一根 bar 市价入场。
- 过滤：ATR ratio、spread、UTC session，部分版本还用 H1 ADX 或 EMA 趋势过滤。
- 出场：初始 SL = ATR 倍数；trailing 支持 `chandelier` 或 `donchian`。
- 成本：模拟 spread、slippage、commission、swap。
- 仓位：默认 `0.01 lot`，`contract_size=100`。

版本区别：

- `v1.py`: 基础版。Donchian 突破 + ATR ratio + H1 ADX 过滤，单仓位，不加仓。
- `v2.py`: 趋势过滤实验版。把趋势过滤抽成 `--trend-filter none|adx|ema200|both`，默认 `ema200`，单仓位。
- `v3.py`: 加仓版。在 V1 框架上加入 pyramiding。盈利达到 R 阈值后可加层，每层 size 按 `pyramid_size_decay` 衰减，并尝试把风险控制在原始 1R 附近。

常用运行方式：

```bash
python xau/scripts/engines/volatility_breakout/v1.py --timeframes H1,H4
python xau/scripts/engines/volatility_breakout/v2.py --input xau/data/market_data/H4/H4_2025.csv --trend-filter ema200
python xau/scripts/engines/volatility_breakout/v3.py --timeframes H4 --pyramid-max-layers 3
```

默认输出：

```text
xau/data/reports/volatility_breakout/v<version>/<TF>/report_YEAR.json
```

### Trend Pullback

路径：`scripts/engines/trend_pullback/`

当前状态：

- `v1.py`: 已实现。
- `v3.py`: 未实现，占位，运行会直接退出。
- `v2.py`: 已删除，因为只是未实现占位。

V1 核心思想：顺势回调。用 EMA50/EMA200 判断趋势，价格回踩 EMA50 后继续站回趋势方向才入场。

主要逻辑：

- 多头趋势：`EMA50 > EMA200`，`EMA200` 斜率向上，`close > EMA200`。
- 空头趋势：`EMA50 < EMA200`，`EMA200` 斜率向下，`close < EMA200`。
- 回调确认：触碰/穿越 EMA50 后收回趋势方向。
- 深度过滤：回调深度至少达到 `pullback_depth_atr_mult * ATR`。
- 出场：固定 SL/TP，默认 `SL=2*ATR`，`TP=3R`。
- 报告中会统计 regime：`true_track_up`、`true_track_down`、`fake_track`、`neutral`。

常用运行方式：

```bash
python xau/scripts/engines/trend_pullback/v1.py --input xau/data/market_data/H4/H4_2025.csv
python xau/scripts/engines/trend_pullback/v1.py --atr-sl-mult 2.0 --tp-rr 3.0
```

默认输出：

```text
xau/data/reports/trend_pullback/v1/<TF>/report_YEAR.json
```

### Mean Reversion

路径：`scripts/engines/mean_reversion/v1.py`

核心思想：均值回归。用 EMA20 作为均值，价格偏离到 `EMA +/- ATR band` 后，结合蜡烛确认做反向交易，目标回到 EMA。

主要逻辑：

- 均值：默认 `EMA20`。
- 偏离带：默认 `EMA +/- 2*ATR`。
- 多头：触碰下轨，并出现 bullish 或长下影确认。
- 空头：触碰上轨，并出现 bearish 或长上影确认。
- 趋势过滤：H1 ADX 高于阈值时不做，默认 `h1_adx_limit=25`。
- 波动过滤：ATR ratio 必须在默认 `[0.8, 1.6]` 之间。
- 极端 bar 过滤：跳过 body 明显放大的 fat-tail bar。
- 时间过滤：默认只做 `00:00-06:00 UTC`。
- 出场：TP 目标是 EMA；SL 默认 `1*ATR`；价格回归到一定比例后把 SL 推到 breakeven。

常用运行方式：

```bash
python xau/scripts/engines/mean_reversion/v1.py --input xau/data/market_data/M15/M15_2025.csv
python xau/scripts/engines/mean_reversion/v1.py --session-start-hour-utc 0 --session-end-hour-utc 6
```

默认输出：

```text
xau/data/reports/mean_reversion/v1/<TF>/report_YEAR.json
```

## Report Contents

每个已实现 engine 的 JSON report 通常包含：

- `engine`, `input_file`, `bars`, `time_start_utc`, `time_end_utc`
- `initial_balance`, `final_balance`, `final_equity`
- `trades`, `win_rate`
- `performance`: net PnL、return、profit factor、expectancy、drawdown 等
- `costs`: spread/slippage/commission/swap 统计
- `filters` 或 `params`: 当前运行参数和过滤计数
- `equity_series`: bar-by-bar equity
- `sample_trades`: 前 30 笔交易样本

## Current Road

当前比较像三条策略路线：

- 趋势突破：优先看 `volatility_breakout/v1.py` 和 `v2.py`。V3 是加仓实验，风险模型更复杂。
- 顺势回调：只看 `trend_pullback/v1.py`，V3 还没写。
- 夜盘/低趋势均值回归：看 `mean_reversion/v1.py`。

如果要继续推进，建议先固定一个目标：

1. 先选一个 engine 和一个 timeframe。
2. 只跑最近几年或单年数据，确认信号和交易明细合理。
3. 再做参数搜索或 walk-forward。
4. 最后才考虑 MT5 实盘/模拟盘转换。

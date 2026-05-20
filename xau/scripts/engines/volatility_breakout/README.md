# Volatility Breakout Engines

这一组 engine 是 XAU 的趋势突破路线。核心假设是：当波动扩张、点差可接受、趋势强度足够时，价格突破近期 Donchian 通道后可能延续一段趋势。

## Shared Model

三个版本都围绕同一套基础结构：

- 数据：读取 `xau/data/market_data/<TF>/*.csv`，必须包含 `time, open, high, low, close, tick_volume, spread`。
- 信号：当前 bar 的 `high/low` 触发 Donchian 上/下轨突破。
- 成交：信号出现后，下一根 bar 市价入场。
- 成本：模拟 spread、slippage、commission、swap。
- 出场：初始 ATR 止损，之后用 trailing stop 或 Donchian exit。
- 报告：输出 JSON 到 `xau/data/reports/volatility_breakout/v*/<TF>/report_YEAR.json`。

默认成本和仓位：

```text
initial_balance = 1000
lot_size = 0.01
contract_size = 100
point_value = 0.01
slippage_ticks = 1
commission_per_trade = 0.05
```

默认突破参数：

```text
donchian_breakout_period = 20
donchian_exit_period = 10
atr_period = 14
atr_ratio_lookback = 100
atr_ratio_min = 1.0
spread_max_points = 30
sl_atr_mult = 2.0
trail_mode = chandelier
trail_atr_mult = 3.0
```

## V1

文件：`v1.py`

V1 是基础版，结构最干净，适合当 baseline。

过滤条件：

- `atr_ratio >= atr_ratio_min`
- `spread <= spread_max_points`
- H1 ADX filter 默认开启：`h1_adx >= 20`

入场：

```text
high >= previous 20-bar Donchian high -> long
low <= previous 20-bar Donchian low -> short
```

如果同一根 bar 同时突破上下轨，会跳过，因为无法知道先后顺序。

出场：

- 默认 `chandelier`: 根据入场后的最高/最低点和 ATR 推进止损。
- 可选 `donchian`: 碰到前 10 根 Donchian 反向通道后出场。

仓位：

- 单仓位。
- 不反手。
- 不加仓。

运行：

```bash
python xau/scripts/engines/volatility_breakout/v1.py --timeframes H1,H4
python xau/scripts/engines/volatility_breakout/v1.py --input xau/data/market_data/H4/H4_2025.csv
python xau/scripts/engines/volatility_breakout/v1.py --input xau/data/market_data/H4/H4_2025.csv --disable-h1-adx-filter
```

适合回答的问题：

```text
XAU 在 ATR 扩张并且 H1 ADX 有趋势强度时，Donchian 突破是否能靠 trailing stop 捕捉趋势。
```

## V2

文件：`v2.py`

V2 是趋势过滤实验版。它保留 V1 的 Donchian 突破和出场结构，但把趋势过滤扩展为可选模式。

新增参数：

```text
trend_filter = none | adx | ema200 | both
ema_period = 200
```

过滤模式：

- `none`: 不做趋势过滤，只保留 ATR ratio 和 spread。
- `adx`: 只要求 H1 ADX 达标。
- `ema200`: long 只允许 `close > EMA200`，short 只允许 `close < EMA200`。
- `both`: ADX 和 EMA200 方向都必须通过。

默认模式是：

```text
trend_filter = ema200
```

运行：

```bash
python xau/scripts/engines/volatility_breakout/v2.py --timeframes H1,H4
python xau/scripts/engines/volatility_breakout/v2.py --input xau/data/market_data/H4/H4_2025.csv --trend-filter ema200
python xau/scripts/engines/volatility_breakout/v2.py --input xau/data/market_data/H4/H4_2025.csv --trend-filter both
```

适合回答的问题：

```text
Donchian 突破是否需要方向性 EMA 过滤，还是只靠 ADX 趋势强度就够。
```

## V3

文件：`v3.py`

V3 是加仓实验版。它基于 V1 的突破模型，在盈利方向达到 R 阈值后允许 pyramiding。

新增参数：

```text
enable_pyramiding = True
pyramid_trigger_r = 1.0
pyramid_max_layers = 3
pyramid_size_decay = 0.5
```

加仓逻辑：

- 第一层正常入场。
- 当价格相对第一层 entry favorable move 达到指定 R 阈值时，尝试加下一层。
- 第二层 size 默认是第一层的 `0.5`，第三层默认是 `0.25`。
- 每层有自己的 entry、SL、commission、PnL。
- 已盈利的层会尝试把 SL 推到 breakeven。
- 新增层时会检查总开放风险，尽量把风险控制在原始 1R 附近。

出场：

- 每一层独立检查 SL 或 Donchian exit。
- 报告里的 `trade_details` 是按 layer 记录，而不是按 campaign 记录。

运行：

```bash
python xau/scripts/engines/volatility_breakout/v3.py --timeframes H4
python xau/scripts/engines/volatility_breakout/v3.py --input xau/data/market_data/H4/H4_2025.csv --pyramid-max-layers 3
python xau/scripts/engines/volatility_breakout/v3.py --input xau/data/market_data/H4/H4_2025.csv --disable-pyramiding
```

适合回答的问题：

```text
突破策略的收益是否主要来自少数大趋势，以及加仓是否能放大右尾，同时不显著扩大左尾。
```

## Practical Notes

- V1 是 baseline，优先用它确认数据、信号和成本是否合理。
- V2 用来比较趋势过滤质量。
- V3 风险模型更复杂，建议在 V1/V2 已经稳定后再看。
- `leverage` 目前只是报告参数，没有真实 margin check。
- 这些 engine 是 backtest engine，不是 MT5 下单脚本。

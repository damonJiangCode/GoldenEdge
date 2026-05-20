# Mean Reversion Engines

这一组 engine 是 XAU 的均值回归路线。核心假设是：在趋势强度不高、波动没有失控的时间段里，价格偏离均值后有机会回到 EMA。

## Current Files

```text
v1.py  implemented
```

## V1

文件：`v1.py`

V1 使用 EMA20 作为均值，用 ATR band 定义偏离区域。

默认核心参数：

```text
ema_period = 20
atr_period = 14
band_atr_mult = 2.0
sl_atr_mult = 1.0
adx_period = 14
h1_adx_limit = 25
atr_ratio_lookback = 100
atr_ratio_min = 0.8
atr_ratio_max = 1.6
session_start_hour_utc = 0
session_end_hour_utc = 6
wick_body_ratio = 1.5
fat_tail_body_lookback = 5
fat_tail_body_mult = 2.0
breakeven_retrace_ratio = 0.5
```

指标：

- `EMA20`: 均值目标。
- `ATR14`: 波动单位。
- `upper_band = EMA + 2 * ATR`
- `lower_band = EMA - 2 * ATR`
- H1 ADX: 用于过滤趋势环境。
- ATR ratio: 当前 ATR 相对过去 100 根 ATR 均值。

入场过滤：

- H1 ADX 必须低于 `h1_adx_limit`，默认 `< 25`。
- ATR ratio 必须在 `[0.8, 1.6]`。
- fat-tail bar 会跳过，避免在极端动量 bar 上反向接刀。
- 默认只在 `00:00-06:00 UTC` 入场。

信号：

多头：

```text
low <= lower_band
并且 candle bullish 或出现长下影
```

空头：

```text
high >= upper_band
并且 candle bearish 或出现长上影
```

出场：

- TP：目标是 EMA。
- SL：默认 `1 * ATR`。
- Breakeven：当价格回归到一定比例后，把 SL 推到 entry。

仓位：

- 单仓位。
- 不加仓。
- 不反手。

运行：

```bash
python xau/scripts/engines/mean_reversion/v1.py --input xau/data/market_data/M15/M15_2025.csv
python xau/scripts/engines/mean_reversion/v1.py --session-start-hour-utc 0 --session-end-hour-utc 6
python xau/scripts/engines/mean_reversion/v1.py --band-atr-mult 2.0 --sl-atr-mult 1.0
```

默认输出：

```text
xau/data/reports/mean_reversion/v1/<TF>/report_YEAR.json
```

## Practical Notes

- 这条路线和 breakout 正好相反：它不想在趋势很强时交易。
- H1 ADX filter 是关键保护层，默认趋势强度高于 25 就不做。
- session 默认偏夜盘/低波动窗口，如果换 timeframe 或 broker server 数据，需要重新验证。
- TP 到 EMA 意味着盈亏比不是固定的，会随 entry 和 EMA 的距离变化。

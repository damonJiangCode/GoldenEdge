# Trend Pullback Engines

这一组 engine 是 XAU 的顺势回调路线。核心假设是：在明确趋势里，价格回踩短期均线后重新站回趋势方向，可能继续顺趋势运行。

## Current Files

```text
v1.py  implemented
v3.py  placeholder, not implemented
```

`v2.py` 已删除，因为只是未实现占位。

## V1

文件：`v1.py`

V1 是目前唯一可运行版本。

核心指标：

```text
EMA fast = 50
EMA slow = 200
ATR = 14
ADX = 14
ATR percentile window = 200
```

多头趋势条件：

```text
EMA50 > EMA200
EMA200 slope > 0
close > EMA200
```

空头趋势条件：

```text
EMA50 < EMA200
EMA200 slope < 0
close < EMA200
```

回调条件：

- 多头：`low <= EMA50` 且 `close > EMA50`。
- 空头：`high >= EMA50` 且 `close < EMA50`。
- 回调深度必须至少达到 `pullback_depth_atr_mult * ATR`，默认 `0.3 * ATR`。

出场：

```text
SL = 2 * ATR
TP = 3R
```

仓位：

- 单仓位。
- 不加仓。
- 不反手。
- 没有强制年末平仓或数据结束平仓。

报告会额外统计 market regime：

```text
true_track_up
true_track_down
fake_track
neutral
```

这些 regime 基于 EMA200 slope、ADX 和 ATR percentile，用来观察交易发生在哪种市场状态里。

运行：

```bash
python xau/scripts/engines/trend_pullback/v1.py --input xau/data/market_data/H4/H4_2025.csv
python xau/scripts/engines/trend_pullback/v1.py --atr-sl-mult 2.0 --tp-rr 3.0
python xau/scripts/engines/trend_pullback/v1.py --pullback-depth-atr-mult 0.3
```

默认输出：

```text
xau/data/reports/trend_pullback/v1/<TF>/report_YEAR.json
```

## V3

文件：`v3.py`

当前未实现，运行会直接退出：

```text
trend_pullback v3 is not implemented yet.
```

如果之后继续写，建议不要直接从 V1 堆复杂度。更好的顺序是：

1. 先给 V1 加更明确的 session/spread filter。
2. 再决定 V2 是做 trailing exit，还是做 multi-timeframe trend confirmation。
3. 最后再考虑 V3 是否需要 partial exit 或 pyramiding。

## Practical Notes

- 这条路线和 `volatility_breakout` 不同，它不是追突破，而是在趋势里等回调。
- V1 的优势是逻辑容易检查，SL/TP 很明确。
- 弱点是 EMA 回调可能在震荡里频繁假信号，所以 regime 和 ADX 相关统计很重要。

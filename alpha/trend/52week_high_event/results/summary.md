# 52-Week High Event Study Summary

## 1. 研究问题

当资产首次突破过去 52 周最高收盘价时，未来收益是否显著高于随机时期？
这里验证的是事件本身是否具有预测未来收益的能力，不是验证某个交易策略。

## 2. 事件定义

- Price: `Adj Close`
- `rolling_high_252 = AdjClose.shift(1).rolling(252).max()`
- `new_high = AdjClose > rolling_high_252`
- `event = new_high & (~new_high.shift(1).fillna(False))`
- 连续创新高只记录第一次突破，减少样本重叠。
- Forward returns: `FR20`, `FR60`, `FR120`; 未来数据不足的样本直接丢弃。

## 3. 对照组与统计口径

- 从全部非事件日中 bootstrap 抽样 `1000` 次。
- 每次抽取数量等于对应事件样本数量。
- `p_value` 为事件均值相对 bootstrap 随机均值分布的双侧经验 p-value。
- `normal_approx_p_value` 保留在 CSV 中，作为 t-statistic 的正态近似参考。
- `cohens_d` 用事件日收益和全部可用非事件日收益的 pooled std 计算。

## 4. 总体结果

| horizon | event_sample_count | event_mean | random_mean | difference | t_statistic | p_value | cohens_d | event_win_rate | interpretation |
|---|---|---|---|---|---|---|---|---|---|
| FR20 | 2413 | 0.61% | 0.52% | 0.09% | 0.79 | 0.44 | 0.02 | 60.63% | B_event_approximately_random |
| FR60 | 2385 | 2.02% | 1.55% | 0.47% | 2.34 | 0.02 | 0.05 | 68.55% | A_supports_trend_alpha |
| FR120 | 2321 | 3.95% | 3.13% | 0.83% | 2.81 | 0.01 | 0.06 | 72.04% | A_supports_trend_alpha |

## 5. Event Group 单独统计

| horizon | sample_count | mean | median | std | win_rate |
|---|---|---|---|---|---|
| FR20 | 2413 | 0.61% | 0.39% | 4.29% | 60.63% |
| FR60 | 2385 | 2.02% | 1.63% | 7.23% | 68.55% |
| FR120 | 2321 | 3.95% | 2.95% | 10.95% | 72.04% |

## 6. Bootstrap Random Group

| horizon | bootstrap_runs | mean | std | percentile_5 | percentile_95 |
|---|---|---|---|---|---|
| FR20 | 1000 | 0.52% | 0.11% | 0.33% | 0.70% |
| FR60 | 1000 | 1.55% | 0.20% | 1.22% | 1.88% |
| FR120 | 1000 | 3.13% | 0.29% | 2.62% | 3.62% |

## 7. 分资产类别结果

| asset_class | horizon | event_sample_count | event_mean | random_mean | difference | p_value | cohens_d | event_win_rate | interpretation |
|---|---|---|---|---|---|---|---|---|---|
| bond | FR20 | 841 | 0.18% | 0.30% | -0.12% | 0.15 | -0.05 | 58.98% | B_event_approximately_random |
| bond | FR60 | 826 | 0.92% | 0.89% | 0.03% | 0.84 | 0.01 | 68.89% | B_event_approximately_random |
| bond | FR120 | 808 | 1.31% | 1.78% | -0.47% | 0.03 | -0.08 | 70.67% | C_event_weaker_than_random |
| commodity | FR20 | 403 | 2.17% | 0.44% | 1.73% | 0.00 | 0.23 | 57.82% | A_supports_trend_alpha |
| commodity | FR60 | 398 | 4.47% | 1.43% | 3.04% | 0.00 | 0.23 | 64.82% | A_supports_trend_alpha |
| commodity | FR120 | 383 | 7.72% | 2.92% | 4.80% | 0.00 | 0.25 | 68.41% | A_supports_trend_alpha |
| equity | FR20 | 1169 | 0.37% | 0.79% | -0.41% | 0.01 | -0.07 | 62.79% | C_event_weaker_than_random |
| equity | FR60 | 1161 | 1.96% | 2.25% | -0.29% | 0.33 | -0.03 | 69.60% | B_event_approximately_random |
| equity | FR120 | 1130 | 4.57% | 4.57% | 0.00% | 0.99 | 0.00 | 74.25% | B_event_approximately_random |

## 8. 结果解释框架

- 情况 A: `Event Return > Random Return` 且差异显著，支持 Trend Alpha。
- 情况 B: `Event Return ≈ Random Return`，不支持 Trend Alpha。
- 情况 C: `Event Return < Random Return`，说明突破 52 周新高之后未来收益弱于普通时期。
- 注意: 收益较低不等于负收益，也不等于适合做空。
- 因此需要单独看 Event Group 中 `FR20 > 0`, `FR60 > 0`, `FR120 > 0` 的比例，也就是上表的 `event_win_rate`。

## 9. 总体判断

- FR20: Event mean 0.61%, Random mean 0.52%, Difference 0.09%, p-value 0.44; 结论: 不支持 Trend Alpha.
- FR60: Event mean 2.02%, Random mean 1.55%, Difference 0.47%, p-value 0.02; 结论: 支持 Trend Alpha.
- FR120: Event mean 3.95%, Random mean 3.13%, Difference 0.83%, p-value 0.01; 结论: 支持 Trend Alpha.

## 10. 事件数量

- Total first-breakout events before forward-return horizon filtering: `2429`
| asset_class | symbol | event_count |
|---|---|---|
| bond | IEF | 158 |
| bond | LQD | 229 |
| bond | SHY | 340 |
| bond | TLT | 117 |
| commodity | DBA | 85 |
| commodity | GLD | 153 |
| commodity | SLV | 88 |
| commodity | USO | 83 |
| equity | EFA | 258 |
| equity | IWM | 215 |
| equity | QQQ | 325 |
| equity | SPY | 378 |
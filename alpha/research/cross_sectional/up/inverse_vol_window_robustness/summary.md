# Inverse Volatility Window Robustness Test

## 1. Research Question

在固定 Original 12 ETF `mom_126 Top5` 信号下，只改变Inverse Volatility回看窗口，检验风险改善是否具有参数邻域稳定性。本实验不优化参数。

## 2. Fixed Design

- Sample: `2008-02-01` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum window: 126 trading days
- Volatility windows: 21, 42, 63, 84, 105, 126, 147, 168, 189, 252 trading days
- Daily-return standard deviation; inverse-vol weights normalized to 100%
- Transaction cost: 5 bps; no MA filter
- Equal Weight baseline: CAGR 10.36%, Sharpe 0.81, MaxDD -29.06%
- Stable plateau: at least 3 consecutive candidates with Sharpe range <= 0.15, CAGR range <= 2%, MaxDD range <= 10%
- Isolated spike: internal Sharpe exceeds the mean of adjacent candidates by more than 0.15

## 3. Performance

| Vol Window | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 10.49% | 0.99 | -18.46% | 10.67% | 0.57 | 492.51% | 14679.08% |
| 42 | 10.48% | 0.98 | -17.22% | 10.72% | 0.61 | 492.10% | 13812.79% |
| 63 | 10.28% | 0.96 | -17.85% | 10.73% | 0.58 | 473.10% | 13497.89% |
| 84 | 10.28% | 0.97 | -17.50% | 10.71% | 0.59 | 473.96% | 13379.05% |
| 105 | 10.36% | 0.97 | -17.63% | 10.74% | 0.59 | 480.76% | 13291.42% |
| 126 | 10.32% | 0.97 | -17.22% | 10.75% | 0.60 | 476.94% | 13244.12% |
| 147 | 10.30% | 0.96 | -17.24% | 10.76% | 0.60 | 475.58% | 13228.36% |
| 168 | 10.32% | 0.96 | -17.14% | 10.79% | 0.60 | 477.21% | 13121.23% |
| 189 | 10.27% | 0.96 | -16.95% | 10.80% | 0.61 | 472.13% | 13090.83% |
| 252 | 10.19% | 0.95 | -16.97% | 10.79% | 0.60 | 465.08% | 13076.98% |

## 4. Relative Change vs Equal Weight

正的 MaxDD Change 表示回撤改善。

| Vol Window | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| 21 | 0.13% | 0.17 | 10.60% |
| 42 | 0.12% | 0.17 | 11.84% |
| 63 | -0.08% | 0.15 | 11.20% |
| 84 | -0.08% | 0.15 | 11.56% |
| 105 | -0.00% | 0.16 | 11.42% |
| 126 | -0.04% | 0.15 | 11.84% |
| 147 | -0.06% | 0.15 | 11.82% |
| 168 | -0.04% | 0.15 | 11.92% |
| 189 | -0.09% | 0.15 | 12.10% |
| 252 | -0.17% | 0.14 | 12.09% |

## 5. Robustness Score

| Vol Window | Sharpe | Neighbor Sharpe MAE | Robustness Score |
| --- | --- | --- | --- |
| 21 | 0.99 | 0.00 | 98.08 |
| 42 | 0.98 | 0.01 | 94.56 |
| 63 | 0.96 | 0.01 | 94.98 |
| 84 | 0.97 | 0.00 | 98.48 |
| 105 | 0.97 | 0.00 | 97.93 |
| 126 | 0.97 | 0.00 | 98.30 |
| 147 | 0.96 | 0.00 | 99.22 |
| 168 | 0.96 | 0.00 | 98.43 |
| 189 | 0.96 | 0.01 | 97.20 |
| 252 | 0.95 | 0.01 | 97.18 |

## 6. Stable Plateau Test

Longest qualifying plateau: **21-252**.

| Start Window | End Window | Count | Sharpe Range | CAGR Range | MaxDD Range | Contains 126 | 126 Is Interior |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 21 | 252 | 10 | 0.03 | 0.30% | 1.51% | True | True |

1. Stable plateau exists: **Yes**.
2. 126-day is inside a plateau and is an interior point.
3. Isolated Sharpe spikes: **None**.

## 7. Average Weight by Momentum Rank

| Vol Window | Rank1 | Rank2 | Rank3 | Rank4 | Rank5 |
| --- | --- | --- | --- | --- | --- |
| 21 | 13.64% | 17.30% | 18.74% | 23.14% | 27.18% |
| 42 | 13.74% | 17.22% | 18.91% | 23.19% | 26.94% |
| 63 | 13.90% | 17.16% | 18.94% | 23.08% | 26.91% |
| 84 | 13.94% | 17.27% | 18.94% | 22.92% | 26.93% |
| 105 | 14.07% | 17.38% | 18.84% | 22.83% | 26.88% |
| 126 | 14.17% | 17.36% | 18.88% | 22.75% | 26.83% |
| 147 | 14.26% | 17.37% | 18.87% | 22.71% | 26.80% |
| 168 | 14.33% | 17.42% | 18.93% | 22.72% | 26.60% |
| 189 | 14.36% | 17.40% | 18.99% | 22.72% | 26.54% |
| 252 | 14.39% | 17.32% | 19.02% | 22.64% | 26.63% |

## 8. Average Trailing Volatility by Momentum Rank

The daily standard deviations below are unannualized and use each row's stated lookback window.

| Vol Window | Rank1 | Rank2 | Rank3 | Rank4 | Rank5 |
| --- | --- | --- | --- | --- | --- |
| 21 | 1.38% | 1.04% | 1.00% | 0.86% | 0.83% |
| 42 | 1.40% | 1.06% | 1.01% | 0.89% | 0.86% |
| 63 | 1.40% | 1.08% | 1.03% | 0.91% | 0.87% |
| 84 | 1.40% | 1.08% | 1.04% | 0.94% | 0.89% |
| 105 | 1.39% | 1.09% | 1.06% | 0.96% | 0.91% |
| 126 | 1.39% | 1.11% | 1.07% | 0.97% | 0.92% |
| 147 | 1.40% | 1.13% | 1.09% | 1.00% | 0.94% |
| 168 | 1.41% | 1.14% | 1.10% | 1.01% | 0.96% |
| 189 | 1.41% | 1.16% | 1.10% | 1.02% | 0.97% |
| 252 | 1.42% | 1.20% | 1.11% | 1.04% | 0.98% |

## 9. Position Concentration

| Vol Window | HHI | Effective Positions |
| --- | --- | --- |
| 21 | 0.29 | 3.85 |
| 42 | 0.29 | 3.89 |
| 63 | 0.29 | 3.90 |
| 84 | 0.29 | 3.91 |
| 105 | 0.29 | 3.92 |
| 126 | 0.29 | 3.93 |
| 147 | 0.29 | 3.94 |
| 168 | 0.29 | 3.94 |
| 189 | 0.28 | 3.95 |
| 252 | 0.29 | 3.94 |

## 10. Interpretation

1. **Inverse Vol 是否对窗口鲁棒？** 是，所有候选窗口均提高 Sharpe 且降低 MaxDD。
2. **风险改善是否持续？** 所有窗口的 MaxDD 都优于 Equal Weight。
3. **是否存在明显最佳窗口？** 没有窗口满足孤立尖峰定义；应解释平台而非单点。
4. **126日是否局部峰值？** 不是；它位于稳定平台内部，Robustness Score 为 98.30。
5. **高Momentum资产是否普遍更高波动？** 是，所有测试窗口中Rank1平均波动均高于Rank5，且Inverse Vol持续降低Rank1权重。
6. **改善来自参数还是机制？** 广泛窗口均改善且形成平台，更支持风险平衡机制本身。

## 11. Final Conclusion

Inverse Volatility 的优势具有很强的参数邻域稳定性：21–252日全部候选窗口形成同一平台，均提高Sharpe并降低MaxDD，126日位于平台内部且没有孤立尖峰。因此改善更可能来自风险平衡机制本身，而不是某个特殊Vol Window。本实验不选择最佳窗口，也不改变Momentum、Universe或其它策略参数。

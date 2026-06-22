# Position Sizing Test B: Inverse Vol vs Inverse Variance

## 1. Research Question

在固定 Original 12 ETF `mom_126 Top5` 和126日风险窗口下，比较温和的Inverse Vol与更激进的Inverse Variance仓位分配。本实验不优化参数。

## 2. Fixed Design

- Sample: `2008-02-01` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum and volatility windows: 126 trading days
- Top5 is identical across all strategies
- Transaction cost: 5 bps; no MA filter
- Inverse Vol: `weight proportional to 1 / vol`
- Inverse Variance: `weight proportional to 1 / vol^2`

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Equal Weight | 10.36% | 0.81 | -29.06% | 13.16% | 0.36 | 478.53% | 9373.90% |
| Inverse Vol | 10.32% | 0.97 | -17.22% | 10.75% | 0.60 | 476.94% | 13244.12% |
| Inverse Variance | 9.62% | 0.97 | -17.47% | 9.95% | 0.55 | 417.69% | 15810.40% |

## 4. Relative Change vs Equal Weight

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Inverse Vol | -0.04% | 0.15 | 11.84% |
| Inverse Variance | -0.74% | 0.16 | 11.59% |

## 5. Weight Distribution by Momentum Rank

| Strategy | Rank1 | Rank2 | Rank3 | Rank4 | Rank5 |
| --- | --- | --- | --- | --- | --- |
| Equal Weight | 20.00% | 20.00% | 20.00% | 20.00% | 20.00% |
| Inverse Vol | 14.17% | 17.36% | 18.88% | 22.75% | 26.83% |
| Inverse Variance | 10.65% | 15.26% | 17.99% | 24.76% | 31.34% |

## 6. Position Concentration

| Strategy | Average HHI | Effective Positions |
| --- | --- | --- |
| Equal Weight | 0.20 | 5.00 |
| Inverse Vol | 0.29 | 3.93 |
| Inverse Variance | 0.42 | 3.07 |

## 7. Long-Run Average ETF Target Weight

Weights include zero in months when an ETF is not selected.

| ETF | Equal Weight | Inverse Vol | Inverse Variance |
| --- | --- | --- | --- |
| SPY | 12.47% | 13.75% | 15.13% |
| QQQ | 13.58% | 11.41% | 9.98% |
| IWM | 10.33% | 8.14% | 6.41% |
| EFA | 7.72% | 7.63% | 7.49% |
| GLD | 9.58% | 7.90% | 6.77% |
| SLV | 8.74% | 4.84% | 2.66% |
| USO | 7.53% | 4.01% | 2.23% |
| DBA | 6.14% | 6.14% | 6.16% |
| TLT | 7.72% | 5.75% | 4.29% |
| IEF | 6.60% | 8.93% | 10.57% |
| SHY | 3.91% | 13.63% | 18.35% |
| LQD | 5.67% | 7.86% | 9.96% |

## 8. Ex-Ante Risk Contribution

At each rebalance, component variance contribution is `w_i * (Sigma w)_i / (w' Sigma w)` using the trailing 126-day daily covariance matrix. Contributions are summed by asset class and averaged across rebalances; they may be negative when covariance is diversifying.

| Strategy | Equity Risk Contribution | Commodity Risk Contribution | Bond Risk Contribution |
| --- | --- | --- | --- |
| Equal Weight | 48.14% | 42.01% | 9.86% |
| Inverse Vol | 48.31% | 29.04% | 22.65% |
| Inverse Variance | 42.37% | 17.14% | 40.49% |

## 9. Interpretation

1. **Inverse Variance 是否进一步提高 Sharpe？** 仅有边际提高，变化 +0.008；Inverse Variance/Inverse Vol 为 0.974/0.965。
2. **是否进一步降低 MaxDD？** 否。Inverse Variance/Inverse Vol 为 -17.47%/-17.22%。
3. **是否因过度压低高波动资产而损失收益？** CAGR 相对Inverse Vol变化 -0.69%。
4. **是否明显提高集中度？** 是。HHI 0.286 -> 0.419，Effective Positions 3.93 -> 3.07。
5. **Inverse Vol 是否更接近平衡点？** 是。Inverse Vol的CAGR/Sharpe/MaxDD为 10.32%/0.965/-17.22%；Inverse Variance为 9.62%/0.974/-17.47%。后者只获得极小Sharpe增量，却损失CAGR并略微恶化MaxDD。
6. **改善来自风险平衡还是极端压低？** 更支持温和风险平衡。Bond平均目标权重从Inverse Vol的 36.17% 升至Inverse Variance的 43.16%；Bond风险贡献从 22.65% 升至 40.49%，而Commodity风险贡献被进一步压低，未换来更好MaxDD。

## 10. Final Conclusion

在当前 Original 12 ETF Momentum Framework 中，**Inverse Variance 不优于 Inverse Vol**。它进一步降低名义波动，却以更高集中度、更高换手、0.70个百分点CAGR损失和略差MaxDD为代价，只增加约0.008 Sharpe。风险控制的平衡点更接近温和的Inverse Vol，说明优势来自风险平衡本身，而不是尽可能压低高波动资产。本实验不测试其它Vol窗口、Risk Parity或其它权重指数。

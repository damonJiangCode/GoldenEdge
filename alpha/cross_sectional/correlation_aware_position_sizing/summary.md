# Correlation-Aware Position Sizing Test

## 1. Research Question

在固定 Original 12 ETF `mom_126 Top5` 和Inverse Vol框架中，加入简单的平均相关性惩罚，检验资产间相关性是否提供额外风险管理价值。本实验不优化参数。

## 2. Fixed Design

- Sample: `2008-02-01` to `2025-12-31`
- Monthly rebalance; month-end signal effective next trading day
- Momentum, volatility, and correlation windows: 126 trading days
- Top5 is identical across all strategies
- Diversification Score: `max(0.10, 1 - average correlation to the other four holdings)`
- Correlation-Adjusted weight: `(1 / vol) x Diversification Score`, normalized to 100%
- Transaction cost: 5 bps; no MA filter

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Equal Weight | 10.36% | 0.81 | -29.06% | 13.16% | 0.36 | 478.53% | 9373.90% |
| Inverse Vol | 10.32% | 0.97 | -17.22% | 10.75% | 0.60 | 476.94% | 13244.12% |
| Correlation-Adjusted IV | 10.10% | 0.96 | -17.96% | 10.62% | 0.56 | 458.39% | 14461.90% |

## 4. Relative Change vs Inverse Vol

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Equal Weight | 0.04% | -0.15 | -11.84% |
| Correlation-Adjusted IV | -0.22% | -0.01 | -0.75% |

## 5. Correlation Diagnostics

Unweighted pairwise correlation is identical by construction because all strategies hold the same Top5. Weighted Pairwise Correlation reflects sizing differences.

| Strategy | Average Pairwise Correlation | Weighted Pairwise Correlation |
| --- | --- | --- |
| Equal Weight | 0.35 | 0.35 |
| Inverse Vol | 0.35 | 0.37 |
| Correlation-Adjusted IV | 0.35 | 0.31 |

## 6. Position Concentration

| Strategy | HHI | Effective Positions |
| --- | --- | --- |
| Equal Weight | 0.20 | 5.00 |
| Inverse Vol | 0.29 | 3.93 |
| Correlation-Adjusted IV | 0.30 | 3.77 |

## 7. Weight Distribution by Momentum Rank

| Strategy | Rank1 | Rank2 | Rank3 | Rank4 | Rank5 |
| --- | --- | --- | --- | --- | --- |
| Equal Weight | 20.00% | 20.00% | 20.00% | 20.00% | 20.00% |
| Inverse Vol | 14.17% | 17.36% | 18.88% | 22.75% | 26.83% |
| Correlation-Adjusted IV | 14.31% | 16.50% | 17.91% | 21.97% | 29.31% |

## 8. Average Target Asset-Class Exposure

| Strategy | Equity Weight | Commodity Weight | Bond Weight |
| --- | --- | --- | --- |
| Equal Weight | 44.09% | 32.00% | 23.91% |
| Inverse Vol | 40.93% | 22.90% | 36.17% |
| Correlation-Adjusted IV | 35.32% | 26.87% | 37.81% |

## 9. Correlation Penalty Frequency

Scores are averaged only over months when the ETF is selected in Top5. Higher average correlation means a lower diversification score and stronger penalty.

| ETF | Average Correlation Score | Average Diversification Score | Selection Count |
| --- | --- | --- | --- |
| SPY | 0.49 | 0.51 | 134 |
| QQQ | 0.37 | 0.63 | 146 |
| IWM | 0.48 | 0.52 | 111 |
| EFA | 0.56 | 0.44 | 83 |
| GLD | 0.29 | 0.71 | 103 |
| SLV | 0.33 | 0.67 | 94 |
| USO | 0.26 | 0.74 | 81 |
| DBA | 0.17 | 0.83 | 66 |
| TLT | 0.17 | 0.83 | 83 |
| IEF | 0.30 | 0.70 | 71 |
| SHY | 0.23 | 0.77 | 42 |
| LQD | 0.32 | 0.68 | 61 |

## 10. Interpretation

1. **Correlation Adjustment 是否提高 Sharpe？** 否。变化 -0.007。
2. **是否降低 MaxDD？** 否。变化 -0.75%。
3. **是否降低平均相关性？** Unweighted指标不会变化；Weighted Pairwise Correlation变化 -0.064。
4. **是否减少Equity内部重复？** Equity平均目标权重变化 -5.61%，且高相关Equity的Diversification Score显示具体惩罚强度。
5. **是否自动增加Commodity或Bond？** Commodity变化 3.97%，Bond变化 1.64%。
6. **改善是否超过Inverse Vol？** 否。Weighted Pairwise Correlation虽下降 0.064，但CAGR下降 0.22%、Sharpe下降 0.007，且MaxDD恶化 0.75%。
7. **Original 12是否已足够分散？** 对当前简单相关性惩罚而言，是。Original 12与Inverse Vol已经吸收了大部分可用的简单分散价值，进一步惩罚相关性没有改善实现后的风险收益。

## 11. Final Conclusion

Correlation-Adjusted Inverse Vol **不优于**纯Inverse Vol。它降低了目标权重口径的持仓相关性，并减少Equity重复暴露，但同时降低CAGR与Sharpe、恶化MaxDD、提高集中度和换手率。因此，当前证据不支持把风险管理从单资产Inverse Vol扩展到这条简单的平均相关性惩罚公式。

这不代表完整协方差模型或风险预算一定无效；它只说明在固定Original 12、mom_126、Top5与126日估计窗口下，简单Correlation Adjustment没有提供独立增量价值。本实验未测试其它相关窗口、惩罚下限或Risk Parity。

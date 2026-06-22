# Position Sizing Test A

## 1. Research Question

在固定 Original 12 ETF、`mom_126 Top5` 和月度调仓信号下，仅改变目标仓位分配，比较 Equal Weight、Rank Weight、Inverse Volatility 和 Rank x Inverse Volatility。本实验不优化权重或窗口。

## 2. Fixed Design

- Sample: `2008-02-01` to `2025-12-31`
- Month-end signal effective next trading day
- Momentum window: 126 trading days
- Volatility window: trailing 126 daily returns through the signal date
- Transaction cost: 5 bps; no MA filter
- All strategies select the identical Top5 each month
- Initial portfolio is established from cash on the sample start date

## 3. Performance

| Strategy | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Equal Weight | 10.36% | 0.81 | -29.06% | 13.16% | 0.36 | 478.53% | 9373.90% |
| Rank Weight | 10.15% | 0.73 | -28.72% | 14.72% | 0.35 | 459.02% | 10881.52% |
| Inverse Vol | 10.32% | 0.97 | -17.22% | 10.75% | 0.60 | 476.94% | 13244.12% |
| Rank x Inverse Vol | 10.27% | 0.84 | -20.14% | 12.63% | 0.51 | 471.67% | 13194.52% |

## 4. Relative Change vs Equal Weight

正的 MaxDD Change 表示回撤改善。

| Strategy | CAGR Change | Sharpe Change | MaxDD Change |
| --- | --- | --- | --- |
| Rank Weight | -0.21% | -0.08 | 0.34% |
| Inverse Vol | -0.04% | 0.15 | 11.84% |
| Rank x Inverse Vol | -0.09% | 0.02 | 8.92% |

## 5. Position Concentration

HHI and Effective Positions are calculated from target weights at each rebalance and then averaged.

| Strategy | Average HHI | Effective Positions |
| --- | --- | --- |
| Equal Weight | 0.20 | 5.00 |
| Rank Weight | 0.23 | 4.44 |
| Inverse Vol | 0.29 | 3.93 |
| Rank x Inverse Vol | 0.27 | 3.89 |

## 6. Weight Distribution by Momentum Rank

| Strategy | Avg Weight Rank1 | Avg Weight Rank2 | Avg Weight Rank3 | Avg Weight Rank4 | Avg Weight Rank5 |
| --- | --- | --- | --- | --- | --- |
| Equal Weight | 20.00% | 20.00% | 20.00% | 20.00% | 20.00% |
| Rank Weight | 30.00% | 25.00% | 20.00% | 15.00% | 10.00% |
| Inverse Vol | 14.17% | 17.36% | 18.88% | 22.75% | 26.83% |
| Rank x Inverse Vol | 25.16% | 24.97% | 20.72% | 17.40% | 11.76% |

## 7. Turnover Impact

Annual Turnover is total absolute turnover divided by trading years. Cost Drag Estimate is `Annual Turnover x 5 bps` and excludes compounding interaction.

| Strategy | Annual Turnover | Cost Drag Estimate |
| --- | --- | --- |
| Equal Weight | 524.01% | 0.26% |
| Rank Weight | 608.28% | 0.30% |
| Inverse Vol | 740.35% | 0.37% |
| Rank x Inverse Vol | 737.58% | 0.37% |

## 8. Interpretation

1. **Equal Weight 是否已经足够优秀？** 不是唯一合理选择。Inverse Vol 在 CAGR 仅变化 -0.04% 时显著提高 Sharpe 并改善 MaxDD，说明 sizing 提供了独立于选股的风险收益改善。
2. **Rank Weight 是否提高 CAGR？** 否，变化 -0.21%。
3. **Rank Weight 是否导致集中？** Average HHI 从 0.200 变为 0.225，Effective Positions 从 5.00 变为 4.44。
4. **Inverse Vol 是否提高 Sharpe？** 是，变化 +0.15。
5. **Inverse Vol 是否降低 MaxDD？** 是，变化 11.84%。
6. **Rank x Inverse Vol 是否保留 Alpha 并降低风险？** 是。CAGR/Sharpe/MaxDD 为 10.27%/0.84/-20.14%。
7. **哪种最符合保留收益并控制风险？** 在 CAGR 不低于 Equal Weight 1个百分点的固定方案中，`Inverse Vol` 的 Sharpe 最高，同时拥有最浅 MaxDD。Inverse Vol 的估算年成本拖累只比 Equal Weight 高 0.11%，不足以解释其风险改善。

## 9. Final Conclusion

在当前 Original 12 ETF Momentum Framework 中，**Inverse Volatility 明显优于 Equal Weight 的样本内风险收益表现**：CAGR 基本保留，Sharpe、MaxDD、Volatility 和 Calmar 均显著改善。Rank Weight 不增加收益且提高风险；Rank x Inverse Vol 只实现部分改善。Inverse Vol 应进入后续样本外验证，但本实验不扩展到其它权重、波动窗口、Kelly 或 Risk Parity。

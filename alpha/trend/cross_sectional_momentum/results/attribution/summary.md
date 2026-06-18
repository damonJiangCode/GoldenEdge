# Mixed Asset Momentum Performance Attribution

## 1. Research Scope

- Strategy: `mom_126_Top5`
- Universe: 12 ETF Mixed Asset Universe
- Sample: `2007-08-01` to `2025-12-31`
- Monthly rebalance, Top5 equal weight, 5 bps transaction cost
- Momentum signal: 126 trading days

本分析回答收益来自哪些资产，以及移除主要赢家后策略是否仍然成立。它是全样本归因和集中度诊断，不是独立样本外检验。

## 2. Attribution Method

- 每日资产毛贡献率：`start_of_day_weight × asset_return`
- 交易成本按各资产绝对调仓额分摊
- 每日资产 PnL：`portfolio_equity_before_return × net_asset_contribution_rate`
- 所有资产 `total_contribution` 之和精确等于组合最终 Total Return
- `avg_return_when_held` 是资产在日初权重大于零时的平均日收益

## 3. Asset Contribution

| symbol | selection_count | selection_pct | avg_weight | avg_return_when_held | total_contribution | contribution_pct |
| --- | --- | --- | --- | --- | --- | --- |
| QQQ | 150 | 67.87% | 20.05% | 0.08% | 136.49% | 21.88% |
| GLD | 108 | 48.87% | 20.06% | 0.09% | 113.46% | 18.19% |
| SLV | 95 | 42.99% | 20.00% | 0.06% | 89.04% | 14.27% |
| SPY | 136 | 61.54% | 19.99% | 0.04% | 56.57% | 9.07% |
| EFA | 86 | 38.91% | 20.00% | 0.05% | 51.42% | 8.24% |
| IWM | 111 | 50.23% | 19.98% | 0.03% | 38.90% | 6.24% |
| DBA | 70 | 31.67% | 19.99% | 0.04% | 32.81% | 5.26% |
| LQD | 61 | 27.60% | 20.00% | 0.06% | 31.25% | 5.01% |
| USO | 87 | 39.37% | 19.93% | 0.02% | 30.07% | 4.82% |
| TLT | 86 | 38.91% | 19.97% | 0.04% | 24.83% | 3.98% |
| IEF | 73 | 33.03% | 19.98% | 0.03% | 16.42% | 2.63% |
| SHY | 42 | 19.00% | 20.02% | 0.01% | 2.59% | 0.41% |

## 4. Top Contributors

1. 前三大贡献资产：`QQQ, GLD, SLV`。
2. 前三大资产合计贡献组合净收益的 54.34%。当其他资产存在负贡献时，该比例可能超过 100%。

## 5. Removal Sensitivity

每个移除场景都会从投资 Universe 删除对应资产，然后重新计算排名、Top5 持仓、换手和交易成本。

| scenario | removed_symbols | CAGR | Sharpe | MaxDD | CAGR Retention | Sharpe Retention | MaxDD Change |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline |  | 11.36% | 0.88 | -29.06% | 100.00% | 100.00% | 0.00% |
| RemoveTop1 | QQQ | 10.05% | 0.83 | -26.51% | 88.45% | 94.47% | 2.54% |
| RemoveTop2 | QQQ,GLD | 8.40% | 0.75 | -25.72% | 73.91% | 84.56% | 3.34% |
| RemoveTop3 | QQQ,GLD,SLV | 6.26% | 0.65 | -21.07% | 55.09% | 73.56% | 7.99% |

- Baseline: CAGR 11.36%, Sharpe 0.88, MaxDD -29.06%。
- Remove Top1: CAGR 10.05%, Sharpe 0.83, MaxDD -26.51%。
- Remove Top2: CAGR 8.40%, Sharpe 0.75, MaxDD -25.72%。
- Remove Top3: CAGR 6.26%, Sharpe 0.65, MaxDD -21.07%。

## 6. Final Conclusion

移除前三大贡献资产后策略仍为正，但 CAGR/Sharpe 有实质下降。收益存在一定 breadth，同时也有不可忽视的赢家集中度。

需要注意：贡献资产和移除对象都由同一全样本识别，因此该结果适合判断历史收益集中度，不适合直接预测未来应该排除或保留哪些资产。

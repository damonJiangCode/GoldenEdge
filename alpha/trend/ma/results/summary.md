# MA200 Trend Filter Research Summary

## 1. 研究问题

MA200 趋势过滤是否能在不同资产类别中改善风险收益特征？

## 2. Alpha 假设

- 如果价格高于长期均线，说明资产可能处于强势趋势。
- 如果价格低于长期均线，说明资产可能处于弱势状态。
- 因此，只在价格高于 MA200 时持有，可能降低熊市回撤。

## 3. 实验规则

- MA200: 200 日简单移动平均
- 价格: `Adj Close`
- 防未来函数: `position = signal.shift(1)`
- 仓位: `100%` or `0%`
- 不做空
- 不加杠杆
- 成本: 每次仓位变化扣 `0.05%`

## 4. 总体结论

- MaxDD 改善比例: 100.00% (12/12)
- Sharpe 提高比例: 41.67% (5/12)
- CAGR 提高比例: 25.00% (3/12)
- 效果最好资产类别: `equity`
- 效果最差资产类别: `bond`
- 总体判断: MA200 普遍更像风险过滤器，而不是收益增强 Alpha。

## 5. 分资产类别结论

| asset_class | symbols_count | avg_strategy_cagr | avg_benchmark_cagr | avg_strategy_sharpe | avg_benchmark_sharpe | avg_strategy_max_drawdown | avg_benchmark_max_drawdown | avg_cagr_diff | avg_sharpe_diff | avg_maxdd_improvement | percent_symbols_sharpe_improved | percent_symbols_maxdd_improved | percent_symbols_cagr_improved |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bond | 4 | 1.57% | 3.54% | 0.55 | 0.70 | -19.55% | -25.73% | -1.97% | -0.15 | 6.18% | 0.00% | 100.00% | 0.00% |
| commodity | 4 | 3.54% | 2.56% | 0.31 | 0.28 | -54.05% | -72.00% | 0.98% | 0.02 | 17.95% | 50.00% | 100.00% | 50.00% |
| equity | 4 | 6.20% | 7.66% | 0.53 | 0.44 | -27.99% | -64.46% | -1.46% | 0.09 | 36.47% | 75.00% | 100.00% | 25.00% |

### Bond
- Avg CAGR diff: -1.97%; Avg Sharpe diff: -0.15; Avg MaxDD improvement: 6.18%.
- 主要价值是降低回撤，收益改善不足。
### Commodity
- Avg CAGR diff: 0.98%; Avg Sharpe diff: 0.02; Avg MaxDD improvement: 17.95%.
- 同时有一定收益和风险调整改善。
### Equity
- Avg CAGR diff: -1.46%; Avg Sharpe diff: 0.09; Avg MaxDD improvement: 36.47%.
- 主要价值是降低回撤，收益改善不足。

## 6. 研究判断

- MA200 是否像 Alpha: 不强。多数情况下它不稳定提高 CAGR。
- MA200 是否更像 Risk Filter: 是。核心价值是降低 MaxDD 和降低风险暴露。
- 是否值得作为后续策略的风险控制模块: 值得，尤其适合先作为跨资产组合的风险开关测试。

## 7. 下一步建议

- 测试 MA100/150/200/250 鲁棒性。
- 测试其他 trend proxy: momentum, Donchian, 52-week high。
- 继续做跨资产趋势研究，并重点看组合层面的回撤、Sharpe 和换手。
- 增加现金收益或短债替代空仓的版本，但要和纯空仓版本分开记录。

## 8. Symbol Metrics

| symbol | asset_class | strategy_cagr | benchmark_cagr | strategy_sharpe | benchmark_sharpe | strategy_max_drawdown | benchmark_max_drawdown | cagr_diff | sharpe_diff | maxdd_improvement |
|---|---|---|---|---|---|---|---|---|---|---|
| IEF | bond | 1.61% | 3.69% | 0.32 | 0.56 | -18.32% | -23.92% | -2.08% | -0.24 | 5.61% |
| LQD | bond | 3.05% | 4.71% | 0.59 | 0.59 | -11.64% | -24.95% | -1.67% | -0.00 | 13.32% |
| SHY | bond | 1.68% | 2.00% | 1.23 | 1.31 | -2.37% | -5.71% | -0.32% | -0.08 | 3.34% |
| TLT | bond | -0.04% | 3.77% | 0.05 | 0.33 | -45.89% | -48.35% | -3.82% | -0.28 | 2.46% |
| DBA | commodity | 2.40% | 1.08% | 0.27 | 0.15 | -41.21% | -67.97% | 1.32% | 0.12 | 26.76% |
| GLD | commodity | 7.91% | 10.94% | 0.60 | 0.68 | -35.06% | -45.56% | -3.03% | -0.07 | 10.49% |
| SLV | commodity | 6.68% | 8.15% | 0.40 | 0.41 | -63.07% | -76.28% | -1.47% | -0.01 | 13.21% |
| USO | commodity | -2.83% | -9.94% | -0.04 | -0.10 | -76.85% | -98.19% | 7.11% | 0.06 | 21.34% |
| EFA | equity | 5.45% | 6.21% | 0.50 | 0.39 | -28.80% | -61.04% | -0.76% | 0.10 | 32.24% |
| IWM | equity | 4.05% | 8.22% | 0.35 | 0.45 | -28.92% | -58.64% | -4.17% | -0.10 | 29.72% |
| QQQ | equity | 8.42% | 8.17% | 0.62 | 0.43 | -32.70% | -82.96% | 0.25% | 0.20 | 50.26% |
| SPY | equity | 6.89% | 8.04% | 0.67 | 0.50 | -21.54% | -55.19% | -1.15% | 0.17 | 33.65% |
# Asset Class Removal Test

## 1. Research Goal

识别 12 ETF Mixed Asset `mom_126 Top5` 的收益与风险优势究竟来自 Equity、Commodity、Bond，还是来自跨类别轮动本身。

- Sample: `2007-08-01` to `2025-12-31`
- Monthly rebalance, Top5 equal weight
- Momentum window: 126 trading days
- Transaction cost: 5 bps
- 不搜索任何新参数

## 2. Baseline And Removal Scenarios

| scenario | remaining_classes | CAGR | Sharpe | MaxDD | Volatility | Calmar | Total Return | Turnover | CAGR Retention | Sharpe Retention | MaxDD Change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | Equity + Commodity + Bond | 11.36% | 0.88 | -29.06% | 13.20% | 0.39 | 623.86% | 9708.32% | 100.00% | 100.00% | 0.00% |
| Remove Equity | Commodity + Bond | 6.37% | 0.61 | -24.05% | 11.07% | 0.26 | 210.63% | 7103.97% | 56.07% | 69.42% | 5.01% |
| Remove Commodity | Equity + Bond | 8.71% | 0.86 | -24.61% | 10.31% | 0.35 | 365.65% | 6339.57% | 76.67% | 97.87% | 4.44% |
| Remove Bond | Equity + Commodity | 9.35% | 0.62 | -47.04% | 16.73% | 0.20 | 419.06% | 7250.59% | 82.33% | 70.22% | -17.98% |

`Remove Equity` 等价于 `Commodity + Bond`；`Remove Commodity` 等价于 `Equity + Bond`；`Remove Bond` 等价于 `Equity + Commodity`。它们是同一组 Universe，不作为重复证据计算。

## 3. Historical PnL By Asset Class

| asset_class | asset_count | selection_count | selection_slot_pct | total_contribution | contribution_pct |
| --- | --- | --- | --- | --- | --- |
| Equity | 4 | 483 | 43.71% | 283.39% | 45.42% |
| Commodity | 4 | 360 | 32.58% | 265.38% | 42.54% |
| Bond | 4 | 262 | 23.71% | 75.09% | 12.04% |

PnL contribution 是 baseline 持仓的历史会计归因；removal test 则会重新排名并允许剩余资产替代被删除资产，因此两者回答不同问题。

## 4. Interpretation

1. 历史 PnL 贡献最大的类别：`Equity`。
2. 删除后 CAGR 损失最大的类别：`Equity`；Sharpe 损失最大的类别：`Equity`。
3. 更像 Alpha/return 来源：`Equity` 最强，`Commodity` 次之。
4. 更像风险分散器：`Bond`。删除 Bond 后 MaxDD 从 -29.06% 恶化至 -47.04%。
5. Mixed Asset 优势主要来自：Equity Trend 提供核心收益、Commodity Trend 增强收益、Bond Diversification 压低波动与回撤，并由跨类别排名实现 Asset Rotation。

## 5. Evidence Levels

| evidence_level | finding | basis |
| --- | --- | --- |
| Strong Evidence | Equity is the primary return engine | Equity contributes 45.42% of PnL; removal cuts CAGR to 6.37% and Sharpe to 0.61. |
| Strong Evidence | Bond is the primary risk diversifier | Bond contributes only 12.04% of PnL, but removal worsens MaxDD by 17.98% and raises volatility by 3.53%. |
| Moderate Evidence | Commodity is a return enhancer, not an essential Sharpe source | Commodity contributes 42.54% of PnL, yet removal retains 97.87% of Sharpe and improves MaxDD. |
| Moderate Evidence | Asset rotation across classes adds value | Baseline has higher CAGR and Sharpe than every two-class universe, but class roles are asymmetric. |
| Weak Evidence | Commodity is the dominant standalone Alpha source | Its historical PnL contribution is high, but removing it leaves 97%+ of baseline Sharpe. |

## 6. Final Answer

当前 Mixed Asset Momentum 的优势不是某一个资产类别单独产生的。

- **Strong Evidence:** Equity 是主要收益引擎；Bond 是主要风险分散器。
- **Moderate Evidence:** Commodity 提供重要历史收益贡献，跨类别轮动使完整 Universe 的 CAGR/Sharpe 高于所有双类别组合。
- **Weak Evidence:** Commodity 是不可替代的风险调整 Alpha 来源。删除 Commodity 后 Sharpe 几乎完全保留，且 MaxDD 改善。

最准确的结构性解释是：`Equity Trend + Commodity Return Enhancement + Bond Diversification + Cross-Class Rotation`。其中 Equity 和 Bond 对完整策略最不可替代，Commodity 的作用更偏向提高收益，而不是提高 Sharpe。

## 7. Limitations

- 这是全样本 sensitivity analysis，不是 out-of-sample 因果证明。
- 删除某一类别后仍维持 Top5，会提高剩余类别内的持仓密度；结果包含替代效应。
- 资产类别贡献与移除影响不是线性可加的，不能把 retention 简单解释为独立因果份额。

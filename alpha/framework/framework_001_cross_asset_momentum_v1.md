# Framework 001 — Cross-Asset Momentum Framework V1

## Document Status

- Status: Validated Research Framework
- Version: V1
- Framework date: 2026-06-22
- Validation date: 2026-06-23
- Evidence basis: Existing repository studies only
- Scope: Long-only cross-asset ETF momentum
- Readiness: Validated research framework; ready for live-readiness assessment, not live deployment

This document archives the first formal Alpha Framework in the project. It consolidates completed research and validation records and does not introduce a new experiment, parameter search, or unverified conclusion.

## Objective

Build a simple and auditable cross-asset allocation framework that tests whether assets with stronger medium-term relative performance continue to outperform, while controlling portfolio risk through position sizing.

The framework is designed to capture winner continuation and dynamic rotation across Equity, Commodity, and Bond ETFs. Its purpose is not to maximize in-sample return. The objective is to retain the observed momentum effect with a parameter-robust signal, a compact universe, controlled drawdown, and explicit transaction costs.

## Final Framework

| Component | Definition |
| --- | --- |
| Universe | Original 12 ETF Universe |
| Price | Adjusted Close |
| Momentum | 126 trading-day total return |
| Selection | Cross-sectional Top5 |
| Weighting | Inverse Volatility, normalized to 100% |
| Volatility Window | 126 trading days of daily returns |
| Rebalance | Monthly; month-end signal, effective next trading day |
| Transaction Cost | 5 bps applied to portfolio turnover |
| Direction | Long only |
| Leverage | None |
| MA Filter | None |

Momentum and volatility are calculated using information available through the month-end signal date. Future returns are never used to construct the signal or target weights.

### Original 12 ETF Universe

**Equity**

- `SPY` — US large-cap equity
- `QQQ` — US Nasdaq-100 / growth equity
- `IWM` — US small-cap equity
- `EFA` — developed ex-US equity

**Commodity**

- `GLD` — gold
- `SLV` — silver
- `USO` — crude oil
- `DBA` — agriculture

**Bond**

- `TLT` — long-duration US Treasury
- `IEF` — intermediate-duration US Treasury
- `SHY` — short-duration US Treasury
- `LQD` — investment-grade corporate credit

## Research Journey

### 1. XAUUSD Trend Following Stage

**Research question:** Can persistent directional movement in gold support systematic trend, pullback, or breakout rules after realistic execution assumptions?

**Core experiment:** The earlier `xau/` workspace tested XAUUSD trend-following and volatility-breakout structures across historical years, including parameter-island and holdout diagnostics.

**Main conclusion:** The XAU work produced promising trend and breakout candidates, but also exposed substantial overfitting and drawdown risk. Its reports explicitly classify selected parameters as research candidates rather than production-ready evidence. This stage established the project's research discipline and is historical context, not direct validation of the ETF framework.

### 2. Cross-Asset Momentum Discovery

**Research question:** Do the strongest assets in a mixed ETF universe continue to outperform, and can that effect be converted into a monthly portfolio?

**Core experiment:** The project first validated past-return versus future-return relationships, then tested monthly Top1, Top3, and Top5 portfolios using 63- and 126-day momentum across the Original 12 ETFs with 5 bps transaction costs.

**Main conclusion:** The evidence supported winner continuation more strongly than loser continuation. `mom_126 Top5` produced the strongest initial portfolio result, with materially better risk-adjusted performance than narrower Top1 and Top3 portfolios. Relative evidence was strongest against the Equal Weight universe; statistically significant outperformance versus SPY was not established.

### 3. Momentum Window Robustness

**Research question:** Is 126-day momentum an isolated in-sample optimum or part of a stable parameter region?

**Core experiment:** With Top5, Equal Weight, monthly rebalance, and costs fixed, momentum windows from 42 to 252 trading days were tested under a predeclared stable-plateau rule.

**Main conclusion:** The 105-252 day region formed a stable risk/return plateau. The 126-day window was inside the plateau and was not an isolated Sharpe spike. Longer windows generally reduced turnover, while no reliable monotonic performance relationship was established.

### 4. Category Allocation Research

**Research question:** Does the Original 12 result come from momentum ranking or from an implicit fixed allocation among Equity, Commodity, and Bond assets?

**Core experiment:** Free Global Top5 was compared with fixed `3-1-1`, `2-2-1`, and `1-3-1` category-slot structures. Additional representative-universe and Bond-anchor studies examined category balance and defensive allocation.

**Main conclusion:** Free Top5 outperformed every fixed category allocation. Its long-run average slots were approximately 2.20 Equity, 1.60 Commodity, and 1.20 Bond, but the exact `2-2-1` structure occurred in only 6.51% of rebalance months. The successful feature was dynamic category rotation generated by momentum, not a mechanically fixed category mix.

### 5. Expanded 45 ETF Research

**Research question:** Does the framework retain its characteristics when the ranking universe expands from 12 to 45 ETFs?

**Core experiment:** Original 12 and Expanded 45 Global Top5 were compared on the same common sample with identical momentum, portfolio, rebalance, and cost rules.

**Main conclusion:** Expanded Global Top5 materially deteriorated: Sharpe fell from approximately 0.89 to 0.46 and MaxDD worsened from approximately -23.09% to -39.59% on the matched sample. Bond exposure was crowded out while correlated Equity and Commodity candidates gained more ranking opportunities. Universe expansion increased nominal breadth but did not preserve effective breadth.

### 6. Correlation Clustering Research

**Research question:** Did the Expanded 45 universe add independent risk sources or mainly correlated duplicates?

**Core experiment:** Monthly-return hierarchical clustering used correlation distance and average linkage without running a strategy backtest. Representative-cluster universes were subsequently tested under the existing fixed strategy design.

**Main conclusion:** The 45 ETFs mapped to roughly nine interpretable risk clusters at the selected diagnostic threshold; 23 ETFs fell into one broad Equity cluster. Representative ETFs repaired much of the Expanded universe's volatility and drawdown damage, but did not fully recover Original 12 performance. Deduplication is necessary for universe design, but category opportunity balance also matters.

### 7. MA200 Research

**Research question:** Does an MA200 trend filter provide persistent incremental value to cross-sectional momentum?

**Core experiment:** MA200 Cash and Reweight implementations, annual/regime attribution, neighboring MA lengths, and MA200 interactions with Inverse Vol were evaluated while holding the momentum framework fixed.

**Main conclusion:** MA200 Cash can reduce drawdown during stress periods, and MA200 lies within a stable risk-filter parameter region. However, its full-sample Sharpe benefit was materially influenced by crisis years, it dragged returns during the 2023-2025 bull market, and it did not add value when combined with Inverse Vol. MA200 Reweight materially worsened results. MA200 remains a possible crisis overlay, not part of Framework V1.

### 8. Position Sizing Research

**Research question:** Can portfolio sizing improve risk-adjusted performance without changing the momentum Alpha signal?

**Core experiment:** Equal Weight, Rank Weight, Inverse Vol, Rank x Inverse Vol, Inverse Variance, and Inverse Vol windows from 21 to 252 trading days were compared using identical monthly Top5 selections.

**Main conclusion:** Inverse Vol preserved CAGR near 10.3% while raising Sharpe from approximately 0.81 to 0.97 and improving MaxDD from approximately -29.06% to -17.22%. All tested 21-252 day volatility windows formed one stable plateau. Inverse Variance added only about 0.008 Sharpe while reducing CAGR, slightly worsening MaxDD, increasing concentration, and shifting more risk toward Bonds. The evidence supports moderate risk balancing rather than aggressive suppression of volatile assets.

### 9. Correlation Adjustment Research

**Research question:** Does a simple correlation penalty improve Inverse Vol by reducing duplicated risk among the selected Top5?

**Core experiment:** Correlation-Adjusted Inverse Vol multiplied inverse-vol weights by `max(0.10, 1 - average correlation)` using the same 126-day trailing window.

**Main conclusion:** The adjustment lowered weighted pairwise correlation from approximately 0.372 to 0.308, but Sharpe declined from approximately 0.965 to 0.958 and MaxDD worsened from approximately -17.22% to -17.96%. Concentration and turnover increased. Simple average-correlation penalization did not provide incremental value over Inverse Vol.

## Confirmed Findings

The following findings are supported by the completed studies, subject to their stated samples and assumptions:

- Cross-asset winner continuation is present strongly enough to construct a viable research portfolio in the Original 12 universe.
- Monthly `mom_126 Top5` has materially better risk-adjusted performance than the tested Top1 and Top3 variants.
- Momentum behavior is stable across the tested 105-252 day region; 126 days is not an isolated peak.
- Original 12 is more effective than Expanded 45 for unrestricted Global Top5 ranking.
- The Original 12 advantage reflects both useful cross-asset diversity and balanced ranking opportunities; nominal ticker count is not effective breadth.
- Dynamic category rotation is more effective than the tested fixed category-slot allocations.
- Equity is the principal return engine, Commodity contributes return opportunities, and Bond is an important risk diversifier in the existing attribution studies.
- Returns are not entirely dependent on one ETF: removing leading contributors reduced performance but did not eliminate the strategy.
- Inverse Vol materially improves Sharpe and MaxDD while approximately preserving Equal Weight CAGR.
- Inverse Vol improvement is robust across all tested 21-252 day volatility windows; the 126-day choice is not an isolated sizing optimum.
- Inverse Vol provides a better overall return/risk balance than Inverse Variance in the fixed comparison.
- Simple correlation adjustment lowers a correlation diagnostic but does not improve realized risk-adjusted performance.

These findings do not establish live-trading profitability. Benchmark-relative statistical evidence remains mixed, and chronological out-of-sample validation has not yet been completed.

## Rejected Ideas or Currently Unsupported Directions

The following ideas are excluded from Framework V1 because current evidence rejected them or did not show incremental value:

- **Fixed Category Allocation:** `3-1-1`, `2-2-1`, and `1-3-1` all underperformed free Original Top5 in the completed comparison.
- **Expanded 45 ETF Global Ranking:** correlated duplicates and unequal cluster representation materially worsened Sharpe and MaxDD.
- **MA200 Reweight:** filtering and fully reweighting the remaining assets worsened risk-adjusted performance.
- **MA200 added to Inverse Vol:** no independent or complementary improvement was demonstrated in the fixed interaction test.
- **Inverse Variance:** more aggressive low-volatility concentration did not improve the overall CAGR/Sharpe/MaxDD balance over Inverse Vol.
- **Rank Weight:** overweighting the highest momentum ranks did not improve CAGR and increased risk concentration.
- **Simple Correlation Penalty:** lower weighted correlation did not translate into better Sharpe or MaxDD.
- **Loser Continuation as a standalone premise:** evidence primarily supported winner continuation, not persistent absolute declines among losers.

“Rejected” here means not supported for inclusion in V1 under the completed designs. It does not claim universal invalidity outside the tested samples or rules.

## Current Champion Strategy

**Original 12 ETF Universe**  
**+ 126-Day Cross-Sectional Momentum**  
**+ Monthly Top5 Selection**  
**+ 126-Day Inverse Volatility Weighting**

### Verified In-Sample Performance

| Metric | Result |
| --- | ---: |
| Sample | 2008-02-01 to 2025-12-31 |
| CAGR | 10.32% |
| Sharpe | 0.97 |
| Max Drawdown | -17.22% |
| Annual Volatility | 10.75% |
| Calmar | 0.60 |
| Total Return | 476.94% |
| Total Turnover | 13244.12% |

These figures include the study's 5 bps turnover cost model. They are in-sample research results, not a forecast and not evidence of live execution readiness.

## Validation Status

Framework 001 has completed the first formal validation sequence without changing rules or optimizing parameters:

- **Walk-Forward Validation:** positive CAGR and Sharpe in all four sequential segments; MaxDD improved versus Equal Weight Top5 in every segment.
- **Regime Analysis:** return contribution is strongest in favorable risk-asset regimes, while SPY Bear and Weak Equity regimes show materially shallower drawdown than SPY and Equal Weight Top5.
- **Bootstrap Validation:** monthly-block bootstrap showed 100.00% positive-CAGR probability, 2.27% probability of MaxDD worse than -30%, and persistent Sharpe/MaxDD advantage versus Equal Weight Top5.
- **Monte Carlo Path Simulation:** path randomization confirmed sequence risk mainly affects drawdown, while long-run wealth remains stable across shuffle, fixed-block, and stationary-bootstrap simulations.

The validation sequence supports promoting Framework 001 from research champion to **Validated Research Framework**. This is not live-trading approval.

## Open Questions

The next phase should focus on live-readiness and implementation risk:

- **Transaction-Cost Stress:** test whether the conclusion survives wider spreads, slippage, and implementation shortfall.
- **Data and Instrument Robustness:** address ETF inception, survivorship, adjusted-price quality, and investability constraints.
- **Live Trading Readiness:** define broker execution, order timing, fractional-share constraints, cash handling, monitoring, reconciliation, and failure procedures.
- **Paper Trading Simulation:** rehearse signal generation, order creation, fills, logging, and exception handling before any live deployment.

Until these questions are completed, Framework 001 should be treated as a validated research framework and frozen reference specification, not as a production strategy.

## Evidence Index

This framework is consolidated from the following existing research records:

- XAUUSD context: [`xau/vb/v1/reports/H4/summary.md`](../../xau/vb/v1/reports/H4/summary.md), [`xau/tp/v1/optimization/OVERFITTING_ASSESSMENT.md`](../../xau/tp/v1/optimization/OVERFITTING_ASSESSMENT.md)
- Momentum validation: [`research/time_series/momentum_validation/summary.md`](../research/time_series/momentum_validation/summary.md)
- Initial portfolio study: [`research/cross_sectional/mixed_asset_momentum/summary.md`](../research/cross_sectional/mixed_asset_momentum/summary.md)
- Momentum robustness: [`research/cross_sectional/momentum_window_robustness/summary.md`](../research/cross_sectional/momentum_window_robustness/summary.md)
- Category allocation: [`research/cross_sectional/original_12_category_allocation/summary.md`](../research/cross_sectional/original_12_category_allocation/summary.md)
- Expanded universe: [`research/cross_sectional/expanded_universe_momentum/summary.md`](../research/cross_sectional/expanded_universe_momentum/summary.md)
- Correlation clustering: [`research/cross_sectional/etf_correlation_clustering/summary.md`](../research/cross_sectional/etf_correlation_clustering/summary.md)
- MA200 studies: [`research/cross_sectional/ma200_filtered_momentum/summary.md`](../research/cross_sectional/ma200_filtered_momentum/summary.md), [`research/cross_sectional/ma_filter_robustness/summary.md`](../research/cross_sectional/ma_filter_robustness/summary.md), [`research/cross_sectional/ma200_inverse_vol_interaction/summary.md`](../research/cross_sectional/ma200_inverse_vol_interaction/summary.md)
- Position sizing: [`research/cross_sectional/position_sizing_test_a/summary.md`](../research/cross_sectional/position_sizing_test_a/summary.md), [`research/cross_sectional/inverse_vol_window_robustness/summary.md`](../research/cross_sectional/inverse_vol_window_robustness/summary.md), [`research/cross_sectional/position_sizing_test_b/summary.md`](../research/cross_sectional/position_sizing_test_b/summary.md)
- Correlation-aware sizing: [`research/cross_sectional/correlation_aware_position_sizing/summary.md`](../research/cross_sectional/correlation_aware_position_sizing/summary.md)
- Formal validation: [`validation/walk_forward_001_cross_asset_momentum_v1.md`](../validation/walk_forward_001_cross_asset_momentum_v1.md), [`validation/regime_001_cross_asset_momentum_v1.md`](../validation/regime_001_cross_asset_momentum_v1.md), [`validation/bootstrap_001_cross_asset_momentum_v1.md`](../validation/bootstrap_001_cross_asset_momentum_v1.md), [`validation/monte_carlo_001_cross_asset_momentum_v1.md`](../validation/monte_carlo_001_cross_asset_momentum_v1.md)

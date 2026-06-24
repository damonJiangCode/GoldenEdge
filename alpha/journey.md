# Research Journey

## 2026-06-16

- Started MA200 trend-filter research across equity, commodity, and bond ETFs.
- Found that MA200 consistently reduces drawdown but is not a stable standalone return Alpha.
- Completed the initial 52-week-high event study and separated event prediction from strategy backtesting.

## 2026-06-17

- Expanded MA200 and 52-week-high validation to the 12 ETF Mixed Asset Universe.
- Completed time-series momentum validation using 63/126/252-day lookbacks and 20/60/120-day forward returns.
- Built the first Mixed Asset Cross-Sectional Momentum portfolio with monthly Top1/Top3/Top5 selection.
- Identified `mom_126 Top5` as the strongest fixed portfolio specification in the initial study.
- Completed momentum-window robustness testing; the 105-252 day region behaved as a stable parameter plateau rather than an isolated 126-day peak.

## 2026-06-18

- Expanded the Equity ETF data universe to 24 instruments and the Commodity ETF universe to 14 instruments.
- Completed Equity-only and Commodity-only cross-sectional studies; neither universe was stronger or more stable than the Mixed Asset Universe.
- Completed asset-level performance attribution. QQQ, GLD, and SLV contributed 54.34% of baseline net return, while all 12 ETFs contributed positively.
- Completed top-contributor removal tests. Removing QQQ/GLD/SLV reduced CAGR and Sharpe but did not eliminate the strategy.
- Completed asset-class removal analysis. Equity is the main return engine, Commodity enhances return, and Bond is the main risk diversifier.
- Completed Bottom Loser Continuation validation. Evidence primarily supports Winner Continuation, with limited relative loser weakness and no robust evidence that losers continue falling.
- Refactored the research repository into `research/cross_sectional/`, `research/time_series/`, and `shared/`, with a consistent `scripts/`, `summary.md`, `metrics/`, and `outputs/` convention for every study.
- Moved the unified ETF data store and download pipeline to `shared/data/`; research folders continue to reference one shared data source.

## 2026-06-19
- Completed the fixed-parameter MA200 filter test for Mixed Asset mom_126 Top5.
- Version A (ineligible allocations held as cash) preserved CAGR, improved Sharpe from 0.88 to 0.91, and reduced MaxDD from -29.06% to -17.82%.
- Version B (fully invested among fewer eligible assets) reduced Sharpe to 0.77 and worsened MaxDD to -32.77%.
- Concluded that MA200 is useful as a conditional cash and risk overlay, not as a fully invested concentration rule.

## 2026-06-20
- Completed annual and market-regime attribution for the MA200 Version A filter.
- Found that drawdown protection survives excluding 2008, but the full-sample Sharpe improvement does not.
- Identified meaningful protection in several stress periods and a 4.75 percentage-point return drag during 2023-2025.
- Reclassified MA200 Version A as a crisis-risk overlay rather than a persistent return enhancer.
- Completed MA-length robustness testing from MA100 through MA300 using the fixed Version A framework.
- Identified MA125-MA250 as the longest stable platform under the predeclared Sharpe, CAGR, and MaxDD thresholds; MA200 lies inside the platform.
- Found no isolated Sharpe spike, while every tested MA length improved MaxDD versus the unfiltered baseline.
- Completed the requested 40-ETF shared-data universe by adding TIP, HYG, and UUP through the unified download pipeline.
- Added currency as a shared asset class while retaining five extra Equity ETFs pending a deletion decision.
- Completed the fixed-parameter Expanded Universe Momentum test on the strict 45-ETF common sample.
- Found that expansion increased nominal selection breadth but reduced Sharpe from 0.89 to 0.46 and worsened MaxDD from -23.09% to -39.59%.
- Observed that original 12 ETFs supplied only 28.62% of expanded Top5 slots, while Bond exposure fell from 17.89% to 2.73%; the strategy is materially Universe-sensitive.
- Completed the Asset Rotation vs Category Rotation test using the same Expanded Universe sample and fixed momentum design.
- Category Balanced restored roughly 20% Bond exposure and recovered CAGR/MaxDD to 11.77%/-22.43%, making it the closest structure to Original 12 ETF Top5.
- Category Winner based on whole-class momentum reached Sharpe 0.71 and MaxDD -18.66%; evidence supports combining asset-level momentum with explicit category structure.
- Completed monthly-return correlation clustering for the 45-ETF Expanded Universe without running a strategy backtest.
- Identified 9 interpretable risk clusters at correlation-distance threshold 0.50; 23 ETFs collapsed into one Broad Equity Beta cluster.
- Confirmed that much of the expanded breadth is nominal, with Energy/Broad Commodity duplication and only a few standalone diversifiers such as UUP and UNG.
- Completed the fixed Representative Cluster Universe Momentum test using one ETF from each of the 9 identified risk clusters.
- Removing duplicate ranking opportunities raised Sharpe from 0.46 to 0.67 and improved MaxDD from -39.59% to -20.91%, but CAGR remained 7.93% versus 11.34% for Original 12.
- Concluded that cluster deduplication repairs much of the risk profile but is insufficient without balancing the number of ranking opportunities across asset classes.
- Completed the Representative Cluster Universe plus fixed Category Balanced allocation test.
- Category balancing raised CAGR/Sharpe to 9.81%/0.79, restored Bond exposure to 19.89%, and reduced total turnover while remaining close to Original 12 under predeclared criteria.
- Confirmed that robust Universe design requires both correlation deduplication and balanced ranking opportunities across asset classes.
- Completed cluster-level direct contribution and one-at-a-time removal sensitivity for the Representative Category Balanced framework.
- Equity was the primary return and Sharpe engine; Precious Metals and Palladium were secondary return sources, while Bond provided the clearest drawdown protection.
- Natural Gas was the main sample-period drag and USD had no role under the current zero-currency-slot rule; removal findings remain sensitivity evidence rather than optimization instructions.
- Completed the Bond Anchor vs Category Balanced comparison with fixed IEF and two predefined Alpha-sleeve ranking rules.
- Bond Anchor Global Top4 lowered drawdown but reduced CAGR/Sharpe; adding a two-Commodity cap restored Sharpe to 0.80 but did not dominate Category Balanced across all metrics.
- Concluded that a fixed risk anchor cannot replace category concentration control; future sizing research should separate the Bond anchor from Alpha-sleeve risk limits.
- Completed the Original 12 ETF category-allocation comparison across free Top5, 3-1-1, 2-2-1, and 1-3-1 structures.
- Original Top5 outperformed every fixed allocation and averaged 2.20 Equity, 1.60 Commodity, and 1.20 Bond slots; 2-2-1 was the nearest fixed structure.
- Exact 2-2-1 occurred in only 6.51% of months, confirming that dynamic category rotation rather than a stable mechanical allocation explains much of Original 12's success.

## 2026-06-22
- Completed the first fixed-signal position-sizing test on Original 12 ETF Top5.
- Inverse Volatility preserved CAGR near 10.3% while raising Sharpe from 0.81 to 0.97 and improving MaxDD from -29.06% to -17.22%.
- Rank Weight reduced Sharpe and increased volatility; Rank x Inverse Vol delivered only partial risk improvement.
- Identified Inverse Volatility as the strongest in-sample sizing candidate for chronological out-of-sample validation, without changing the Alpha signal.
- Completed the fixed MA200 x Inverse Vol interaction test using both Cash and Reweight implementations.
- MA200 Cash reduced Equal Weight drawdown but did not improve Sharpe; MA200 Reweight materially worsened both EW and IV variants.
- Inverse Volatility alone remained superior to every MA200 combination, providing no evidence of incremental MA/IV complementarity in the current framework.
- Completed Inverse Volatility window robustness testing from 21 through 252 trading days.
- All ten windows formed one stable plateau with only 0.034 Sharpe range, 0.30 percentage-point CAGR range, and 1.51 percentage-point MaxDD range.
- Confirmed that IV improvement comes from a stable risk-balancing mechanism: Rank1 assets were consistently more volatile and downweighted across every window, with no isolated parameter spike.
- Completed the fixed Inverse Vol versus Inverse Variance position-sizing comparison.
- Inverse Variance reduced volatility further but increased HHI from 0.286 to 0.419, cut effective positions to 3.07, and shifted roughly 40% of ex-ante risk to Bonds.
- The additional 0.008 Sharpe came with a 0.70 percentage-point CAGR loss and slightly worse MaxDD, supporting Inverse Vol as the better risk/return balance.
- Completed the fixed Correlation-Aware Inverse Vol position-sizing test on Original 12 ETF Top5.
- The adjustment lowered weighted pairwise correlation from 0.372 to 0.308, but Sharpe slipped from 0.965 to 0.958 and MaxDD worsened from -17.22% to -17.96%.
- Concluded that the simple average-correlation penalty adds no incremental value beyond Inverse Vol in this universe; lower measured correlation alone did not improve realized risk-adjusted performance.

## 2026-06-23
- Completed Walk Forward Validation 001 for Framework 001 using the frozen Original 12 ETF, mom_126, Top5, 126-day Inverse Vol framework.
- The framework produced positive CAGR and positive Sharpe in all four walk-forward segments from 2008-2025.
- Inverse Vol improved MaxDD versus Equal Weight Top5 in 4/4 segments and improved Sharpe in 3/4 segments; WF3 was nearly flat but slightly lower on Sharpe.
- Confirmed that Framework 001 is robust enough to proceed to deeper validation, with the caveat that it is mainly a Sharpe and drawdown framework rather than a SPY-CAGR maximizer.
- Completed Regime Analysis 001 for Framework 001 using objective SPY trend, SPY return, Commodity proxy, Bond stress, and realized-volatility regimes.
- Found that absolute return is concentrated in favorable risk-asset regimes such as SPY Bull and Strong Equity, while Commodity Bull and Bond Bull regimes also show strong Sharpe.
- Confirmed that the framework is defensive but not immune in SPY Bear and Weak Equity regimes; the main benefit there is materially shallower drawdown versus SPY and Equal Weight Top5.
- High-volatility regimes show clear inverse-vol sizing value, with better Sharpe and much shallower MaxDD versus Equal Weight Top5.
- Completed Bootstrap Validation 001 using 10,000 daily bootstrap simulations and 10,000 monthly-block bootstrap simulations on Framework 001 daily net returns.
- Monthly-block bootstrap showed Framework 001 P(CAGR > 0) = 100.00%, P(Sharpe > 0) = 100.00%, and P(MaxDD worse than -30%) = 2.27%.
- Framework 001 preserved its Sharpe and MaxDD advantages over Equal Weight Top5 with 96.36% and 97.12% monthly-block probabilities.
- Bootstrap confirmed the recurring thesis: the framework is statistically credible for Sharpe and drawdown control, but not a reliable SPY-CAGR maximizer.
- Completed Monte Carlo Path Simulation 001 using return shuffle, fixed 21-day block sampling, and stationary bootstrap with average block length 21 trading days.
- Confirmed that sequence risk mainly affects drawdown rather than terminal wealth under pure return shuffling; shuffled paths kept CAGR fixed near 10.29% while MaxDD varied widely.
- Fixed block Monte Carlo was the strictest tail-risk method, with P(MaxDD worse than -30%) = 4.22% and a worst path near flat final wealth.
- Stationary bootstrap showed P(CAGR > 0) = 100.00%, P(CAGR > 5%) = 98.66%, and 5th percentile final wealth = 2.98x.
- Marked Framework 001 as a Validated Research Framework and opened `alpha/live_readiness/` for pre-live assessment work.

## 2026-06-24
- Completed Cross-Sectional Loser Effect 001 under `alpha/research/cross_sectional/down/loser_effect_001`.
- Tested Original 12 ETF monthly worst-ranked assets using fixed 126-day lookback and forward horizons of 5, 10, 20, 40, 60, and 120 trading days.
- Found no statistically robust standalone loser continuation: 7/18 aggregate cells had negative mean forward returns, but 0/18 were significantly negative.
- Longer horizons showed more mean-reversion behavior, especially Top3/Top5 Losers at FR60 and FR120.
- Classified the loser side as mixed behavior rather than a validated short-side alpha direction; loser research remains useful for future long-short spread diagnostics.

## Current Direction

- Primary research candidate: Mixed Asset medium-term Cross-Sectional Momentum with monthly Top5 selection and Inverse Volatility sizing.
- Next validation priorities: transaction-cost stress, paper trading simulation, execution assumptions, monitoring, reconciliation, and live failure procedures.
- MA200 remains a candidate risk-control module rather than a standalone Alpha source.

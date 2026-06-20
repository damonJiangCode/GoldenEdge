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
- Refactored the research repository into `cross_sectional/`, `time_series/`, and `shared/`, with a consistent `scripts/`, `summary.md`, `metrics/`, and `outputs/` convention for every study.
- Moved the unified ETF data store and download pipeline to `shared/data/`; research folders continue to reference one shared data source.

## 2026-06-19
- Completed the fixed-parameter MA200 filter test for Mixed Asset mom_126 Top5.
- Version A (ineligible allocations held as cash) preserved CAGR, improved Sharpe from 0.88 to 0.91, and reduced MaxDD from -29.06% to -17.82%.
- Version B (fully invested among fewer eligible assets) reduced Sharpe to 0.77 and worsened MaxDD to -32.77%.
- Concluded that MA200 is useful as a conditional cash and risk overlay, not as a fully invested concentration rule.

## Current Direction

- Primary research candidate: Mixed Asset medium-term Cross-Sectional Momentum with monthly Top5 selection.
- Next validation priorities: chronological out-of-sample testing, walk-forward stability, transaction-cost stress, and market-regime analysis.
- MA200 remains a candidate risk-control module rather than a standalone Alpha source.

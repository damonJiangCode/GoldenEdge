# Framework001 — Cross-Asset Momentum Alpha Research Summary

## 1. Research Goal

This project studies whether cross-sectional momentum can be converted into a robust multi-asset ETF portfolio framework.

The core research question is:

> Across different asset classes, do assets with stronger past performance continue to outperform, and can that effect be implemented as a stable portfolio strategy?

This is not a single backtest. The project includes signal validation, universe design, position sizing research, robustness tests, regime analysis, bootstrap validation, Monte Carlo simulation, and 2026 out-of-sample testing.

## 2. Universe

The final frozen universe is the Original 12 ETF universe.

### Equity

- SPY
- QQQ
- IWM
- EFA

### Commodity

- GLD
- SLV
- USO
- DBA

### Bond

- TLT
- IEF
- SHY
- LQD

The main historical sample is:

`2008-02-01` to `2025-12-31`

An additional out-of-sample test was run on 2026 data through:

`2026-06-23`

## 3. Final Framework001

Framework001 is currently frozen as:

- Universe: Original 12 ETF
- Signal: 126 trading-day cross-sectional momentum
- Selection: Monthly Top5
- Rebalance: Month-end signal, next trading day execution
- Weighting: 126 trading-day inverse volatility
- Transaction cost: 5 bps on turnover
- Long only
- No leverage
- No shorting
- No MA filter

In plain English:

> Each month, rank the 12 ETFs by their past 126-day return, select the strongest 5, then allocate using inverse volatility so that lower-volatility holdings receive larger weights.

## 4. Historical Performance

Framework001 historical performance is approximately:

| Metric | Framework001 |
| --- | ---: |
| CAGR | 10.3% |
| Sharpe | 0.97 |
| Max Drawdown | -17.2% |
| Total Return | 4.8x |

The main improvement came from replacing equal-weight Top5 momentum with inverse-volatility weighting.

Inverse volatility preserved most of the return while materially improving Sharpe and reducing drawdown.

## 5. Main Findings

### Cross-Asset Momentum Works

The Original 12 ETF universe shows a real cross-sectional momentum effect.

Past winners across equities, commodities, and bonds tend to remain useful portfolio candidates.

The best structure was not Top1 or Top3. A Top5 portfolio provided a better balance between return capture and diversification.

### Inverse Volatility Is the Key Upgrade

Several position sizing methods were tested:

- Equal Weight
- Rank Weight
- Inverse Volatility
- Rank x Inverse Volatility
- Inverse Variance
- Correlation-adjusted Inverse Volatility

The strongest result came from 126-day inverse-volatility weighting.

Inverse Volatility improved risk-adjusted return without over-concentrating the portfolio into low-volatility assets.

### Original 12 Beats the Expanded Universe

The universe was expanded to 45 ETFs, but performance deteriorated.

The expanded universe added many highly correlated ETFs, especially within equities and commodities. It increased nominal breadth, but not true independent risk sources.

The Original 12 universe performed better because it had:

- Better balance across asset classes
- Less duplicate exposure
- Cleaner rotation between equity, commodity, and bond regimes

### MA200 Was Not Added

MA200 trend filtering reduced some crisis drawdowns, but it did not provide a stable independent improvement once inverse-volatility sizing was already used.

MA200 remains a possible risk overlay, but it is not part of Framework001.

### Loser Side Is Not Reliable Enough

The loser side was also tested:

> Do the worst-ranked ETFs continue to underperform?

The answer was mixed.

Short-term loser continuation existed in some cases, but longer horizons often showed mean reversion. There was no strong evidence for a stable short-loser alpha.

Framework001 therefore remains long-only.

## 6. Validation Results

### Walk Forward Validation

Framework001 was tested across multiple historical segments from 2008 to 2025.

Results:

- Positive CAGR in all walk-forward segments
- Positive Sharpe in all walk-forward segments
- Inverse Volatility reduced drawdown versus Equal Weight Top5 in every segment

Conclusion:

> The framework is not dependent on one single historical period.

### Regime Analysis

Framework001 was tested across market regimes, including:

- Equity bull regimes
- Equity bear regimes
- Commodity bull and bear regimes
- Bond stress regimes
- High-volatility regimes

The framework performs best when risk assets trend, but it also shows meaningful drawdown control during weaker equity environments.

It is defensive, but not immune.

### Bootstrap Validation

Daily bootstrap and monthly-block bootstrap simulations were run.

Monthly-block bootstrap showed:

- P(CAGR > 0): 100%
- P(Sharpe > 0): 100%
- P(MaxDD worse than -30%): about 2.3%

Conclusion:

> The historical result is statistically credible and not obviously caused by a few lucky months.

### Monte Carlo Path Simulation

Monte Carlo path simulation tested sequence risk.

The strictest block simulation showed:

- Most paths remained profitable
- Severe drawdowns are possible
- But the framework did not show evidence of path fragility

Conclusion:

> Framework001 has acceptable path risk for a validated research framework.

### 2026 Out-of-Sample Test

The 2026 OOS test used new data only.

2026-01-02 to 2026-06-23:

| Metric | Framework001 |
| --- | ---: |
| Total Return | 9.34% |
| Sharpe | 1.11 |
| Max Drawdown | -8.66% |

Framework001 outperformed Equal Weight Top5 on Sharpe and drawdown control.

It also slightly exceeded SPY on CAGR and MaxDD during this partial OOS window, but it did not outperform Original 12 Equal Weight on Sharpe or drawdown.

Conclusion:

> 2026 OOS behavior is normal so far. There is no evidence of framework break, but the sample is still partial-year and should not be over-interpreted.

## 7. Recent Framework Extension Tests

### Absolute Momentum Integration

Tested rule:

`126-day return > 0`

Result:

- Reweight versions improved CAGR slightly but worsened Sharpe and MaxDD
- Cash versions slightly improved Sharpe but did not materially improve drawdown

Conclusion:

> Absolute Momentum Cash is a weak candidate for further validation, but not strong enough to upgrade Framework001.

### Number of Holdings: Top3 vs Top5 vs Top7

Results:

| Strategy | CAGR | Sharpe | MaxDD |
| --- | ---: | ---: | ---: |
| Top3 | 10.02% | 0.70 | -30.15% |
| Top5 | 10.32% | 0.97 | -17.22% |
| Top7 | 6.73% | 0.87 | -15.24% |

Conclusion:

> Top3 is too concentrated. Top7 is more defensive but dilutes returns too much. Top5 remains the best balance.

### Momentum Ensemble

Tested signal:

Average rank of:

- 63-day momentum
- 126-day momentum
- 252-day momentum

Result:

| Strategy | CAGR | Sharpe | MaxDD |
| --- | ---: | ---: | ---: |
| 126-day baseline | 10.32% | 0.965 | -17.22% |
| Momentum ensemble | 10.21% | 0.957 | -14.06% |

The ensemble improved drawdown but slightly reduced CAGR and Sharpe.

Conclusion:

> Momentum Ensemble is a drawdown-improvement candidate, but not strong enough to replace the simpler 126-day signal.

## 8. Current Final Conclusion

The current best framework remains:

> Original 12 ETF  
> 126-day Cross-Sectional Momentum  
> Monthly Top5  
> 126-day Inverse Volatility Weighting

Framework001 is not designed to maximize raw CAGR.

Its strength is:

- Capturing medium-term cross-asset momentum
- Maintaining diversification across asset classes
- Improving Sharpe through inverse-volatility sizing
- Reducing drawdown versus equal-weight momentum
- Remaining robust across walk-forward, regime, bootstrap, Monte Carlo, and OOS tests

The current evidence does not justify replacing Framework001 with Absolute Momentum, Top3, Top7, or Momentum Ensemble.

## 9. Next Steps

The next research stage should focus less on improving in-sample performance and more on live-readiness:

- Transaction cost stress test
- Slippage assumptions
- Paper trading simulation
- Execution rules
- Monitoring and alerting
- Portfolio reconciliation
- Failure procedures

Framework001 is best classified as:

> Validated Research Framework, ready for live-readiness assessment, but not yet a live trading system.

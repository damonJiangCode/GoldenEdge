# Regime Analysis 001 — Cross-Asset Momentum Framework V1

## 1. Research Question

Framework 001 has passed Walk Forward Validation. This report asks how the frozen framework behaves across objective market regimes: where it earns returns, where it is weak, which asset classes carry it, and whether the result depends on one market state.

No parameter is optimized. No strategy rule is changed.

## 2. Fixed Framework

| Component | Definition |
| --- | --- |
| Universe | Original 12 ETF |
| Equity | SPY, QQQ, IWM, EFA |
| Commodity | GLD, SLV, USO, DBA |
| Bond | TLT, IEF, SHY, LQD |
| Signal | 126 trading-day momentum |
| Selection | Monthly rebalance; month-end signal; next trading day execution; Top5 momentum ETFs |
| Weighting | Inverse Volatility; 126 trading-day daily-return volatility; normalized to 100% |
| Cost | 5 bps transaction cost applied to turnover |
| Constraints | Long only; no leverage; no shorting; no MA filter |

## 3. Regime Definitions

All regimes are rule-based and calculated from data available at each date. This analysis uses daily regime labels from `2008-02-01` to `2025-12-31`.

- **SPY Trend Regime:** SPY Adj Close above or below/equal to SPY SMA200.
- **SPY Return Regime:** trailing 126-day SPY return above +10%, below -10%, or neutral.
- **Commodity Regime:** trailing 126-day DBC return above +10%, below -10%, or neutral. DBC is used only as an external Commodity regime proxy; it is not part of the Original 12 ETF trading universe.
- **Bond Stress Regime:** trailing 126-day TLT return above +10%, below -10%, or neutral.
- **Realized Volatility Regime:** full-sample terciles of trailing 63-day SPY realized volatility. Low threshold = 11.79%; high threshold = 16.84%.

Performance is calculated by compressing the daily returns belonging to each regime state. CAGR is annualized by the number of regime days, not by calendar span. This makes the table answer: when this state occurs, how does the strategy behave?

## 4. Regime Performance

### SPY Trend Regime

| Regime Set | Regime | Strategy | Days | CAGR | Sharpe | MaxDD | Volatility | Total Return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPY Trend Regime | SPY Bull Regime | Inverse Vol Framework | 3529 | 14.20% | 1.26 | -13.00% | 11.00% | 542.34% |
| SPY Trend Regime | SPY Bull Regime | Equal Weight Top5 Momentum | 3529 | 15.90% | 1.26 | -13.64% | 12.36% | 689.91% |
| SPY Trend Regime | SPY Bull Regime | SPY Buy & Hold | 3529 | 26.47% | 1.86 | -10.10% | 13.08% | 2581.19% |
| SPY Trend Regime | SPY Bull Regime | Original 12 Equal Weight | 3529 | 11.75% | 1.38 | -11.81% | 8.29% | 373.73% |
| SPY Trend Regime | SPY Bear Regime | Inverse Vol Framework | 979 | -2.73% | -0.23 | -19.08% | 9.76% | -10.18% |
| SPY Trend Regime | SPY Bear Regime | Equal Weight Top5 Momentum | 979 | -7.70% | -0.43 | -38.63% | 15.68% | -26.76% |
| SPY Trend Regime | SPY Bear Regime | SPY Buy & Hold | 979 | -29.40% | -0.83 | -78.03% | 34.73% | -74.14% |
| SPY Trend Regime | SPY Bear Regime | Original 12 Equal Weight | 979 | -12.50% | -0.71 | -47.05% | 16.72% | -40.47% |

### SPY Return Regime

| Regime Set | Regime | Strategy | Days | CAGR | Sharpe | MaxDD | Volatility | Total Return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPY Return Regime | Strong Equity Regime | Inverse Vol Framework | 1623 | 26.13% | 1.94 | -11.01% | 12.40% | 345.96% |
| SPY Return Regime | Strong Equity Regime | Equal Weight Top5 Momentum | 1623 | 28.58% | 1.93 | -12.40% | 13.52% | 404.89% |
| SPY Return Regime | Strong Equity Regime | SPY Buy & Hold | 1623 | 31.45% | 2.32 | -11.83% | 12.09% | 481.96% |
| SPY Return Regime | Strong Equity Regime | Original 12 Equal Weight | 1623 | 16.29% | 1.83 | -8.71% | 8.44% | 164.29% |
| SPY Return Regime | Neutral Equity Regime | Inverse Vol Framework | 2573 | 2.65% | 0.32 | -15.40% | 9.50% | 30.60% |
| SPY Return Regime | Neutral Equity Regime | Equal Weight Top5 Momentum | 2573 | 3.87% | 0.37 | -19.69% | 12.10% | 47.29% |
| SPY Return Regime | Neutral Equity Regime | SPY Buy & Hold | 2573 | 14.01% | 0.81 | -17.73% | 18.13% | 281.57% |
| SPY Return Regime | Neutral Equity Regime | Original 12 Equal Weight | 2573 | 6.19% | 0.67 | -19.34% | 9.58% | 84.65% |
| SPY Return Regime | Weak Equity Regime | Inverse Vol Framework | 312 | -0.76% | -0.01 | -13.39% | 10.95% | -0.94% |
| SPY Return Regime | Weak Equity Regime | Equal Weight Top5 Momentum | 312 | -18.36% | -1.01 | -27.96% | 18.36% | -22.21% |
| SPY Return Regime | Weak Equity Regime | SPY Buy & Hold | 312 | -60.95% | -1.75 | -68.12% | 47.31% | -68.78% |
| SPY Return Regime | Weak Equity Regime | Original 12 Equal Weight | 312 | -35.78% | -1.82 | -42.07% | 22.85% | -42.21% |

### Commodity Regime

| Regime Set | Regime | Strategy | Days | CAGR | Sharpe | MaxDD | Volatility | Total Return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Commodity Regime | Commodity Bull Regime | Inverse Vol Framework | 1102 | 20.71% | 1.50 | -12.48% | 13.16% | 127.77% |
| Commodity Regime | Commodity Bull Regime | Equal Weight Top5 Momentum | 1102 | 25.79% | 1.51 | -15.51% | 16.05% | 172.79% |
| Commodity Regime | Commodity Bull Regime | SPY Buy & Hold | 1102 | 15.21% | 0.95 | -22.91% | 16.31% | 85.73% |
| Commodity Regime | Commodity Bull Regime | Original 12 Equal Weight | 1102 | 10.71% | 1.11 | -12.90% | 9.61% | 56.06% |
| Commodity Regime | Commodity Neutral Regime | Inverse Vol Framework | 2606 | 9.35% | 0.91 | -16.98% | 10.43% | 152.04% |
| Commodity Regime | Commodity Neutral Regime | Equal Weight Top5 Momentum | 2606 | 9.15% | 0.78 | -18.07% | 12.17% | 147.29% |
| Commodity Regime | Commodity Neutral Regime | SPY Buy & Hold | 2606 | 17.53% | 1.12 | -18.80% | 15.58% | 431.46% |
| Commodity Regime | Commodity Neutral Regime | Original 12 Equal Weight | 2606 | 9.26% | 1.05 | -11.42% | 8.83% | 149.91% |
| Commodity Regime | Commodity Bear Regime | Inverse Vol Framework | 800 | 0.16% | 0.06 | -17.29% | 7.60% | 0.50% |
| Commodity Regime | Commodity Bear Regime | Equal Weight Top5 Momentum | 800 | -4.72% | -0.35 | -27.10% | 11.71% | -14.24% |
| Commodity Regime | Commodity Bear Regime | SPY Buy & Hold | 800 | -10.53% | -0.17 | -51.17% | 32.91% | -29.77% |
| Commodity Regime | Commodity Bear Regime | Original 12 Equal Weight | 800 | -9.71% | -0.55 | -39.32% | 16.28% | -27.69% |

### Bond Stress Regime

| Regime Set | Regime | Strategy | Days | CAGR | Sharpe | MaxDD | Volatility | Total Return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bond Stress Regime | Bond Bull Regime | Inverse Vol Framework | 851 | 15.60% | 1.66 | -12.12% | 8.98% | 63.16% |
| Bond Stress Regime | Bond Bull Regime | Equal Weight Top5 Momentum | 851 | 17.08% | 1.34 | -14.28% | 12.31% | 70.33% |
| Bond Stress Regime | Bond Bull Regime | SPY Buy & Hold | 851 | 6.23% | 0.36 | -27.52% | 27.04% | 22.63% |
| Bond Stress Regime | Bond Bull Regime | Original 12 Equal Weight | 851 | 10.64% | 0.81 | -15.72% | 13.55% | 40.70% |
| Bond Stress Regime | Bond Neutral Regime | Inverse Vol Framework | 3134 | 9.25% | 0.85 | -21.66% | 11.19% | 200.45% |
| Bond Stress Regime | Bond Neutral Regime | Equal Weight Top5 Momentum | 3134 | 9.26% | 0.73 | -29.06% | 13.25% | 200.83% |
| Bond Stress Regime | Bond Neutral Regime | SPY Buy & Hold | 3134 | 11.58% | 0.70 | -40.68% | 17.79% | 290.59% |
| Bond Stress Regime | Bond Neutral Regime | Original 12 Equal Weight | 3134 | 5.15% | 0.57 | -28.69% | 9.72% | 86.74% |
| Bond Stress Regime | Bond Bear Regime | Inverse Vol Framework | 523 | 8.16% | 0.79 | -14.52% | 10.71% | 17.69% |
| Bond Stress Regime | Bond Bear Regime | Equal Weight Top5 Momentum | 523 | 6.02% | 0.49 | -18.21% | 13.96% | 12.90% |
| Bond Stress Regime | Bond Bear Regime | SPY Buy & Hold | 523 | 19.50% | 1.06 | -20.28% | 18.49% | 44.74% |
| Bond Stress Regime | Bond Bear Regime | Original 12 Equal Weight | 523 | 3.47% | 0.36 | -16.77% | 11.19% | 7.34% |

### Realized Volatility Regime

| Regime Set | Regime | Strategy | Days | CAGR | Sharpe | MaxDD | Volatility | Total Return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Realized Volatility Regime | Low Volatility Regime | Inverse Vol Framework | 1503 | 5.65% | 0.66 | -11.18% | 8.98% | 38.77% |
| Realized Volatility Regime | Low Volatility Regime | Equal Weight Top5 Momentum | 1503 | 4.01% | 0.44 | -16.97% | 9.99% | 26.41% |
| Realized Volatility Regime | Low Volatility Regime | SPY Buy & Hold | 1503 | 10.05% | 0.99 | -12.18% | 10.24% | 77.02% |
| Realized Volatility Regime | Low Volatility Regime | Original 12 Equal Weight | 1503 | 1.53% | 0.26 | -17.89% | 6.62% | 9.48% |
| Realized Volatility Regime | Medium Volatility Regime | Inverse Vol Framework | 1502 | 15.63% | 1.30 | -11.67% | 11.68% | 137.66% |
| Realized Volatility Regime | Medium Volatility Regime | Equal Weight Top5 Momentum | 1502 | 16.46% | 1.21 | -14.83% | 13.28% | 147.97% |
| Realized Volatility Regime | Medium Volatility Regime | SPY Buy & Hold | 1502 | 16.23% | 1.11 | -22.23% | 14.45% | 145.09% |
| Realized Volatility Regime | Medium Volatility Regime | Original 12 Equal Weight | 1502 | 8.87% | 1.00 | -11.28% | 8.90% | 65.98% |
| Realized Volatility Regime | High Volatility Regime | Inverse Vol Framework | 1503 | 9.83% | 0.88 | -13.77% | 11.39% | 74.94% |
| Realized Volatility Regime | High Volatility Regime | Equal Weight Top5 Momentum | 1503 | 10.82% | 0.74 | -29.06% | 15.60% | 84.56% |
| Realized Volatility Regime | High Volatility Regime | SPY Buy & Hold | 1503 | 8.18% | 0.41 | -50.51% | 29.65% | 59.79% |
| Realized Volatility Regime | High Volatility Regime | Original 12 Equal Weight | 1503 | 7.65% | 0.57 | -30.65% | 14.88% | 55.20% |

## 5. Relative Performance vs Equal Weight Top5

Positive MaxDD Improvement means IV has shallower drawdown.

| Regime Set | Regime | IV Sharpe - EW Sharpe | IV MaxDD Improvement vs EW | IV CAGR - EW CAGR |
| --- | --- | --- | --- | --- |
| SPY Trend Regime | SPY Bull Regime | 0.01 | 0.64% | -1.70% |
| SPY Trend Regime | SPY Bear Regime | 0.20 | 19.54% | 4.98% |
| SPY Return Regime | Strong Equity Regime | 0.01 | 1.38% | -2.45% |
| SPY Return Regime | Neutral Equity Regime | -0.05 | 4.29% | -1.22% |
| SPY Return Regime | Weak Equity Regime | 1.00 | 14.57% | 17.60% |
| Commodity Regime | Commodity Bull Regime | -0.01 | 3.03% | -5.08% |
| Commodity Regime | Commodity Neutral Regime | 0.13 | 1.09% | 0.20% |
| Commodity Regime | Commodity Bear Regime | 0.41 | 9.81% | 4.88% |
| Bond Stress Regime | Bond Bull Regime | 0.32 | 2.16% | -1.48% |
| Bond Stress Regime | Bond Neutral Regime | 0.11 | 7.40% | -0.01% |
| Bond Stress Regime | Bond Bear Regime | 0.30 | 3.69% | 2.14% |
| Realized Volatility Regime | Low Volatility Regime | 0.21 | 5.80% | 1.64% |
| Realized Volatility Regime | Medium Volatility Regime | 0.09 | 3.16% | -0.83% |
| Realized Volatility Regime | High Volatility Regime | 0.14 | 15.29% | -0.99% |

## 6. Relative Performance vs SPY

Positive MaxDD Improvement means IV has shallower drawdown.

| Regime Set | Regime | IV Sharpe - SPY Sharpe | IV MaxDD Improvement vs SPY | IV CAGR - SPY CAGR |
| --- | --- | --- | --- | --- |
| SPY Trend Regime | SPY Bull Regime | -0.60 | -2.90% | -12.27% |
| SPY Trend Regime | SPY Bear Regime | 0.59 | 58.94% | 26.68% |
| SPY Return Regime | Strong Equity Regime | -0.39 | 0.81% | -5.32% |
| SPY Return Regime | Neutral Equity Regime | -0.49 | 2.34% | -11.37% |
| SPY Return Regime | Weak Equity Regime | 1.73 | 54.73% | 60.19% |
| Commodity Regime | Commodity Bull Regime | 0.55 | 10.43% | 5.50% |
| Commodity Regime | Commodity Neutral Regime | -0.21 | 1.82% | -8.18% |
| Commodity Regime | Commodity Bear Regime | 0.23 | 33.88% | 10.69% |
| Bond Stress Regime | Bond Bull Regime | 1.30 | 15.40% | 9.37% |
| Bond Stress Regime | Bond Neutral Regime | 0.14 | 19.02% | -2.33% |
| Bond Stress Regime | Bond Bear Regime | -0.27 | 5.76% | -11.34% |
| Realized Volatility Regime | Low Volatility Regime | -0.33 | 1.01% | -4.40% |
| Realized Volatility Regime | Medium Volatility Regime | 0.19 | 10.56% | -0.60% |
| Realized Volatility Regime | High Volatility Regime | 0.47 | 36.74% | 1.66% |

## 7. Asset Class Exposure by Regime

Framework 001 average daily weights.

| Regime Set | Regime | Equity Weight | Commodity Weight | Bond Weight |
| --- | --- | --- | --- | --- |
| SPY Trend Regime | SPY Bull Regime | 50.22% | 23.89% | 25.89% |
| SPY Trend Regime | SPY Bear Regime | 7.46% | 19.16% | 73.39% |
| SPY Return Regime | Strong Equity Regime | 62.67% | 27.28% | 10.05% |
| SPY Return Regime | Neutral Equity Regime | 31.96% | 20.89% | 47.15% |
| SPY Return Regime | Weak Equity Regime | 1.90% | 16.09% | 82.01% |
| Commodity Regime | Commodity Bull Regime | 47.23% | 34.36% | 18.41% |
| Commodity Regime | Commodity Neutral Regime | 45.65% | 22.88% | 31.47% |
| Commodity Regime | Commodity Bear Regime | 16.90% | 6.96% | 76.15% |
| Bond Stress Regime | Bond Bull Regime | 14.21% | 16.16% | 69.63% |
| Bond Stress Regime | Bond Neutral Regime | 47.84% | 23.93% | 28.23% |
| Bond Stress Regime | Bond Bear Regime | 43.06% | 27.34% | 29.60% |
| Realized Volatility Regime | Low Volatility Regime | 56.52% | 20.18% | 23.30% |
| Realized Volatility Regime | Medium Volatility Regime | 48.36% | 26.00% | 25.64% |
| Realized Volatility Regime | High Volatility Regime | 17.93% | 22.40% | 59.67% |

## 8. ETF Exposure by Regime

Full ETF exposure is saved to CSV. The highest average weights in selected key regimes:

| Regime Set | Regime | Top ETF Weights |
| --- | --- | --- |
| SPY Trend Regime | SPY Bear Regime | SHY 41.18%, IEF 18.51%, LQD 8.18%, GLD 7.75%, TLT 5.51% |
| SPY Return Regime | Weak Equity Regime | SHY 49.24%, IEF 19.55%, LQD 6.79%, GLD 6.53%, TLT 6.43% |
| Commodity Regime | Commodity Bull Regime | SPY 15.62%, DBA 11.88%, QQQ 11.71%, EFA 9.95%, IWM 9.94% |
| Bond Stress Regime | Bond Bear Regime | SHY 25.87%, SPY 13.39%, DBA 12.74%, QQQ 10.32%, EFA 9.70% |
| Realized Volatility Regime | High Volatility Regime | SHY 29.82%, IEF 16.60%, GLD 9.33%, LQD 8.05%, QQQ 5.67% |

## 9. Regime Contribution

Contribution uses additive daily net return contribution: the sum of IV Framework daily returns in each regime divided by the full-sample sum of IV Framework daily returns. It is not a compounded wealth attribution, but it is additive across regimes within each regime set.

| Regime Set | Regime | Contribution To Total Return | Contribution Percent |
| --- | --- | --- | --- |
| SPY Trend Regime | SPY Bull Regime | 194.53% | 104.79% |
| SPY Trend Regime | SPY Bear Regime | -8.88% | -4.79% |
| SPY Return Regime | Strong Equity Regime | 154.53% | 83.24% |
| SPY Return Regime | Neutral Equity Regime | 31.32% | 16.87% |
| SPY Return Regime | Weak Equity Regime | -0.20% | -0.11% |
| Commodity Regime | Commodity Bull Regime | 86.14% | 46.40% |
| Commodity Regime | Commodity Neutral Regime | 98.09% | 52.84% |
| Commodity Regime | Commodity Bear Regime | 1.42% | 0.76% |
| Bond Stress Regime | Bond Bull Regime | 50.33% | 27.11% |
| Bond Stress Regime | Bond Neutral Regime | 117.83% | 63.47% |
| Bond Stress Regime | Bond Bear Regime | 17.48% | 9.42% |
| Realized Volatility Regime | Low Volatility Regime | 35.18% | 18.95% |
| Realized Volatility Regime | Medium Volatility Regime | 90.66% | 48.84% |
| Realized Volatility Regime | High Volatility Regime | 59.81% | 32.22% |

Top contribution states:

| Regime Set | Regime | Contribution To Total Return | Contribution Percent |
| --- | --- | --- | --- |
| SPY Trend Regime | SPY Bull Regime | 194.53% | 104.79% |
| SPY Return Regime | Strong Equity Regime | 154.53% | 83.24% |
| Bond Stress Regime | Bond Neutral Regime | 117.83% | 63.47% |
| Commodity Regime | Commodity Neutral Regime | 98.09% | 52.84% |
| Realized Volatility Regime | Medium Volatility Regime | 90.66% | 48.84% |
| Commodity Regime | Commodity Bull Regime | 86.14% | 46.40% |

## 10. Best and Weakest Regimes

Best IV Framework regimes by Sharpe:

| Regime Set | Regime | Days | CAGR | Sharpe | MaxDD | Total Return |
| --- | --- | --- | --- | --- | --- | --- |
| SPY Return Regime | Strong Equity Regime | 1623 | 26.13% | 1.94 | -11.01% | 345.96% |
| Bond Stress Regime | Bond Bull Regime | 851 | 15.60% | 1.66 | -12.12% | 63.16% |
| Commodity Regime | Commodity Bull Regime | 1102 | 20.71% | 1.50 | -12.48% | 127.77% |
| Realized Volatility Regime | Medium Volatility Regime | 1502 | 15.63% | 1.30 | -11.67% | 137.66% |
| SPY Trend Regime | SPY Bull Regime | 3529 | 14.20% | 1.26 | -13.00% | 542.34% |

Weakest IV Framework regimes by Sharpe:

| Regime Set | Regime | Days | CAGR | Sharpe | MaxDD | Total Return |
| --- | --- | --- | --- | --- | --- | --- |
| SPY Trend Regime | SPY Bear Regime | 979 | -2.73% | -0.23 | -19.08% | -10.18% |
| SPY Return Regime | Weak Equity Regime | 312 | -0.76% | -0.01 | -13.39% | -0.94% |
| Commodity Regime | Commodity Bear Regime | 800 | 0.16% | 0.06 | -17.29% | 0.50% |
| SPY Return Regime | Neutral Equity Regime | 2573 | 2.65% | 0.32 | -15.40% | 30.60% |
| Realized Volatility Regime | Low Volatility Regime | 1503 | 5.65% | 0.66 | -11.18% | 38.77% |

## 11. Interpretation Questions

1. **In which regimes does Framework 001 perform best?** The strongest states are risk-on but not one-dimensional: Bond Bull, Medium Volatility, Commodity Bull, and SPY Bull / Strong Equity regimes all rank well. The best single Sharpe state is `SPY Return Regime / Strong Equity Regime` with Sharpe 1.94.
2. **In which regimes is it weakest?** The weakest states are `SPY Trend Regime / SPY Bear Regime` and other stress states where major sleeves are simultaneously under pressure. Weak Equity has CAGR -0.76% and Sharpe -0.01.
3. **Does Framework 001 depend mainly on equity bull markets?** For absolute net contribution, yes, SPY Bull / Strong Equity states are the dominant return contributors. But the framework is not simply SPY beta: Commodity Bull and Bond Bull states also show strong Sharpe, and bear-state losses are much smaller than SPY. In SPY Bull, Equity exposure averages 50.22%; the framework still keeps meaningful Commodity/Bond exposure.
4. **Does it protect capital during SPY bear regimes?** Yes relative to SPY and Equal Weight Top5. In SPY Bear, IV MaxDD is -19.08%; MaxDD improvement versus SPY is 58.94%. Absolute CAGR is -2.73%, so it is defensive but not immune.
5. **Does it benefit from commodity bull regimes?** Yes. Commodity Bull CAGR is 20.71%, Sharpe 1.50. Commodity sleeve exposure rises to 34.36%, while the top individual weights remain mixed across Equity and Commodity: SPY 15.62%, DBA 11.88%, QQQ 11.71%, EFA 9.95%, IWM 9.94%.
6. **How does it behave during bond bear regimes?** Bond Bear is manageable but not the best environment: CAGR 8.16%, Sharpe 0.79, MaxDD -14.52%. The framework reduces reliance on Bonds and leans more into Equity/Commodity winners.
7. **Does inverse-vol weighting add the most value during high-volatility regimes?** Yes. In High Volatility, IV Sharpe minus Equal Weight Sharpe is 0.14, and MaxDD improvement is 15.29%. This is where sizing discipline is most visibly useful.
8. **Which asset classes dominate in each regime?** SPY Bull and Strong Equity states have higher Equity exposure; Commodity Bull shifts more weight to Commodity; SPY Bear, Weak Equity, and Bond Bull states show higher Bond exposure. The allocation is regime-adaptive rather than static.
9. **Which ETFs are most important in each regime?** In stress and weak-equity states, SHY and IEF are central, with GLD often present as an additional diversifier. In Commodity Bull, DBA and other Commodity sleeve members gain more weight but Equity winners can still remain among the largest positions. In Equity Bull states, SPY/QQQ/IWM/EFA participate more heavily.
10. **Does regime analysis support the framework thesis?** Yes, with nuance. The framework has a reasonable regime profile: it earns most absolute return during favorable risk-asset regimes, but it materially controls drawdown in adverse regimes and rotates exposure across Equity, Commodity, and Bond sleeves.

## 12. Final Conclusion

Framework 001 has a reasonable regime profile. Its absolute return is not evenly distributed: SPY Bull and Strong Equity states are the largest contributors. The important validation result is that performance is not explained by raw equity beta alone. Commodity Bull, Bond Bull, Medium Volatility, and High Volatility states also show useful behavior, while SPY Bear and Weak Equity losses are materially shallower than SPY and Equal Weight Top5.

The evidence supports the framework thesis: Cross-Asset Momentum plus Inverse Volatility behaves like a regime-adaptive allocation system with strong participation in risk-on markets and meaningful risk control in stress markets. It still does not maximize SPY CAGR in strong equity markets, and it is not crisis-proof. But the regime behavior is coherent enough to proceed to deeper validation.

Next validation candidates:

- Bootstrap
- Monte Carlo
- Paper Trading Simulation

## 13. Output Files

- Regime labels: `alpha/validation/outputs/regime_001_labels.csv`
- Regime performance: `alpha/validation/metrics/regime_001_performance.csv`
- Relative vs Equal Weight Top5: `alpha/validation/metrics/regime_001_relative_vs_equal_weight.csv`
- Relative vs SPY: `alpha/validation/metrics/regime_001_relative_vs_spy.csv`
- Asset-class exposure: `alpha/validation/metrics/regime_001_asset_class_exposure.csv`
- ETF exposure: `alpha/validation/metrics/regime_001_etf_exposure.csv`
- Regime contribution: `alpha/validation/metrics/regime_001_contribution.csv`
- Daily details: `alpha/validation/outputs/regime_001_daily_details.csv`
- Daily weights: `alpha/validation/outputs/regime_001_daily_weights.csv`

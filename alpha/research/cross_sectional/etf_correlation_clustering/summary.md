# ETF Correlation Clustering Analysis

## 1. Research Question

识别 Expanded 45 ETF Universe 的月收益相关结构，判断名义资产数量对应多少个相对独立风险簇。本研究不运行任何交易策略。

## 2. Data and Sample

- Price: Adjusted Close
- Frequency: month-end returns
- ETFs included: 45
- Common daily sample: `2015-10-08` to `2025-12-31`
- Monthly return observations: 122
- Correlation distance: `sqrt(0.5 * (1 - correlation))`
- Hierarchical clustering: average linkage

## 3. Highest Correlation Pairs

| ETF 1 | ETF 2 | Correlation | Asset Class 1 | Asset Class 2 | Category 1 | Category 2 |
| --- | --- | --- | --- | --- | --- | --- |
| SPY | VTI | 1.00 | Equity | Equity | Core | Core |
| SPY | QUAL | 0.98 | Equity | Equity | Core | StyleFactor |
| XLRE | VNQ | 0.98 | Equity | Equity | Sector | RealEstate |
| QQQ | IWF | 0.98 | Equity | Equity | Core | StyleFactor |
| VTI | QUAL | 0.98 | Equity | Equity | Core | StyleFactor |
| QQQ | XLK | 0.97 | Equity | Equity | Core | Sector |
| DBC | GSG | 0.96 | Commodity | Commodity | BroadCommodity | BroadCommodity |
| XLK | IWF | 0.96 | Equity | Equity | Sector | StyleFactor |
| IWD | VLUE | 0.96 | Equity | Equity | StyleFactor | StyleFactor |
| DIA | IWD | 0.95 | Equity | Equity | Core | StyleFactor |
| SPY | IWF | 0.95 | Equity | Equity | Core | StyleFactor |
| VTI | IWF | 0.95 | Equity | Equity | Core | StyleFactor |
| USO | GSG | 0.94 | Commodity | Commodity | Energy | BroadCommodity |
| SPY | DIA | 0.94 | Equity | Equity | Core | Core |
| IWF | QUAL | 0.94 | Equity | Equity | StyleFactor | StyleFactor |
| VTI | DIA | 0.94 | Equity | Equity | Core | Core |
| XLI | IWD | 0.94 | Equity | Equity | Sector | StyleFactor |
| DBO | GSG | 0.93 | Commodity | Commodity | Energy | BroadCommodity |
| TLT | IEF | 0.93 | Bond | Bond | Bond | Bond |
| VTI | IWD | 0.93 | Equity | Equity | Core | StyleFactor |

## 4. Lowest Correlation Pairs

| ETF 1 | ETF 2 | Correlation | Asset Class 1 | Asset Class 2 | Category 1 | Category 2 |
| --- | --- | --- | --- | --- | --- | --- |
| EEM | UUP | -0.63 | Equity | Currency | Core | USD |
| EFA | UUP | -0.62 | Equity | Currency | Core | USD |
| LQD | UUP | -0.56 | Bond | Currency | Bond | USD |
| GLD | UUP | -0.51 | Commodity | Currency | PreciousMetal | USD |
| SLV | UUP | -0.51 | Commodity | Currency | PreciousMetal | USD |
| PPLT | UUP | -0.50 | Commodity | Currency | PreciousMetal | USD |
| TIP | UUP | -0.48 | Bond | Currency | Bond | USD |
| HYG | UUP | -0.46 | Bond | Currency | Bond | USD |
| XLB | UUP | -0.46 | Equity | Currency | Sector | USD |
| IEF | UUP | -0.43 | Bond | Currency | Bond | USD |
| SHY | UUP | -0.41 | Bond | Currency | Bond | USD |
| XLV | UUP | -0.41 | Equity | Currency | Sector | USD |
| USMV | UUP | -0.40 | Equity | Currency | StyleFactor | USD |
| XLRE | UUP | -0.40 | Equity | Currency | Sector | USD |
| VNQ | UUP | -0.38 | Equity | Currency | RealEstate | USD |
| XLP | UUP | -0.38 | Equity | Currency | Sector | USD |
| MTUM | UUP | -0.38 | Equity | Currency | StyleFactor | USD |
| IWD | UUP | -0.38 | Equity | Currency | StyleFactor | USD |
| TLT | UUP | -0.37 | Bond | Currency | Bond | USD |
| QUAL | UUP | -0.37 | Equity | Currency | StyleFactor | USD |

## 5. Average Correlation by Asset Class Pair

| Class Pair | Average Correlation | Pair Count |
| --- | --- | --- |
| Equity - Equity | 0.72 | 276 |
| Equity - Commodity | 0.23 | 336 |
| Equity - Bond | 0.35 | 144 |
| Equity - Currency | -0.36 | 24 |
| Commodity - Commodity | 0.27 | 91 |
| Commodity - Bond | 0.03 | 84 |
| Commodity - Currency | -0.20 | 14 |
| Bond - Bond | 0.66 | 15 |
| Bond - Currency | -0.45 | 6 |
| Currency - Currency | NA | 0 |

## 6. Threshold Diagnostics

| Distance Threshold | Number of Clusters | Largest Cluster Size | Median Cluster Size | Singleton Count |
| --- | --- | --- | --- | --- |
| 0.30 | 24.00 | 8.00 | 1.00 | 17.00 |
| 0.40 | 16.00 | 21.00 | 1.00 | 11.00 |
| 0.50 | 9.00 | 23.00 | 3.00 | 4.00 |
| 0.60 | 6.00 | 30.00 | 4.00 | 2.00 |
| 0.70 | 2.00 | 44.00 | 22.50 | 1.00 |

Selected threshold: **0.50**. It produces 9 clusters, largest size 23, median size 3.0, and 4 singletons. The threshold is selected for interpretable cluster balance only, not strategy performance.

## 7. Selected Cluster Output

| Cluster ID | Cluster Size | Symbols | Cluster Label | Dominant Asset Class | Dominant Category | Intra-Cluster Average Correlation | Average Annualized Volatility |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4 | CORN,DBA,SOYB,WEAT | Agriculture / Broad Commodity | Commodity | Agriculture | 0.53 | 16.18% |
| 2 | 6 | DBC,DBO,GSG,USO,XLE,XOP | Energy / Broad Commodity | Commodity | Energy | 0.75 | 29.03% |
| 3 | 23 | DIA,EEM,EFA,HYG,IWD,IWF,IWM,MTUM,QQQ,QUAL,SPY,USMV,VLUE,VNQ,VTI,XLB,XLF,XLI,XLK,XLP,XLRE,XLV,XLY | Broad Equity Beta | Equity | Sector | 0.76 | 16.27% |
| 4 | 3 | GLD,PPLT,SLV | Precious Metals | Commodity | PreciousMetal | 0.63 | 22.39% |
| 5 | 5 | IEF,LQD,SHY,TIP,TLT | Treasury / Investment Grade Bonds | Bond | Bond | 0.76 | 7.01% |
| 6 | 1 | PALL | Palladium | Commodity | PreciousMetal | NA | 31.36% |
| 7 | 1 | UNG | Natural Gas | Commodity | Energy | NA | 53.06% |
| 8 | 1 | UUP | US Dollar | Currency | USD | NA | 6.66% |
| 9 | 1 | XLU | Utilities Equity | Equity | Sector | NA | 15.13% |

## 8. Representative ETFs

Representatives prioritize local history length, common-sample dollar-volume liquidity, and broad/clean exposure preference. Expense ratios are not present in the local dataset and are therefore not asserted. Historical returns are not used.

| Cluster ID | Cluster Label | Representative ETF | Reason |
| --- | --- | --- | --- |
| 1 | Agriculture / Broad Commodity | DBA | History from 2007-01-05; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |
| 2 | Energy / Broad Commodity | DBC | History from 2006-02-06; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |
| 3 | Broad Equity Beta | SPY | History from 2000-01-03; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |
| 4 | Precious Metals | GLD | History from 2004-11-18; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |
| 5 | Treasury / Investment Grade Bonds | IEF | History from 2002-07-30; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |
| 6 | Palladium | PALL | History from 2010-01-08; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |
| 7 | Natural Gas | UNG | History from 2007-04-18; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |
| 8 | US Dollar | UUP | History from 2007-03-01; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |
| 9 | Utilities Equity | XLU | History from 2000-01-03; selected from the earliest-history cohort using liquidity and broad/clean exposure preference, not return performance. |

## 9. Diagnostics

1. **Does the Universe contain highly correlated duplicates?** Yes. The largest and highest-correlation clusters show substantial overlap, especially within equity styles/sectors and related commodity exposures.
2. **How many effective risk clusters?** At the selected threshold, approximately **9** clusters versus 45 tickers.
3. **Most redundant groups?** Broad Equity Beta (DIA,EEM,EFA,HYG,IWD,IWF,IWM,MTUM,QQQ,QUAL,SPY,USMV,VLUE,VNQ,VTI,XLB,XLF,XLI,XLK,XLP,XLRE,XLV,XLY); Energy / Broad Commodity (DBC,DBO,GSG,USO,XLE,XOP); Treasury / Investment Grade Bonds (IEF,LQD,SHY,TIP,TLT).
4. **Genuinely diversifying exposures?** Palladium, Natural Gas, US Dollar, Utilities Equity; the lowest-correlation table also identifies the strongest cross-cluster diversifiers.
5. **True or nominal breadth?** Expansion added both real exposures and many correlated variants. Because the effective cluster count is materially below 45 and the largest clusters contain repeated exposures, much of the added breadth is nominal.
6. **Is Original 12 close to a representative-cluster universe?** The Original 12 covers 5/9 selected clusters. It captures the main broad Equity, Energy/Commodity, Precious Metal, Agriculture, and Bond clusters, but misses several standalone diversifiers; it is a compact core rather than a complete representative-cluster universe.

## 10. Final Conclusion

The correlation structure supports **redundant ETFs and unequal cluster representation** as important causes of Expanded Global Top5 deterioration. A global rank gives large clusters more opportunities to occupy limited Top5 slots, while volatile specialized clusters can generate more extreme ranks and smaller Bond/defensive clusters can be crowded out. This is a structural diagnosis rather than a causal backtest, and it does not show a general failure of momentum; it shows that nominal ticker breadth is not equivalent to balanced independent-risk breadth.

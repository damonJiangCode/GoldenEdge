# GoldenEdge — Systematic Trading Research

An independent quantitative research workspace (Nov 2025 – present) covering two lines of work:

1. **[Framework001](alpha/report/framework001.md): cross-asset ETF momentum.** A long-only, monthly-rebalanced portfolio across equities, commodities and bonds, built through ~30 controlled studies and then validated out of sample.
2. **[XAUUSD systematic strategies](xau/README.md).** Intraday breakout, mean-reversion and trend-pullback engines, plus a shared-account portfolio engine, developed under a strict anti-overfitting protocol.

The emphasis throughout is **research discipline over headline returns**. Each change is a single controlled experiment, parameters must sit on stable plateaus, out-of-sample years are frozen in code, and negative results are kept and documented.

> All performance figures below are **backtests** (plus a short live-data out-of-sample window). Nothing here is a live track record or investment advice.

---

## Framework001: Cross-Asset Momentum

**Rule:** at each month-end, rank 12 ETFs by 126-trading-day return, hold the top 5, and size them by inverse 126-day volatility. Long only, no leverage, 5 bps cost on turnover.

| Universe | |
|---|---|
| Equity | SPY, QQQ, IWM, EFA |
| Commodity | GLD, SLV, USO, DBA |
| Bond | TLT, IEF, SHY, LQD |

### Results (backtest, 2008-02 → 2025-12)

| Strategy | CAGR | Sharpe | Max DD |
|---|---:|---:|---:|
| **Framework001 (Top5, inverse-vol)** | **10.3%** | **0.97** | **-17.2%** |
| Top5, equal weight | ~10.3% | 0.81 | -29.1% |
| Top3, inverse-vol | 10.0% | 0.70 | -30.2% |
| Top7, inverse-vol | 6.7% | 0.87 | -15.2% |

**2026 out-of-sample** (new data only, 2026-01-02 → 2026-06-23): +9.3% return, Sharpe 1.11, max DD -8.7%.

### Validation

| Test | Outcome |
|---|---|
| [Sub-period walk-forward](alpha/validation/framework_001/walk_forward_001_cross_asset_momentum_v1.md) (4 segments, frozen params) | Positive CAGR and Sharpe in every segment; worst segment Sharpe 0.79 |
| [Regime analysis](alpha/validation/framework_001/regime_001_cross_asset_momentum_v1.md) | Strongest in trending risk-on regimes; drawdown controlled in equity bear regimes |
| [Monthly block bootstrap](alpha/validation/framework_001/bootstrap_001_cross_asset_momentum_v1.md) | P(CAGR > 0) = 100%; P(MaxDD worse than -30%) ≈ 2.3% |
| [Monte Carlo path simulation](alpha/validation/framework_001/monte_carlo_001_cross_asset_momentum_v1.md) | Most paths profitable; no evidence of path fragility |
| [2026 live-data OOS](alpha/validation/framework_001/oos_001_framework_001_2026.md) | Behaviour consistent with the backtest |
| Parameter robustness | Momentum lookbacks from 105 to 252 days and vol windows from 21 to 252 days both sit on flat plateaus, with no isolated peak |

### Key findings

- **Inverse-vol sizing was the main improvement.** It lifted Sharpe from 0.81 to 0.97 and cut max drawdown from -29% to -17% at roughly the same CAGR. Rank weighting, inverse variance and correlation-adjusted variants were all tested and did no better.
- **More breadth made things worse.** Expanding to 45 ETFs dropped Sharpe from 0.89 to 0.46. Correlation clustering showed that 23 of the equity ETFs collapsed into a single risk cluster, so the added breadth was nominal. A robust universe needs both de-duplication and balance across asset classes.
- **Rejected ideas stay documented.** An MA200 trend filter worked only as a crisis overlay and added nothing on top of inverse-vol sizing. Loser-side continuation was not robust, absolute momentum and a momentum ensemble did not beat the baseline, and an ML trade filter showed no predictive power (AUC ≈ 0.49).
- **Attribution.** Equity is the return engine, commodities add return, and bonds are the main diversifier. Every one of the 12 ETFs contributed positively.

The full research log is in [alpha/journey.md](alpha/journey.md), and each study has its own `summary.md` under [alpha/research/](alpha/research/).

---

## XAUUSD Strategy Research

Engines for XAUUSD (H4 volatility breakout, M15 mean reversion, H1 trend pullback) plus a regime baseline that runs several strategies inside one shared account, with margin accounting, position caps and per-strategy P&L attribution.

What this part demonstrates:

- **Frozen out-of-sample data.** The VB V2 engine refuses to load data from 2024 onward; all design work uses 2015–2023 only ([research policy](xau/vb/v2/RESEARCH_POLICY.md)).
- **Self-audit of overfitting.** An earlier parameter-island winner was reclassified as in-sample and re-selected under a search / selection / confirmation split ([assessment](xau/tp/v1/optimization/OVERFITTING_ASSESSMENT.md)).
- **Correctness fixes.** H1 indicator timing aligned to the actual decision bar, stop ATR taken from the signal bar rather than the entry bar, gap-through stops filled at the open, risk-based position sizing with broker lot-step and margin checks ([V2 assessment](xau/vb/v2/research/ASSESSMENT.md)).
- **Cost stress.** Results are reported under base, stress and severe execution-cost scenarios. They hold under base costs, weaken materially under severe costs, and that is stated plainly ([summary](xau/reports/regime_baseline_robust/summary.md)).
- **Data pipeline.** An MT5 M1 ingester resamples bars to higher timeframes, with unit tests ([ingest](xau/marketdata/ingest/README.md)).

---

## Repository Layout

```text
alpha/                 Cross-asset ETF research
  shared/              Data download (yfinance), loaders, universes, backtest utilities
  research/            One folder per study: scripts/, summary.md, metrics/, outputs/
  framework/           Frozen framework specification
  validation/          Walk-forward, regime, bootstrap, Monte Carlo, OOS
  report/              Consolidated Framework001 report
xau/                   XAUUSD engines, optimization, reports, MT5 data ingest
eur/                   Earlier EURUSD M15 backtests
mt5/                   MetaTrader 5 live/demo execution scripts (Windows)
ai/                    Early ML trade-filter experiment
```

## Reproducing

```bash
python -m venv .venv && source .venv/bin/activate
pip install pandas numpy yfinance matplotlib scipy
python alpha/shared/data/download_data.py
python alpha/validation/framework_001/scripts/run_walk_forward_001.py
python alpha/validation/framework_001/scripts/run_oos_001.py
```

MT5 scripts need Windows and the `MetaTrader5` package. Credentials are read from environment variables (`MT5_ACCOUNT`, `MT5_PASSWORD`, `MT5_SERVER`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) and are never committed.

## Known Limitations

- Results are backtests on daily or intraday OHLC data. Intrabar SL/TP ordering cannot be fully reproduced from OHLC bars.
- Framework001 assumes rebalancing at the month-end close on which the signal is computed (market-on-close). A one-day execution-lag sensitivity test is pending.
- The 2026 OOS window is partial-year and should not be over-interpreted.
- The XAU history has been reused across many experiments. Only the frozen V2 OOS years are clean holdouts.

# Copilot Instructions — GoldenEdge

Keep these instructions short and actionable for AI coding agents working in this repository.

Goal
- Help an AI quickly become productive: run, test, and change trading strategies under `2025/` and `2026/`.

Project structure & big picture
- Strategies are organized by year/month under `2025/` and `2026/` (e.g. `2026/jan/strategies/T02_V1.py`).
- Each strategy is a self-contained Python script that:
  - fetches market data via `MetaTrader5` (`mt5.copy_rates_*`) in `get_data()`
  - computes indicators with `talib` (RSI, ADX, ATR, BBANDS)
  - decides signals in `check_trend_signal()` / `check_range_signal()`
  - places orders in `place_order()` and manages positions with `close_all_positions()`
  - runs continuously via `main()` -> `run()` loop with `RUNTIME_SECONDS` throttle

Key files / locations
- Example strategy to inspect: `2026/jan/strategies/T02_V1.py` (main loop, logging, Telegram alerts).
- Utility directory: `utlib/` contains helper notes and `requirements.txt` (check for environment hints).
- Logs are written to a `logs/` folder created relative to the script (`LOG_DIR = "../logs"`).
- Records and summaries live in `records/` (CSV files like `month_sum.csv`).

Runtime & dependencies
- Requires `MetaTrader5` Python package and `TA-Lib` bindings; these are imported directly in scripts.
- Scripts assume access to a running MetaTrader 5 terminal (see `METADATA['path']` in strategies).
- Running locally: execute the strategy script with Python (example):

  python 2026/jan/strategies/T02_V1.py

- See `utlib/requirements.txt` for package versions; validate `MetaTrader5` and `talib` availability.

Patterns & conventions
- Single-file strategy: prefer small, focused scripts where indicators, signal logic, and order code co-exist.
- Logging: use `LOG_DIR` + `log_message()` for persistent logs; also send critical messages via Telegram using `send_telegram_message()`.
- Sensitive values (account, password, bot token) are currently embedded in `METADATA` / `TELEGRAM` dicts — treat these as secrets when editing.
- Position checks: use `has_positions()` to determine current position state; many flows expect `None`, `"long"`, `"short"`, or `"error"`.
- Trading safety: before placing an order, scripts close opposite-direction positions and re-check state.

Common modification tasks (examples)
- Add new indicator: update `get_data()` to compute the new column, then use it in `check_trend_signal()`.
- Implement range logic: `check_range_signal()` is a stub in many strategies — implement consistent return values (`'long'|'short'|None`).
- Adjust order sizing / SL/TP: change `PARAMETERS` keys like `LOT`, `SL_MULTIPLIER`, `TP_MULTIPLIER`.

Testing & debugging tips
- To debug without MT5, mock `mt5` calls or wrap `get_data()` to load sample CSVs.
- Use short `RUNTIME_SECONDS` to iterate faster during development.
- Review `LOG_FILE` (value taken from `METADATA['log_file']`) in the strategy's `../logs` directory.

Integration points
- MetaTrader 5: all trading actions use `mt5.*` calls; ensure terminal path and account credentials match the environment.
- Telegram: `send_telegram_message()` posts to the configured bot; useful for CI/alerting when running headless.
- External files: `records/` CSVs are used for aggregated stats; editing them should preserve CSV schema.

What NOT to change without asking
- Hardcoded credentials in `METADATA` / `TELEGRAM` — rotate/separate them into environment variables first.
- The sign conventions returned by `has_positions()` and `check_*_signal()` (must be `None`, `'long'`, or `'short'`).

If you modify files
- Keep changes minimal and localized; follow the repository pattern of per-strategy single-file scripts.
- When adding new dependencies, update `utlib/requirements.txt` and mention install steps in a short PR description.

Questions for the maintainer
- Preferred secure secrets storage (env vars, `.env`, or separate config file)?
- Any tests or sample market data used for offline validation?

End of instructions.

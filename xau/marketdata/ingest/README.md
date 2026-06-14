# MT5 M1 Ingest

`mt5_m1_ingest.py` downloads M1 bars from MT5, then builds higher timeframes
locally so every backtest timeframe comes from the same source data.

The default range is **2026-01-01 00:00 UTC through 2026-06-01 00:00 UTC
(exclusive)**, which covers January through May 2026.

## Download M1 And Build Higher Timeframes

Run this on Windows with MetaTrader 5 installed and connected:

```powershell
python xau/marketdata/ingest/mt5_m1_ingest.py run
```

The default outputs are:

```text
xau/marketdata/M1/M1_2026.csv
xau/marketdata/M15/M15_2026.csv
xau/marketdata/M30/M30_2026.csv
xau/marketdata/H1/H1_2026.csv
xau/marketdata/H4/H4_2026.csv
```

The files are named by year even when the requested range is only part of that
year. Use `--merge-existing` when extending an existing annual M1 file.

Credentials should be passed with environment variables rather than committed:

```powershell
$env:MT5_LOGIN="60089394"
$env:MT5_PASSWORD="Jwz990118."
$env:MT5_SERVER="TradeMaxGlobal-Demo"
$env:MT5_TERMINAL_PATH="C:\Program Files\MetaTrader 5_1\terminal64.exe"
python xau/marketdata/ingest/mt5_m1_ingest.py run
```

If the currently open MT5 terminal is already logged in, credentials and
`MT5_TERMINAL_PATH` are usually unnecessary.

## Build Timeframes From An Existing M1 File

This works without MT5 and can run on macOS/Linux:

```bash
.venv/bin/python xau/marketdata/ingest/mt5_m1_ingest.py resample \
  --start 2026-01-01 --end 2026-06-01
```

To build only selected timeframes:

```bash
.venv/bin/python xau/marketdata/ingest/mt5_m1_ingest.py resample \
  --start 2026-01-01 --end 2026-06-01 --targets M15 H1 H4
```

Aggregation uses the first open, maximum high, minimum low, last close, summed
tick volume, and rounded mean spread. Timestamps are UTC and bars are aligned to
UTC timeframe boundaries.

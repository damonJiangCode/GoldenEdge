import MetaTrader5 as mt5  
import pandas as pd  
from datetime import datetime
from pathlib import Path
import pytz  

# data from
DATA_FROM_YEAR = 2025
DATA_FROM_MONTH = 1
DATA_FROM_DAY = 1

# data to
DATA_TO_YEAR = 2025
DATA_TO_MONTH = 12
DATA_TO_DAY = 31

# output file
OUTPUT_NAME = "M15_2025.csv"
BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / ".." / "data" / "historical" / "eur"
OUTPUT_FILE = OUTPUT_DIR / OUTPUT_NAME

# CONFIGURATION
METADATA = {
    "account": 10009666460,
    "password": "L!RsP8Uv",
    "server": "MetaQuotes-Demo",
    "path": r"C:\\Program Files\\MetaTrader 5_1\\terminal64.exe",
}


def download_historical_data():
    # 1. Initialize MT5 connection
    if not mt5.initialize(path=METADATA["path"]):
        print(f"MT5 Initialization failed, error code: {mt5.last_error()}")
        return

    # 2. Login to the account
    authorized = mt5.login(
        METADATA["account"], METADATA["password"], METADATA["server"]
    )
    if not authorized:
        print(f"Login failed, error code: {mt5.last_error()}")
        mt5.shutdown()
        return

    print("✅ Connected to MT5 successfully")

    # 3. Define the Timeframe and Range (UTC)
    timezone = pytz.timezone("Etc/UTC")
    utc_from = datetime(DATA_FROM_YEAR, DATA_FROM_MONTH, DATA_FROM_DAY, tzinfo=timezone)
    utc_to = datetime(DATA_TO_YEAR, DATA_TO_MONTH, DATA_TO_DAY, tzinfo=timezone)

    symbol = "EURUSD"
    timeframe = mt5.TIMEFRAME_M15

    # 4. Fetch Rates
    print(f"Downloading M15 data for {symbol} (Full Year {DATA_FROM_YEAR})...")
    if not mt5.symbol_select(symbol, True):
        print(f"❌ Symbol {symbol} not found")
        mt5.shutdown()
        return

    rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)

    if rates is None or len(rates) == 0:
        print(
            f"❌ Failed to fetch data. Check if symbol '{symbol}' is correct in your Market Watch."
        )
        mt5.shutdown()
        return

    # 5. Convert to DataFrame
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # 6. Export to CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print("-" * 40)
    print(f"✅ Data Downloaded Successfully")
    print(f"Filename: {OUTPUT_FILE}")
    print(f"Total Rows: {len(df)}")
    print("Data Sample:")
    print(df.head())
    print("-" * 40)

    # Shutdown connection
    mt5.shutdown()


if __name__ == "__main__":
    download_historical_data()

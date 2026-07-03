from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd

SYMBOL_CANDIDATES = ["Boom 1000 Index", "Boom1000", "Boom 1000 Index.pro"]
TIMEFRAME = mt5.TIMEFRAME_H1   
DAYS_BACK = 60                 
OUTPUT_CSV = "boom1000_1h.csv"


def connect():
    if not mt5.initialize():
        raise RuntimeError(f"initialize() failed, error code = {mt5.last_error()}")

    account_info = mt5.account_info()
    if account_info is None:
        mt5.shutdown()
        raise RuntimeError("No account info. Connection might be broken.")

    print("Connected to account:", account_info.login)


def find_symbol():
    """Auto-detect the correct Boom 1000 symbol name for this broker."""
    symbols = mt5.symbols_get()
    boom_symbols = [s.name for s in symbols if "boom" in s.name.lower() and "1000" in s.name]
    print("Available Boom 1000 symbols:", boom_symbols)

    for candidate in SYMBOL_CANDIDATES:
        if candidate in boom_symbols:
            return candidate

    if boom_symbols:
        print(f"None of the hardcoded candidates matched exactly, using first found: {boom_symbols[0]}")
        return boom_symbols[0]

    raise RuntimeError("No Boom 1000 symbol found on this account. Check symbol list above.")


def fetch_candles(symbol):
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Failed to select {symbol}")

    to_date = datetime.now()
    from_date = to_date - timedelta(days=DAYS_BACK)

    rates = mt5.copy_rates_range(symbol, TIMEFRAME, from_date, to_date)

    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No candle data returned. Error code: {mt5.last_error()}")

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
    return df


def main():
    connect()
    try:
        symbol = find_symbol()
        df = fetch_candles(symbol)
        df.to_csv(OUTPUT_CSV, index=False)
        print(f"Saved {len(df)} 1H candles for {symbol} -> {OUTPUT_CSV}")
        print(df.head())
        print(df.tail())
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
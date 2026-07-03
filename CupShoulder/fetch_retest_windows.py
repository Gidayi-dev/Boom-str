from datetime import timedelta
import MetaTrader5 as mt5
import pandas as pd

SYMBOL = "Boom 1000 Index"  
MINUTES_BEFORE = 30          
MINUTES_AFTER = 60           

INPUT_CSV = "detected_patterns.csv"
OUTPUT_CSV = "retest_windows_m1.csv"


def connect():
    if not mt5.initialize():
        raise RuntimeError(f"initialize() failed, error code = {mt5.last_error()}")
    if mt5.account_info() is None:
        mt5.shutdown()
        raise RuntimeError("No account info. Connection might be broken.")


def main():
    connect()
    try:
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"Failed to select {SYMBOL}")

        patterns = pd.read_csv(INPUT_CSV, parse_dates=['retest_time'])
        all_rows = []

        for idx, row in patterns.iterrows():
            retest_time = row['retest_time']
            if pd.isna(retest_time):
                print(f"Pattern {idx}: no retest_time, skipping")
                continue

            start = retest_time - timedelta(minutes=MINUTES_BEFORE)
            end = retest_time + timedelta(minutes=MINUTES_AFTER)

            rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, start, end)
            if rates is None or len(rates) == 0:
                print(f"Pattern {idx}: no M1 data returned for window {start} -> {end}")
                continue

            wdf = pd.DataFrame(rates)
            wdf['time'] = pd.to_datetime(wdf['time'], unit='s')
            wdf = wdf[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
            wdf['pattern_id'] = idx
            wdf['retest_time'] = retest_time
            all_rows.append(wdf)
            print(f"Pattern {idx}: fetched {len(wdf)} M1 candles around retest {retest_time}")

        if not all_rows:
            raise RuntimeError("No M1 data fetched for any pattern.")

        combined = pd.concat(all_rows, ignore_index=True)
        combined.to_csv(OUTPUT_CSV, index=False)
        print(f"\nSaved {len(combined)} rows -> {OUTPUT_CSV}")

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
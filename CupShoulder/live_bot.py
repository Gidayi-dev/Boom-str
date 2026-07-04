import time
import traceback
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import pandas as pd

import config
from cup_handle import scan_cup_and_handle
from journal import init_journal, log_new_patterns, resolve_pending, summarize
from notify import send_pattern_alert


def connect():
    if not mt5.initialize():
        raise RuntimeError(f"initialize() failed, error code = {mt5.last_error()}")
    if mt5.account_info() is None:
        mt5.shutdown()
        raise RuntimeError("No account info. Connection might be broken.")
    if not mt5.symbol_select(config.SYMBOL, True):
        raise RuntimeError(f"Failed to select symbol {config.SYMBOL}")
    print(f"[{datetime.now()}] Connected. Account: {mt5.account_info().login}")


def fetch_h1_candles():
    to_date = datetime.now()
    from_date = to_date - timedelta(days=config.CANDLE_LOOKBACK_DAYS)
    rates = mt5.copy_rates_range(config.SYMBOL, mt5.TIMEFRAME_H1, from_date, to_date)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No H1 candle data returned. Error: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]


def fetch_m1_candles(start, end):
    rates = mt5.copy_rates_range(config.SYMBOL, mt5.TIMEFRAME_M1, start, end)
    if rates is None or len(rates) == 0:
        return pd.DataFrame(columns=['time', 'open', 'high', 'low', 'close'])
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['time', 'open', 'high', 'low', 'close']]


def run_cycle(journal_df):
    # 1. Detect patterns on latest H1 data
    h1_df = fetch_h1_candles()
    patterns = scan_cup_and_handle(h1_df, **config.PATTERN_PARAMS)
    print(f"[{datetime.now()}] Scanned {len(h1_df)} H1 candles -> {len(patterns)} pattern(s) found in lookback window")

    # 2. Log any newly confirmed patterns
    journal_df, new_ids = log_new_patterns(journal_df, patterns)
    if new_ids:
        print(f"[{datetime.now()}] {len(new_ids)} NEW pattern(s) logged: {new_ids}")

    # 3. Notify for anything logged but not yet notified
    unnotified = journal_df[(journal_df['notified'] == False) | (journal_df['notified'].isna())]
    for idx, row in unnotified.iterrows():
        send_pattern_alert(row)
        journal_df.at[idx, 'notified'] = True

    # 4. Resolve outcomes for pending patterns using fresh M1 data
    pending = journal_df[journal_df['status'] == 'PENDING']
    if not pending.empty:
        earliest_retest = pending['retest_time'].min()
        m1_df = fetch_m1_candles(earliest_retest - timedelta(minutes=2), datetime.now())
        if not m1_df.empty:
            journal_df = resolve_pending(journal_df, m1_df)

    # 5. Save + report
    journal_df.to_csv(config.JOURNAL_CSV, index=False)
    summarize(journal_df)

    return journal_df


def main():
    connect()
    journal_df = init_journal(config.JOURNAL_CSV)

    try:
        while True:
            try:
                journal_df = run_cycle(journal_df)
            except Exception as e:
                print(f"[{datetime.now()}] ERROR during cycle (bot keeps running): {e}")
                traceback.print_exc()

            print(f"[{datetime.now()}] Sleeping {config.POLL_INTERVAL_SECONDS}s...\n")
            time.sleep(config.POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nStopping bot (Ctrl+C received)...")
    finally:
        mt5.shutdown()
        print("MT5 connection closed. Journal saved at", config.JOURNAL_CSV)


if __name__ == "__main__":
    main()
import MetaTrader5 as mt5
from journal import init_journal
import pandas as pd
from notify import send_pattern_alert

if not mt5.initialize():
    print("MT5 initialize failed:", mt5.last_error())
    quit()

fake_row = pd.Series({
    'retest_time': '2026-07-05 00:40:00',
    'breakout_price': 15000.0,
    'cup_depth_pct': 1.5,
    'handle_depth_pct': 0.7,
})
send_pattern_alert(fake_row)

mt5.shutdown()
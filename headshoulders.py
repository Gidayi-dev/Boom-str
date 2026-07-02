from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd

# 1. INITIALIZE FIRST
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

# 2. Check connection
account_info = mt5.account_info()
if account_info is None:
    print("No account info. Connection might be broken.")
    quit()
else:
    print("Connected to account:", account_info.login)

# 3. Find the correct symbol name (Deriv uses names like "Boom1000" not "Boom 1000 Index")
symbols = mt5.symbols_get()
boom_symbols = [s.name for s in symbols if "boom" in s.name.lower()]
print("Available Boom symbols:", boom_symbols)

# Pick the correct one (replace with what you see)
symbol_name = "Boom 1000 Index"  # or "Boom 1000 Index.pro", etc.

# Enable it
if not mt5.symbol_select(symbol_name, True):
    print(f"Failed to select {symbol_name}")
    mt5.shutdown()
    quit()

# 4. Date range (try a shorter period first – Boom indices may not have 30 days of ticks)
to_date = datetime.now()
from_date = to_date - timedelta(days=1)   # try 1 day first

# 5. Fetch ticks
ticks = mt5.copy_ticks_range(symbol_name, from_date, to_date, mt5.COPY_TICKS_ALL)

if ticks is not None and len(ticks) > 0:
    df = pd.DataFrame(ticks)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"✅ Loaded {len(df)} ticks from {from_date.date()} to {to_date.date()}")
    print(df.head())
else:
    print(f"❌ No ticks for {symbol_name} in that range.")
    print(f"Error code: {mt5.last_error()}")

mt5.shutdown()
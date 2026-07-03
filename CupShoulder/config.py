SYMBOL = "Boom 1000 Index"     
TIMEFRAME_LABEL = "1H"           

POLL_INTERVAL_SECONDS = 300     
CANDLE_LOOKBACK_DAYS = 15        

ENABLE_TELEGRAM = True
ENABLE_DESKTOP_POPUP = True
TELEGRAM_BOT_TOKEN = "8823385345:AAHPbTQ0qWdT7RWsEDQbodpWf77Z1dn8egw"          
TELEGRAM_CHAT_ID = "8289775882"            

PATTERN_PARAMS = dict(
    min_cup_bars=15,
    max_cup_bars=150,
    rim_tolerance=0.02,
    min_cup_depth=0.015,
    max_cup_depth=0.15,
    min_handle_bars=8,
    max_handle_bars=40,
    max_handle_depth_ratio=0.5,
    breakout_lookahead=40,
    retest_tolerance=0.01,
    retest_lookahead=20,
)

OUTCOME_HORIZONS_MIN = [5, 10, 15, 30]
WIN_THRESHOLD_PCT = 0.05
LOSS_THRESHOLD_PCT = -0.05

JOURNAL_CSV = "journal.csv"
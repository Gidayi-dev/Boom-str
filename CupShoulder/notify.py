import requests
import os
import time
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ENABLE_TELEGRAM,
    ENABLE_DESKTOP_POPUP, ENABLE_MT5_ALERT,
)

try:
    from plyer import notification as _plyer_notification
    _HAS_TOAST = True
except Exception:
    _HAS_TOAST = False


def send_telegram(message):
    if not ENABLE_TELEGRAM:
        return
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[notify] Telegram not configured (missing token/chat_id) -- skipping")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        if resp.status_code != 200:
            print(f"[notify] Telegram send failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[notify] Telegram error: {e}")


def send_desktop_popup(title, message):
    if not ENABLE_DESKTOP_POPUP:
        return
    if not _HAS_TOAST:
        print("[notify] plyer not installed -- run: pip install plyer")
        return
    try:
        _plyer_notification.notify(title=title, message=message, timeout=15)
    except Exception as e:
        print(f"[notify] Desktop popup error: {e}")


def send_mt5_alert(message):
    """
    Writes a signal file into MT5's Common\\Files folder. A companion MQL5
    script (BoomBotWatcher.mq5) polls this file and fires MT5's native
    Alert() + sound the moment it sees a new message -- this is the only
    way to trigger a REAL in-terminal MT5 alert from Python, since the
    Python API itself has no access to MQL5's Alert() function.
    """
    if not ENABLE_MT5_ALERT:
        return
    try:
        import MetaTrader5 as mt5
        info = mt5.terminal_info()
        if info is None:
            print("[notify] MT5 not connected -- can't write signal file")
            return
        common_files_dir = os.path.join(info.commondata_path, "Files")
        os.makedirs(common_files_dir, exist_ok=True)
        file_path = os.path.join(common_files_dir, "boombot_signal.txt")

        # unique id (timestamp) + message, so the watcher can detect "new" vs "already seen"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"{time.time()}|{message}")

    except Exception as e:
        print(f"[notify] MT5 signal write failed: {e}")


def send_pattern_alert(pattern_row):
    title = "Cup & Handle Signal - Boom 1000"
    message = (
        f"Retest confirmed at {pattern_row['retest_time']}\n"
        f"Rim/breakout level ~{pattern_row.get('breakout_price', 'n/a')}\n"
        f"Cup depth: {pattern_row['cup_depth_pct']}% | Handle depth: {pattern_row['handle_depth_pct']}%\n"
        f"This is ONE signal -- confirm with your other strategies before entering."
    )
    print(f"\n=== ALERT ===\n{message}\n=============\n")
    send_telegram(f"{title}\n\n{message}")
    send_desktop_popup(title, message)
    send_mt5_alert(f"{title} | Retest {pattern_row['retest_time']} | Level ~{pattern_row.get('breakout_price', 'n/a')}")
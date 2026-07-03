import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ENABLE_TELEGRAM, ENABLE_DESKTOP_POPUP

try:
    from win10toast import ToastNotifier
    _toaster = ToastNotifier()
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
        print("[notify] win10toast not installed -- run: pip install win10toast")
        return
    try:
        _toaster.show_toast(title, message, duration=15, threaded=True)
    except Exception as e:
        print(f"[notify] Desktop popup error: {e}")


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
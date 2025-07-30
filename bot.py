import os
import time
import threading
import logging
import requests
from telegram import Bot
from flask import Flask

# ------------- CONFIG -------------
TOKEN     = os.environ["TELEGRAM_TOKEN"]
GROUP_ID  = int(os.environ["GROUP_ID"])
INTERVAL  = 3600                   # seconds between pushes
# ----------------------------------

logging.basicConfig(level=logging.INFO)
bot = Bot(TOKEN)
app = Flask(__name__)

def btc_dominance() -> float:
    """Fetch BTC dominance from CoinGecko with retries."""
    url = "https://api.coingecko.com/api/v3/global"
    for attempt in range(1, 4):
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            payload = r.json()
            return payload["data"]["market_cap_percentage"]["btc"]
        except Exception as e:
            logging.warning("CoinGecko fetch failed (%s) – retry %s/3", e, attempt)
            time.sleep(2 * attempt)
    raise RuntimeError("CoinGecko unavailable after retries")

def send_message():
    """Send current BTC dominance to Telegram."""
    dom = btc_dominance()
    text = f"₿ BTC Dominance: {dom:.2f}%"
    bot.send_message(chat_id=GROUP_ID, text=text)
    logging.info("Sent: %s", text)

def scheduler():
    """Run forever, posting every INTERVAL seconds."""
    while True:
        try:
            send_message()
        except Exception as e:
            logging.exception("Scheduler error: %s", e)
        time.sleep(INTERVAL)

# Start background thread
threading.Thread(target=scheduler, daemon=True).start()

# Flask keep-alive route (Render free tier)
@app.route("/")
def keepalive():
    return "OK", 200

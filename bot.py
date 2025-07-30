import os
import time
import logging
import threading
import requests
from telegram import Bot
from flask import Flask

# ---------- config ----------
TOKEN        = os.environ["TELEGRAM_TOKEN"]
GROUP_ID     = int(os.environ["GROUP_ID"])
THREAD_ID    = int(os.environ.get("THREAD_ID", 0))
INTERVAL_S   = 3600         # 1 hour
# ----------------------------

bot     = Bot(TOKEN)
app     = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def fetch_btc_dominance() -> float:
    url = "https://api.coingecko.com/api/v3/global"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()["data"]["market_cap_percentage"]["btc"]

def send_dominance():
    dom = fetch_btc_dominance()
    text = f"₿ BTC Dominance: {dom:.2f}%"
    bot.send_message(
        chat_id=GROUP_ID,
        message_thread_id=THREAD_ID or None,
        text=text
    )
    logging.info("Sent: %s", text)

def scheduler():
    while True:
        try:
            send_dominance()
        except Exception as e:
            logging.exception("Send failed: %s", e)
        time.sleep(INTERVAL_S)

# Start scheduler in background thread
threading.Thread(target=scheduler, daemon=True).start()

# ---------- Flask keep-alive ----------
@app.route("/")
def home():
    return "OK", 200

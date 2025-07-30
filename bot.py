import os
import time
import threading
import logging
import requests
from flask import Flask
from telegram.ext import ApplicationBuilder   # <-- async helper

# ------------- config -------------
TOKEN     = os.environ["TELEGRAM_TOKEN"]
GROUP_ID  = int(os.environ["GROUP_ID"])
INTERVAL  = 3600
# ----------------------------------

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Build the async application once and extract its sync bot wrapper
bot = ApplicationBuilder().token(TOKEN).build().bot

def btc_dominance() -> float:
    url = "https://api.coingecko.com/api/v3/global"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    payload = r.json()
    if "data" not in payload or "market_cap_percentage" not in payload["data"]:
        raise RuntimeError("Unexpected CoinGecko response: " + str(payload))
    return payload["data"]["market_cap_percentage"]["btc"]

def send_message(retry=3, delay=5):
    for _ in range(retry):
        try:
            dom = btc_dominance()
            text = f"₿ BTC Dominance: {dom:.2f}%"
            bot.send_message(chat_id=GROUP_ID, text=text)
            logging.info("Sent: %s", text)
            return
        except Exception as e:
            logging.exception("Failed to send, retrying… %s", e)
            time.sleep(delay)

def scheduler():
    while True:
        try:
            send_message()
        except Exception as e:
            logging.exception(e)
        time.sleep(INTERVAL)

threading.Thread(target=scheduler, daemon=True).start()

@app.route("/")
def keepalive():
    return "OK", 200

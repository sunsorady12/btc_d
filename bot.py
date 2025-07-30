import os, time, threading, logging, requests
from telegram.ext import ExtBot
from flask import Flask

TOKEN    = os.environ["TELEGRAM_TOKEN"]
GROUP_ID = int(os.environ["GROUP_ID"])
INTERVAL = 3600

logging.basicConfig(level=logging.INFO)
bot = ExtBot(token=TOKEN)
app = Flask(__name__)

def btc_dominance():
    data = requests.get("https://api.coingecko.com/api/v3/global", timeout=15).json()
    return data["data"]["market_cap_percentage"]["btc"]

def send_message():
    dom = btc_dominance()
    text = f"₿ BTC Dominance: {dom:.2f}%"
    bot.send_message(chat_id=GROUP_ID, text=text)
    logging.info("Sent: %s", text)

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

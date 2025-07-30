import time
import threading
import logging
import requests
import asyncio
from telegram import Bot, error
from telegram.helpers import escape_markdown
from flask import Flask

# Environment variables validation
TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
if not TOKEN or not GROUP_ID:
    logging.error("Missing required environment variables")
    exit(1)
try:
    GROUP_ID = int(GROUP_ID)
except ValueError:
    logging.error("Invalid GROUP_ID format")
    exit(1)

INTERVAL = 3600  # 1 hour

# Initialize components
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
bot = Bot(TOKEN)
app = Flask(__name__)

def btc_dominance():
    """Fetch BTC dominance with error handling"""
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/global",
            timeout=15,
            headers={'User-Agent': 'BTC-Dominance-Tracker/1.0'}
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["market_cap_percentage"]["btc"]
    except (requests.RequestException, KeyError, ValueError) as e:
        logging.error(f"API Error: {str(e)}")
        raise

async def send_message():
    """Send message with proper async handling"""
    try:
        dom = btc_dominance()
        text = f"₿ BTC Dominance: {escape_markdown(str(dom), 2)}%"
        await bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode="MarkdownV2"
        )
        logging.info("Message sent: %s", text)
    except error.RetryAfter as e:
        logging.warning("Rate limited. Retrying in %s seconds", e.retry_after)
        await asyncio.sleep(e.retry_after)
        await send_message()  # Retry
    except Exception as e:
        logging.exception("Failed to send message")

def scheduler_loop():
    """Async event loop for scheduler"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            loop.run_until_complete(send_message())
        except Exception as e:
            logging.error("Scheduler error: %s", str(e))
        time.sleep(INTERVAL)

# Start scheduler thread
thread = threading.Thread(target=scheduler_loop, daemon=True)
thread.start()

@app.route("/")
def keepalive():
    return "OK", 200

@app.route("/trigger", methods=["POST"])
def manual_trigger():
    """Endpoint for manual trigger"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(send_message())
        return "Message sent", 200
    except Exception as e:
        logging.exception("Manual trigger failed")
        return "Error", 500
    finally:
        loop.close()

# Run Flask app if executed directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

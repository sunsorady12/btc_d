import os
import time
import threading
import logging
import requests
import asyncio
import random
from telegram import Bot, error
from telegram.helpers import escape_markdown
from flask import Flask

# Environment variables validation
TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
THREAD_ID = os.getenv("THREAD_ID")

if not TOKEN or not GROUP_ID:
    logging.error("Missing required environment variables")
    exit(1)
try:
    GROUP_ID = int(GROUP_ID)
    if THREAD_ID:
        THREAD_ID = int(THREAD_ID)
except ValueError:
    logging.error("Invalid GROUP_ID or THREAD_ID format")
    exit(1)

INTERVAL = 3600  # 1 hour

# Initialize components
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
bot = Bot(TOKEN)
app = Flask(__name__)

# Add a requests session with retry logic
session = requests.Session()
retry_strategy = requests.adapters.Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

def btc_dominance():
    """Fetch BTC dominance with enhanced error handling"""
    try:
        response = session.get(
            "https://api.coingecko.com/api/v3/global",
            timeout=15,
            headers={
                'User-Agent': 'BTC-Dominance-Tracker/1.0',
                'Accept': 'application/json'
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]["market_cap_percentage"]["btc"]
    except (requests.RequestException, KeyError, ValueError) as e:
        logging.error(f"API Error: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise

async def send_message():
    """Send message with proper async handling and thread support"""
    try:
        dom = btc_dominance()
        text = f"₿ BTC Dominance: {dom:.2f}%"  # Removed Markdown for simplicity
        
        # Prepare message parameters
        message_params = {
            "chat_id": GROUP_ID,
            "text": text
        }
        
        # Add thread ID if provided
        if THREAD_ID:
            message_params["message_thread_id"] = THREAD_ID
        
        await bot.send_message(**message_params)
        logging.info("Message sent to %s (thread: %s): %s", 
                     GROUP_ID, THREAD_ID or "main", text)
    
    except error.RetryAfter as e:
        wait_time = e.retry_after + random.uniform(1, 3)
        logging.warning("Rate limited. Retrying in %.1f seconds", wait_time)
        await asyncio.sleep(wait_time)
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
            # Add cooldown on critical errors
            time.sleep(60)
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

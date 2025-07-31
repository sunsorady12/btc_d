import os
import time
import threading
import logging
import requests
import asyncio
from telegram import Bot, error
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
BTC_ALERT_THRESHOLD = 55.0  # Alert when BTC dominance < 55%

# Initialize components
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
bot = Bot(TOKEN)
app = Flask(__name__)

def fetch_market_data():
    """Fetch market data with error handling"""
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/global",
            timeout=15,
            headers={'User-Agent': 'Crypto-Market-Tracker/1.0'}
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]
    except (requests.RequestException, KeyError, ValueError) as e:
        logging.error(f"API Error: {str(e)}")
        raise

def calculate_metrics(data):
    """Calculate market metrics from API data"""
    try:
        # BTC and ETH Dominance
        btc_dom = data["market_cap_percentage"]["btc"]
        eth_dom = data["market_cap_percentage"]["eth"]
        
        # Alt Season Index calculation (percentage of market cap excluding BTC & ETH)
        total_mcap = data["total_market_cap"]["usd"]
        btc_mcap = total_mcap * btc_dom / 100
        eth_mcap = total_mcap * eth_dom / 100
        altcoin_mcap = total_mcap - btc_mcap - eth_mcap
        alt_season_index = (altcoin_mcap / total_mcap) * 100
        
        # Format values
        total_mcap_formatted = total_mcap / 1e12  # Convert to trillions
        market_change = data.get("market_cap_change_percentage_24h_usd", 0)
        
        return {
            "btc_dom": btc_dom,
            "alt_season_index": alt_season_index,
            "total_mcap": total_mcap_formatted,
            "market_change": market_change
        }
    except KeyError as e:
        logging.error(f"Data missing in API response: {str(e)}")
        raise

async def send_message():
    """Send message with proper async handling"""
    try:
        # Fetch and process data
        raw_data = fetch_market_data()
        metrics = calculate_metrics(raw_data)
        
        # Create message
        alert_flag = ""
        if metrics["btc_dom"] < BTC_ALERT_THRESHOLD:
            alert_flag = "🚨 *ALERT: BTC DOMINANCE UNDER 55%!*\n\n"
            
        text = (
            f"{alert_flag}"
            f"₿ *BTC Dominance*: `{metrics['btc_dom']:.2f}%`\n"
            f"🌱 *Alt Season Index*: `{metrics['alt_season_index']:.2f}%`\n"
            f"🌐 *Total Market Cap*: `${metrics['total_mcap']:.2f}T`\n"
            f"📈 *24h Change*: `{metrics['market_change']:+.2f}%`"
        )

        await bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode="MarkdownV2"
        )
        logging.info("Message sent with BTC: %.2f%%, Alt Season: %.2f%%", 
                    metrics['btc_dom'], metrics['alt_season_index'])
        
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

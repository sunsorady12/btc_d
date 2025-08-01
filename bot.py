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
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")  # New API key
if not TOKEN or not GROUP_ID or not COINMARKETCAP_API_KEY:   # Added check for new key
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
    """Fetch market data from CoinMarketCap with error handling"""
    try:
        # Updated endpoint and headers for CoinMarketCap
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY
        }
        response = requests.get(
            "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest",
            timeout=15,
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return data["data"]
    except (requests.RequestException, KeyError, ValueError) as e:
        logging.error(f"API Error: {str(e)}")
        raise

def calculate_metrics(data):
    """Calculate market metrics from CoinMarketCap data"""
    try:
        # Extract BTC/ETH dominance and market metrics
        btc_dom = data["btc_dominance"]
        eth_dom = data["eth_dominance"]
        total_mcap = data["quote"]["USD"]["total_market_cap"]
        market_change = data["quote"]["USD"]["total_market_cap_yesterday_percentage_change"]
        
        # Alt Season Index = 100% - (BTC Dominance + ETH Dominance)
        alt_season_index = 100 - btc_dom - eth_dom
        
        # Format total market cap in trillions
        total_mcap_formatted = total_mcap / 1e12  
        
        return {
            "btc_dom": btc_dom,
            "alt_season_index": alt_season_index,
            "total_mcap": total_mcap_formatted,
            "market_change": market_change
        }
    except KeyError as e:
        logging.error(f"Data missing in API response: {str(e)}")
        raise

# ... rest of the code remains unchanged (send_message, scheduler_loop, Flask routes, etc.) ...

import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# --- TELEGRAM SETTINGS ---
# Your personal API ID and Hash (from my.telegram.org)
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

# LIST OF CHANNEL IDs: Supports "one or more" channels as per schema objective 1
# You can add multiple IDs here separated by commas in your .env
# Example: -10012345678, -10098765432
raw_channels = os.getenv("SIGNAL_CHANNEL_ID", "")
SIGNAL_CHANNEL_ID = [int(i.strip()) for i in raw_channels.split(",") if i.strip()]

# NEW: Reporting Bot Token (from @BotFather) & Your ID (from @userinfobot)
# This ensures you get P/L reports directly as requested in objective 5
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MY_TELEGRAM_USER_ID = int(os.getenv("MY_TELEGRAM_USER_ID", 0))

# --- BROKER 1: VANTAGE (MT5 - FOREX) ---
MT5_LOGIN = int(os.getenv("MT5_LOGIN", 0))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
MT5_PATH = os.getenv("MT5_PATH", "")

# --- BROKER 2: POCKET OPTION (BINARY) ---
# Your SSID is the authentication session found in your browser's Inspect tools
POCKET_OPTION_SSID = os.getenv("POCKET_OPTION_SSID", "")
BINARY_TRADE_AMOUNT = 10 # Default amount for binary trades

# --- RISK MANAGEMENT ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4o-mini"

# REVISED: Strictly 2% of balance per trade as requested
MAX_RISK_PER_TRADE_PERCENT = 2.0
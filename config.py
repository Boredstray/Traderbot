import os
from dotenv import load_dotenv

# Load the variables from the .env file
load_dotenv()

# --- TELEGRAM API CREDENTIALS ---
TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
SIGNAL_CHANNEL_ID = os.getenv('SIGNAL_CHANNEL_ID')

# --- OPENAI API CREDENTIALS ---
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = "gpt-4o-mini"

# --- VANTAGE (METATRADER 5) CREDENTIALS ---
MT5_LOGIN = int(os.getenv('MT5_LOGIN', 0))
MT5_PASSWORD = os.getenv('MT5_PASSWORD')
MT5_SERVER = os.getenv('MT5_SERVER')
MT5_PATH = os.getenv('MT5_PATH')

# --- RISK MANAGEMENT SETTINGS ---
MAX_RISK_PER_TRADE_PERCENT = float(os.getenv('MAX_RISK_PERCENT', 2.0))

# --- ASSET SETTINGS ---
# Default contract sizes (AI will attempt to verify these with the broker)
DEFAULT_CONTRACT_SIZE = 100
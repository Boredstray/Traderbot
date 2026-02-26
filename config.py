import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_API_ID = int(os.getenv('TELEGRAM_API_ID', 0))
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH', "")

raw_channels = os.getenv('SIGNAL_CHANNEL_ID', "")
SIGNAL_CHANNEL_ID = [int(i.strip()) for i in raw_channels.split(",") if i.strip()]

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "")
MY_TELEGRAM_USER_ID = int(os.getenv('MY_TELEGRAM_USER_ID', 0))

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', "")
OPENAI_MODEL = 'gpt-4o-mini'

MT5_LOGIN = int(os.getenv('MT5_LOGIN', 0))
MT5_PASSWORD = os.getenv('MT5_PASSWORD', "")
MT5_SERVER = os.getenv('MT5_SERVER', "")
MT5_PATH = os.getenv('MT5_PATH', "")

POCKET_OPTION_SSID = os.getenv('POCKET_OPTION_SSID', "")
BINARY_TRADE_AMOUNT = 10 # Default amount for binary trades

MAX_RISK_PER_TRADE_PERCENT = float(os.getenv('MAX_RISK_PERCENT', 2.0))
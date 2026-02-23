"""
CONFIG.PY - The Central Control Panel
Fill in your API keys and Account details below.
"""

# 1. TELEGRAM API CREDENTIALS (from my.telegram.org)
TELEGRAM_API_ID = 12345678  # <--- REPLACE WITH YOUR API ID
TELEGRAM_API_HASH = 'your_api_hash_here'  # <--- REPLACE WITH YOUR API HASH
# The username or ID of the channel you want to listen to (e.g., 'XAUUSD_Signals')
SIGNAL_CHANNEL_ID = 'channel_username_or_id' 

# 2. OPENAI API CREDENTIALS (for the CrewAI 'Brain')
OPENAI_API_KEY = 'sk-proj-xxxxxxxxxxxxxxxxxxxx' # <--- REPLACE WITH YOUR OPENAI KEY
OPENAI_MODEL = "gpt-4o-mini"

# 3. METATRADER 5 ACCOUNT DETAILS
MT5_LOGIN = 12345678  # <--- YOUR MT5 ACCOUNT NUMBER
MT5_PASSWORD = 'your_mt5_password'  # <--- YOUR MT5 PASSWORD
MT5_SERVER = 'Broker-ServerName'  # <--- YOUR BROKER SERVER (e.g., 'ICMarkets-Demo')
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe" # Path to your MT5 terminal

# 4. RISK MANAGEMENT SETTINGS (Based on your Schema)
MAX_RISK_PER_TRADE_PERCENT = 5.0  # The bot will never risk more than 5% of balance
USE_REPORTS = True  # Set to True to send Gain/Loss reports back to you on Telegram

# 5. ASSET CONFIGURATION (XAUUSD Example)
# Gold contract size is usually 100. Adjust if your broker uses different sizing.
XAUUSD_CONTRACT_SIZE = 100
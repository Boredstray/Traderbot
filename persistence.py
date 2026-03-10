"""
PERSISTENCE.PY - Handles active trades persistence and logging
"""
import json
import os
import logging
from datetime import datetime

# File paths
ACTIVE_TRADES_FILE = "active_trades.json"
LOG_FILE = "trading_bot.log"

def setup_logging():
    """Configure logging for debugging and monitoring."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def save_active_trades(active_trades):
    """Save active trades to JSON file for persistence across restarts."""
    try:
        # Convert any non-serializable objects to serializable format
        serializable_trades = {}
        for ticket, trade_info in active_trades.items():
            serializable_trades[str(ticket)] = {
                "entry": float(trade_info.get("entry", 0)),
                "tp1": float(trade_info.get("tp1", 0)),
                "symbol": str(trade_info.get("symbol", "")),
                "action": str(trade_info.get("action", "")),
                "be_moved": bool(trade_info.get("be_moved", False)),
                "timestamp": datetime.now().isoformat()
            }
        
        with open(ACTIVE_TRADES_FILE, 'w') as f:
            json.dump(serializable_trades, f, indent=2)
        
        logger.info(f"✅ Saved {len(serializable_trades)} active trades to persistence")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save active trades: {e}")
        return False

def load_active_trades():
    """Load active trades from JSON file on bot startup."""
    try:
        if not os.path.exists(ACTIVE_TRADES_FILE):
            logger.info("No existing active trades file found. Starting fresh.")
            return {}
        
        with open(ACTIVE_TRADES_FILE, 'r') as f:
            trades = json.load(f)
        
        # Convert string keys back to integers where possible
        loaded_trades = {}
        for ticket, trade_info in trades.items():
            try:
                loaded_trades[int(ticket)] = trade_info
            except ValueError:
                loaded_trades[ticket] = trade_info
        
        logger.info(f"✅ Loaded {len(loaded_trades)} active trades from persistence")
        return loaded_trades
    except Exception as e:
        logger.error(f"❌ Failed to load active trades: {e}")
        return {}

def clear_active_trades():
    """Clear the active trades file after all positions are closed."""
    try:
        if os.path.exists(ACTIVE_TRADES_FILE):
            os.remove(ACTIVE_TRADES_FILE)
            logger.info("🗑️ Cleared active trades persistence file")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to clear active trades: {e}")
        return False

def log_trade_execution(trade_type, symbol, action, result):
    """Log trade execution details."""
    if trade_type == "BINARY":
        logger.info(f"🎯 BINARY TRADE: {action} {symbol} - Result: {result}")
    else:
        logger.info(f"✅ FOREX TRADE: {action} {symbol} - Result: {result}")

def log_signal_received(raw_text):
    """Log incoming signal for debugging."""
    logger.info(f"📥 Signal received: {raw_text[:100]}...")

def log_error(error_type, error_message):
    """Log errors with context."""
    logger.error(f"❌ {error_type}: {error_message}")


import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import config
import time
from datetime import datetime, timedelta

# 1. INITIALIZE AI
llm = ChatOpenAI(model=config.OPENAI_MODEL, api_key=config.OPENAI_API_KEY)

def initialize_mt5():
    if not mt5.initialize(path=config.MT5_PATH):
        return False
    return mt5.login(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER)

def get_vantage_symbol(raw_symbol):
    """Cross-references symbol with Vantage (e.g. AUDCAD-ECN -> AUDCAD)."""
    initialize_mt5()
    clean_symbol = raw_symbol.split('-')[0].split('.')[0].upper()
    symbol_info = mt5.symbol_info(clean_symbol)
    if symbol_info is None:
        all_symbols = [s.name for s in mt5.symbols_get()]
        for s in all_symbols:
            if clean_symbol in s: return s
        return None
    return clean_symbol

def calculate_risk_and_spread(symbol, entry, sl, action):
    """Adds broker spread to SL and enforces 2% risk limit."""
    info = mt5.symbol_info(symbol)
    if info is None: return 0.01, sl
    
    spread_points = info.spread * info.point
    adjusted_sl = sl - spread_points if action.upper() == "BUY" else sl + spread_points
    
    account = mt5.account_info()
    risk_amount = account.balance * (config.MAX_RISK_PER_TRADE_PERCENT / 100)
    sl_dist = abs(entry - adjusted_sl)
    
    if sl_dist == 0: return 0.01, adjusted_sl
    
    # Lot calculation: Risk / (Distance * Contract Value)
    # Note: 100 is standard for Gold, 100,000 for Forex. 
    contract_size = 100 if "XAU" in symbol or "GOLD" in symbol.upper() else 100000
    lot = risk_amount / (sl_dist * contract_size)
    
    return max(0.01, round(lot, 2)), adjusted_sl

def get_detailed_report():
    """
    OBJECTIVE 5: The Loop-back.
    Checks history for closed trades and reports PROFIT/LOSS + Balance.
    """
    if not initialize_mt5(): return None
    
    # Check trades closed in the last 15 minutes
    from_date = datetime.now() - timedelta(minutes=15)
    history = mt5.history_deals_get(from_date, datetime.now())
    
    if history and len(history) > 0:
        # Get the most recent closing deal
        deal = history[-1]
        
        # Determine if it was a Profit or Loss based on the 'reason' and profit amount
        # mt5.DEAL_REASON_TP (Take Profit) or mt5.DEAL_REASON_SL (Stop Loss)
        status = "PROFIT 🟢" if deal.profit > 0 else "LOSS 🔴"
        
        # Fetch current balance after the trade
        account_info = mt5.account_info()
        new_balance = account_info.balance if account_info else "Unknown"
        
        report = {
            "symbol": deal.symbol,
            "status": status,
            "profit": round(deal.profit, 2),
            "balance": round(new_balance, 2)
        }
        return report
    return None

def move_to_break_even(ticket, entry_price):
    """Moves SL to entry price to protect profit."""
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": mt5.positions_get(ticket=ticket)[0].symbol,
        "sl": entry_price,
        "position": ticket,
    }
    return mt5.order_send(request)

# --- AI AGENTS ---
parser_agent = Agent(
    role='Expert Signal Analyst',
    goal='Extract exact trade data and normalize symbols for Vantage.',
    backstory='You identify signals from raw text, extracting Entry, TPs, and SL accurately.',
    llm=llm
)

def run_trading_crew(raw_text):
    parse_task = Task(
        description=f"Analyze this signal text: {raw_text}. Identify Symbol, Action, Entry, TP1, TP2, TP3, and SL.",
        expected_output="JSON list: [SYMBOL, ACTION, ENTRY, TP1, TP2, TP3, SL]",
        agent=parser_agent
    )
    return Crew(agents=[parser_agent], tasks=[parse_task]).kickoff()

def execute_vantage_trade(symbol, action, lot, tp, sl):
    """Places the trade on Vantage MT5."""
    if not initialize_mt5(): return None
    mt5.symbol_select(symbol, True)
    
    trade_type = mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(symbol)
    price = tick.ask if action.upper() == "BUY" else tick.bid
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": trade_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": 123456,
        "comment": "Vantage AI Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return mt5.order_send(request)
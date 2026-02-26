from pocket_option import PocketOptionClient
import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import json
import asyncio
from datetime import datetime, timedelta # FIXED: Added for time-based reporting
from crewai import Agent, Task, Crew
from langchain_openai import ChatOpenAI
import config

# --- 1. INITIALIZATION & AI SETUP ---
llm = ChatOpenAI(model=config.OPENAI_MODEL, api_key=config.OPENAI_API_KEY)

def initialize_mt5():
    """Initializes connection to Vantage MT5."""
    if not mt5.initialize(path=config.MT5_PATH):
        return False
    return mt5.login(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER)

async def execute_pocket_option_trade(data):
    """Binary Execution Engine using Pocket Option Client."""
    client = PocketOptionClient(config.POCKET_OPTION_SSID)
    try:
        await client.connect()
        direction = "CALL" if data['action'].upper() in ["BUY", "CALL"] else "PUT"
        result = await client.place_order(
            asset=data['symbol'],
            amount=config.BINARY_TRADE_AMOUNT,
            direction=direction,
            duration=int(data.get('expiry', 5)) * 60
        )
        return result
    except Exception as e:
        return f"Binary Error: {e}"

# --- 2. AI ROUTING & PARSING ---
parser_agent = Agent(
    role='Powerhouse Multi-Asset Trading Analyst',
    goal='Distinguish between Forex and Binary signals and extract precise trade data.',
    backstory="""You are an elite trading algorithm. 
    - FOREX: Identified by TP/SL values. Output format: [SYMBOL, ACTION, ENTRY, TP1, TP2, SL].
    - BINARY: Identified by 'Expiration', 'PUT/CALL', 'GALE', or 'OTC'.
    - ACTIONS: Normalize 'PUT/RED' to 'SELL' and 'CALL/GREEN' to 'BUY'.""",
    llm=llm
)

def run_trading_crew(raw_text):
    """Parses signals and routes them to the correct execution path."""
    parse_task = Task(
        description=f"Analyze: '{raw_text}'. Identify if it is 'FOREX' or 'BINARY'. Extract all data.",
        expected_output="A JSON object with type, symbol, action, and all parameters.",
        agent=parser_agent
    )
    crew = Crew(agents=[parser_agent], tasks=[parse_task])
    result = crew.kickoff()
    return json.loads(str(result).replace("```json", "").replace("```", "").strip())

# --- 3. FOREX UTILITIES ---
def get_vantage_symbol(raw_symbol):
    """Matches raw signals to Vantage-specific symbols."""
    initialize_mt5()
    clean = raw_symbol.split('-')[0].replace("/", "").upper()
    info = mt5.symbol_info(clean)
    if info: return clean
    all_symbols = [s.name for s in mt5.symbols_get()]
    for s in all_symbols:
        if clean in s: return s
    return None

def calculate_risk_and_spread(symbol, entry, sl, action):
    """Enforces strictly 2% risk limit and adjusts for spread."""
    info = mt5.symbol_info(symbol)
    if info is None: return 0.01, sl
    
    # Adjust SL for broker spread
    spread_points = info.spread * info.point
    adjusted_sl = sl - spread_points if action.upper() == "BUY" else sl + spread_points
    
    account = mt5.account_info()
    risk_amount = account.balance * (config.MAX_RISK_PER_TRADE_PERCENT / 100)
    sl_dist = abs(entry - adjusted_sl)
    
    if sl_dist == 0: return 0.01, adjusted_sl
    
    # Lot calculation: Risk / (Distance * Contract Value)
    contract_size = 100 if "XAU" in symbol or "GOLD" in symbol.upper() else 100000
    lot = risk_amount / (sl_dist * contract_size)
    
    return max(0.01, round(lot, 2)), adjusted_sl

# --- 4. EXECUTION ENGINES ---
def execute_vantage_trade(symbol, action, lot, tp, sl):
    """Forex Execution Engine."""
    if not initialize_mt5(): return None
    mt5.symbol_select(symbol, True)
    
    trade_type = mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(symbol)
    price = tick.ask if action.upper() == "BUY" else tick.bid
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": trade_type,
        "price": price,
        "sl": float(sl),
        "tp": float(tp),
        "magic": 123456,
        "comment": "Powerhouse Forex",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return mt5.order_send(request)

# --- 5. MONITORING & REPORTING ---
def get_detailed_report():
    """Objective 5: Checks history for closed trades and reports Profit/Loss."""
    if not initialize_mt5(): return None
    
    # Check trades closed in the last 24 hours
    from_date = datetime.now() - timedelta(days=1)
    history = mt5.history_deals_get(from_date, datetime.now())
    
    if history and len(history) > 0:
        deal = history[-1] # Get most recent closing deal
        status = "PROFIT 🟢" if deal.profit > 0 else "LOSS 🔴"
        account_info = mt5.account_info()
        
        return {
            "symbol": deal.symbol,
            "status": status,
            "profit": round(deal.profit, 2),
            "balance": round(account_info.balance, 2) if account_info else "Unknown"
        }
    return None

def move_to_break_even(ticket, entry_price):
    """Moves SL to entry price once TP1 is hit."""
    pos = mt5.positions_get(ticket=ticket)
    if not pos: return None
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": pos[0].symbol,
        "sl": float(entry_price),
        "position": ticket,
    }
    return mt5.order_send(request)
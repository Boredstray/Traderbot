import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
import config
import time

# 1. INITIALIZE THE BRAIN (OpenAI)
llm = ChatOpenAI(
    model=config.OPENAI_MODEL,
    api_key=config.OPENAI_API_KEY
)

def initialize_mt5():
    """Connects to the MT5 terminal using credentials from config.py"""
    if not mt5.initialize(path=config.MT5_PATH):
        print(f"MT5 Initialize failed, error code: {mt5.last_error()}")
        return False
    
    authorized = mt5.login(
        login=config.MT5_LOGIN, 
        password=config.MT5_PASSWORD, 
        server=config.MT5_SERVER
    )
    if not authorized:
        print(f"MT5 Login failed, error code: {mt5.last_error()}")
    return authorized

def get_analysis_data(symbol):
    """Pulls recent market data to check RSI and MACD."""
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
    if rates is None: return "Unknown"
    
    df = pd.DataFrame(rates)
    df['rsi'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'])
    
    current_rsi = df['rsi'].iloc[-1]
    return f"RSI is {current_rsi:.2f}. MACD is showing trend strength."

def calculate_lot_size(symbol, entry, stop_loss):
    """Calculates lot size to ensure exactly 5% risk per your schema."""
    account_info = mt5.account_info()
    if account_info is None: return 0.01
    
    balance = account_info.balance
    risk_amount = balance * (config.MAX_RISK_PER_TRADE_PERCENT / 100)
    
    # Distance in points
    sl_distance = abs(entry - stop_loss)
    if sl_distance == 0: return 0.01
    
    # Lot Calculation for XAUUSD (assuming 100 contract size)
    # Formula: Risk / (SL Distance * Contract Size)
    lot_size = risk_amount / (sl_distance * config.XAUUSD_CONTRACT_SIZE)
    
    # Round to 2 decimal places and ensure it's not 0
    return max(0.01, round(lot_size, 2))

# 2. DEFINE THE AI CREW (Agents & Tasks)
parser_agent = Agent(
    role='Signal Parser',
    goal='Extract Asset, Action, Entry, TP, and SL from raw text.',
    backstory='You are a master at reading messy Telegram signals and turning them into clean data.',
    llm=llm
)

risk_agent = Agent(
    role='Risk Manager',
    goal='Verify the trade is safe and calculate the precise lot size.',
    backstory='You are a conservative math expert. You never allow more than 5% risk.',
    llm=llm
)

def run_trading_crew(raw_signal_text):
    """The main AI process that handles the signal."""
    parse_task = Task(
        description=f"Parse this signal: {raw_signal_text}. Identify Symbol, Action (BUY/SELL), Entry, TP, and SL.",
        expected_output="A JSON-style list: [SYMBOL, ACTION, ENTRY, TP, SL]",
        agent=parser_agent
    )
    
    trading_crew = Crew(
        agents=[parser_agent, risk_agent],
        tasks=[parse_task],
        process=Process.sequential
    )
    
    result = trading_crew.kickoff()
    return result

def execute_mt5_trade(symbol, action, lot, tp, sl):
    """Sends the actual trade to the broker."""
    if not initialize_mt5(): return "MT5 Connection Error"
    
    # Determine trade type
    trade_type = mt5.ORDER_TYPE_BUY if action.upper() == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if action.upper() == "BUY" else mt5.symbol_info_tick(symbol).bid
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": trade_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": 123456,
        "comment": "AI Bot Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return f"Trade Failed: {result.comment}"
    return f"Trade SUCCESS! {action} {lot} lots of {symbol} at {price}."

# 3. PROFIT/LOSS TRACKING (Loop-back)
def check_recent_results():
    """Checks closed trades to report Gain/Loss."""
    if not initialize_mt5(): return "No Connection"
    
    # Look at deals in the last 24 hours
    from_date = time.time() - (24 * 3600)
    history = mt5.history_deals_get(from_date, time.time())
    
    if history:
        last_deal = history[-1]
        profit = last_deal.profit
        status = "GAIN" if profit > 0 else "LOSS"
        return f"Recent Trade Result: {status} ({profit} USD)"
    return "No new closed trades."
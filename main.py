"""
MAIN.PY - The Unified Command Center (Vantage Edition)
Connects Telegram -> AI Agents -> Vantage MT5
"""

import asyncio
from telethon import TelegramClient, events
import config
import trading_engine
import MetaTrader5 as mt5

# Initialize Telegram
client = TelegramClient('vantage_session', config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)

# Tracking dictionary for Break-Even and Monitoring
active_trades = {}

print("--- Vantage AI Bot: Online & Listening ---")

@client.on(events.NewMessage(chats=config.SIGNAL_CHANNEL_ID))
async def signal_handler(event):
    raw_text = event.raw_text
    
    # 1. TRIGGER LOGIC: Recognize signals even without 'SIGNAL ALERT' (Obj 1 & 3)
    trigger_keywords = ['SIGNAL ALERT', 'XAUUSD', 'BUY', 'SELL', 'ENTRY', 'TP', 'SL']
    is_potential_signal = any(key in raw_text.upper() for key in trigger_keywords)

    if is_potential_signal:
        print("\n[!] Signal detected. Analyzing...")
        
        try:
            # 2. AI PARSING & NORMALIZATION (Obj 3)
            # Extracts: [SYMBOL, ACTION, ENTRY, TP1, TP2, TP3, SL]
            ai_raw = trading_engine.run_trading_crew(raw_text)
            data = eval(str(ai_raw)) 
            raw_sym, action, entry, tp1, tp2, tp3, raw_sl = data

            # 3. VANTAGE ASSET CROSS-REFERENCING (Obj 3)
            symbol = trading_engine.get_vantage_symbol(raw_sym)
            if not symbol:
                print(f"Error: Asset {raw_sym} not found on Vantage.")
                return

            # 4. SPREAD & RISK CALCULATION (Obj 4)
            # Adds spread to SL and enforces 2% risk limit.
            lot, adj_sl = trading_engine.calculate_risk_and_spread(symbol, entry, raw_sl, action)

            # 5. EXECUTION & REPORTING (Obj 1)
            response = trading_engine.execute_vantage_trade(symbol, action, lot, tp1, adj_sl)
            
            if response and response.retcode == mt5.TRADE_RETCODE_DONE:
                ticket = response.order
                active_trades[ticket] = {
                    "entry": entry, "tp1": tp1, "symbol": symbol, "action": action.upper(), "be_moved": False
                }
                
                # Send the signal used to trade back to you in your requested format
                summary = (
                    f"✅ **TRADE EXECUTED**\n\n"
                    f"SIGNAL ALERT\n\n"
                    f"{action.upper()} {symbol} {entry}\n"
                    f"TP1: {tp1}\n"
                    f"TP2: {tp2}\n"
                    f"TP3: {tp3}\n"
                    f"🔴SL: {adj_sl}\n"
                    f"(Lot: {lot})"
                )
                await client.send_message('me', summary)
            else:
                print(f"Trade Rejected: {response.comment if response else 'Connection Error'}")

        except Exception as e:
            print(f"Parsing Error: {e}")

async def monitoring_loop():
    """
    WATCHDOG: Monitors TP1 for Break-Even and reports PROFIT/LOSS (Obj 5).
    """
    while True:
        await asyncio.sleep(15) # Check every 15 seconds
        
        # Part A: Check for closed trades (Loop-back Profit/Loss)
        report = trading_engine.get_detailed_report()
        if report:
            msg = (f"📊 **{report['status']} REPORT**\n"
                   f"Asset: {report['symbol']}\n"
                   f"Profit: ${report['profit']}\n"
                   f"New Balance: ${report['balance']}")
            await client.send_message('me', msg)

        # Part B: Move SL to Break-Even if TP1 hit
        if not active_trades: continue
        
        trading_engine.initialize_mt5()
        for ticket in list(active_trades.keys()):
            info = active_trades[ticket]
            pos = mt5.positions_get(ticket=ticket)
            
            if not pos:
                active_trades.pop(ticket) # Position closed by broker
                continue
            
            # Check if TP1 reached to move SL to Entry
            tick = mt5.symbol_info_tick(info['symbol'])
            price = tick.bid if info['action'] == "BUY" else tick.ask
            tp1_hit = (price >= info['tp1']) if info['action'] == "BUY" else (price <= info['tp1'])
            
            if tp1_hit and not info['be_moved']:
                res = trading_engine.move_to_break_even(ticket, info['entry'])
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    info['be_moved'] = True
                    await client.send_message('me', f"🛡️ **BREAK-EVEN**: SL moved to {info['entry']} for {info['symbol']}")

async def main():
    await client.start()
    print("Bot is listening...")
    await asyncio.gather(client.run_until_disconnected(), monitoring_loop())

if __name__ == "__main__":
    asyncio.run(main())
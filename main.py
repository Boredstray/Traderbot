"""
MAIN.PY - The Powerhouse Command Center
Routes Signals to Vantage (MT5) or Pocket Option (Binary)
"""

import asyncio
import json
from telethon import TelegramClient, events
import config
import trading_engine
import MetaTrader5 as mt5

# 1. INITIALIZE CLIENTS
# 'client' listens to the signal channels using your personal account
client = TelegramClient('vantage_session', config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)

# Tracking for Forex trades (Break-Even and Monitoring)
active_trades = {}

print("--- POWERHOUSE BOT: ONLINE & LISTENING ---")
print(f"Monitoring Channels: {config.SIGNAL_CHANNEL_ID}")

@client.on(events.NewMessage(chats=config.SIGNAL_CHANNEL_ID))
async def signal_handler(event):
    raw_text = event.raw_text
    trigger_keywords = ['SIGNAL ALERT', 'XAUUSD', 'BUY', 'SELL', 'ENTRY', 'TP', 'SL', 'EXPIRATION', 'PUT', 'CALL']
    is_potential_signal = any(key in raw_text.upper() for key in trigger_keywords)

    if is_potential_signal:
        print("\n[!] Signal detected. Routing to AI Parser...")
        
        try:
            # 1. AI PARSING - Returns a dictionary with 'type', 'symbol', 'action', etc.
            data = trading_engine.run_trading_crew(raw_text)
            
            # --- PATH A: BINARY OPTIONS (Pocket Option) ---
            if data.get('type') == 'BINARY':
                print("[!] Binary Signal Identified. Executing on Pocket Option...")
                # Note: We do NOT call Vantage functions here to prevent it from opening
                response = await trading_engine.execute_pocket_option_trade(data)
                
                summary = (
                    f"🎯 **BINARY TRADE PLACED**\n\n"
                    f"Asset: {data['symbol']}\n"
                    f"Action: {data['action'].upper()}\n"
                    f"Expiry: {data.get('expiry', '5')} mins\n"
                    f"Gale: {data.get('gale_steps', '0')} steps detected"
                    f"Status: {response}"
                )
                await client.send_message('me', summary)

            # --- PATH B: FOREX (Vantage MT5) ---
            else:
                print("[!] Forex Signal Identified. Executing on Vantage...")
                symbol = trading_engine.get_vantage_symbol(data['symbol'])
                if not symbol:
                    print(f"Error: Asset {data['symbol']} not found on Vantage.")
                    return

                # Only initialize and calculate risk for Forex trades
                lot, adj_sl = trading_engine.calculate_risk_and_spread(
                    symbol, data['entry'], data['sl'], data['action']
                )

                response = trading_engine.execute_vantage_trade(
                    symbol, data['action'], lot, data['tp1'], adj_sl
                )
                
                if response and response.retcode == mt5.TRADE_RETCODE_DONE:
                    # (Existing Vantage tracking logic for Break-Even)
                    active_trades[response.order] = {
                        "entry": data['entry'], "tp1": data['tp1'], 
                        "symbol": symbol, "action": data['action'].upper(), "be_moved": False
                    }
                    await client.send_message('me', f"✅ **FOREX TRADE EXECUTED**: {symbol} {data['action']}")
                else:
                    print(f"Vantage Rejected: {response.comment if response else 'Error'}")

        except Exception as e:
            print(f"Execution Error: {e}")
            await client.send_message('me', f"⚠️ **Execution Error**: {str(e)}")

async def monitoring_loop():
    """
    WATCHDOG: Monitors MT5 for Break-Even and reports Profit/Loss.
    """
    while True:
        await asyncio.sleep(15) 
        
        # Check for closed trades (Reporting)
        report = trading_engine.get_detailed_report()
        if report:
            msg = (f"📊 **{report['status']} REPORT**\n"
                   f"Asset: {report['symbol']}\n"
                   f"Profit: ${report['profit']}\n"
                   f"New Balance: ${report['balance']}")
            await client.send_message('me', msg)

        # Break-Even Monitoring (Forex only)
        if not active_trades: continue
        
        trading_engine.initialize_mt5()
        for ticket in list(active_trades.keys()):
            info = active_trades[ticket]
            pos = mt5.positions_get(ticket=ticket)
            
            if not pos:
                active_trades.pop(ticket) # Position closed
                continue
            
            # Check TP1 to move SL to Entry (Retained logic)
            tick = mt5.symbol_info_tick(info['symbol'])
            price = tick.bid if info['action'] == "BUY" else tick.ask
            tp1_hit = (price >= info['tp1']) if info['action'] == "BUY" else (price <= info['tp1'])
            
            if tp1_hit and not info['be_moved']:
                res = trading_engine.move_to_break_even(ticket, info['entry'])
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    info['be_moved'] = True
                    await client.send_message('me', f"🛡️ **BE**: SL moved to {info['entry']} for {info['symbol']}")

async def main():
    await client.start()
    # Runs the listener and the watchdog simultaneously
    await asyncio.gather(client.run_until_disconnected(), monitoring_loop())

if __name__ == "__main__":
    asyncio.run(main())
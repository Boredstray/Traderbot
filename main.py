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
    
    # TRIGGER LOGIC: Identify if this looks like a trade signal (Forex or Binary)
    keywords = ['SIGNAL', 'BUY', 'SELL', 'PUT', 'CALL', 'TP', 'SL', 'EXPIRATION', 'OTC']
    if not any(key in raw_text.upper() for key in keywords):
        return

    print("\n[!] Signal detected. Routing to AI Parser...")
    
    try:
        # 2. AI PARSING & ROUTING
        # Now returns a dict with 'type' (FOREX/BINARY) and specific data
        data = trading_engine.run_trading_crew(raw_text)
        
        # --- PATH A: FOREX (VANTAGE MT5) ---
        if data.get('type') == 'FOREX':
            symbol = trading_engine.get_vantage_symbol(data['symbol'])
            if not symbol:
                await client.send_message('me', f"❌ Error: Asset {data['symbol']} not found on Vantage.")
                return

            # Risk calculation (Now using your revised 2% limit)
            lot, adj_sl = trading_engine.calculate_risk_and_spread(
                symbol, data['entry'], data['sl'], data['action']
            )

            response = trading_engine.execute_vantage_trade(
                symbol, data['action'], lot, data['tp1'], adj_sl
            )
            
            if response and response.retcode == mt5.TRADE_RETCODE_DONE:
                active_trades[response.order] = {
                    "entry": data['entry'], "tp1": data['tp1'], 
                    "symbol": symbol, "action": data['action'].upper(), "be_moved": False
                }
                summary = (
                    f"✅ **FOREX TRADE EXECUTED**\n\n"
                    f"{data['action'].upper()} {symbol} @ {data['entry']}\n"
                    f"TP1: {data['tp1']} | TP2: {data.get('tp2', 'N/A')}\n"
                    f"🔴 SL: {adj_sl} (Lot: {lot})"
                )
                await client.send_message('me', summary)
            else:
                error_msg = response.comment if response else "Connection Error"
                await client.send_message('me', f"❌ MT5 Rejected: {error_msg}")

        # --- PATH B: BINARY (POCKET OPTION) ---
        elif data.get('type') == 'BINARY':
            # Execute on Pocket Option (Binary Engine handles the Websocket)
            res = await trading_engine.execute_pocket_option_trade(data)
            
            summary = (
                f"🔥 **BINARY TRADE PLACED**\n\n"
                f"Asset: {data['symbol']}\n"
                f"Action: {data['action'].upper()}\n"
                f"Expiry: {data.get('expiry', '5')} mins\n"
                f"Gale: {data.get('gale_steps', '0')} steps detected"
            )
            await client.send_message('me', summary)

    except Exception as e:
        print(f"Routing Error: {e}")
        await client.send_message('me', f"⚠️ Parser Error: {str(e)}")

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
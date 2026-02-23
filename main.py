"""
MAIN.PY - The Command Center
This script connects to Telegram and coordinates the AI Agents and MT5.
Run this file to start the bot.
"""

import asyncio
from telethon import TelegramClient, events
import config
import trading_engine

# 1. INITIALIZE TELEGRAM CLIENT
# This uses your API ID and Hash from config.py to log in as 'your' account
client = TelegramClient('trading_session', config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)

print("--- AI Trading Bot Starting ---")

# 2. THE SIGNAL LISTENER
@client.on(events.NewMessage(chats=config.SIGNAL_CHANNEL_ID))
async def signal_handler(event):
    raw_text = event.raw_text
    print(f"\n[New Message Received]:\n{raw_text}")

    # Pattern Matching: Check for keywords defined in your Schema
    keywords = ['SIGNAL ALERT', 'XAUUSD', 'BUY', 'SELL', 'TP', 'SL']
    if any(key in raw_text.upper() for key in keywords):
        print(">>> Signal detected! Initiating AI Analysis...")
        
        try:
            # Step A: Run the CrewAI Agents to parse and calculate risk
            # This returns a result like: ["XAUUSD", "BUY", 2050.0, 2060.0, 2040.0]
            ai_result = trading_engine.run_trading_crew(raw_text)
            print(f"AI Analysis Complete: {ai_result}")

            # Step B: Perform Technical Analysis (RSI/MACD)
            # This fulfills Objective 2 of your Schema
            analysis = trading_engine.get_analysis_data("XAUUSD")
            print(f"Technical Filter: {analysis}")

            # Step C: Human-in-the-loop (Safety Switch)
            # To automate fully, remove the input() and 'if' check below.
            print("\nPROPOSED TRADE:")
            print(f"Details: {ai_result}")
            print(f"Market Sentiment: {analysis}")
            
            confirm = input("Confirm execution on MT5? (y/n): ")
            
            if confirm.lower() == 'y':
                # Parse the AI result (simple string split for this example)
                # In a production bot, we'd use a more robust JSON parser
                # For now, let's assume the AI outputs: Symbol, Action, Entry, TP, SL
                # Example: "XAUUSD, BUY, 2350.0, 2360.0, 2340.0"
                parts = str(ai_result).replace('[','').replace(']','').split(',')
                symbol = parts[0].strip()
                action = parts[1].strip()
                entry = float(parts[2].strip())
                tp = float(parts[3].strip())
                sl = float(parts[4].strip())

                # Step D: Calculate 5% Lot Size
                lot = trading_engine.calculate_lot_size(symbol, entry, sl)
                
                # Step E: Execute Trade
                execution_status = trading_engine.execute_mt5_trade(symbol, action, lot, tp, sl)
                print(execution_status)
                
                # Report back to you on Telegram
                await client.send_message('me', f"🚀 Bot Executed Trade: {execution_status}")

        except Exception as e:
            print(f"Critical Error processing signal: {e}")
            await client.send_message('me', f"⚠️ Bot Error: {e}")

# 3. THE LOOP-BACK REPORTER (Objective 5)
async def report_results_loop():
    """Background task to check for closed trades and report GAIN/LOSS."""
    while True:
        await asyncio.sleep(300) # Check every 5 minutes
        result = trading_engine.check_recent_results()
        if "GAIN" in result or "LOSS" in result:
            print(f"[Loop-back]: {result}")
            await client.send_message('me', f"📊 {result}")

# 4. START THE BOT
async def main():
    await client.start()
    print("Bot is now listening to Telegram...")
    
    # Run the listener and the result reporter simultaneously
    await asyncio.gather(
        client.run_until_disconnected(),
        report_results_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
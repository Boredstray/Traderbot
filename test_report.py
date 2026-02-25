import asyncio
from telethon import TelegramClient
import config

async def test_bot():
    print("Testing connection to Telegram...")
    client = TelegramClient('test_session', config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH)
    await client.start()
    
    # This sends a test message to YOUR personal Telegram
    print("Sending test message to you...")
    await client.send_message('me', "🚀 **Powerhouse Dry Run**: Reporting Bot is Online!")
    
    print("Success! Check your Telegram.")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_bot())
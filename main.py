import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiohttp import web
from dotenv import load_dotenv
load_dotenv()

from database import init_db
from handlers import router

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    # Only show critical errors/warnings to avoid spam and sensitive token/update logging
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Explicitly silence aiogram event updates to keep console clean and hide user IDs
    logging.getLogger('aiogram.event').setLevel(logging.CRITICAL)
    
    # Initialize DB
    await init_db()
    
    if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
        print("ERROR: BOT_TOKEN is not set in .env file!!")
        return

    # Secure cookies dynamically from Environment Variables (for Render deployment)
    yt_cookies = os.getenv("YOUTUBE_COOKIES")
    if yt_cookies:
        # Save exact string format to cookies.txt 
        # Replacing actual \\n literal from env with real newlines just in case
        formatted_cookies = yt_cookies.replace('\\n', '\n')
        with open("cookies.txt", "w", encoding="utf-8") as f:
            f.write(formatted_cookies)
        print("Successfully loaded cookies.txt from YOUTUBE_COOKIES environment variable!")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(router)
    
    print("Bot is started seamlessly! Press Ctrl+C to stop.")
    
    # Simple Web Server for Render Healthcheck (binding to PORT)
    async def handle_ping(request):
        return web.Response(text="Bot is running!")
        
    app = web.Application()
    app.router.add_get('/', handle_ping)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    # Run Both Web Server and Bot Polling Concurrently
    await asyncio.gather(
        site.start(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped!")

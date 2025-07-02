import asyncio
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

async def main():
    app = Client(
        "betting_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        plugins=dict(root="bot/handlers") # Load handlers from bot/handlers
    )

    app.bet_context = {}
    app.deposit_context = {}
    app.withdraw_context = {}
    app.admin_context = {}

    print("Bot starting...")
    await app.run()
    print("Bot stopped.")

if __name__ == "__main__":
    asyncio.run(main())
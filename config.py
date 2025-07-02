import os

API_ID = int(os.environ.get("API_ID", "1234567"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7574049112:AAGCO6Oa0SueVU4F3M1e_LC-T9T3N6PkZaU")

ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "123456789,987654321").split(",")))

DATABASE_URL = os.environ.get("DATABASE_URL", "mongodb://localhost:27017/betting_bot")
# For SQLite, you might use: DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./bot.db")

# Optional: Payment API keys or other sensitive info
# BKASH_API_KEY = os.environ.get("BKASH_API_KEY", "")
# PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_CLIENT_ID", "")
# PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_CLIENT_SECRET", "")
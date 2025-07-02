# Telegram Betting Broker Bot

This project aims to build an ultra-advanced Telegram bot for a Color Prediction-style Betting Broker Game Platform. The bot will feature modern betting mechanics, a highly interactive UI via Telegram, and a full-featured admin dashboard.

## Features:

### Core Game Systems:
- Classic Color Prediction (Red, Green, Violet) with 3-minute rounds.
- Auto-generated or manually controlled results.
- Dynamic odds & reward distribution.
- Multiple bets per round.
- Extra Game Modes: Parity/Evens, Number Prediction, Wheel Spin, Lucky 7.

### User System:
- Dynamic onboarding & referral system.
- User balance + profile view.
- In-bot Wallet with live balance updates.
- Transaction & game history logs.
- Leaderboards (weekly, monthly, all-time).
- Daily Bonus, Streak Bonus, VIP Rewards.
- Multi-language support (optional).

### Payment System (Modular):
- Deposits via bKash, Nagad, Rocket, PayPal (API/manual).
- Unique transaction ID input with screenshot proof (optional).
- Admin/manual verification flow.
- Withdrawals with minimum balance limit.
- Admin review + approval system.
- Payment tracking and automatic balance updates.

### Admin Panel (via Telegram ID):
- Add/Edit/Delete Admin/Staff accounts.
- Control all game results (auto/manual).
- Real-time analytics: total bets, revenue, active users.
- Ban/Unban Users.
- Broadcast messages to all users.
- Update game settings (odds, timers, limits, colors).
- Manual fund add/remove.
- Review & approve payments (with inline buttons).
- Set maintenance mode.

## Tech Stack:
- **Language**: Python (async)
- **Bot Framework**: Pyrogram (or Telethon)
- **Database**: MongoDB or SQLite (flexible)
- **Structure**: Modular file structure (bots, games, db, admin, payment).
- **UI**: Inline keyboards, callback queries, custom menus.
- **Data**: Persistent storage for users, bets, rounds, transactions.
- **Security**: Security checks, user logging, error handling.

## Setup Instructions:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your_username/telegram-betting-bot.git
    cd telegram-betting-bot
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/Scripts/activate  # On Windows
    # source venv/bin/activate  # On macOS/Linux
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the bot:**
    - Create a `config.py` file (or use environment variables) with your bot token, API ID, API Hash, and admin IDs.
    - Example `config.py`:
      ```python
      API_ID = 1234567
      API_HASH = "your_api_hash"
      BOT_TOKEN = "your_bot_token"
      ADMIN_IDS = [123456789, 987654321] # Your Telegram user IDs
      DATABASE_URL = "mongodb://localhost:27017/betting_bot" # or sqlite:///./bot.db
      ```

5.  **Run the bot:**
    ```bash
    python main.py
    ```

## Project Structure (Planned):

```
.
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── bot/
│   ├── __init__.py
│   ├── client.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── user_commands.py
│   │   └── admin_commands.py
│   └── utils/
│       ├── __init__.py
│       └── keyboards.py
├── database/
│   ├── __init__.py
│   ├── models.py
│   └── db_manager.py
├── games/
│   ├── __init__.py
│   ├── color_prediction.py
│   ├── parity_evens.py
│   └── game_manager.py
├── payments/
│   ├── __init__.py
│   ├── deposit.py
│   └── withdrawal.py
└── admin/
    ├── __init__.py
    └── admin_panel.py
```
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import User, Transaction, Bet, DailyBonus, Leaderboard
from database.db_manager import connect_db
from games.game_manager import GameManager
from payments.deposit import DepositManager
from payments.withdrawal import WithdrawalManager
from datetime import datetime, timedelta
import asyncio

# Initialize managers
game_manager = GameManager()
deposit_manager = DepositManager()
withdrawal_manager = WithdrawalManager()

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    user = User.objects(user_id=user_id).first()

    if not user:
        # New user onboarding
        # Check for referral code in command arguments
        referral_code = None
        if len(message.command) > 1:
            potential_referral_code = message.command[1]
            referred_by_user = User.objects(referral_code=potential_referral_code).first()
            if referred_by_user:
                referral_code = potential_referral_code
                await client.send_message(user_id, f"Welcome! You were referred by {referred_by_user.username or referred_by_user.first_name}.")
            else:
                await client.send_message(user_id, "Invalid referral code.")

        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            balance=0.0,
            referral_code=f"REF{user_id}", # Simple referral code generation
            referred_by=referred_by_user if referral_code else None
        )
        user.save()
        await client.send_message(user_id, 
                                  f"Welcome to the Betting Broker Bot, {first_name}!\n\n" \
                                  "I'm your ultimate betting companion. Here's what you can do:\n\n" \
                                  "🎮 **Play Games**: Predict colors, numbers, and more.\n" \
                                  "💰 **Manage Wallet**: Deposit and withdraw funds easily.\n" \
                                  "📊 **Track Progress**: View your profile, history, and climb leaderboards.\n" \
                                  "🤝 **Refer Friends**: Earn rewards by inviting others.\n\n" \
                                  "Use the menu below or type commands to get started!",
                                  parse_mode="Markdown")
    else:
        await client.send_message(user_id, f"Welcome back, {first_name}! How can I help you today?",
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton("🎮 Play Games", callback_data="games_menu")],
                                      [InlineKeyboardButton("💰 Wallet", callback_data="wallet_menu")],
                                      [InlineKeyboardButton("📊 Profile & History", callback_data="profile_menu")]
                                  ]))

@Client.on_message(filters.command("profile"))
async def profile_command(client: Client, message):
    user_id = message.from_user.id
    user = User.objects(user_id=user_id).first()

    if not user:
        await client.send_message(user_id, "Please /start the bot first.")
        return

    referred_by_info = "None" 
    if user.referred_by:
        referred_by_user = User.objects(id=user.referred_by.id).first()
        if referred_by_user:
            referred_by_info = referred_by_user.username or referred_by_user.first_name

    profile_text = f"**👤 Your Profile**\n\n" \
                   f"**ID**: `{user.user_id}`\n" \
                   f"**Username**: @{user.username or 'N/A'}\n" \
                   f"**Balance**: {user.balance:.2f}\n" \
                   f"**Referral Code**: `{user.referral_code}`\n" \
                   f"**Referred By**: {referred_by_info}\n" \
                   f"**Joined**: {user.created_at.strftime('%Y-%m-%d %H:%M')}"

    await client.send_message(user_id, profile_text, parse_mode="Markdown")

@Client.on_message(filters.command("games"))
async def games_command(client: Client, message):
    await client.send_message(message.from_user.id, 
                              "**🎮 Choose a Game**",
                              reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🌈 Color Prediction", callback_data="game_color_prediction")],
            [InlineKeyboardButton("🎲 Parity/Evens", callback_data="game_parity_evens")],
            [InlineKeyboardButton("🔢 Number Prediction", callback_data="game_number_prediction")],
            [InlineKeyboardButton("🎡 Wheel Spin", callback_data="game_wheel_spin")],
            [InlineKeyboardButton("🍀 Lucky 7", callback_data="game_lucky_7")]
                              ]),
                              parse_mode="Markdown")

@Client.on_callback_query(filters.regex("^game_"))
async def game_callback(client: Client, callback_query):
    game_type = callback_query.data.replace("game_", "")
    user_id = callback_query.from_user.id

    game_instance = await game_manager.get_game_instance(game_type)
    if not game_instance:
        await callback_query.answer("Game not found or not implemented yet.", show_alert=True)
        return

    current_round_info = await game_manager.get_current_round_info(game_type)

    if not current_round_info:
        await callback_query.answer("No active round for this game. Please try again later.", show_alert=True)
        return

    round_id = current_round_info['round_id']
    end_time = current_round_info['end_time']
    time_left = int((end_time - datetime.utcnow()).total_seconds())

    if time_left <= 0:
        await callback_query.answer("Betting for this round has closed. Please wait for the next round.", show_alert=True)
        return

    if game_type == 'color_prediction':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔴 Red (x2)", callback_data=f"bet_color_{round_id}_red"),
             InlineKeyboardButton("🟢 Green (x2)", callback_data=f"bet_color_{round_id}_green")],
            [InlineKeyboardButton("🟣 Violet (x5)", callback_data=f"bet_color_{round_id}_violet")],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])
        message_text = f"**🔴 Color Prediction Game**\n\n" \
                       f"**Round ID**: `{round_id}`\n" \
                       f"**Time Left**: {time_left} seconds\n\n" \
                       "Choose your color and amount to bet. Example: `/bet red 10`"

    elif game_type == 'parity_evens':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Even (x2)", callback_data=f"bet_parity_{round_id}_even"),
             InlineKeyboardButton("Odd (x2)", callback_data=f"bet_parity_{round_id}_odd")],
            [InlineKeyboardButton("0 (x10)", callback_data=f"bet_parity_{round_id}_0"),
             InlineKeyboardButton("1 (x10)", callback_data=f"bet_parity_{round_id}_1"),
             InlineKeyboardButton("2 (x10)", callback_data=f"bet_parity_{round_id}_2")],
            [InlineKeyboardButton("3 (x10)", callback_data=f"bet_parity_{round_id}_3"),
             InlineKeyboardButton("4 (x10)", callback_data=f"bet_parity_{round_id}_4"),
             InlineKeyboardButton("5 (x10)", callback_data=f"bet_parity_{round_id}_5")],
            [InlineKeyboardButton("6 (x10)", callback_data=f"bet_parity_{round_id}_6"),
             InlineKeyboardButton("7 (x10)", callback_data=f"bet_parity_{round_id}_7"),
             InlineKeyboardButton("8 (x10)", callback_data=f"bet_parity_{round_id}_8")],
            [InlineKeyboardButton("9 (x10)", callback_data=f"bet_parity_{round_id}_9")],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])
        message_text = f"**🎲 Parity/Evens & Number Prediction Game**\n\n" \
                       f"**Round ID**: `{round_id}`\n" \
                       f"**Time Left**: {time_left} seconds\n\n" \
                       "Choose even/odd or predict a number (0-9) and amount to bet. Example: `/bet even 10` or `/bet 7 5`"
    elif game_type == 'number_prediction':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("0 (x9)", callback_data=f"bet_number_prediction_{round_id}_0"),
             InlineKeyboardButton("1 (x9)", callback_data=f"bet_number_prediction_{round_id}_1"),
             InlineKeyboardButton("2 (x9)", callback_data=f"bet_number_prediction_{round_id}_2")],
            [InlineKeyboardButton("3 (x9)", callback_data=f"bet_number_prediction_{round_id}_3"),
             InlineKeyboardButton("4 (x9)", callback_data=f"bet_number_prediction_{round_id}_4"),
             InlineKeyboardButton("5 (x9)", callback_data=f"bet_number_prediction_{round_id}_5")],
            [InlineKeyboardButton("6 (x9)", callback_data=f"bet_number_prediction_{round_id}_6"),
             InlineKeyboardButton("7 (x9)", callback_data=f"bet_number_prediction_{round_id}_7"),
             InlineKeyboardButton("8 (x9)", callback_data=f"bet_number_prediction_{round_id}_8")],
            [InlineKeyboardButton("9 (x9)", callback_data=f"bet_number_prediction_{round_id}_9")],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])
        message_text = f"**🔢 Number Prediction Game**\n\n" \
                       f"**Round ID**: `{round_id}`\n" \
                       f"**Time Left**: {time_left} seconds\n\n" \
                       "Predict a number (0-9) and amount to bet. Example: `/bet number 7 5`"
    elif game_type == 'wheel_spin':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Red (x2)", callback_data=f"bet_wheel_spin_{round_id}_red"),
             InlineKeyboardButton("Green (x2)", callback_data=f"bet_wheel_spin_{round_id}_green"),
             InlineKeyboardButton("Blue (x2)", callback_data=f"bet_wheel_spin_{round_id}_blue")],
            [InlineKeyboardButton("x5 Multiplier", callback_data=f"bet_wheel_spin_{round_id}_x5")],
            [InlineKeyboardButton("x10 Multiplier", callback_data=f"bet_wheel_spin_{round_id}_x10")],
            [InlineKeyboardButton("x20 Multiplier", callback_data=f"bet_wheel_spin_{round_id}_x20")],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])
        message_text = f"**🎡 Wheel Spin Game**\n\n" \
                       f"**Round ID**: `{round_id}`\n" \
                       f"**Time Left**: {time_left} seconds\n\n" \
                       "Choose your bet and amount. Example: `/bet wheel red 10`"
    elif game_type == 'lucky_7':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Sum < 7 (x2)", callback_data=f"bet_lucky_7_{round_id}_less_than_7")],
            [InlineKeyboardButton("Sum = 7 (x5)", callback_data=f"bet_lucky_7_{round_id}_equal_to_7")],
            [InlineKeyboardButton("Sum > 7 (x2)", callback_data=f"bet_lucky_7_{round_id}_greater_than_7")],
            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])
        message_text = f"**🍀 Lucky 7 Game**\n\n" \
                       f"**Round ID**: `{round_id}`\n" \
                       f"**Time Left**: {time_left} seconds\n\n" \
                       "Predict the sum of two dice rolls and amount to bet. Example: `/bet lucky less_than_7 10`"
    else:
        await callback_query.answer("Game type not supported.", show_alert=True)
        return

    await callback_query.message.edit_text(message_text, reply_markup=keyboard, parse_mode="Markdown")

@Client.on_message(filters.command("bet"))
async def bet_command(client: Client, message):
    user_id = message.from_user.id
    user = User.objects(user_id=user_id).first()

    if not user:
        await client.send_message(user_id, "Please /start the bot first.")
        return

    if len(message.command) < 3:
        await client.send_message(user_id, "Usage: `/bet <game_type> <bet_value> <amount>`\nExample: `/bet color red 10` or `/bet parity even 5` or `/bet number 7 5` or `/bet wheel red 10` or `/bet lucky less_than_7 10`")
        return

    game_type_str = message.command[1].lower()
    bet_value = message.command[2].lower()
    try:
        amount = float(message.command[3])
        if amount <= 0:
            raise ValueError
    except (ValueError, IndexError):
        await client.send_message(user_id, "Invalid amount. Please enter a positive number.")
        return

    game_instance = await game_manager.get_game_instance(game_type_str)
    if not game_instance:
        await client.send_message(user_id, "Invalid game type. Available: `color`, `parity`, `number_prediction`, `wheel_spin`, `lucky_7`")
        return

    current_round_info = await game_manager.get_current_round_info(game_type_str)
    if not current_round_info:
        await client.send_message(user_id, "No active round for this game. Please wait for the next round.")
        return

    round_id = current_round_info['round_id']

    success, msg = await game_instance.place_bet(user_id, round_id, game_type_str, bet_value, amount)

@Client.on_callback_query(filters.regex("^game_number_prediction$"))
async def game_number_prediction_callback(client: Client, callback_query):
    game_manager = GameManager()
    game_type = "number_prediction"
    current_round = game_manager.get_game_instance(game_type).current_round

    if current_round and current_round.status == 'active':
        text = f"**🔢 Number Prediction Game - Round {current_round.round_number}**\n\n" \
               f"Time remaining: {int((current_round.end_time - datetime.now()).total_seconds())} seconds\n" \
               f"Predict a number from 0-9!"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("0", callback_data=f"bet_{game_type}_{current_round.round_id}_0"),
             InlineKeyboardButton("1", callback_data=f"bet_{game_type}_{current_round.round_id}_1"),
             InlineKeyboardButton("2", callback_data=f"bet_{game_type}_{current_round.round_id}_2"),
             InlineKeyboardButton("3", callback_data=f"bet_{game_type}_{current_round.round_id}_3"),
             InlineKeyboardButton("4", callback_data=f"bet_{game_type}_{current_round.round_id}_4")],
            [InlineKeyboardButton("5", callback_data=f"bet_{game_type}_{current_round.round_id}_5"),
             InlineKeyboardButton("6", callback_data=f"bet_{game_type}_{current_round.round_id}_6"),
             InlineKeyboardButton("7", callback_data=f"bet_{game_type}_{current_round.round_id}_7"),
             InlineKeyboardButton("8", callback_data=f"bet_{game_type}_{current_round.round_id}_8"),
             InlineKeyboardButton("9", callback_data=f"bet_{game_type}_{current_round.round_id}_9")],

            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])
    else:
        text = "No active Number Prediction game round. Please wait for the next round."
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])

    await callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^game_wheel_spin$"))
async def game_wheel_spin_callback(client: Client, callback_query):
    game_manager = GameManager()
    game_type = "wheel_spin"
    current_round = game_manager.get_game_instance(game_type).current_round

    if current_round and current_round.status == 'active':
        text = f"**🎡 Wheel Spin Game - Round {current_round.round_number}**\n\n" \
               f"Time remaining: {int((current_round.end_time - datetime.now()).total_seconds())} seconds\n" \
               f"Spin the wheel! Choose your bet:"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Red (2x)", callback_data=f"bet_{game_type}_{current_round.round_id}_red"),
             InlineKeyboardButton("Green (2x)", callback_data=f"bet_{game_type}_{current_round.round_id}_green"),
             InlineKeyboardButton("Blue (2x)", callback_data=f"bet_{game_type}_{current_round.round_id}_blue")],
            [InlineKeyboardButton("x5 Multiplier", callback_data=f"bet_{game_type}_{current_round.round_id}_x5")],
            [InlineKeyboardButton("x10 Multiplier", callback_data=f"bet_{game_type}_{current_round.round_id}_x10")],
            [InlineKeyboardButton("x20 Multiplier", callback_data=f"bet_{game_type}_{current_round.round_id}_x20")],

            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])
    else:
        text = "No active Wheel Spin game round. Please wait for the next round."
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])

    await callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    await callback_query.answer()

@Client.on_callback_query(filters.regex("^game_lucky_7$"))
async def game_lucky_7_callback(client: Client, callback_query):
    game_manager = GameManager()
    game_type = "lucky_7"
    current_round = game_manager.get_game_instance(game_type).current_round

    if current_round and current_round.status == 'active':
        text = f"**🍀 Lucky 7 Game - Round {current_round.round_number}**\n\n" \
               f"Time remaining: {int((current_round.end_time - datetime.now()).total_seconds())} seconds\n" \
               f"Roll two dice! Predict the sum:"
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Sum < 7 (x2)", callback_data=f"bet_{game_type}_{current_round.round_id}_less_than_7")],
            [InlineKeyboardButton("Sum = 7 (x5)", callback_data=f"bet_{game_type}_{current_round.round_id}_equal_to_7")],
            [InlineKeyboardButton("Sum > 7 (x2)", callback_data=f"bet_{game_type}_{current_round.round_id}_greater_than_7")],

            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])
    else:
        text = "No active Lucky 7 game round. Please wait for the next round."
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Games", callback_data="games_menu")]
        ])

    await callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    await callback_query.answer()
    await client.send_message(user_id, msg)

@Client.on_callback_query(filters.regex("^bet_"))
async def inline_bet_callback(client: Client, callback_query):
    # Format: bet_gameType_roundId_betValue
    parts = callback_query.data.split('_')
    if len(parts) < 4:
        await callback_query.answer("Invalid bet data.", show_alert=True)
        return

    # Determine game_type_str, round_id_str, and bet_value based on the callback data structure
    if callback_query.data.startswith("bet_color_"):
        game_type_str = "color_prediction"
        _, _, round_id_str, bet_value = parts
    elif callback_query.data.startswith("bet_parity_"):
        game_type_str = "parity_evens"
        _, _, round_id_str, bet_value = parts
    elif callback_query.data.startswith("bet_number_prediction_"):
        game_type_str = "number_prediction"
        _, _, _, round_id_str, bet_value = parts
    elif callback_query.data.startswith("bet_wheel_spin_"):
        game_type_str = "wheel_spin"
        _, _, _, round_id_str, bet_value = parts
    elif callback_query.data.startswith("bet_lucky_7_"):
        game_type_str = "lucky_7"
        _, _, _, round_id_str, bet_value = parts
    else:
         await callback_query.answer("Invalid game type in bet data.", show_alert=True)
         return
    bet_value = parts[-1]
    user_id = callback_query.from_user.id

    try:
        round_id = int(round_id_str)
    except ValueError:
        await callback_query.answer("Invalid round ID.", show_alert=True)
        return

    # Prompt user for amount
    await callback_query.message.reply_text(
        f"You selected to bet on **{bet_value.upper()}** for **{game_type_str.replace('_', ' ').title()}** (Round {round_id}).\n" \
        "Please reply to this message with the amount you want to bet.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="cancel_bet")]
        ])
    )
    # Store context for the next message (amount input)
    client.bet_context[user_id] = {
        "game_type": game_type_str,
        "round_id": round_id,
        "bet_value": bet_value,
        "message_id": callback_query.message.id # To edit the original message later
    }

@Client.on_message(filters.text & filters.private & filters.reply)
async def handle_bet_amount_reply(client: Client, message):
    user_id = message.from_user.id

    if user_id not in client.bet_context:
        return # Not a reply to a bet prompt

    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("Invalid amount. Please enter a positive number.")
        return

    context = client.bet_context.pop(user_id) # Remove context after use
    game_type_str = context["game_type"]
    round_id = context["round_id"]
    bet_value = context["bet_value"]
    original_message_id = context["message_id"]

    user = User.objects(user_id=user_id).first()
    if not user:
        await message.reply_text("Please /start the bot first.")
        return

    game_instance = await game_manager.get_game_instance(game_type_str)
    if not game_instance:
        await message.reply_text("Invalid game type.")
        return

    success, msg = await game_instance.place_bet(user_id, round_id, game_type_str, bet_value, amount)
    await message.reply_text(msg)

    # Optionally, edit the original message to show bet confirmation or remove prompt
    # await client.edit_message_text(user_id, original_message_id, f"Bet placed: {msg}")

@Client.on_callback_query(filters.regex("^cancel_bet$"))
async def cancel_bet_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in client.bet_context:
        del client.bet_context[user_id]
    await callback_query.message.edit_text("Betting process cancelled.")

@Client.on_callback_query(filters.regex("^wallet_menu$"))
async def wallet_menu_callback(client: Client, callback_query):
    await callback_query.message.edit_text(
        "**💰 Wallet Management**\n\n" \
        "Here you can manage your funds.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Deposit", callback_data="deposit_start")],
            [InlineKeyboardButton("➖ Withdraw", callback_data="withdraw_start")],
            [InlineKeyboardButton("📜 Transaction History", callback_data="history_transactions")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^deposit_start$"))
async def deposit_start_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    await callback_query.message.edit_text(
        "**➕ Deposit Funds**\n\n" \
        "To deposit, please send the amount to one of our payment methods (e.g., bKash, Nagad, Rocket, PayPal). " \
        "Then, reply to this message with the **Transaction ID** and **Amount** (e.g., `TXN12345 100.00`). " \
        "You can also attach a screenshot for faster approval.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel Deposit", callback_data="cancel_deposit")]
        ]),
        parse_mode="Markdown"
    )
    client.deposit_context[user_id] = {"state": "waiting_for_deposit_info", "message_id": callback_query.message.id}

@Client.on_message(filters.text & filters.private & filters.reply)
async def handle_deposit_info_reply(client: Client, message):
    user_id = message.from_user.id

    if user_id not in client.deposit_context or client.deposit_context[user_id]["state"] != "waiting_for_deposit_info":
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text("Invalid format. Please provide Transaction ID and Amount (e.g., `TXN12345 100.00`).")
        return

    transaction_id = parts[0]
    try:
        amount = float(parts[1])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("Invalid amount. Please enter a positive number.")
        return

    # Assuming payment method is manual for now, can be extended
    payment_method = "Manual Transfer"
    screenshot_proof = None # Will be handled if a photo is sent

    success, msg = await deposit_manager.create_deposit_request(user_id, amount, payment_method, transaction_id, screenshot_proof)
    await message.reply_text(msg)
    del client.deposit_context[user_id]

@Client.on_callback_query(filters.regex("^cancel_deposit$"))
async def cancel_deposit_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in client.deposit_context:
        del client.deposit_context[user_id]
    await callback_query.message.edit_text("Deposit process cancelled.")

@Client.on_callback_query(filters.regex("^withdraw_start$"))
async def withdraw_start_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    user = User.objects(user_id=user_id).first()

    if not user:
        await callback_query.answer("Please /start the bot first.", show_alert=True)
        return

    await callback_query.message.edit_text(
        f"**➖ Withdraw Funds**\n\n" \
        f"Your current balance: {user.balance:.2f}\n" \
        f"Minimum withdrawal amount: {WithdrawalManager.MIN_WITHDRAWAL_BALANCE:.2f}\n\n" \
        "Please reply to this message with the **Amount** and your **Payment Method/Address** (e.g., `50.00 bKash 01XXXXXXXXX`).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel Withdrawal", callback_data="cancel_withdraw")]
        ]),
        parse_mode="Markdown"
    )
    client.withdraw_context[user_id] = {"state": "waiting_for_withdraw_info", "message_id": callback_query.message.id}

@Client.on_message(filters.text & filters.private & filters.reply)
async def handle_withdraw_info_reply(client: Client, message):
    user_id = message.from_user.id

    if user_id not in client.withdraw_context or client.withdraw_context[user_id]["state"] != "waiting_for_withdraw_info":
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text("Invalid format. Please provide Amount, Payment Method, and Address (e.g., `50.00 bKash 01XXXXXXXXX`).")
        return

    try:
        amount = float(parts[0])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("Invalid amount. Please enter a positive number.")
        return

    payment_method = parts[1]
    payment_address = parts[2]

    success, msg = await withdrawal_manager.create_withdrawal_request(user_id, amount, payment_method, payment_address)
    await message.reply_text(msg)
    del client.withdraw_context[user_id]

@Client.on_callback_query(filters.regex("^cancel_withdraw$"))
async def cancel_withdraw_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in client.withdraw_context:
        del client.withdraw_context[user_id]
    await callback_query.message.edit_text("Withdrawal process cancelled.")

@Client.on_callback_query(filters.regex("^history_transactions$"))
async def history_transactions_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    user = User.objects(user_id=user_id).first()

    if not user:
        await callback_query.answer("Please /start the bot first.", show_alert=True)
        return

    transactions = Transaction.objects(user=user).order_by('-created_at').limit(10) # Last 10 transactions

    if not transactions:
        await callback_query.message.edit_text("You have no transaction history yet.",
                                              reply_markup=InlineKeyboardMarkup([
                                                  [InlineKeyboardButton("🔙 Back to Wallet", callback_data="wallet_menu")]
                                              ]))
        return

    history_text = "**📜 Your Last 10 Transactions**\n\n"
    for txn in transactions:
        history_text += f"**Type**: {txn.transaction_type.title()}\n" \
                        f"**Amount**: {txn.amount:.2f}\n" \
                        f"**Status**: {txn.status.title()}\n" \
                        f"**Date**: {txn.created_at.strftime('%Y-%m-%d %H:%M')}\n" \
                        f"---\n"

    await callback_query.message.edit_text(history_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup([
                                              [InlineKeyboardButton("🔙 Back to Wallet", callback_data="wallet_menu")]
                                          ]))

@Client.on_callback_query(filters.regex("^profile_menu$"))
async def profile_menu_callback(client: Client, callback_query):
    await callback_query.message.edit_text(
        "**📊 Profile & Stats**\n\n" \
        "Explore your personal details and game statistics.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 View Profile", callback_data="view_profile")],
            [InlineKeyboardButton("🏆 Leaderboards", callback_data="leaderboards_menu")],
            [InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^view_profile$"))
async def view_profile_callback(client: Client, callback_query):
    # Re-use the logic from profile_command
    message = callback_query.message
    message.from_user = callback_query.from_user # Hack to make it work with existing command
    await profile_command(client, message)

@Client.on_callback_query(filters.regex("^leaderboards_menu$"))
async def leaderboards_menu_callback(client: Client, callback_query):
    await callback_query.message.edit_text(
        "**🏆 Leaderboards**\n\n" \
        "See who's on top!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Weekly", callback_data="leaderboard_weekly")],
            [InlineKeyboardButton("Monthly", callback_data="leaderboard_monthly")],
            [InlineKeyboardButton("All-Time", callback_data="leaderboard_all_time")],
            [InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_menu")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^leaderboard_"))
async def leaderboard_callback(client: Client, callback_query):
    period = callback_query.data.replace("leaderboard_", "")
    
    leaderboard_entries = []
    if period == "weekly":
        leaderboard_entries = Leaderboard.objects().order_by('-weekly_earnings').limit(10)
    elif period == "monthly":
        leaderboard_entries = Leaderboard.objects().order_by('-monthly_earnings').limit(10)
    elif period == "all_time":
        leaderboard_entries = Leaderboard.objects().order_by('-all_time_earnings').limit(10)

    if not leaderboard_entries:
        await callback_query.message.edit_text(f"No {period.title()} leaderboard data yet.",
                                              reply_markup=InlineKeyboardMarkup([
                                                  [InlineKeyboardButton("🔙 Back to Leaderboards", callback_data="leaderboards_menu")]
                                              ]))
        return

    leaderboard_text = f"**🏆 {period.title()} Leaderboard**\n\n"
    for i, entry in enumerate(leaderboard_entries):
        user = User.objects(id=entry.user.id).first()
        if user:
            earnings = getattr(entry, f"{period}_earnings", 0.0)
            leaderboard_text += f"{i+1}. @{user.username or user.first_name} - {earnings:.2f}\n"

    await callback_query.message.edit_text(leaderboard_text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup([
                                              [InlineKeyboardButton("🔙 Back to Leaderboards", callback_data="leaderboards_menu")]
                                          ]))

@Client.on_callback_query(filters.regex("^daily_bonus$"))
async def daily_bonus_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    user = User.objects(user_id=user_id).first()

    if not user:
        await callback_query.answer("Please /start the bot first.", show_alert=True)
        return

    daily_bonus_entry = DailyBonus.objects(user=user).first()
    if not daily_bonus_entry:
        daily_bonus_entry = DailyBonus(user=user, last_claimed=datetime.min, streak_count=0)
        daily_bonus_entry.save()

    now = datetime.utcnow()
    last_claimed_date = daily_bonus_entry.last_claimed.date()
    today_date = now.date()

    if last_claimed_date == today_date:
        await callback_query.answer("You have already claimed your daily bonus today!", show_alert=True)
        return

    bonus_amount = 10.0 # Base daily bonus
    streak_bonus_multiplier = 1.0

    if last_claimed_date == today_date - timedelta(days=1):
        daily_bonus_entry.streak_count += 1
        streak_bonus_multiplier = 1 + (daily_bonus_entry.streak_count * 0.1) # 10% extra per streak day
        bonus_amount *= streak_bonus_multiplier
        msg = f"You claimed your daily bonus of {bonus_amount:.2f}! Your streak is now {daily_bonus_entry.streak_count} days!"
    else:
        daily_bonus_entry.streak_count = 1
        msg = f"You claimed your daily bonus of {bonus_amount:.2f}! Start a new streak!"

    user.balance += bonus_amount
    daily_bonus_entry.last_claimed = now
    user.save()
    daily_bonus_entry.save()

    await callback_query.answer(msg, show_alert=True)
    await callback_query.message.edit_text(f"**🎁 Daily Bonus**\n\n{msg}\nYour new balance: {user.balance:.2f}",
                                          reply_markup=InlineKeyboardMarkup([
                                              [InlineKeyboardButton("🔙 Back to Profile", callback_data="profile_menu")]
                                          ]),
                                          parse_mode="Markdown")

@Client.on_callback_query(filters.regex("^main_menu$"))
async def main_menu_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    user = User.objects(user_id=user_id).first()
    if not user:
        await callback_query.answer("Please /start the bot first.", show_alert=True)
        return

    await callback_query.message.edit_text(f"Welcome back, {user.first_name}! How can I help you today?",
                                  reply_markup=InlineKeyboardMarkup([
                                      [InlineKeyboardButton("🎮 Play Games", callback_data="games_menu")],
                                      [InlineKeyboardButton("💰 Wallet", callback_data="wallet_menu")],
                                      [InlineKeyboardButton("📊 Profile & History", callback_data="profile_menu")]
                                  ]))

# Add a dictionary to store temporary bet context for users
# This should ideally be handled by a more robust state management system or database
# For simplicity, adding it directly to the client instance
Client.bet_context = {}
Client.deposit_context = {}
Client.withdraw_context = {}

# Connect to DB when the bot starts
connect_db()

# Start all games when the bot starts
asyncio.create_task(game_manager.start_all_games())

print("User commands loaded.")
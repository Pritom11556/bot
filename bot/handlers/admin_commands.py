from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import User, Transaction, GameRound
from admin.admin_panel import AdminPanel
from config import ADMIN_IDS

admin_panel = AdminPanel()

@Client.on_message(filters.command("admin") & filters.private)
async def admin_menu_command(client: Client, message):
    if not await admin_panel.is_admin(message.from_user.id):
        await message.reply_text("You are not authorized to access the admin panel.")
        return

    await message.reply_text(
        "**⚙️ Admin Panel**\n\n" \
        "Welcome, Admin! Choose an action:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 View Analytics", callback_data="admin_analytics")],
            [InlineKeyboardButton("💰 Manage Payments", callback_data="admin_payments")],
            [InlineKeyboardButton("🎮 Manage Games", callback_data="admin_games")],
            [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")],
            [InlineKeyboardButton("📣 Broadcast Message", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🛠️ Set Maintenance Mode", callback_data="admin_maintenance")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^admin_analytics$"))
async def admin_analytics_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    analytics = await admin_panel.get_analytics()
    text = f"**📊 System Analytics**\n\n" \
           f"**Total Users**: {analytics['total_users']}\n" \
           f"**Total Bets**: {analytics['total_bets']}\n" \
           f"**Total Revenue (Simplified)**: {analytics['total_revenue']:.2f}\n" \
           f"**Active Users (Last 7 Days)**: {analytics['active_users_last_7_days']}"

    await callback_query.message.edit_text(text, parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup([
                                              [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_menu")]
                                          ]))

@Client.on_callback_query(filters.regex("^admin_payments$"))
async def admin_payments_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    await callback_query.message.edit_text(
        "**💰 Payment Management**\n\n" \
        "Review and approve deposits/withdrawals.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Pending Deposits", callback_data="admin_pending_deposits")],
            [InlineKeyboardButton("📤 Pending Withdrawals", callback_data="admin_pending_withdrawals")],
            [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_menu")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^admin_pending_deposits$"))
async def admin_pending_deposits_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    pending_deposits = Transaction.objects(transaction_type='deposit', status='pending').all()

    if not pending_deposits:
        await callback_query.message.edit_text("No pending deposit requests.",
                                              reply_markup=InlineKeyboardMarkup([
                                                  [InlineKeyboardButton("🔙 Back to Payment Management", callback_data="admin_payments")]
                                              ]))
        return

    for deposit in pending_deposits:
        user = User.objects(id=deposit.user.id).first()
        text = f"**📥 Pending Deposit Request**\n\n" \
               f"**User**: {user.first_name} (@{user.username or 'N/A'}) (ID: {user.user_id})\n" \
               f"**Amount**: {deposit.amount:.2f}\n" \
               f"**Method**: {deposit.payment_method}\n" \
               f"**Txn ID**: `{deposit.transaction_id}`\n" \
               f"**Date**: {deposit.created_at.strftime('%Y-%m-%d %H:%M')}"
        
        if deposit.screenshot_proof:
            text += f"\n[Screenshot Proof]({deposit.screenshot_proof})"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_deposit_{deposit.transaction_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_deposit_{deposit.transaction_id}")]
        ])
        await client.send_message(callback_query.from_user.id, text, reply_markup=keyboard, parse_mode="Markdown")
    
    await callback_query.answer("Displayed pending deposit requests.")

@Client.on_callback_query(filters.regex("^approve_deposit_"))
async def approve_deposit_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    transaction_id = callback_query.data.replace("approve_deposit_", "")
    from payments.deposit import DepositManager
    deposit_manager = DepositManager()
    success, msg = await deposit_manager.approve_deposit(transaction_id, callback_query.from_user.id)
    await callback_query.message.edit_text(f"Deposit {transaction_id}: {msg}")
    await callback_query.answer(msg, show_alert=True)

@Client.on_callback_query(filters.regex("^reject_deposit_"))
async def reject_deposit_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    transaction_id = callback_query.data.replace("reject_deposit_", "")
    from payments.deposit import DepositManager
    deposit_manager = DepositManager()
    success, msg = await deposit_manager.reject_deposit(transaction_id, callback_query.from_user.id)
    await callback_query.message.edit_text(f"Deposit {transaction_id}: {msg}")
    await callback_query.answer(msg, show_alert=True)

@Client.on_callback_query(filters.regex("^admin_pending_withdrawals$"))
async def admin_pending_withdrawals_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    pending_withdrawals = Transaction.objects(transaction_type='withdrawal', status='pending').all()

    if not pending_withdrawals:
        await callback_query.message.edit_text("No pending withdrawal requests.",
                                              reply_markup=InlineKeyboardMarkup([
                                                  [InlineKeyboardButton("🔙 Back to Payment Management", callback_data="admin_payments")]
                                              ]))
        return

    for withdrawal in pending_withdrawals:
        user = User.objects(id=withdrawal.user.id).first()
        text = f"**📤 Pending Withdrawal Request**\n\n" \
               f"**User**: {user.first_name} (@{user.username or 'N/A'}) (ID: {user.user_id})\n" \
               f"**Amount**: {withdrawal.amount:.2f}\n" \
               f"**Method**: {withdrawal.payment_method}\n" \
               f"**Address**: {withdrawal.screenshot_proof} " \
               f"**Txn ID**: `{withdrawal.transaction_id}`\n" \
               f"**Date**: {withdrawal.created_at.strftime('%Y-%m-%d %H:%M')}"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Approve", callback_data=f"approve_withdrawal_{withdrawal.transaction_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"reject_withdrawal_{withdrawal.transaction_id}")]
        ])
        await client.send_message(callback_query.from_user.id, text, reply_markup=keyboard, parse_mode="Markdown")
    
    await callback_query.answer("Displayed pending withdrawal requests.")

@Client.on_callback_query(filters.regex("^approve_withdrawal_"))
async def approve_withdrawal_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    transaction_id = callback_query.data.replace("approve_withdrawal_", "")
    from payments.withdrawal import WithdrawalManager
    withdrawal_manager = WithdrawalManager()
    success, msg = await withdrawal_manager.approve_withdrawal(transaction_id, callback_query.from_user.id)
    await callback_query.message.edit_text(f"Withdrawal {transaction_id}: {msg}")
    await callback_query.answer(msg, show_alert=True)

@Client.on_callback_query(filters.regex("^reject_withdrawal_"))
async def reject_withdrawal_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    transaction_id = callback_query.data.replace("reject_withdrawal_", "")
    from payments.withdrawal import WithdrawalManager
    withdrawal_manager = WithdrawalManager()
    success, msg = await withdrawal_manager.reject_withdrawal(transaction_id, callback_query.from_user.id)
    await callback_query.message.edit_text(f"Withdrawal {transaction_id}: {msg}")
    await callback_query.answer(msg, show_alert=True)

@Client.on_callback_query(filters.regex("^admin_games$"))
async def admin_games_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    await callback_query.message.edit_text(
        "**🎮 Game Management**\n\n" \
        "Control game results and settings.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎲 Set Game Result", callback_data="admin_set_game_result")],
            [InlineKeyboardButton("⚙️ Update Game Settings", callback_data="admin_update_game_settings")],
            [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_menu")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^admin_set_game_result$"))
async def admin_set_game_result_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    await callback_query.message.edit_text(
        "**🎲 Set Game Result**\n\n" \
        "Reply to this message with `game_type round_id result` (e.g., `color_prediction 123 red`).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="admin_cancel_action")]
        ]),
        parse_mode="Markdown"
    )
    client.admin_context[callback_query.from_user.id] = {"state": "waiting_for_game_result", "message_id": callback_query.message.id}

@Client.on_message(filters.text & filters.private & filters.reply)
async def handle_admin_reply(client: Client, message):
    user_id = message.from_user.id
    if user_id not in client.admin_context:
        return

    context = client.admin_context[user_id]

    if context["state"] == "waiting_for_game_result":
        parts = message.text.split()
        if len(parts) != 3:
            await message.reply_text("Invalid format. Usage: `game_type round_id result`")
            return
        
        game_type, round_id_str, result = parts
        try:
            round_id = int(round_id_str)
        except ValueError:
            await message.reply_text("Invalid round ID.")
            return

        success = await admin_panel.set_game_result(round_id, game_type, result)
        if success:
            await message.reply_text(f"Game result for Round {round_id} ({game_type}) set to {result}.")
        else:
            await message.reply_text(f"Failed to set game result for Round {round_id} ({game_type}).")
        del client.admin_context[user_id]

    elif context["state"] == "waiting_for_broadcast_message":
        broadcast_message = message.text
        users = User.objects().all()
        for user in users:
            try:
                await client.send_message(user.user_id, f"**📣 Admin Broadcast:**\n\n{broadcast_message}", parse_mode="Markdown")
            except Exception as e:
                print(f"Failed to send broadcast to {user.user_id}: {e}")
        await message.reply_text("Broadcast message sent to all users.")
        del client.admin_context[user_id]

    elif context["state"] == "waiting_for_add_funds":
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply_text("Invalid format. Usage: `user_id amount`")
            return
        try:
            target_user_id = int(parts[0])
            amount = float(parts[1])
            if amount <= 0:
                raise ValueError
        except ValueError:
            await message.reply_text("Invalid user ID or amount.")
            return
        
        success = await admin_panel.add_funds(target_user_id, amount)
        if success:
            await message.reply_text(f"Successfully added {amount} to user {target_user_id}'s balance.")
        else:
            await message.reply_text(f"Failed to add funds to user {target_user_id}. User not found?")
        del client.admin_context[user_id]

    elif context["state"] == "waiting_for_remove_funds":
        parts = message.text.split()
        if len(parts) != 2:
            await message.reply_text("Invalid format. Usage: `user_id amount`")
            return
        try:
            target_user_id = int(parts[0])
            amount = float(parts[1])
            if amount <= 0:
                raise ValueError
        except ValueError:
            await message.reply_text("Invalid user ID or amount.")
            return
        
        success = await admin_panel.remove_funds(target_user_id, amount)
        if success:
            await message.reply_text(f"Successfully removed {amount} from user {target_user_id}'s balance.")
        else:
            await message.reply_text(f"Failed to remove funds from user {target_user_id}. User not found or insufficient balance?")
        del client.admin_context[user_id]

    elif context["state"] == "waiting_for_ban_user":
        try:
            target_user_id = int(message.text)
        except ValueError:
            await message.reply_text("Invalid user ID.")
            return
        success = await admin_panel.ban_user(target_user_id)
        if success:
            await message.reply_text(f"User {target_user_id} has been banned.")
        else:
            await message.reply_text(f"Failed to ban user {target_user_id}.")
        del client.admin_context[user_id]

    elif context["state"] == "waiting_for_unban_user":
        try:
            target_user_id = int(message.text)
        except ValueError:
            await message.reply_text("Invalid user ID.")
            return
        success = await admin_panel.unban_user(target_user_id)
        if success:
            await message.reply_text(f"User {target_user_id} has been unbanned.")
        else:
            await message.reply_text(f"Failed to unban user {target_user_id}.")
        del client.admin_context[user_id]

    elif context["state"] == "waiting_for_add_admin":
        try:
            target_user_id = int(message.text)
        except ValueError:
            await message.reply_text("Invalid user ID.")
            return
        success = await admin_panel.add_admin(target_user_id)
        if success:
            await message.reply_text(f"User {target_user_id} has been made an admin.")
        else:
            await message.reply_text(f"Failed to make user {target_user_id} an admin. User not found?")
        del client.admin_context[user_id]

    elif context["state"] == "waiting_for_remove_admin":
        try:
            target_user_id = int(message.text)
        except ValueError:
            await message.reply_text("Invalid user ID.")
            return
        success = await admin_panel.remove_admin(target_user_id)
        if success:
            await message.reply_text(f"User {target_user_id} has been removed from admin.")
        else:
            await message.reply_text(f"Failed to remove user {target_user_id} from admin. User not found or not an admin?")
        del client.admin_context[user_id]

@Client.on_callback_query(filters.regex("^admin_users$"))
async def admin_users_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    await callback_query.message.edit_text(
        "**👥 User Management**\n\n" \
        "Manage user accounts.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add/Remove Funds", callback_data="admin_manage_funds")],
            [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user")],
            [InlineKeyboardButton("✅ Unban User", callback_data="admin_unban_user")],
            [InlineKeyboardButton("👑 Add Admin", callback_data="admin_add_admin")],
            [InlineKeyboardButton("🗑️ Remove Admin", callback_data="admin_remove_admin")],
            [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_menu")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^admin_manage_funds$"))
async def admin_manage_funds_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    await callback_query.message.edit_text(
        "**💰 Manage User Funds**\n\n" \
        "Choose an action: ",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Funds", callback_data="admin_add_funds")],
            [InlineKeyboardButton("➖ Remove Funds", callback_data="admin_remove_funds")],
            [InlineKeyboardButton("🔙 Back to User Management", callback_data="admin_users")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^admin_add_funds$"))
async def admin_add_funds_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    await callback_query.message.edit_text(
        "**➕ Add Funds**\n\n" \
        "Reply to this message with `user_id amount` (e.g., `123456789 100.00`).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="admin_cancel_action")]
        ]),
        parse_mode="Markdown"
    )
    client.admin_context[callback_query.from_user.id] = {"state": "waiting_for_add_funds", "message_id": callback_query.message.id}

@Client.on_callback_query(filters.regex("^admin_remove_funds$"))
async def admin_remove_funds_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    await callback_query.message.edit_text(
        "**➖ Remove Funds**\n\n" \
        "Reply to this message with `user_id amount` (e.g., `123456789 50.00`).",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="admin_cancel_action")]
        ]),
        parse_mode="Markdown"
    )
    client.admin_context[callback_query.from_user.id] = {"state": "waiting_for_remove_funds", "message_id": callback_query.message.id}

@Client.on_callback_query(filters.regex("^admin_ban_user$"))
async def admin_ban_user_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    await callback_query.message.edit_text(
        "**🚫 Ban User**\n\n" \
        "Reply to this message with the `user_id` to ban.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="admin_cancel_action")]
        ]),
        parse_mode="Markdown"
    )
    client.admin_context[callback_query.from_user.id] = {"state": "waiting_for_ban_user", "message_id": callback_query.message.id}

@Client.on_callback_query(filters.regex("^admin_unban_user$"))
async def admin_unban_user_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    await callback_query.message.edit_text(
        "**✅ Unban User**\n\n" \
        "Reply to this message with the `user_id` to unban.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="admin_cancel_action")]
        ]),
        parse_mode="Markdown"
    )
    client.admin_context[callback_query.from_user.id] = {"state": "waiting_for_unban_user", "message_id": callback_query.message.id}

@Client.on_callback_query(filters.regex("^admin_add_admin$"))
async def admin_add_admin_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    await callback_query.message.edit_text(
        "**👑 Add Admin**\n\n" \
        "Reply to this message with the `user_id` to make an admin.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="admin_cancel_action")]
        ]),
        parse_mode="Markdown"
    )
    client.admin_context[callback_query.from_user.id] = {"state": "waiting_for_add_admin", "message_id": callback_query.message.id}

@Client.on_callback_query(filters.regex("^admin_remove_admin$"))
async def admin_remove_admin_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    await callback_query.message.edit_text(
        "**🗑️ Remove Admin**\n\n" \
        "Reply to this message with the `user_id` to remove from admin.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="admin_cancel_action")]
        ]),
        parse_mode="Markdown"
    )
    client.admin_context[callback_query.from_user.id] = {"state": "waiting_for_remove_admin", "message_id": callback_query.message.id}

@Client.on_callback_query(filters.regex("^admin_broadcast$"))
async def admin_broadcast_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    await callback_query.message.edit_text(
        "**📣 Broadcast Message**\n\n" \
        "Reply to this message with the text you want to broadcast to all users.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="admin_cancel_action")]
        ]),
        parse_mode="Markdown"
    )
    client.admin_context[callback_query.from_user.id] = {"state": "waiting_for_broadcast_message", "message_id": callback_query.message.id}

@Client.on_callback_query(filters.regex("^admin_maintenance$"))
async def admin_maintenance_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return

    await callback_query.message.edit_text(
        "**🛠️ Maintenance Mode**\n\n" \
        "Toggle maintenance mode for the bot.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Enable Maintenance Mode", callback_data="admin_enable_maintenance")],
            [InlineKeyboardButton("❌ Disable Maintenance Mode", callback_data="admin_disable_maintenance")],
            [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_menu")]
        ]),
        parse_mode="Markdown"
    )

@Client.on_callback_query(filters.regex("^admin_enable_maintenance$"))
async def admin_enable_maintenance_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    success = await admin_panel.set_maintenance_mode(True)
    if success:
        await callback_query.message.edit_text("Maintenance mode **ENABLED**.",
                                              reply_markup=InlineKeyboardMarkup([
                                                  [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_menu")]
                                              ]))
    else:
        await callback_query.answer("Failed to enable maintenance mode.", show_alert=True)

@Client.on_callback_query(filters.regex("^admin_disable_maintenance$"))
async def admin_disable_maintenance_callback(client: Client, callback_query):
    if not await admin_panel.is_admin(callback_query.from_user.id):
        await callback_query.answer("Not authorized.", show_alert=True)
        return
    success = await admin_panel.set_maintenance_mode(False)
    if success:
        await callback_query.message.edit_text("Maintenance mode **DISABLED**.",
                                              reply_markup=InlineKeyboardMarkup([
                                                  [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_menu")]
                                              ]))
    else:
        await callback_query.answer("Failed to disable maintenance mode.", show_alert=True)

@Client.on_callback_query(filters.regex("^admin_cancel_action$"))
async def admin_cancel_action_callback(client: Client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in client.admin_context:
        del client.admin_context[user_id]
    await callback_query.message.edit_text("Admin action cancelled.",
                                          reply_markup=InlineKeyboardMarkup([
                                              [InlineKeyboardButton("🔙 Back to Admin Menu", callback_data="admin_menu")]
                                          ]))

@Client.on_callback_query(filters.regex("^admin_menu$"))
async def back_to_admin_menu_callback(client: Client, callback_query):
    await admin_menu_command(client, callback_query.message) # Re-use the admin_menu_command logic

# Add a dictionary to store temporary admin context for users
Client.admin_context = {}

print("Admin commands loaded.")
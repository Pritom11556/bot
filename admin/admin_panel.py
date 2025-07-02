from database.models import User, GameRound, Bet, Transaction
from database.db_manager import connect_db
from config import ADMIN_IDS
from datetime import datetime

class AdminPanel:
    def __init__(self):
        pass

    async def is_admin(self, user_id: int) -> bool:
        return user_id in ADMIN_IDS or User.objects(user_id=user_id, is_admin=True).first() is not None

    async def add_admin(self, user_id: int) -> bool:
        user = User.objects(user_id=user_id).first()
        if user:
            user.is_admin = True
            user.save()
            return True
        return False

    async def remove_admin(self, user_id: int) -> bool:
        user = User.objects(user_id=user_id).first()
        if user and user.is_admin:
            user.is_admin = False
            user.save()
            return True
        return False

    async def ban_user(self, user_id: int) -> bool:
        # Implement user banning logic (e.g., add a 'is_banned' field to User model)
        # For now, just a placeholder
        print(f"User {user_id} banned.")
        return True

    async def unban_user(self, user_id: int) -> bool:
        # Implement user unbanning logic
        print(f"User {user_id} unbanned.")
        return True

    async def get_analytics(self):
        total_users = User.objects.count()
        total_bets = Bet.objects.count()
        total_revenue = Bet.objects.sum('amount') # Sum of all bet amounts
        # This is a simplified revenue. Real revenue would be bets - payouts.

        # You might want to calculate active users based on recent activity
        active_users = User.objects(updated_at__gte=datetime.utcnow() - datetime.timedelta(days=7)).count()

        return {
            "total_users": total_users,
            "total_bets": total_bets,
            "total_revenue": total_revenue,
            "active_users_last_7_days": active_users
        }

    async def set_game_result(self, round_id: int, game_type: str, result: str) -> bool:
        game_round = GameRound.objects(round_id=round_id, game_type=game_type).first()
        if game_round:
            game_round.result = result
            game_round.is_manual_result = True
            game_round.save()
            # Trigger bet settlement for this round if it hasn't been settled
            return True
        return False

    async def add_funds(self, user_id: int, amount: float) -> bool:
        user = User.objects(user_id=user_id).first()
        if user:
            user.balance += amount
            user.save()
            # Log this transaction
            return True
        return False

    async def remove_funds(self, user_id: int, amount: float) -> bool:
        user = User.objects(user_id=user_id).first()
        if user and user.balance >= amount:
            user.balance -= amount
            user.save()
            # Log this transaction
            return True
        return False

    async def set_maintenance_mode(self, status: bool):
        # This would typically involve updating a setting in the database or a config file
        # that the bot checks before processing user commands.
        print(f"Maintenance mode set to: {status}")
        return True

# Example usage (for testing)
async def main():
    connect_db()
    admin_panel = AdminPanel()

    # Create a dummy admin user if not exists
    if not User.objects(user_id=ADMIN_IDS[0]).first():
        User(user_id=ADMIN_IDS[0], username="superadmin", is_admin=True, balance=1000.0).save()

    # Test analytics
    analytics = await admin_panel.get_analytics()
    print(f"Analytics: {analytics}")

    # Test adding/removing funds
    user_id_to_test = 12345
    if not User.objects(user_id=user_id_to_test).first():
        User(user_id=user_id_to_test, username="testuser_for_admin", balance=50.0).save()

    await admin_panel.add_funds(user_id_to_test, 100.0)
    user = User.objects(user_id=user_id_to_test).first()
    print(f"User {user_id_to_test} balance after add: {user.balance}")

    await admin_panel.remove_funds(user_id_to_test, 20.0)
    user = User.objects(user_id=user_id_to_test).first()
    print(f"User {user_id_to_test} balance after remove: {user.balance}")

    from mongoengine import disconnect
    disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
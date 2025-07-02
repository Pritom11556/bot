import random
from datetime import datetime, timedelta
from database.models import User, GameRound, Bet

class WheelSpinGame:
    def __init__(self):
        self.current_round = None
        self.round_duration = 60  # seconds for a round
        self.bet_cutoff = 10    # seconds before round ends to stop bets
        self.wheel_options = {
            "red": 2.0, "green": 2.0, "blue": 2.0, # Example colors with 2x payout
            "x5": 5.0, "x10": 10.0, "x20": 20.0 # Example multipliers
        }

    async def start_new_round(self, game_type: str):
        # End any existing round first
        if self.current_round and self.current_round.status == 'active':
            await self.end_round(game_type)

        round_number = await self._get_next_round_number(game_type)
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=self.round_duration)
        self.current_round = GameRound(
            game_type=game_type,
            round_number=round_number,
            start_time=start_time,
            end_time=end_time,
            status='active'
        )
        await self.current_round.commit()
        print(f"Started new {game_type} round {round_number}")
        return self.current_round

    async def _get_next_round_number(self, game_type: str):
        last_round = await GameRound.objects(game_type=game_type).order_by('-round_number').first()
        return (last_round.round_number + 1) if last_round else 1

    async def place_bet(self, user_id: int, round_id: str, predicted_option: str, amount: float):
        user = await User.objects(user_id=user_id).first()
        game_round = await GameRound.objects(id=round_id).first()

        if not user or not game_round:
            return False, "User or game round not found."

        if game_round.status != 'active':
            return False, "Current round is not active."

        if datetime.now() > game_round.end_time - timedelta(seconds=self.bet_cutoff):
            return False, "Betting for this round has closed."

        if user.balance < amount:
            return False, "Insufficient balance."

        if predicted_option not in self.wheel_options:
            return False, "Invalid wheel option."

        user.balance -= amount
        await user.commit()

        bet = Bet(
            user=user,
            game_round=game_round,
            bet_amount=amount,
            prediction=predicted_option,
            bet_time=datetime.now()
        )
        await bet.commit()
        return True, "Bet placed successfully."

    async def end_round(self, game_type: str):
        if not self.current_round or self.current_round.game_type != game_type or self.current_round.status != 'active':
            return False, "No active round to end for this game type."

        # Determine result (randomly pick an option from wheel_options)
        result = random.choice(list(self.wheel_options.keys()))
        self.current_round.result = result
        self.current_round.status = 'ended'
        await self.current_round.commit()

        await self._settle_bets(self.current_round)
        print(f"Ended {game_type} round {self.current_round.round_number} with result {result}")
        return True, f"Round {self.current_round.round_number} ended. Result: {result}"

    async def _settle_bets(self, game_round: GameRound):
        winning_bets = await Bet.objects(game_round=game_round, prediction=game_round.result).all()
        losing_bets = await Bet.objects(game_round=game_round, prediction__ne=game_round.result).all()

        # Payout for winning bets based on multiplier
        for bet in winning_bets:
            user = await User.objects(id=bet.user.id).first()
            if user:
                payout_multiplier = self.wheel_options.get(game_round.result, 1.0) # Default to 1x if not found
                winnings = bet.bet_amount * payout_multiplier
                user.balance += winnings
                await user.commit()
                bet.status = 'won'
                bet.winnings = winnings
                await bet.commit()
                print(f"User {user.user_id} won {winnings} in {game_round.game_type} round {game_round.round_number}")

        for bet in losing_bets:
            bet.status = 'lost'
            await bet.commit()

# Example Usage (for testing)
async def main():
    from database.db_manager import connect_db, disconnect_db

    await connect_db()

    # Clear existing data for clean test
    await User.objects.delete()
    await GameRound.objects.delete()
    await Bet.objects.delete()

    game = WheelSpinGame()
    game_type = "wheel_spin"

    # Create a test user
    user = User(user_id=12345, first_name="TestUser", username="testuser", balance=1000.0)
    await user.commit()

    # Start a new round
    current_round = await game.start_new_round(game_type)
    print(f"Current round ID: {current_round.id}")

    # Place some bets
    success, msg = await game.place_bet(user.user_id, current_round.id, "red", 100.0)
    print(f"Bet 1: {msg}")
    success, msg = await game.place_bet(user.user_id, current_round.id, "x5", 50.0)
    print(f"Bet 2: {msg}")

    # Simulate time passing and end the round
    # In a real bot, this would be triggered by a scheduler
    await asyncio.sleep(2) # Simulate some time
    success, msg = await game.end_round(game_type)
    print(msg)

    # Check user balance after settlement
    updated_user = await User.objects(user_id=user.user_id).first()
    print(f"Updated user balance: {updated_user.balance}")

    await disconnect_db()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
import random
from datetime import datetime, timedelta
from database.models import User, GameRound, Bet

class Lucky7Game:
    def __init__(self):
        self.current_round = None
        self.round_duration = 60  # seconds for a round
        self.bet_cutoff = 10    # seconds before round ends to stop bets

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

    async def place_bet(self, user_id: int, round_id: str, prediction_type: str, amount: float):
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

        if prediction_type not in ['less_than_7', 'equal_to_7', 'greater_than_7']:
            return False, "Invalid prediction type. Choose 'less_than_7', 'equal_to_7', or 'greater_than_7'."

        user.balance -= amount
        await user.commit()

        bet = Bet(
            user=user,
            game_round=game_round,
            bet_amount=amount,
            prediction=prediction_type,
            bet_time=datetime.now()
        )
        await bet.commit()
        return True, "Bet placed successfully."

    async def end_round(self, game_type: str):
        if not self.current_round or self.current_round.game_type != game_type or self.current_round.status != 'active':
            return False, "No active round to end for this game type."

        # Roll two dice (1-6) and sum them
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        result_sum = dice1 + dice2

        # Determine the result category
        if result_sum < 7:
            result_category = 'less_than_7'
        elif result_sum == 7:
            result_category = 'equal_to_7'
        else: # result_sum > 7
            result_category = 'greater_than_7'

        self.current_round.result = f"{result_sum} ({result_category})"
        self.current_round.status = 'ended'
        await self.current_round.commit()

        await self._settle_bets(self.current_round, result_sum)
        print(f"Ended {game_type} round {self.current_round.round_number}. Dice: {dice1}+{dice2}={result_sum}. Result: {result_category}")
        return True, f"Round {self.current_round.round_number} ended. Dice: {dice1}+{dice2}={result_sum}. Result: {result_category}"

    async def _settle_bets(self, game_round: GameRound, result_sum: int):
        bets = await Bet.objects(game_round=game_round).all()

        for bet in bets:
            user = await User.objects(id=bet.user.id).first()
            if not user:
                continue

            winnings = 0.0
            bet_status = 'lost'

            if bet.prediction == 'less_than_7' and result_sum < 7:
                winnings = bet.bet_amount * 2.0  # Example payout for <7
                bet_status = 'won'
            elif bet.prediction == 'equal_to_7' and result_sum == 7:
                winnings = bet.bet_amount * 5.0  # Example payout for =7
                bet_status = 'won'
            elif bet.prediction == 'greater_than_7' and result_sum > 7:
                winnings = bet.bet_amount * 2.0  # Example payout for >7
                bet_status = 'won'

            if winnings > 0:
                user.balance += winnings
                await user.commit()
                print(f"User {user.user_id} won {winnings} in {game_round.game_type} round {game_round.round_number}")

            bet.status = bet_status
            bet.winnings = winnings
            await bet.commit()

# Example Usage (for testing)
async def main():
    from database.db_manager import connect_db, disconnect_db

    await connect_db()

    # Clear existing data for clean test
    await User.objects.delete()
    await GameRound.objects.delete()
    await Bet.objects.delete()

    game = Lucky7Game()
    game_type = "lucky_7"

    # Create a test user
    user = User(user_id=12345, first_name="TestUser", username="testuser", balance=1000.0)
    await user.commit()

    # Start a new round
    current_round = await game.start_new_round(game_type)
    print(f"Current round ID: {current_round.id}")

    # Place some bets
    success, msg = await game.place_bet(user.user_id, current_round.id, "less_than_7", 100.0)
    print(f"Bet 1: {msg}")
    success, msg = await game.place_bet(user.user_id, current_round.id, "equal_to_7", 50.0)
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
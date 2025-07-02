import asyncio
from datetime import datetime, timedelta
from database.models import GameRound, Bet, User

class ParityEvensGame:
    def __init__(self):
        self.current_round = None
        self.round_duration = 180 # seconds (3 minutes)
        self.countdown_task = None

    async def start_new_round(self):
        if self.current_round and self.current_round.start_time + timedelta(seconds=self.round_duration) > datetime.utcnow():
            # Round already in progress
            return

        last_round = GameRound.objects(game_type='parity_evens').order_by('-round_id').first()
        new_round_id = (last_round.round_id + 1) if last_round else 1

        self.current_round = GameRound(
            round_id=new_round_id,
            game_type='parity_evens',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(seconds=self.round_duration)
        )
        self.current_round.save()
        print(f"Started new Parity/Evens Round: {new_round_id}")

        # Start countdown for the round
        self.countdown_task = asyncio.create_task(self._countdown_timer())

    async def _countdown_timer(self):
        await asyncio.sleep(self.round_duration)
        await self.end_current_round()

    async def end_current_round(self):
        if not self.current_round:
            return

        # Determine result (random number 0-9)
        import random
        result_number = random.randint(0, 9)
        self.current_round.result = str(result_number) # Store as string
        self.current_round.save()

        print(f"Round {self.current_round.round_id} ended. Result: {self.current_round.result}")

        await self._settle_bets(self.current_round)
        self.current_round = None # Reset for next round

    async def _settle_bets(self, game_round):
        bets = Bet.objects(game_round=game_round, is_settled=False)
        result_number = int(game_round.result)
        
        for bet in bets:
            user = bet.user
            payout_multiplier = 0

            if bet.bet_value == 'even' and result_number % 2 == 0:
                payout_multiplier = 2
            elif bet.bet_value == 'odd' and result_number % 2 != 0:
                payout_multiplier = 2
            elif bet.bet_value == str(result_number): # Direct number prediction
                payout_multiplier = 10 # Example payout for direct number

            if payout_multiplier > 0:
                payout_amount = bet.amount * payout_multiplier
                user.balance += payout_amount
                bet.payout = payout_amount
                print(f"User {user.user_id} won {payout_amount} in round {game_round.round_id}")
            else:
                print(f"User {user.user_id} lost {bet.amount} in round {game_round.round_id}")

            bet.is_settled = True
            bet.save()
            user.save()

    async def place_bet(self, user_id: int, round_id: int, bet_type: str, bet_value: str, amount: float):
        user = User.objects(user_id=user_id).first()
        game_round = GameRound.objects(round_id=round_id, game_type='parity_evens').first()

        if not user or not game_round:
            return False, "User or round not found."

        if user.balance < amount:
            return False, "Insufficient balance."

        if game_round.end_time < datetime.utcnow():
            return False, "Betting for this round has closed."

        # Validate bet_value for parity/evens or number prediction
        valid_bet_values = ['even', 'odd'] + [str(i) for i in range(10)]
        if bet_value not in valid_bet_values:
            return False, "Invalid bet value."

        user.balance -= amount
        user.save()

        bet = Bet(
            user=user,
            game_round=game_round,
            bet_type=bet_type,
            bet_value=bet_value,
            amount=amount
        )
        bet.save()
        return True, "Bet placed successfully."

# Example usage (for testing)
async def main():
    from database.db_manager import connect_db
    connect_db()

    game = ParityEvensGame()
    await game.start_new_round()
    await asyncio.sleep(5) # Simulate some time passing

    # Simulate a user and a bet
    user = User(user_id=456, username="testuser2", balance=100.0)
    user.save()

    success, message = await game.place_bet(user.user_id, game.current_round.round_id, 'parity', 'even', 10.0)
    print(f"Bet status: {success}, Message: {message}")

    await asyncio.sleep(game.round_duration) # Wait for round to end

    from mongoengine import disconnect
    disconnect()

if __name__ == "__main__":
    asyncio.run(main())
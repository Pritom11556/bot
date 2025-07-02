from games.color_prediction import ColorPredictionGame
from games.parity_evens import ParityEvensGame
from gamesfrom .number_prediction import NumberPredictionGame
from .wheel_spin import WheelSpinGame
from .lucky_7 import Lucky7Game

class GameManager:
    def __init__(self):
        self.games = {
            "color_prediction": ColorPredictionGame(),
            "parity_evens": ParityEvensGame(),
            "number_prediction": NumberPredictionGame(),
            "wheel_spin": WheelSpinGame(),
            "lucky_7": Lucky7Game()
        }

    async def start_all_games(self):
        await self.color_prediction_game.start_new_round()
        await self.parity_evens_game.start_new_round()
        # Start other games here

    async def get_game_instance(self, game_type: str):
        if game_type == 'color_prediction':
            return self.color_prediction_game
        elif game_type == 'parity_evens':
            return self.parity_evens_game
        # Add other game types here
        return None

    async def get_current_round_info(self, game_type: str):
        game = await self.get_game_instance(game_type)
        if game and game.current_round:
            return {
                "round_id": game.current_round.round_id,
                "start_time": game.current_round.start_time,
                "end_time": game.current_round.end_time,
                "game_type": game.current_round.game_type
            }
        return None
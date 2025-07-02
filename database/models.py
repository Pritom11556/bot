from datetime import datetime
from mongoengine import Document, StringField, IntField, FloatField, DateTimeField, ListField, ReferenceField, BooleanField

class User(Document):
    user_id = IntField(required=True, unique=True)
    username = StringField()
    first_name = StringField()
    last_name = StringField()
    balance = FloatField(default=0.0)
    referral_code = StringField(unique=True)
    referred_by = ReferenceField('self')
    is_admin = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

class GameRound(Document):
    round_id = IntField(required=True, unique=True)
    game_type = StringField(required=True) # e.g., 'color_prediction', 'parity_evens'
    start_time = DateTimeField(default=datetime.utcnow)
    end_time = DateTimeField()
    result = StringField()
    is_manual_result = BooleanField(default=False)
    meta = {'allow_inheritance': True}

class ColorPredictionRound(GameRound):
    # Specific fields for Color Prediction
    pass

class Bet(Document):
    user = ReferenceField(User, required=True)
    game_round = ReferenceField(GameRound, required=True)
    bet_type = StringField(required=True) # e.g., 'color', 'number', 'parity'
    bet_value = StringField(required=True) # e.g., 'red', 'green', 'violet', 'even', 'odd', '7'
    amount = FloatField(required=True)
    payout = FloatField(default=0.0)
    is_settled = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)

class Transaction(Document):
    user = ReferenceField(User, required=True)
    transaction_type = StringField(required=True) # 'deposit', 'withdrawal', 'bet', 'win', 'bonus', 'referral'
    amount = FloatField(required=True)
    status = StringField(default='pending') # 'pending', 'approved', 'rejected'
    payment_method = StringField()
    transaction_id = StringField(unique=True) # For external payment IDs
    screenshot_proof = StringField() # URL or file ID
    approved_by = ReferenceField(User) # Admin who approved
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

class Leaderboard(Document):
    user = ReferenceField(User, required=True, unique=True)
    weekly_earnings = FloatField(default=0.0)
    monthly_earnings = FloatField(default=0.0)
    all_time_earnings = FloatField(default=0.0)
    updated_at = DateTimeField(default=datetime.utcnow)

class DailyBonus(Document):
    user = ReferenceField(User, required=True, unique=True)
    last_claimed = DateTimeField()
    streak_count = IntField(default=0)

# Add more models as needed for other game types, VIP, etc.
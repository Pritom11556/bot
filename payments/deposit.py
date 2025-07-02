from database.models import Transaction, User
from datetime import datetime

class DepositManager:
    async def create_deposit_request(self, user_id: int, amount: float, payment_method: str, transaction_id: str, screenshot_proof: str = None):
        user = User.objects(user_id=user_id).first()
        if not user:
            return False, "User not found."

        # Check for existing transaction with the same ID to prevent duplicates
        if Transaction.objects(transaction_id=transaction_id).first():
            return False, "Transaction ID already exists. Please use a unique ID."

        deposit = Transaction(
            user=user,
            transaction_type='deposit',
            amount=amount,
            status='pending',
            payment_method=payment_method,
            transaction_id=transaction_id,
            screenshot_proof=screenshot_proof,
            created_at=datetime.utcnow()
        )
        deposit.save()
        return True, "Deposit request submitted successfully. Awaiting admin approval."

    async def approve_deposit(self, transaction_id: str, admin_user_id: int):
        transaction = Transaction.objects(transaction_id=transaction_id, transaction_type='deposit', status='pending').first()
        admin_user = User.objects(user_id=admin_user_id, is_admin=True).first()

        if not transaction:
            return False, "Pending deposit transaction not found."
        if not admin_user:
            return False, "Admin user not found or not authorized."

        user = transaction.user
        user.balance += transaction.amount
        user.save()

        transaction.status = 'approved'
        transaction.approved_by = admin_user
        transaction.updated_at = datetime.utcnow()
        transaction.save()
        return True, f"Deposit of {transaction.amount} for user {user.user_id} approved."

    async def reject_deposit(self, transaction_id: str, admin_user_id: int):
        transaction = Transaction.objects(transaction_id=transaction_id, transaction_type='deposit', status='pending').first()
        admin_user = User.objects(user_id=admin_user_id, is_admin=True).first()

        if not transaction:
            return False, "Pending deposit transaction not found."
        if not admin_user:
            return False, "Admin user not found or not authorized."

        transaction.status = 'rejected'
        transaction.approved_by = admin_user
        transaction.updated_at = datetime.utcnow()
        transaction.save()
        return True, f"Deposit request {transaction_id} rejected."

    async def get_pending_deposits(self):
        return Transaction.objects(transaction_type='deposit', status='pending').all()
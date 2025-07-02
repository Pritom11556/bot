from database.models import Transaction, User
from datetime import datetime

class WithdrawalManager:
    MIN_WITHDRAWAL_BALANCE = 10.0 # Example minimum balance for withdrawal

    async def create_withdrawal_request(self, user_id: int, amount: float, payment_method: str, payment_address: str):
        user = User.objects(user_id=user_id).first()
        if not user:
            return False, "User not found."

        if user.balance < amount:
            return False, "Insufficient balance for withdrawal."

        if user.balance < self.MIN_WITHDRAWAL_BALANCE:
            return False, f"Minimum balance for withdrawal is {self.MIN_WITHDRAWAL_BALANCE}."

        # Deduct balance immediately to prevent double spending
        user.balance -= amount
        user.save()

        withdrawal = Transaction(
            user=user,
            transaction_type='withdrawal',
            amount=amount,
            status='pending',
            payment_method=payment_method,
            transaction_id=f"WITHDRAWAL_{user_id}_{int(datetime.utcnow().timestamp())}", # Unique ID
            # In a real scenario, payment_address might be sensitive and handled differently
            # For now, storing it here for simplicity
            screenshot_proof=payment_address, # Re-using this field for payment address for now
            created_at=datetime.utcnow()
        )
        withdrawal.save()
        return True, "Withdrawal request submitted successfully. Awaiting admin approval."

    async def approve_withdrawal(self, transaction_id: str, admin_user_id: int):
        transaction = Transaction.objects(transaction_id=transaction_id, transaction_type='withdrawal', status='pending').first()
        admin_user = User.objects(user_id=admin_user_id, is_admin=True).first()

        if not transaction:
            return False, "Pending withdrawal transaction not found."
        if not admin_user:
            return False, "Admin user not found or not authorized."

        transaction.status = 'approved'
        transaction.approved_by = admin_user
        transaction.updated_at = datetime.utcnow()
        transaction.save()
        return True, f"Withdrawal of {transaction.amount} for user {transaction.user.user_id} approved."

    async def reject_withdrawal(self, transaction_id: str, admin_user_id: int):
        transaction = Transaction.objects(transaction_id=transaction_id, transaction_type='withdrawal', status='pending').first()
        admin_user = User.objects(user_id=admin_user_id, is_admin=True).first()

        if not transaction:
            return False, "Pending withdrawal transaction not found."
        if not admin_user:
            return False, "Admin user not found or not authorized."

        # Refund the balance if withdrawal is rejected
        user = transaction.user
        user.balance += transaction.amount
        user.save()

        transaction.status = 'rejected'
        transaction.approved_by = admin_user
        transaction.updated_at = datetime.utcnow()
        transaction.save()
        return True, f"Withdrawal request {transaction_id} rejected and amount refunded."

    async def get_pending_withdrawals(self):
        return Transaction.objects(transaction_type='withdrawal', status='pending').all()
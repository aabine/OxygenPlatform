from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from app.modules.payments.models import Transaction, PaymentStatus
from app.modules.payments.schemas import TransactionCreate
from app.modules.payments.paystack import PaystackService
from app.modules.orders.models import Order
from app.core.config import settings

class TransactionService:
    def __init__(self, db: Session):
        self.db = db
        self.paystack = PaystackService()
        self.platform_fee_percentage = settings.PLATFORM_FEE_PERCENTAGE

    def _calculate_split(self, amount: float) -> tuple[float, float]:
        """Calculate vendor amount and platform fee"""
        platform_fee = amount * (self.platform_fee_percentage / 100)
        vendor_amount = amount - platform_fee
        return vendor_amount, platform_fee

    async def update_transaction_status(
        self,
        payment_id: str,
        status: str,
        payment_data: dict
    ) -> Transaction:
        """Update transaction status and payment details"""
        transaction = self.db.query(Transaction).filter(Transaction.payment_id == payment_id).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
            
        transaction.status = PaymentStatus(status)
        transaction.payment_method = payment_data.get("payment_method")
        transaction.payment_channel = payment_data.get("payment_channel")
        transaction.paid_at = payment_data.get("paid_at")
        transaction.metadata = payment_data.get("metadata")
        
        self.db.commit()
        self.db.refresh(transaction)
        return transaction
        
    async def update_order_payment_status(
        self,
        order_id: int,
        status: str
    ):
        """Update order payment status"""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
            
        order.payment_status = status
        self.db.commit()

    async def create_payment(
        self,
        order_id: int,
        email: str,
        callback_url: Optional[str] = None
    ):
        """Create a new payment transaction"""
        # Get order
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Calculate amounts
        vendor_amount, platform_fee = self._calculate_split(order.total_amount)

        # Initialize payment with Paystack
        metadata = {
            "order_id": order_id,
            "vendor_id": order.vendor_id,
            "platform_fee": platform_fee
        }

        payment_data = await self.paystack.initialize_payment(
            amount=order.total_amount,
            email=email,
            callback_url=callback_url,
            metadata=metadata
        )

        # Create transaction record
        transaction = Transaction(
            payment_id=payment_data["reference"],
            payment_provider="paystack",
            order_id=order_id,
            vendor_id=order.vendor_id,
            total_amount=order.total_amount,
            vendor_amount=vendor_amount,
            platform_fee=platform_fee,
            status=PaymentStatus.PENDING,
            metadata=str(metadata)
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        return {
            "transaction": transaction,
            "authorization_url": payment_data["authorization_url"],
            "access_code": payment_data["access_code"],
            "reference": payment_data["reference"]
        }

    async def verify_payment(self, payment_id: str):
        """Verify payment status with Paystack"""
        # Get transaction
        transaction = (
            self.db.query(Transaction)
            .filter(Transaction.payment_id == payment_id)
            .first()
        )
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        # Verify with Paystack
        payment_data = await self.paystack.verify_payment(payment_id)

        # Update transaction status
        if payment_data["status"] == "success":
            transaction.status = PaymentStatus.SUCCESS
            transaction.paid_at = datetime.utcnow()
            transaction.payment_method = payment_data.get("channel")
            transaction.payment_channel = payment_data.get("authorization", {}).get("channel")

            # Update order status
            order = transaction.order
            order.payment_status = "paid"
            
        elif payment_data["status"] == "failed":
            transaction.status = PaymentStatus.FAILED

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    async def handle_webhook(self, event_type: str, data: dict, signature: str):
        """Handle Paystack webhook events"""
        # Verify webhook signature
        if not self.paystack.verify_webhook_signature(signature, str(data).encode()):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        if event_type == "charge.success":
            reference = data.get("reference")
            await self.verify_payment(reference)
        
        # Handle other event types as needed
        return {"status": "processed"}

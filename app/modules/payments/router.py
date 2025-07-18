from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Header, Request, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.modules.auth.deps import get_current_active_user, check_admin_access
from app.modules.users.models import User
from app.modules.payments.service import TransactionService
from app.modules.payments.analytics import PaymentAnalytics
from app.modules.payments.schemas import (
    PaymentCreate,
    PaymentResponse,
    Transaction,
    PaystackWebhookEvent
)

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    payment: PaymentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new payment for an order"""
    service = TransactionService(db)
    result = await service.create_payment(
        order_id=payment.order_id,
        email=payment.email,
        callback_url=payment.callback_url
    )
    
    return {
        "authorization_url": result["authorization_url"],
        "access_code": result["access_code"],
        "reference": result["reference"]
    }

@router.get("/verify/{payment_id}", response_model=Transaction)
async def verify_payment(
    payment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Verify a payment transaction"""
    service = TransactionService(db)
    return await service.verify_payment(payment_id)

@router.post("/webhook/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(...),
    db: Session = Depends(get_db)
):
    """Handle Paystack webhook events"""
    # Get the raw payload
    payload = await request.body()
    
    # Verify webhook signature
    service = TransactionService(db)
    if not service.paystack.verify_webhook_signature(x_paystack_signature, payload):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Parse the event data
    event_data = await request.json()
    
    # Handle charge.success event
    if event_data["event"] == "charge.success":
        data = event_data["data"]
        reference = data["reference"]
        metadata = data["metadata"]
        
        if not metadata or not metadata.get("order_id"):
            raise HTTPException(status_code=400, detail="Invalid payment metadata")
            
        # Update transaction status
        transaction = await service.update_transaction_status(
            payment_id=reference,
            status="success",
            payment_data={
                "payment_method": data["authorization"]["channel"],
                "payment_channel": data["authorization"]["card_type"],
                "paid_at": datetime.fromtimestamp(data["paid_at"]),
                "metadata": event_data
            }
        )
        
        # Update order payment status
        await service.update_order_payment_status(
            order_id=metadata["order_id"],
            status="paid"
        )
        
        return {"status": "success"}

@router.post("/{payment_id}/refund", response_model=Transaction)
async def refund_payment(
    payment_id: str,
    amount: Optional[float] = None,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Initiate a refund for a payment"""
    service = TransactionService(db)
    return await service.initiate_refund(payment_id, amount, reason, current_user.id)

# Analytics Endpoints

@router.get("/analytics/summary")
async def get_payment_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    vendor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get payment summary statistics"""
    if not (current_user.is_admin or (vendor_id and vendor_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized to access these analytics")
    
    analytics = PaymentAnalytics(db)
    return await analytics.get_payment_summary(start_date, end_date, vendor_id)

@router.get("/analytics/daily-transactions")
async def get_daily_transactions(
    days: int = Query(30, gt=0, le=365),
    vendor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get daily transaction statistics"""
    if not (current_user.is_admin or (vendor_id and vendor_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized to access these analytics")
    
    analytics = PaymentAnalytics(db)
    return await analytics.get_daily_transactions(days, vendor_id)

@router.get("/analytics/status-distribution")
async def get_status_distribution(
    vendor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get distribution of payment statuses"""
    if not (current_user.is_admin or (vendor_id and vendor_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized to access these analytics")
    
    analytics = PaymentAnalytics(db)
    return await analytics.get_payment_status_distribution(vendor_id)

@router.get("/analytics/vendor-performance")
async def get_vendor_performance(
    top_n: int = Query(10, gt=0, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get top performing vendors"""
    check_admin_access(current_user)
    analytics = PaymentAnalytics(db)
    return await analytics.get_vendor_performance(top_n)

@router.get("/analytics/payment-methods")
async def get_payment_method_stats(
    vendor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get statistics by payment method"""
    if not (current_user.is_admin or (vendor_id and vendor_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized to access these analytics")
    
    analytics = PaymentAnalytics(db)
    return await analytics.get_payment_method_stats(vendor_id)

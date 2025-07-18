from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from .models import PaymentStatus, PaymentProvider

class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    email: str
    callback_url: Optional[str] = None
    metadata: Optional[dict] = None

class PaymentResponse(BaseModel):
    authorization_url: str
    access_code: str
    reference: str

class TransactionBase(BaseModel):
    payment_id: str
    payment_provider: PaymentProvider
    order_id: int
    vendor_id: int
    total_amount: float
    vendor_amount: float
    platform_fee: float
    currency: str = "NGN"
    metadata: Optional[dict] = None

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    status: PaymentStatus
    payment_method: Optional[str] = None
    payment_channel: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaystackWebhookEvent(BaseModel):
    event: str
    data: dict

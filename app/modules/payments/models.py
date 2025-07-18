from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLAEnum
from sqlalchemy.orm import relationship
from app.db.base import Base
import enum

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentProvider(str, enum.Enum):
    PAYSTACK = "paystack"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String, unique=True, index=True)  # Payment provider's reference
    payment_provider = Column(SQLAEnum(PaymentProvider), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SQLAEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    
    # Amount details
    total_amount = Column(Float, nullable=False)
    vendor_amount = Column(Float, nullable=False)
    platform_fee = Column(Float, nullable=False)
    
    # Payment details
    payment_method = Column(String)
    payment_channel = Column(String)
    currency = Column(String, default="NGN")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    metadata = Column(String, nullable=True)  # JSON string for additional data

    # Relationships
    order = relationship("Order", back_populates="transactions")
    vendor = relationship("User", back_populates="transactions")

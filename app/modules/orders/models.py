from sqlalchemy import Column, Integer, String, Enum as SQLAlchemyEnum, ForeignKey, DateTime, JSON, Text, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.modules.orders.enums import OrderStatus, OrderUrgency, OrderEventType

# Association table for order-cylinder relationship
order_cylinders = Table(
    'order_cylinders',
    Base.metadata,
    Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
    Column('cylinder_id', Integer, ForeignKey('cylinders.id'), primary_key=True)
)

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    vendor_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    status = Column(SQLAlchemyEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    payment_status = Column(String, default="pending")  # pending, paid, failed, refunded
    total_amount = Column(Integer, nullable=False)
    urgency = Column(SQLAlchemyEnum(OrderUrgency), nullable=False)
    quantity = Column(Integer, nullable=False)
    delivery_location = Column(JSON, nullable=False)  # Hospital's delivery location
    special_instructions = Column(Text, nullable=True)
    
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SQLAlchemyEnum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    urgency = Column(SQLAlchemyEnum(OrderUrgency), nullable=False)
    quantity = Column(Integer, nullable=False)
    delivery_location = Column(JSON, nullable=False)  # Hospital's delivery location
    special_instructions = Column(Text, nullable=True)
    
    # Cylinder exchange tracking
    cylinders_sent = Column(Integer, default=0)
    empty_cylinders_returned = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expected_delivery = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    hospital = relationship("User", foreign_keys=[hospital_id], back_populates="hospital_orders")
    vendor = relationship("User", foreign_keys=[vendor_id], back_populates="vendor_orders")
    cylinders = relationship("Cylinder", secondary=order_cylinders, back_populates="orders")
    logs = relationship("OrderLog", back_populates="order")

    __mapper_args__ = {"eager_defaults": True}

class OrderLog(Base):
    __tablename__ = "order_logs"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    event_type = Column(SQLAlchemyEnum(OrderEventType), nullable=False)
    old_status = Column(SQLAlchemyEnum(OrderStatus), nullable=True)
    new_status = Column(SQLAlchemyEnum(OrderStatus), nullable=True)
    details = Column(JSON, nullable=True)  # For storing event-specific details
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="logs")
    user = relationship("User")

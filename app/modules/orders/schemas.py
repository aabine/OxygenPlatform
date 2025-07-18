from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, validator
from app.modules.orders.enums import OrderStatus, OrderUrgency, OrderEventType
from app.modules.cylinders.schemas import Location, Cylinder

class OrderBase(BaseModel):
    quantity: int = Field(..., gt=0, description="Number of cylinders needed")
    urgency: OrderUrgency
    delivery_location: Location
    special_instructions: str | None = None

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: OrderStatus | None = None
    vendor_id: int | None = None
    expected_delivery: datetime | None = None
    special_instructions: str | None = None
    cylinders_sent: int | None = None
    empty_cylinders_returned: int | None = None

class OrderInDB(OrderBase):
    id: int
    hospital_id: int
    vendor_id: int | None = None
    status: OrderStatus
    cylinders_sent: int = 0
    empty_cylinders_returned: int = 0
    created_at: datetime
    updated_at: datetime | None = None
    expected_delivery: datetime | None = None
    delivered_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class Order(OrderInDB):
    """Public order data"""
    assigned_cylinders: List[Cylinder] = []

class OrderLogBase(BaseModel):
    event_type: OrderEventType
    old_status: OrderStatus | None = None
    new_status: OrderStatus | None = None
    details: dict | None = None
    notes: str | None = None

class OrderLogCreate(OrderLogBase):
    order_id: int
    created_by: int

class OrderLogInDB(OrderLogBase):
    id: int
    order_id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrderLog(OrderLogInDB):
    """Public order log data"""
    pass

class OrderWithLogs(Order):
    """Order with its history logs"""
    logs: List[OrderLog]

class OrderAcceptance(BaseModel):
    """Schema for accepting an order"""
    expected_delivery: datetime
    assigned_cylinder_ids: List[int] = []

class OrderDeliveryUpdate(BaseModel):
    """Schema for updating delivery status"""
    status: OrderStatus
    cylinders_sent: int
    empty_cylinders_returned: int
    delivered_at: datetime | None = None
    notes: str | None = None

class NearbyVendor(BaseModel):
    """Schema for nearby vendor information"""
    id: int
    name: str
    email: str
    location: Location
    distance: float  # Distance in kilometers

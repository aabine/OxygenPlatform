from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class DeliveryStatus(BaseModel):
    """Current status of a delivery"""
    order_id: int
    status: str
    eta: datetime
    current_location: Optional[str] = None
    last_updated: datetime
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    cylinders_loaded: int
    notes: Optional[str] = None

class DeliveryUpdate(BaseModel):
    """Update delivery status"""
    eta: Optional[datetime] = None
    current_location: Optional[str] = None
    status: str = Field(..., description="Current delivery status")
    notes: Optional[str] = None

class DeliveryTimelineEvent(BaseModel):
    """An event in the delivery timeline"""
    timestamp: datetime
    event_type: str
    location: Optional[str] = None
    description: str
    status: str
    driver_info: Optional[dict] = None
    cylinders_info: Optional[dict] = None

class DeliveryTimeline(BaseModel):
    """Complete delivery timeline"""
    order_id: int
    current_status: str
    events: list[DeliveryTimelineEvent]
    eta: Optional[datetime] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    cylinders_loaded: int
    cylinders_delivered: Optional[int] = None

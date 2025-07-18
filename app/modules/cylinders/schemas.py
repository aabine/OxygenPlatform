from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.modules.cylinders.enums import CylinderStatus, CylinderEventType

class Location(BaseModel):
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = None

class CylinderBase(BaseModel):
    serial_number: str = Field(..., description="Unique serial number of the cylinder")
    location: Location | None = None

class CylinderCreate(CylinderBase):
    status: CylinderStatus = CylinderStatus.FILLED

class CylinderUpdate(BaseModel):
    status: CylinderStatus | None = None
    location: Location | None = None
    is_assigned: bool | None = None
    current_order_id: int | None = None

class CylinderInDB(CylinderBase):
    id: int
    status: CylinderStatus
    vendor_id: int
    is_assigned: bool
    current_order_id: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class Cylinder(CylinderInDB):
    """Public cylinder data"""
    pass

class CylinderLogBase(BaseModel):
    event_type: CylinderEventType
    old_status: CylinderStatus | None = None
    new_status: CylinderStatus | None = None
    order_id: int | None = None
    location: Location | None = None
    notes: str | None = None

class CylinderLogCreate(CylinderLogBase):
    cylinder_id: int
    created_by: int

class CylinderLogInDB(CylinderLogBase):
    id: int
    cylinder_id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CylinderLog(CylinderLogInDB):
    """Public cylinder log data"""
    pass

class CylinderWithLogs(Cylinder):
    """Cylinder with its history logs"""
    logs: list[CylinderLog]

class CylinderStatusUpdate(BaseModel):
    """Schema for bulk status updates"""
    cylinder_ids: list[int]
    new_status: CylinderStatus
    location: Location | None = None
    notes: str | None = None

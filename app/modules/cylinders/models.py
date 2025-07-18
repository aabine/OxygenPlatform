from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLAlchemyEnum, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
from app.modules.cylinders.enums import CylinderStatus, CylinderEventType

class Cylinder(Base):
    __tablename__ = "cylinders"

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String, unique=True, index=True, nullable=False)
    status = Column(SQLAlchemyEnum(CylinderStatus), nullable=False, default=CylinderStatus.FILLED)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    location = Column(JSON, nullable=True)  # For tracking current location
    is_assigned = Column(Boolean, default=False)
    current_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    vendor = relationship("User", back_populates="cylinders")
    current_order = relationship("Order", back_populates="cylinders")
    logs = relationship("CylinderLog", back_populates="cylinder")

    __mapper_args__ = {"eager_defaults": True}

class CylinderLog(Base):
    __tablename__ = "cylinder_logs"

    id = Column(Integer, primary_key=True, index=True)
    cylinder_id = Column(Integer, ForeignKey("cylinders.id"), nullable=False)
    event_type = Column(SQLAlchemyEnum(CylinderEventType), nullable=False)
    old_status = Column(SQLAlchemyEnum(CylinderStatus), nullable=True)
    new_status = Column(SQLAlchemyEnum(CylinderStatus), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    location = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    cylinder = relationship("Cylinder", back_populates="logs")
    order = relationship("Order")
    user = relationship("User")

from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class OrderEventType(str, Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    VENDOR_ASSIGNED = "vendor_assigned"
    CYLINDERS_ASSIGNED = "cylinders_assigned"
    CYLINDERS_UPDATED = "cylinders_updated"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

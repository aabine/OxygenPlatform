from enum import Enum

class CylinderStatus(str, Enum):
    FILLED = "filled"
    IN_TRANSIT = "in_transit"
    EMPTY = "empty"
    RETURNED = "returned"

class CylinderEventType(str, Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    LOCATION_UPDATED = "location_updated"
    DELETED = "deleted"

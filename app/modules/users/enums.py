from enum import Enum

class UserRole(str, Enum):
    HOSPITAL = "hospital"
    VENDOR = "vendor"
    ADMIN = "admin"

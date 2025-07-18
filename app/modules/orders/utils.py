from math import radians, sin, cos, sqrt, atan2
from typing import List, Tuple
from app.modules.orders.schemas import Location

def calculate_distance(loc1: Location, loc2: Location) -> float:
    """
    Calculate distance between two points using the Haversine formula.
    Returns distance in kilometers.
    """
    if not all([loc1.latitude, loc1.longitude, loc2.latitude, loc2.longitude]):
        return float('inf')  # Return infinity if coordinates are missing
    
    R = 6371  # Earth's radius in kilometers

    lat1, lon1 = radians(loc1.latitude), radians(loc1.longitude)
    lat2, lon2 = radians(loc2.latitude), radians(loc2.longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c

    return distance

def find_nearby_vendors(
    target_location: Location,
    vendor_locations: List[Tuple[int, Location]],
    max_distance: float = 50.0  # Maximum distance in kilometers
) -> List[Tuple[int, float]]:
    """
    Find vendors within the specified maximum distance.
    Returns list of (vendor_id, distance) tuples, sorted by distance.
    """
    distances = []
    for vendor_id, vendor_location in vendor_locations:
        distance = calculate_distance(target_location, vendor_location)
        if distance <= max_distance:
            distances.append((vendor_id, distance))
    
    # Sort by distance
    return sorted(distances, key=lambda x: x[1])

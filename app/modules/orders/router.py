from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.modules.auth.deps import get_current_active_user
from app.modules.auth.deps import check_hospital_access, check_vendor_access
from app.modules.users.models import User
from app.modules.orders.service import OrderService
from app.modules.orders.schemas import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
    OrderDeliveryUpdate,
    Location,
    OrderLogResponse,
    VendorWithDistance,
    DeliveryStatus,
    DeliveryUpdate,
    DeliveryTimeline
)
from app.modules.orders.enums import OrderStatus
from app.modules.orders.services import DeliveryTrackingService

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_in: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new order (Hospital only)"""
    check_hospital_access(current_user)
    service = OrderService(db)
    return await service.create(order_in, current_user.id)

@router.get("/", response_model=List[OrderResponse])
async def list_orders(
    hospital_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List orders with filters"""
    service = OrderService(db)
    # Apply user-specific filters
    if current_user.is_hospital:
        hospital_id = current_user.id
    elif current_user.is_vendor:
        vendor_id = current_user.id
    
    return await service.list(
        hospital_id=hospital_id,
        vendor_id=vendor_id,
        status=status,
        skip=skip,
        limit=limit
    )

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get order details"""
    service = OrderService(db)
    order = await service.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check access
    if (current_user.is_hospital and order.hospital_id != current_user.id) or \
       (current_user.is_vendor and order.vendor_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this order")
    
    return order

@router.post("/find-vendors", response_model=List[VendorWithDistance])
async def find_nearby_vendors(
    delivery_location: Location,
    quantity: int = Query(..., gt=0),
    max_distance: float = Query(50.0, gt=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Find nearby vendors who can fulfill the order (Hospital only)"""
    check_hospital_access(current_user)
    service = OrderService(db)
    vendors = await service.find_nearby_vendors(
        delivery_location=delivery_location,
        quantity=quantity,
        max_distance=max_distance
    )
    return vendors

@router.post("/{order_id}/accept", response_model=OrderResponse)
async def accept_order(
    order_id: int,
    expected_delivery: datetime = Body(...),
    assigned_cylinder_ids: List[int] = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Accept an order and assign cylinders (Vendor only)"""
    check_vendor_access(current_user)
    service = OrderService(db)
    return await service.accept_order(
        order_id=order_id,
        vendor_id=current_user.id,
        expected_delivery=expected_delivery,
        assigned_cylinder_ids=assigned_cylinder_ids
    )

@router.post("/{order_id}/delivery-status", response_model=OrderResponse)
async def update_delivery_status(
    order_id: int,
    update_data: OrderDeliveryUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update order delivery status (Vendor only)"""
    check_vendor_access(current_user)
    service = OrderService(db)
    order = await service.get(order_id)
    if not order or order.vendor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return await service.update_delivery_status(
        order_id=order_id,
        update_data=update_data,
        user_id=current_user.id
    )

@router.post("/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    reason: str = Body(..., min_length=1),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cancel an order"""
    service = OrderService(db)
    order = await service.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only hospital can cancel pending orders
    # Both hospital and vendor can cancel accepted orders
    if order.status == OrderStatus.PENDING and not current_user.is_hospital:
        raise HTTPException(status_code=403, detail="Only hospital can cancel pending orders")
    
    if order.status == OrderStatus.ACCEPTED and \
       not (current_user.is_hospital or \
            (current_user.is_vendor and order.vendor_id == current_user.id)):
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    
    return await service.cancel_order(
        order_id=order_id,
        user_id=current_user.id,
        reason=reason
    )

@router.get("/{order_id}/logs", response_model=List[OrderLogResponse])
async def get_order_logs(
    order_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get order history logs"""
    service = OrderService(db)
    order = await service.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check access
    if (current_user.is_hospital and order.hospital_id != current_user.id) or \
       (current_user.is_vendor and order.vendor_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this order")
    
    return await service.get_logs(order_id, skip=skip, limit=limit)

@router.get("/{order_id}/delivery", response_model=DeliveryStatus)
async def get_delivery_status(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current delivery status"""
    service = DeliveryTrackingService(db)
    return await service.get_delivery_status(order_id)

@router.get("/{order_id}/delivery/timeline", response_model=DeliveryTimeline)
async def get_delivery_timeline(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get complete delivery timeline"""
    service = DeliveryTrackingService(db)
    return await service.get_delivery_timeline(order_id)

@router.post("/{order_id}/delivery/update", response_model=DeliveryStatus)
async def update_delivery_status(
    order_id: int,
    update: DeliveryUpdate,
    driver_info: Optional[dict] = Body(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update delivery status and location"""
    check_vendor_access(current_user)
    service = DeliveryTrackingService(db)
    return await service.update_delivery_status(
        order_id=order_id,
        update=update,
        user_id=current_user.id,
        driver_info=driver_info
    )

from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from app.core.cache import cache
from app.modules.orders.models import Order, OrderLog
from app.modules.orders.schemas import (
    OrderCreate,
    OrderUpdate,
    OrderLogCreate,
    OrderDeliveryUpdate,
    Location
)
from app.modules.orders.enums import OrderStatus, OrderEventType
from app.modules.orders.utils import find_nearby_vendors
from app.modules.users.enums import UserRole
from app.modules.users.models import User
from app.modules.cylinders.models import Cylinder
from app.modules.cylinders.enums import CylinderStatus
from fastapi import HTTPException, status

class OrderService:
    CACHE_PREFIX = "order"
    
    def __init__(self, db: Session):
        self.db = db

    async def _cache_order(self, order: Order) -> None:
        """Cache order data"""
        if order:
            await cache.set(
                [self.CACHE_PREFIX, order.id],
                {
                    "id": order.id,
                    "hospital_id": order.hospital_id,
                    "vendor_id": order.vendor_id,
                    "status": order.status,
                    "urgency": order.urgency,
                    "quantity": order.quantity,
                    "delivery_location": order.delivery_location,
                    "cylinders_sent": order.cylinders_sent,
                    "empty_cylinders_returned": order.empty_cylinders_returned
                }
            )

    async def _invalidate_order_cache(self, order_id: int) -> None:
        """Invalidate order cache"""
        await cache.delete([self.CACHE_PREFIX, order_id])
        await cache.invalidate_pattern(f"{self.CACHE_PREFIX}:list:*")

    async def create(
        self,
        order_in: OrderCreate,
        hospital_id: int
    ) -> Order:
        """Create a new order"""
        db_order = Order(
            hospital_id=hospital_id,
            **order_in.model_dump()
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)

        # Create initial log
        await self.create_log(
            OrderLogCreate(
                order_id=db_order.id,
                event_type=OrderEventType.CREATED,
                new_status=db_order.status,
                created_by=hospital_id,
                notes="Order created"
            )
        )

        await self._cache_order(db_order)
        return db_order

    async def get(self, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        # Try cache first
        cached = await cache.get([self.CACHE_PREFIX, order_id])
        if cached:
            stmt = select(Order).where(Order.id == order_id)
            return self.db.execute(stmt).scalar_one_or_none()

        # Query database
        stmt = select(Order).where(Order.id == order_id)
        order = self.db.execute(stmt).scalar_one_or_none()
        if order:
            await self._cache_order(order)
        return order

    async def list(
        self,
        hospital_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Order]:
        """List orders with filters"""
        stmt = select(Order)
        
        if hospital_id:
            stmt = stmt.where(Order.hospital_id == hospital_id)
        if vendor_id:
            stmt = stmt.where(Order.vendor_id == vendor_id)
        if status:
            stmt = stmt.where(Order.status == status)
        
        stmt = stmt.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        return self.db.execute(stmt).scalars().all()

    async def find_nearby_vendors(
        self,
        delivery_location: Location,
        quantity: int,
        max_distance: float = 50.0
    ) -> List[Tuple[int, float]]:
        """Find nearby vendors who can fulfill the order"""
        # Get all vendors
        stmt = select(User).where(User.role == UserRole.VENDOR)
        vendors = self.db.execute(stmt).scalars().all()

        # Get vendor locations and available cylinder counts
        vendor_data = []
        for vendor in vendors:
            # Count available (filled) cylinders for vendor
            available_cylinders = (
                self.db.query(Cylinder)
                .filter(
                    and_(
                        Cylinder.vendor_id == vendor.id,
                        Cylinder.status == CylinderStatus.FILLED,
                        Cylinder.is_assigned == False
                    )
                )
                .count()
            )

            if available_cylinders >= quantity and vendor.location:
                vendor_data.append((vendor.id, Location(**vendor.location)))

        # Find nearby vendors
        return find_nearby_vendors(delivery_location, vendor_data, max_distance)

    async def accept_order(
        self,
        order_id: int,
        vendor_id: int,
        expected_delivery: datetime,
        assigned_cylinder_ids: List[int]
    ) -> Order:
        """Accept an order and assign cylinders"""
        order = await self.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status != OrderStatus.PENDING:
            raise HTTPException(status_code=400, detail="Order cannot be accepted")

        # Verify cylinder ownership and availability
        cylinders = (
            self.db.query(Cylinder)
            .filter(
                Cylinder.id.in_(assigned_cylinder_ids),
                Cylinder.vendor_id == vendor_id,
                Cylinder.status == CylinderStatus.FILLED,
                Cylinder.is_assigned == False
            )
            .all()
        )

        if len(cylinders) != len(assigned_cylinder_ids):
            raise HTTPException(
                status_code=400,
                detail="Some cylinders are not available"
            )

        # Update order
        order.vendor_id = vendor_id
        order.status = OrderStatus.ACCEPTED
        order.expected_delivery = expected_delivery

        # Assign cylinders
        for cylinder in cylinders:
            cylinder.is_assigned = True
            cylinder.current_order_id = order_id
            order.cylinders.append(cylinder)

        # Create log entry
        await self.create_log(
            OrderLogCreate(
                order_id=order.id,
                event_type=OrderEventType.VENDOR_ASSIGNED,
                old_status=OrderStatus.PENDING,
                new_status=OrderStatus.ACCEPTED,
                created_by=vendor_id,
                details={
                    "assigned_cylinders": assigned_cylinder_ids,
                    "expected_delivery": expected_delivery.isoformat()
                }
            )
        )

        self.db.commit()
        self.db.refresh(order)
        await self._cache_order(order)
        return order

    async def update_delivery_status(
        self,
        order_id: int,
        update_data: OrderDeliveryUpdate,
        user_id: int
    ) -> Order:
        """Update order delivery status"""
        order = await self.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        old_status = order.status
        order.status = update_data.status
        order.cylinders_sent = update_data.cylinders_sent
        order.empty_cylinders_returned = update_data.empty_cylinders_returned

        if update_data.delivered_at:
            order.delivered_at = update_data.delivered_at

        # Create log entry
        await self.create_log(
            OrderLogCreate(
                order_id=order.id,
                event_type=OrderEventType.STATUS_CHANGED,
                old_status=old_status,
                new_status=update_data.status,
                created_by=user_id,
                details={
                    "cylinders_sent": update_data.cylinders_sent,
                    "empty_cylinders_returned": update_data.empty_cylinders_returned,
                    "notes": update_data.notes
                }
            )
        )

        self.db.commit()
        self.db.refresh(order)
        await self._cache_order(order)
        return order

    async def cancel_order(
        self,
        order_id: int,
        user_id: int,
        reason: str
    ) -> Order:
        """Cancel an order"""
        order = await self.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status not in [OrderStatus.PENDING, OrderStatus.ACCEPTED]:
            raise HTTPException(
                status_code=400,
                detail="Order cannot be cancelled"
            )

        old_status = order.status
        order.status = OrderStatus.CANCELLED

        # Unassign cylinders
        for cylinder in order.cylinders:
            cylinder.is_assigned = False
            cylinder.current_order_id = None

        # Create log entry
        await self.create_log(
            OrderLogCreate(
                order_id=order.id,
                event_type=OrderEventType.CANCELLED,
                old_status=old_status,
                new_status=OrderStatus.CANCELLED,
                created_by=user_id,
                notes=reason
            )
        )

        self.db.commit()
        self.db.refresh(order)
        await self._cache_order(order)
        return order

    async def create_log(self, log_in: OrderLogCreate) -> OrderLog:
        """Create a new order log entry"""
        db_log = OrderLog(**log_in.model_dump())
        self.db.add(db_log)
        self.db.commit()
        self.db.refresh(db_log)
        return db_log

    async def get_logs(
        self,
        order_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[OrderLog]:
        """Get order history logs"""
        stmt = (
            select(OrderLog)
            .where(OrderLog.order_id == order_id)
            .order_by(OrderLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.modules.orders.models import Order, OrderLog
from app.modules.orders.schemas import (
    DeliveryStatus,
    DeliveryUpdate,
    DeliveryTimelineEvent,
    DeliveryTimeline
)
from app.modules.orders.enums import OrderStatus, OrderEventType
from app.core.cache import cache
from app.modules.notifications.service import NotificationService

class DeliveryTrackingService:
    CACHE_PREFIX = "delivery"
    
    def __init__(self, db: Session):
        self.db = db

    async def _cache_delivery_status(self, status: DeliveryStatus) -> None:
        """Cache delivery status"""
        if status:
            await cache.set(
                [self.CACHE_PREFIX, str(status.order_id)],
                status.model_dump()
            )

    async def _invalidate_delivery_cache(self, order_id: int) -> None:
        """Invalidate delivery cache"""
        await cache.delete([self.CACHE_PREFIX, str(order_id)])

    def _create_timeline_event(
        self,
        log: OrderLog,
        order: Order
    ) -> DeliveryTimelineEvent:
        """Convert an order log to a timeline event"""
        event = DeliveryTimelineEvent(
            timestamp=log.created_at,
            event_type=log.event_type,
            status=log.new_status,
            description=log.notes or "",
            location=None,  # Will be filled from details if available
            driver_info=None,
            cylinders_info=None
        )

        # Extract additional info from log details
        if log.details:
            if "location" in log.details:
                event.location = log.details["location"]
            if "driver" in log.details:
                event.driver_info = log.details["driver"]
            if "cylinders" in log.details:
                event.cylinders_info = log.details["cylinders"]

        return event

    async def get_delivery_status(self, order_id: int) -> DeliveryStatus:
        """Get current delivery status"""
        # Try cache first
        cached = await cache.get([self.CACHE_PREFIX, str(order_id)])
        if cached:
            return DeliveryStatus(**cached)

        # Query database
        stmt = select(Order).where(Order.id == order_id)
        order = self.db.execute(stmt).scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Get latest log for status
        stmt = (
            select(OrderLog)
            .where(OrderLog.order_id == order_id)
            .order_by(OrderLog.created_at.desc())
            .limit(1)
        )
        latest_log = self.db.execute(stmt).scalar_one_or_none()

        status = DeliveryStatus(
            order_id=order.id,
            status=order.status,
            eta=order.expected_delivery,
            last_updated=latest_log.created_at if latest_log else order.updated_at,
            cylinders_loaded=len(order.cylinders),
            driver_name=latest_log.details.get("driver", {}).get("name") if latest_log and latest_log.details else None,
            driver_phone=latest_log.details.get("driver", {}).get("phone") if latest_log and latest_log.details else None,
            current_location=latest_log.details.get("location") if latest_log and latest_log.details else None,
            notes=latest_log.notes if latest_log else None
        )

        await self._cache_delivery_status(status)
        return status

    async def update_delivery_status(
        self,
        order_id: int,
        update: DeliveryUpdate,
        user_id: int,
        driver_info: Optional[dict] = None
    ) -> DeliveryStatus:
        """Update delivery status"""
        stmt = select(Order).where(Order.id == order_id)
        order = self.db.execute(stmt).scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.status not in [OrderStatus.ACCEPTED, OrderStatus.IN_TRANSIT, OrderStatus.OUT_FOR_DELIVERY]:
            raise HTTPException(status_code=400, detail="Order is not in delivery phase")

        # Update order status if provided
        if update.status != order.status:
            order.status = update.status

        # Update ETA if provided
        if update.eta:
            order.expected_delivery = update.eta

        # Create log entry with all details
        details = {
            "location": update.current_location,
            "status_update": update.model_dump()
        }
        if driver_info:
            details["driver"] = driver_info
            
        # Create order log entry
        order_log = OrderLog(
            order_id=order_id,
            event_type=OrderEventType.DELIVERY_UPDATE,
            created_by=user_id,
            details=details
        )
        self.db.add(order_log)
        self.db.commit()

        # Send notifications about delivery status update
        notification_service = NotificationService(self.db)
        await notification_service.send_delivery_update(
            order_id=order_id,
            status=update.status,
            eta=update.eta,
            current_location=update.current_location,
            driver_info=driver_info
        )
        
        # Get updated delivery status for response
        return self.get_delivery_status(order_id)

        log = OrderLog(
            order_id=order.id,
            event_type=OrderEventType.STATUS_CHANGED,
            old_status=order.status,
            new_status=update.status,
            created_by=user_id,
            notes=update.notes,
            details=details
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(order)
        self.db.refresh(log)

        # Prepare and cache new status
        status = DeliveryStatus(
            order_id=order.id,
            status=order.status,
            eta=order.expected_delivery,
            last_updated=log.created_at,
            cylinders_loaded=len(order.cylinders),
            driver_name=driver_info.get("name") if driver_info else None,
            driver_phone=driver_info.get("phone") if driver_info else None,
            current_location=update.current_location,
            notes=update.notes
        )

        await self._cache_delivery_status(status)
        return status

    async def get_delivery_timeline(self, order_id: int) -> DeliveryTimeline:
        """Get complete delivery timeline"""
        stmt = select(Order).where(Order.id == order_id)
        order = self.db.execute(stmt).scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Get all logs ordered by timestamp
        stmt = (
            select(OrderLog)
            .where(OrderLog.order_id == order_id)
            .order_by(OrderLog.created_at.asc())
        )
        logs = self.db.execute(stmt).scalars().all()

        # Convert logs to timeline events
        events = [self._create_timeline_event(log, order) for log in logs]

        # Get latest driver info from logs
        latest_driver = None
        for log in reversed(logs):
            if log.details and "driver" in log.details:
                latest_driver = log.details["driver"]
                break

        return DeliveryTimeline(
            order_id=order.id,
            current_status=order.status,
            events=events,
            eta=order.expected_delivery,
            driver_name=latest_driver.get("name") if latest_driver else None,
            driver_phone=latest_driver.get("phone") if latest_driver else None,
            cylinders_loaded=len(order.cylinders),
            cylinders_delivered=order.cylinders_sent
        )

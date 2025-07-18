from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.websocket import manager
from app.modules.orders.models import Order
from app.modules.users.models import User

class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.mail_config = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,
            MAIL_TLS=True,
            MAIL_SSL=False,
            USE_CREDENTIALS=True
        )
        self.fastmail = FastMail(self.mail_config)

    async def notify_new_order(self, order: Order, vendors: List[User]):
        """Notify vendors about a new order"""
        # WebSocket notification
        notification = {
            "type": "new_order",
            "data": {
                "order_id": order.id,
                "hospital_id": order.hospital_id,
                "quantity": order.quantity,
                "urgency": order.urgency,
                "delivery_location": order.delivery_location,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        # Notify each nearby vendor
        for vendor in vendors:
            await manager.notify_vendor(vendor.id, notification)

            # Send email notification
            message = MessageSchema(
                subject="New Gas Cylinder Order Available",
                recipients=[vendor.email],
                body=f"""
                New order available in your area!
                Order ID: {order.id}
                Quantity: {order.quantity} cylinders
                Urgency: {order.urgency}
                Please log in to your dashboard to accept the order.
                """,
                subtype="html"
            )
            await self.fastmail.send_message(message)

    async def send_delivery_update(
        self,
        order_id: int,
        status: str,
        eta: Optional[datetime] = None,
        current_location: Optional[Dict[str, float]] = None,
        driver_info: Optional[Dict[str, Any]] = None
    ):
        """Send delivery status update notifications"""
        # Get order details
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return

        # Create notification data
        notification = {
            "type": "delivery_update",
            "data": {
                "order_id": order_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        if eta:
            notification["data"]["eta"] = eta.isoformat()
        if current_location:
            notification["data"]["current_location"] = current_location
        if driver_info:
            notification["data"]["driver"] = driver_info

        # Send WebSocket notifications
        # Notify the hospital
        await manager.notify_hospital(order.hospital_id, notification)
        # Notify the vendor
        await manager.notify_vendor(order.vendor_id, notification)

        # Send email notifications
        hospital = self.db.query(User).filter(User.id == order.hospital_id).first()
        vendor = self.db.query(User).filter(User.id == order.vendor_id).first()

        # Email content
        status_message = f"Order #{order_id} status has been updated to: {status}"
        eta_message = f"\nExpected delivery time: {eta.strftime('%Y-%m-%d %H:%M:%S')}" if eta else ""
        driver_message = f"\nDriver: {driver_info.get('name', 'N/A')}" if driver_info else ""

        for recipient in [hospital, vendor]:
            if recipient and recipient.email:
                message = MessageSchema(
                    subject=f"Delivery Update - Order #{order_id}",
                    recipients=[recipient.email],
                    body=f"""
                    {status_message}
                    {eta_message}
                    {driver_message}
                    """,
                    subtype="html"
                )
                await self.fastmail.send_message(message)

    async def notify_order_accepted(self, order: Order, vendor: User):
        """Notify hospital that their order was accepted"""
        # WebSocket notification to hospital
        notification = {
            "type": "order_accepted",
            "data": {
                "order_id": order.id,
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "expected_delivery": order.expected_delivery.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await manager.notify_hospital(order.hospital_id, notification)

        # Send email notification
        hospital = self.db.query(User).filter(User.id == order.hospital_id).first()
        if hospital and hospital.email:
            message = MessageSchema(
                subject=f"Order #{order.id} Accepted",
                recipients=[hospital.email],
                body=f"""
                Your order has been accepted by {vendor.name}!
                Expected delivery: {order.expected_delivery}
                You can track your delivery in real-time on your dashboard.
                """,
                subtype="html"
            )
            await self.fastmail.send_message(message)

    async def notify_delivery_update(
        self,
        order: Order,
        status: str,
        eta: datetime,
        location: Optional[str] = None
    ):
        """Notify hospital about delivery updates"""
        # WebSocket notification
        notification = {
            "type": "delivery_update",
            "data": {
                "order_id": order.id,
                "status": status,
                "eta": eta.isoformat(),
                "current_location": location,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        await manager.notify_hospital(order.hospital_id, notification)

        # Send email for significant status changes
        if status in ["OUT_FOR_DELIVERY", "DELIVERED"]:
            hospital = self.db.query(User).filter(User.id == order.hospital_id).first()
            if hospital and hospital.email:
                message = MessageSchema(
                    subject=f"Order #{order.id} Update: {status}",
                    recipients=[hospital.email],
                    body=f"""
                    Your order status has been updated to: {status}
                    Expected arrival: {eta}
                    {f'Current location: {location}' if location else ''}
                    """,
                    subtype="html"
                )
                await self.fastmail.send_message(message)

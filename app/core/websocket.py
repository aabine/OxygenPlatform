from typing import Dict, Set
from fastapi import WebSocket
from app.modules.users.models import User

class ConnectionManager:
    def __init__(self):
        # Store active connections by user_id and type (hospital/vendor)
        self.hospital_connections: Dict[int, Set[WebSocket]] = {}
        self.vendor_connections: Dict[int, Set[WebSocket]] = {}
        
    async def connect_hospital(self, websocket: WebSocket, hospital_id: int):
        """Connect a hospital to websocket updates"""
        await websocket.accept()
        if hospital_id not in self.hospital_connections:
            self.hospital_connections[hospital_id] = set()
        self.hospital_connections[hospital_id].add(websocket)

    async def connect_vendor(self, websocket: WebSocket, vendor_id: int):
        """Connect a vendor to websocket updates"""
        await websocket.accept()
        if vendor_id not in self.vendor_connections:
            self.vendor_connections[vendor_id] = set()
        self.vendor_connections[vendor_id].add(websocket)

    def disconnect_hospital(self, websocket: WebSocket, hospital_id: int):
        """Disconnect a hospital"""
        if hospital_id in self.hospital_connections:
            self.hospital_connections[hospital_id].discard(websocket)
            if not self.hospital_connections[hospital_id]:
                del self.hospital_connections[hospital_id]

    def disconnect_vendor(self, websocket: WebSocket, vendor_id: int):
        """Disconnect a vendor"""
        if vendor_id in self.vendor_connections:
            self.vendor_connections[vendor_id].discard(websocket)
            if not self.vendor_connections[vendor_id]:
                del self.vendor_connections[vendor_id]

    async def notify_vendor(self, vendor_id: int, message: dict):
        """Send notification to a specific vendor"""
        if vendor_id in self.vendor_connections:
            for connection in self.vendor_connections[vendor_id]:
                try:
                    await connection.send_json(message)
                except:
                    # Connection might be closed
                    self.disconnect_vendor(connection, vendor_id)

    async def notify_hospital(self, hospital_id: int, message: dict):
        """Send notification to a specific hospital"""
        if hospital_id in self.hospital_connections:
            for connection in self.hospital_connections[hospital_id]:
                try:
                    await connection.send_json(message)
                except:
                    # Connection might be closed
                    self.disconnect_hospital(connection, hospital_id)

    async def broadcast_to_vendors(self, message: dict):
        """Broadcast message to all connected vendors"""
        for vendor_id in self.vendor_connections:
            await self.notify_vendor(vendor_id, message)

    async def broadcast_to_hospitals(self, message: dict):
        """Broadcast message to all connected hospitals"""
        for hospital_id in self.hospital_connections:
            await self.notify_hospital(hospital_id, message)

manager = ConnectionManager()

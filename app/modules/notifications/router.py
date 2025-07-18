from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.websocket import manager
from app.modules.auth.deps import get_current_user_ws
from app.modules.users.models import User

router = APIRouter()

@router.websocket("/ws/hospital/{hospital_id}")
async def hospital_websocket(
    websocket: WebSocket,
    hospital_id: int,
    current_user: User = Depends(get_current_user_ws)
):
    """WebSocket endpoint for hospitals to receive real-time updates"""
    if not current_user.is_hospital or current_user.id != hospital_id:
        await websocket.close(code=4003)
        return

    await manager.connect_hospital(websocket, hospital_id)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_hospital(websocket, hospital_id)

@router.websocket("/ws/vendor/{vendor_id}")
async def vendor_websocket(
    websocket: WebSocket,
    vendor_id: int,
    current_user: User = Depends(get_current_user_ws)
):
    """WebSocket endpoint for vendors to receive real-time updates"""
    if not current_user.is_vendor or current_user.id != vendor_id:
        await websocket.close(code=4003)
        return

    await manager.connect_vendor(websocket, vendor_id)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_vendor(websocket, vendor_id)

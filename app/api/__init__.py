from fastapi import APIRouter
from app.modules.users.router import router as users_router
from app.modules.auth.router import router as auth_router
from app.modules.cylinders.router import router as cylinders_router
from app.modules.orders.router import router as orders_router

api_router = APIRouter()

# Include module routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(cylinders_router)
api_router.include_router(orders_router)

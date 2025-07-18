from fastapi import APIRouter
from app.routes import users

api_v1_router = APIRouter()

api_v1_router.include_router(users.router, prefix="/users", tags=["users"])

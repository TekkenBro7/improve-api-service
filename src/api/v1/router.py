from fastapi import APIRouter

from src.api.v1.analytics import router as analytics_router
from src.api.v1.transactions import router as transaction_router
from src.api.v1.users import router as users_router

v1_router = APIRouter()
v1_router.include_router(users_router, prefix="/users", tags=["Users"])
v1_router.include_router(
    transaction_router, prefix="/transactions", tags=["Transactions"]
)
v1_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])

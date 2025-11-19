from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get(
    "/transactions",
    response_model=list[dict],
    status_code=status.HTTP_200_OK,
)
async def get_transaction_analysis(
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    return await AnalyticsService(session).get_weekly_analysis()

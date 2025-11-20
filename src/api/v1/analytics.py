from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.worker.tasks import generate_weekly_report

router = APIRouter()


@router.get(
    "/transactions",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
)
async def get_transaction_analysis(
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    generate_weekly_report.send()
    return {"message": "OK"}

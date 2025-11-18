from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.schemas.transaction import RequestTransactionModel, TransactionModel
from src.services.transactions_service import TransactionsService

router = APIRouter()


@router.get(
    "",
    response_model=Optional[list[TransactionModel]] | None,
    status_code=status.HTTP_200_OK,
)
async def get_transactions(
    user_id: Optional[int] = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[TransactionModel]:
    return await TransactionsService(session).get_transactions(user_id=user_id)


@router.post(
    "/{user_id}",
    response_model=Optional[TransactionModel] | None,
    status_code=status.HTTP_200_OK,
)
async def post_transaction(
    user_id: int,
    transaction: RequestTransactionModel,
    session: AsyncSession = Depends(get_async_session),
) -> TransactionModel:
    return await TransactionsService(session).create_transaction(user_id, transaction)


@router.patch(
    "/{transaction_id}/users/{user_id}",
    response_model=Optional[TransactionModel] | None,
    status_code=status.HTTP_200_OK,
)
async def rollback_transaction(
    user_id: int,
    transaction_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> TransactionModel:
    return await TransactionsService(session).rollback_transaction(
        user_id=user_id,
        transaction_id=transaction_id,
    )

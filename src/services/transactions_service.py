from decimal import Decimal
from typing import Optional

from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum, TransactionStatusEnum, UserStatusEnum
from src.database.repositories.transaction_repository import TransactionRepository
from src.database.repositories.user_balance_repository import UserBalanceRepository
from src.database.repositories.user_repository import UserRepository
from src.exceptions.general_exceptions import BadRequestDataException
from src.exceptions.transaction_exceptions import (
    CreateTransactionForBlockedUserException,
    NegativeBalanceException,
    TransactionAlreadyRollbackedException,
    TransactionDoesNotBelongToUserException,
    TransactionNotExistsException,
    UpdateTransactionForBlockedUserException,
)
from src.exceptions.user_exceptions import UserNotExistsException
from src.schemas.transaction import RequestTransactionModel, TransactionModel


class TransactionsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.transaction_repo = TransactionRepository(session)
        self.user_repo = UserRepository(session)
        self.balance_repo = UserBalanceRepository(session)

    async def get_transactions(self, user_id: Optional[int]) -> list[TransactionModel]:
        transactions = await self.transaction_repo.get_transactions(user_id)

        return [
            TransactionModel(
                id=transaction.id,
                user_id=transaction.user_id,
                currency=CurrencyEnum(transaction.currency),
                amount=float(str(transaction.amount)),
                status=TransactionStatusEnum(transaction.status),
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
            )
            for transaction in transactions
        ]

    async def create_transaction(
        self,
        user_id: int,
        transaction: RequestTransactionModel,
    ) -> TransactionModel:
        if user_id < 0:
            raise BadRequestDataException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unprocessable data in request",
            )

        if transaction.currency not in {str(x) for x in CurrencyEnum}:
            raise BadRequestDataException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Currency does not exist",
            )

        if transaction.amount == 0:
            raise BadRequestDataException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Transaction can not have zero amount",
            )

        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UserNotExistsException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id=`{user_id}` does not exist",
            )

        if user.status != UserStatusEnum.ACTIVE:
            raise CreateTransactionForBlockedUserException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id=`{user_id}` is blocked",
            )

        balance = await self.balance_repo.get_user_balance(user_id, transaction.currency)
        if not balance:
            raise NegativeBalanceException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No balance record for currency `{transaction.currency}`",
            )

        new_amount = Decimal(str(balance.amount)) + Decimal(str(transaction.amount))

        if new_amount < 0:
            raise NegativeBalanceException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Negative balance"
            )

        await self.balance_repo.update_balance(balance.id, new_amount)

        tr = await self.transaction_repo.create_transaction(
            user_id=user_id,
            currency=transaction.currency,
            amount=transaction.amount,
            status=TransactionStatusEnum.PROCESSED,
        )

        return TransactionModel(
            id=tr.id,
            user_id=tr.user_id,
            currency=CurrencyEnum(tr.currency),
            amount=float(str(tr.amount)),
            status=TransactionStatusEnum(tr.status),
            created_at=tr.created_at,
            updated_at=tr.updated_at,
        )

    async def rollback_transaction(
        self,
        user_id: int,
        transaction_id: int,
    ) -> TransactionModel:
        """
        Rollback a processed transaction for a given user.

        This method performs the following steps:
        1. Validates that `user_id` and `transaction_id` are positive integers.
        2. Checks that the user exists and is not blocked.
        3. Retrieves the transaction and validates that it belongs to the user
        and has not been rollbacked already.
        4. Fetches the user's balance for the transaction currency.
        5. Updates the balance by reversing the transaction amount:
            - If the transaction was a withdrawal (negative amount), the balance is increased.
            - If the transaction was a deposit (positive amount), the balance is decreased.
        6. Raises `NegativeBalanceException` if the updated balance would become negative.
        7. Updates the transaction status to `ROLLBACKED`.
        8. Returns the updated transaction as a `TransactionModel`.
        """
        if user_id < 0 or transaction_id < 0:
            raise BadRequestDataException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unprocessable data in request",
            )

        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UserNotExistsException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id=`{user_id}` does not exist",
            )

        if user.status == UserStatusEnum.BLOCKED:
            raise UpdateTransactionForBlockedUserException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User with id=`{user_id}` is blocked",
            )

        transaction = await self.transaction_repo.get_transaction_by_id(transaction_id)

        if not transaction:
            raise TransactionNotExistsException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transaction with id=`{transaction_id}` does not exist",
            )

        if transaction.user_id != user_id:
            raise TransactionDoesNotBelongToUserException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transaction with id=`{transaction_id}` does not belong to user with id=`{user_id}`",
            )

        if transaction.status == TransactionStatusEnum.ROLLBACKED:
            raise TransactionAlreadyRollbackedException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transaction with id=`{transaction_id}` is already rollbacked",
            )

        balance = await self.balance_repo.get_user_balance(
            user_id=user_id, currency=transaction.currency
        )

        if not balance:
            raise NegativeBalanceException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No balance record for currency `{transaction.currency}`",
            )

        new_amount = Decimal(str(balance.amount))
        transaction_amount = Decimal(str(transaction.amount))

        if transaction_amount < 0:
            new_amount += abs(transaction_amount)
        else:
            new_amount -= transaction_amount
        if new_amount < 0:
            raise NegativeBalanceException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Negative balance: {new_amount}",
            )

        await self.balance_repo.update_balance(balance.id, new_amount)

        updated_transaction = await self.transaction_repo.update_transaction_status(
            transaction_id,
            TransactionStatusEnum.ROLLBACKED,
        )

        return TransactionModel(
            id=updated_transaction.id,
            user_id=updated_transaction.user_id,
            currency=CurrencyEnum(updated_transaction.currency),
            amount=float(str(updated_transaction.amount)),
            status=TransactionStatusEnum(updated_transaction.status),
            created_at=updated_transaction.created_at,
            updated_at=updated_transaction.updated_at,
        )

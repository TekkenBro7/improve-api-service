from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.transaction import Transaction
from src.database.models.user import User
from src.database.repositories.transaction_repository import TransactionRepository
from src.database.repositories.user_repository import UserRepository


class TestTransactionRepository:
    @pytest_asyncio.fixture
    async def transaction_repo(self, db_session: AsyncSession) -> TransactionRepository:
        return TransactionRepository(db_session)

    @pytest_asyncio.fixture
    async def user_repo(self, db_session: AsyncSession) -> UserRepository:
        return UserRepository(db_session)

    @pytest_asyncio.fixture
    async def sample_user(self, user_repo: UserRepository) -> User:
        user = await user_repo.create_user_with_balances("test@example.com")
        return user

    @pytest_asyncio.fixture
    async def sample_transaction(
        self, transaction_repo: TransactionRepository, sample_user: User
    ) -> Transaction:
        transaction = await transaction_repo.create_transaction(
            user_id=sample_user.id, currency="USD", amount=100.0, status="PROCESSED"
        )
        return transaction

    @pytest_asyncio.fixture
    async def multiple_transactions(
        self, transaction_repo: TransactionRepository, sample_user: User
    ) -> list[Transaction]:
        transactions = []
        for i, currency in enumerate(["USD", "EUR", "BTC"]):
            transaction = await transaction_repo.create_transaction(
                user_id=sample_user.id,
                currency=currency,
                amount=50.0 + i * 10,
                status="PROCESSED",
            )
            transactions.append(transaction)
        return transactions

    @pytest.mark.asyncio
    async def test_create_transaction_success(
        self, transaction_repo: TransactionRepository, sample_user: User
    ) -> None:
        transaction = await transaction_repo.create_transaction(
            user_id=sample_user.id, currency="USD", amount=200.0, status="PROCESSED"
        )

        assert transaction.id is not None
        assert transaction.user_id == sample_user.id
        assert transaction.currency == "USD"
        assert transaction.amount == 200.0
        assert transaction.status == "PROCESSED"

    @pytest.mark.asyncio
    async def test_get_transaction_by_id_found(
        self, transaction_repo: TransactionRepository, sample_transaction: Transaction
    ) -> None:
        found_transaction = await transaction_repo.get_transaction_by_id(
            sample_transaction.id
        )

        assert found_transaction is not None
        assert found_transaction.id == sample_transaction.id
        assert found_transaction.user_id == sample_transaction.user_id

    @pytest.mark.asyncio
    async def test_get_transaction_by_id_not_found(
        self, transaction_repo: TransactionRepository
    ) -> None:
        found_transaction = await transaction_repo.get_transaction_by_id(99999)

        assert found_transaction is None

    @pytest.mark.asyncio
    async def test_update_transaction_status_success(
        self, transaction_repo: TransactionRepository, sample_transaction: Transaction
    ) -> None:
        updated_transaction = await transaction_repo.update_transaction_status(
            sample_transaction.id, "ROLLBACKED"
        )

        assert updated_transaction.id == sample_transaction.id
        assert updated_transaction.status == "ROLLBACKED"

        db_transaction = await transaction_repo.get_transaction_by_id(
            sample_transaction.id
        )
        assert db_transaction is not None
        assert db_transaction.status == "ROLLBACKED"

    @pytest.mark.asyncio
    async def test_get_transactions_all(
        self,
        transaction_repo: TransactionRepository,
        multiple_transactions: list[Transaction],
    ) -> None:
        transactions = await transaction_repo.get_transactions(user_id=None)

        assert len(transactions) >= 3
        assert all(isinstance(t, Transaction) for t in transactions)

    @pytest.mark.asyncio
    async def test_get_transactions_by_user_id(
        self, transaction_repo: TransactionRepository, sample_transaction: Transaction
    ) -> None:
        transactions = await transaction_repo.get_transactions(
            user_id=sample_transaction.user_id
        )

        assert len(transactions) >= 1
        assert all(t.user_id == sample_transaction.user_id for t in transactions)

    @pytest.mark.asyncio
    async def test_count_transactions_between(
        self, transaction_repo: TransactionRepository, sample_transaction: Transaction
    ) -> None:
        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        count = await transaction_repo.count_transactions_between(start_date, end_date)

        assert count >= 1

    @pytest.mark.asyncio
    async def test_count_transactions_between_no_transactions(
        self, transaction_repo: TransactionRepository
    ) -> None:
        future_date = date.today() + timedelta(days=365)

        count = await transaction_repo.count_transactions_between(
            future_date, future_date
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_transactions_between(
        self, transaction_repo: TransactionRepository, sample_transaction: Transaction
    ) -> None:
        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        transactions = await transaction_repo.get_transactions_between(
            start_date, end_date
        )

        assert len(transactions) >= 1
        assert any(t.id == sample_transaction.id for t in transactions)

    @pytest.mark.asyncio
    async def test_get_total_amount_between_usd(
        self, transaction_repo: TransactionRepository, sample_transaction: Transaction
    ) -> None:
        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        total_amount = await transaction_repo.get_total_amount_between(
            start_date, end_date
        )

        assert total_amount > Decimal("0")
        assert isinstance(total_amount, Decimal)

    @pytest.mark.asyncio
    async def test_get_total_amount_between_deposits_only(
        self, transaction_repo: TransactionRepository, sample_user: User
    ) -> None:
        await transaction_repo.create_transaction(
            user_id=sample_user.id, currency="USD", amount=50.0, status="PROCESSED"
        )

        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        total_amount = await transaction_repo.get_total_amount_between(
            start_date, end_date, deposits_only=True
        )

        assert total_amount > Decimal("0")

    @pytest.mark.asyncio
    async def test_count_transactions_exclude_rollbacked(
        self, transaction_repo: TransactionRepository, sample_user: User
    ) -> None:
        await transaction_repo.create_transaction(
            user_id=sample_user.id, currency="USD", amount=100.0, status="ROLLBACKED"
        )

        today = date.today()
        start_date = today - timedelta(days=1)
        end_date = today + timedelta(days=1)

        count_with_rollbacked = await transaction_repo.count_transactions_between(
            start_date, end_date, exclude_rollbacked=False
        )
        count_without_rollbacked = await transaction_repo.count_transactions_between(
            start_date, end_date, exclude_rollbacked=True
        )

        assert count_with_rollbacked >= count_without_rollbacked

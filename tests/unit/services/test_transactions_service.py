import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum, UserStatusEnum
from src.schemas.transaction import RequestTransactionModel
from src.schemas.user import RequestUserModel, RequestUserUpdateModel, UserModel
from src.services.transactions_service import TransactionsService
from src.services.user_service import UserService


class TestTransactionsServiceIntegration:
    @pytest_asyncio.fixture
    async def user_service(self, db_session: AsyncSession) -> UserService:
        return UserService(db_session)

    @pytest_asyncio.fixture
    async def transactions_service(self, db_session: AsyncSession) -> TransactionsService:
        return TransactionsService(db_session)

    @pytest_asyncio.fixture
    async def active_user(self, user_service: UserService) -> UserModel:
        user_data = RequestUserModel(email="active_user@example.com")
        user = await user_service.create_user(user_data)
        return user

    @pytest_asyncio.fixture
    async def blocked_user(self, user_service: UserService) -> UserModel:
        user_data = RequestUserModel(email="blocked_user@example.com")
        user = await user_service.create_user(user_data)

        update_data = RequestUserUpdateModel(status=UserStatusEnum.BLOCKED)
        assert user.id is not None
        blocked_user = await user_service.update_user_status(user.id, update_data)
        return blocked_user

    @pytest.mark.asyncio
    async def test_deposit_and_withdrawal_flow(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        deposit_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=300.0)

        assert active_user.id is not None

        deposit = await transactions_service.create_transaction(
            active_user.id, deposit_data
        )

        withdrawal_data = RequestTransactionModel(
            currency=CurrencyEnum.USD, amount=-150.0
        )
        withdrawal = await transactions_service.create_transaction(
            active_user.id, withdrawal_data
        )

        assert deposit.amount == 300.0
        assert withdrawal.amount == -150.0

    @pytest.mark.asyncio
    async def test_transaction_rollback_flow(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        deposit_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=200.0)

        assert active_user.id is not None

        deposit = await transactions_service.create_transaction(
            active_user.id, deposit_data
        )

        assert deposit.id is not None
        rolled_back = await transactions_service.rollback_transaction(
            active_user.id, deposit.id
        )

        assert rolled_back.status == "ROLLBACKED"

    @pytest.mark.asyncio
    async def test_create_transaction_for_blocked_user(
        self, transactions_service: TransactionsService, blocked_user: UserModel
    ) -> None:
        from src.exceptions.transaction_exceptions import (
            CreateTransactionForBlockedUserException,
        )

        transaction_data = RequestTransactionModel(
            currency=CurrencyEnum.USD, amount=100.0
        )

        with pytest.raises(CreateTransactionForBlockedUserException):
            assert blocked_user.id is not None
            await transactions_service.create_transaction(
                blocked_user.id, transaction_data
            )

    @pytest.mark.asyncio
    async def test_rollback_for_blocked_user(
        self, transactions_service: TransactionsService, user_service: UserService
    ) -> None:
        from src.exceptions.transaction_exceptions import (
            UpdateTransactionForBlockedUserException,
        )

        user_data = RequestUserModel(email="rollback_test@example.com")
        user = await user_service.create_user(user_data)

        transaction_data = RequestTransactionModel(
            currency=CurrencyEnum.USD, amount=100.0
        )
        assert user.id is not None
        transaction = await transactions_service.create_transaction(
            user.id, transaction_data
        )

        update_data = RequestUserUpdateModel(status=UserStatusEnum.BLOCKED)
        await user_service.update_user_status(user.id, update_data)

        with pytest.raises(UpdateTransactionForBlockedUserException):
            assert transaction.id is not None
            await transactions_service.rollback_transaction(user.id, transaction.id)

    @pytest.mark.asyncio
    async def test_multiple_currency_transactions(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        usd_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=100.0)
        eur_data = RequestTransactionModel(currency=CurrencyEnum.EUR, amount=50.0)

        assert active_user.id is not None
        usd_tx = await transactions_service.create_transaction(active_user.id, usd_data)
        eur_tx = await transactions_service.create_transaction(active_user.id, eur_data)

        assert usd_tx.currency == CurrencyEnum.USD
        assert eur_tx.currency == CurrencyEnum.EUR

    @pytest.mark.asyncio
    async def test_get_transactions_for_specific_user(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        transaction_data = RequestTransactionModel(
            currency=CurrencyEnum.USD, amount=100.0
        )

        assert active_user.id is not None

        transaction = await transactions_service.create_transaction(
            active_user.id, transaction_data
        )

        transactions = await transactions_service.get_transactions(active_user.id)

        assert len(transactions) >= 1
        assert any(t.id == transaction.id for t in transactions)
        assert all(t.user_id == active_user.id for t in transactions)

    @pytest.mark.asyncio
    async def test_get_all_transactions(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        transaction_data = RequestTransactionModel(
            currency=CurrencyEnum.USD, amount=100.0
        )

        assert active_user.id is not None

        transaction = await transactions_service.create_transaction(
            active_user.id, transaction_data
        )

        transactions = await transactions_service.get_transactions(None)

        assert len(transactions) >= 1
        assert any(t.id == transaction.id for t in transactions)

    @pytest.mark.asyncio
    async def test_rollback_withdrawal_transaction(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        deposit_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=500.0)

        assert active_user.id is not None
        await transactions_service.create_transaction(active_user.id, deposit_data)

        withdrawal_data = RequestTransactionModel(
            currency=CurrencyEnum.USD, amount=-200.0
        )
        withdrawal = await transactions_service.create_transaction(
            active_user.id, withdrawal_data
        )

        assert withdrawal.id is not None
        rolled_back = await transactions_service.rollback_transaction(
            active_user.id, withdrawal.id
        )

        assert rolled_back.status == "ROLLBACKED"
        assert rolled_back.amount == -200.0

    @pytest.mark.asyncio
    async def test_sequential_transactions_and_rollbacks(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        deposit1 = RequestTransactionModel(currency=CurrencyEnum.USD, amount=100.0)

        assert active_user.id is not None

        _ = await transactions_service.create_transaction(active_user.id, deposit1)

        deposit2 = RequestTransactionModel(currency=CurrencyEnum.USD, amount=200.0)
        tx2 = await transactions_service.create_transaction(active_user.id, deposit2)

        withdrawal = RequestTransactionModel(currency=CurrencyEnum.USD, amount=-50.0)
        _ = await transactions_service.create_transaction(active_user.id, withdrawal)

        assert tx2.id is not None
        rolled_back_tx2 = await transactions_service.rollback_transaction(
            active_user.id, tx2.id
        )

        transactions = await transactions_service.get_transactions(active_user.id)

        assert len(transactions) == 3
        assert rolled_back_tx2.status == "ROLLBACKED"

    @pytest.mark.asyncio
    async def test_transaction_with_different_currencies_balance(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        usd_deposit = RequestTransactionModel(currency=CurrencyEnum.USD, amount=100.0)
        eur_deposit = RequestTransactionModel(currency=CurrencyEnum.EUR, amount=50.0)
        btc_deposit = RequestTransactionModel(currency=CurrencyEnum.BTC, amount=0.001)

        assert active_user.id is not None

        usd_tx = await transactions_service.create_transaction(
            active_user.id, usd_deposit
        )
        eur_tx = await transactions_service.create_transaction(
            active_user.id, eur_deposit
        )
        btc_tx = await transactions_service.create_transaction(
            active_user.id, btc_deposit
        )

        assert usd_tx.currency == CurrencyEnum.USD
        assert eur_tx.currency == CurrencyEnum.EUR
        assert btc_tx.currency == CurrencyEnum.BTC

    @pytest.mark.asyncio
    async def test_cannot_rollback_already_rollbacked_transaction(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        from src.exceptions.transaction_exceptions import (
            TransactionAlreadyRollbackedException,
        )

        assert active_user.id is not None

        deposit_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=100.0)
        deposit = await transactions_service.create_transaction(
            active_user.id, deposit_data
        )

        assert deposit.id is not None
        await transactions_service.rollback_transaction(active_user.id, deposit.id)

        with pytest.raises(TransactionAlreadyRollbackedException):
            await transactions_service.rollback_transaction(active_user.id, deposit.id)

    @pytest.mark.asyncio
    async def test_cannot_rollback_other_user_transaction(
        self, transactions_service: TransactionsService, user_service: UserService
    ) -> None:
        from src.exceptions.transaction_exceptions import (
            TransactionDoesNotBelongToUserException,
        )

        user1_data = RequestUserModel(email="user1@example.com")
        user1 = await user_service.create_user(user1_data)

        user2_data = RequestUserModel(email="user2@example.com")
        user2 = await user_service.create_user(user2_data)

        transaction_data = RequestTransactionModel(
            currency=CurrencyEnum.USD, amount=100.0
        )
        assert user1.id is not None
        transaction = await transactions_service.create_transaction(
            user1.id, transaction_data
        )

        with pytest.raises(TransactionDoesNotBelongToUserException):
            assert user2.id is not None
            assert transaction.id is not None
            await transactions_service.rollback_transaction(user2.id, transaction.id)

    @pytest.mark.asyncio
    async def test_transaction_creates_correct_model_fields(
        self, transactions_service: TransactionsService, active_user: UserModel
    ) -> None:
        transaction_data = RequestTransactionModel(currency=CurrencyEnum.USD, amount=75.5)

        assert active_user.id is not None

        transaction = await transactions_service.create_transaction(
            active_user.id, transaction_data
        )

        assert transaction.id is not None
        assert transaction.user_id == active_user.id
        assert transaction.currency == CurrencyEnum.USD
        assert transaction.amount == 75.5
        assert transaction.status == "PROCESSED"
        assert transaction.created_at is not None
        assert transaction.updated_at is not None

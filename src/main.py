from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, status
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums import CurrencyEnum, TransactionStatusEnum, UserStatusEnum
from src.database.models.transaction import Transaction
from src.database.models.user import User, UserBalance
from src.database.repositories.report_repository import ReportRepository
from src.database.repositories.transaction_repository import TransactionRepository
from src.database.repositories.user_repository import UserRepository
from src.database.session import get_async_session
from src.exceptions import (
    BadRequestDataException,
    CreateTransactionForBlockedUserException,
    NegativeBalanceException,
    TransactionAlreadyRollbackedException,
    TransactionDoesNotBelongToUserException,
    TransactionNotExistsException,
    UpdateTransactionForBlockedUserException,
    UserAlreadyActiveException,
    UserAlreadyBlockedException,
    UserAlreadyExistsException,
    UserNotExistsException,
)
from src.schemas.transaction import (
    RequestTransactionModel,
    TransactionModel,
)
from src.schemas.user import (
    RequestUserModel,
    RequestUserUpdateModel,
    ResponseUserBalanceModel,
    ResponseUserModel,
    UserModel,
)

app = FastAPI()


@app.get(
    "/users",
    response_model=Optional[list[ResponseUserModel]] | None,
    status_code=status.HTTP_200_OK,
)
async def get_users(
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    user_status: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[ResponseUserModel]:
    q = select(User).order_by(User.created.desc())
    if user_id is not None:
        q = q.where(User.id == user_id)
    if email is not None:
        q = q.where(User.email == email)
    if user_status is not None:
        q = q.where(User.status == user_status)
    users_result = await session.execute(q)
    users = users_result.scalars().all()
    results = []
    for user in users:
        created_dt: datetime = (
            user.created if isinstance(user.created, datetime) else datetime.utcnow()
        )

        result = ResponseUserModel(
            id=user.id,
            email=user.email,
            status=UserStatusEnum(user.status),
            created=created_dt,
        )
        balances_result = await session.execute(
            select(UserBalance).where(UserBalance.user_id == user.id)
        )
        balances = balances_result.scalars().all()

        balance_models = []
        for balance in balances:
            balance_model = ResponseUserBalanceModel(
                currency=CurrencyEnum(balance.currency), amount=float(str(balance.amount))
            )
            balance_models.append(balance_model)

        result.balances = sorted(
            balance_models, key=lambda x: x.amount if x.amount is not None else 0.0
        )

        results.append(result)

    return sorted(
        results,
        key=lambda x: x.created if x.created is not None else datetime.min,
        reverse=True,
    )


@app.post("/users", status_code=status.HTTP_200_OK)
async def post_user(
    user: RequestUserModel, session: AsyncSession = Depends(get_async_session)
) -> UserModel:
    email = user.email.strip()
    email = "".join([x for x in email if x != " "])
    if len(email) == 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email can't consist entirely of spaces",
        )
    existing_user_result = await session.execute(
        select(User).where(User.email == user.email)
    )
    if existing_user_result.scalar_one_or_none():
        raise UserAlreadyExistsException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with email=`{0}` already exists".format(user.email),
        )
    db_user = User(email=user.email, status="ACTIVE", created=datetime.utcnow())
    session.add(db_user)
    await session.commit()
    currencies = list({str(x) for x in CurrencyEnum})
    for currency in currencies:
        user_balance = UserBalance(
            user_id=db_user.id, currency=currency, amount=0, created=datetime.utcnow()
        )
        session.add(user_balance)
        await session.commit()

    user_result = await session.execute(select(User).where(User.email == user.email))
    result = user_result.scalar_one()

    created_dt: datetime = (
        result.created if isinstance(result.created, datetime) else datetime.utcnow()
    )

    return UserModel(
        id=result.id,
        email=result.email,
        status=UserStatusEnum(result.status),
        created=created_dt,
    )


@app.patch("/users/{user_id}", response_model=Optional[UserModel] | None)
async def patch_user(
    user_id: int,
    user: RequestUserUpdateModel,
    session: AsyncSession = Depends(get_async_session),
) -> UserModel:
    if user_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unprocessable data in request",
        )
    user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = user_result.scalar_one_or_none()
    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with id=`{0}` does not exist".format(user_id),
        )
    if db_user.status == "BLOCKED" and user.status == "BLOCKED":
        raise UserAlreadyBlockedException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with id=`{0}` is already blocked".format(user_id),
        )
    if db_user.status == "ACTIVE" and user.status == "ACTIVE":
        raise UserAlreadyActiveException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with id=`{0}` is already active".format(user_id),
        )
    await session.execute(
        update(User).values(**{"status": user.status}).where(User.id == user_id)
    )
    await session.commit()
    user_result = await session.execute(select(User).where(User.id == user_id))
    changed_user = user_result.scalar_one()

    created_dt = (
        changed_user.created if isinstance(changed_user.created, datetime) else None
    )

    result = UserModel(
        id=changed_user.id,
        email=changed_user.email,
        status=UserStatusEnum(changed_user.status),
        created=created_dt,
    )
    return result


@app.get(
    "/transactions",
    response_model=Optional[list[TransactionModel]] | None,
    status_code=status.HTTP_200_OK,
)
async def get_transactions(
    user_id: Optional[int] = None,
    session: AsyncSession = Depends(get_async_session),
) -> list[TransactionModel]:
    q = select(Transaction).order_by(Transaction.created.desc())
    if user_id:
        q = q.where(Transaction.user_id == user_id)

    transactions_result = await session.execute(q)
    transactions = transactions_result.scalars().all()
    results = []
    for t in transactions:
        created_dt = t.created if isinstance(t.created, datetime) else None

        result = TransactionModel(
            id=t.id,
            user_id=t.user_id,
            currency=CurrencyEnum(t.currency),
            amount=float(str(t.amount)),
            status=TransactionStatusEnum(t.status),
            created=created_dt,
        )
        results.append(result)
    return results


@app.post(
    "/{user_id}/transactions",
    response_model=Optional[TransactionModel] | None,
    status_code=status.HTTP_200_OK,
)
async def post_transaction(
    user_id: int,
    transaction: RequestTransactionModel,
    session: AsyncSession = Depends(get_async_session),
) -> None:
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

    user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = user_result.scalar_one_or_none()
    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with id=`{0}` does not exist".format(user_id),
        )
    if db_user.status != "ACTIVE":
        raise CreateTransactionForBlockedUserException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with id=`{0}` is blocked".format(user_id),
        )

    balance_result = await session.execute(
        select(UserBalance).where(
            (UserBalance.user_id == user_id)
            & (UserBalance.currency == transaction.currency)
        )
    )
    db_user_balance = balance_result.scalar_one_or_none()
    if not db_user_balance:
        raise NegativeBalanceException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No balance record for currency `{transaction.currency}`",
        )

    new_amount = Decimal(str(db_user_balance.amount)) + Decimal(str(transaction.amount))

    if new_amount < 0:
        raise NegativeBalanceException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Negative balance"
        )

    await session.execute(
        update(UserBalance)
        .values(**{"amount": transaction.amount})
        .where(UserBalance.id == db_user_balance.id)
    )
    await session.commit()
    await session.execute(
        insert(Transaction).values(
            **{
                "user_id": db_user.id,
                "currency": transaction.currency,
                "amount": transaction.amount,
                "status": "PROCESSED",
                "created": datetime.utcnow(),
            }
        )
    )
    await session.commit()


@app.patch(
    "/{user_id}/transactions/{transaction_id}",
    response_model=Optional[TransactionModel] | None,
)
async def patch_rollback_transaction(
    user_id: int, transaction_id: int, session: AsyncSession = Depends(get_async_session)
) -> None:
    if user_id < 0 or transaction_id < 0:
        raise BadRequestDataException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unprocessable data in request",
        )
    user_result = await session.execute(select(User).where(User.id == user_id))
    db_user = user_result.scalar_one_or_none()
    if not db_user:
        raise UserNotExistsException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with id=`{0}` does not exist".format(user_id),
        )
    transaction_result = await session.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    db_transaction = transaction_result.scalar_one_or_none()
    if not db_transaction:
        raise TransactionNotExistsException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction with id=`{0}` does not exist".format(transaction_id),
        )
    if db_transaction.user_id != db_user.id:
        raise TransactionDoesNotBelongToUserException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction with id=`{0}` does not belong to user with id=`{1}`".format(
                transaction_id, user_id
            ),
        )
    if db_transaction.status == "ROLLBACKED":
        raise TransactionAlreadyRollbackedException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction with id=`{0}` is already rollbacked".format(
                transaction_id
            ),
        )
    if db_user.status == "BLOCKED":
        raise UpdateTransactionForBlockedUserException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with id=`{0}` is blocked".format(user_id),
        )

    balance_result = await session.execute(
        select(UserBalance).where(
            (UserBalance.user_id == user_id)
            & (UserBalance.currency == db_transaction.currency)
        )
    )
    db_user_balance = balance_result.scalar_one_or_none()
    if not db_user_balance:
        raise NegativeBalanceException(
            status_code=400,
            detail=f"No balance record for currency `{db_transaction.currency}`",
        )

    new_amount = Decimal(str(db_user_balance.amount))
    transaction_amount = Decimal(str(db_transaction.amount))

    if transaction_amount < 0:
        new_amount += abs(transaction_amount)
    else:
        new_amount -= transaction_amount
    if new_amount < 0:
        raise NegativeBalanceException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Negative balance: {new_amount}",
        )
    await session.execute(
        update(UserBalance)
        .values(**{"amount": new_amount})
        .where(UserBalance.id == db_user_balance.id)
    )
    await session.commit()
    await session.execute(update(Transaction).values(**{"status": "ROLLBACKED"}))
    await session.commit()


@app.get(
    "/transactions/analysis",
    response_model=Optional[list] | None,
    status_code=status.HTTP_200_OK,
)
async def get_transaction_analysis(
    session: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    user_repo = UserRepository(session)
    tx_repo = TransactionRepository(session)
    report_repo = ReportRepository(session)

    dt_gt = datetime.utcnow().date() - timedelta(weeks=1) + timedelta(days=1)
    dt_lt = datetime.utcnow().date()
    results = []
    for i in range(52):
        registered_users_count = await user_repo.count_registered_between(dt_gt, dt_lt)

        registered_and_deposit_users_count = (
            await report_repo.count_users_with_deposit_between(dt_from=dt_gt, dt_to=dt_lt)
        )

        registered_and_not_rollbacked_deposit_users_count = (
            await report_repo.count_users_with_non_rollbacked_deposits(
                dt_from=dt_gt, dt_to=dt_lt
            )
        )

        not_rollbacked_deposit_amount = await tx_repo.get_total_amount_between(
            dt_from=dt_gt, dt_to=dt_lt, deposits_only=True, exclude_rollbacked=True
        )

        not_rollbacked_withdraw_amount = await tx_repo.get_total_amount_between(
            dt_from=dt_gt, dt_to=dt_lt, withdraws_only=True, exclude_rollbacked=True
        )

        transactions_count = await tx_repo.count_transactions_between(dt_gt, dt_lt)

        not_rollbacked_transactions_count = await tx_repo.count_transactions_between(
            dt_gt, dt_lt, exclude_rollbacked=True
        )

        result = {
            "start_date": dt_gt,
            "end_date": dt_lt,
            "registered_users_count": registered_users_count,
            "registered_and_deposit_users_count": registered_and_deposit_users_count,
            "registered_and_not_rollbacked_deposit_users_count": registered_and_not_rollbacked_deposit_users_count,
            "not_rollbacked_deposit_amount": not_rollbacked_deposit_amount,
            "not_rollbacked_withdraw_amount": not_rollbacked_withdraw_amount,
            "transactions_count": transactions_count,
            "not_rollbacked_transactions_count": not_rollbacked_transactions_count,
        }
        for field in (
            "registered_users_count",
            "registered_and_deposit_users_count",
            "registered_and_not_rollbacked_deposit_users_count",
            "not_rollbacked_deposit_amount",
            "not_rollbacked_withdraw_amount",
            "transactions_count",
            "not_rollbacked_transactions_count",
        ):
            if result[field] > 0:  # type: ignore
                results.append(result)
                break
        dt_gt -= timedelta(weeks=1)
        dt_lt -= timedelta(weeks=1)
    return results


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7999, reload=True)

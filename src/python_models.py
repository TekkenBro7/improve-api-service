from datetime import datetime
from enum import StrEnum
from typing import Any, Optional

from pydantic import BaseModel
from pydantic.v1 import root_validator


class CurrencyEnum(StrEnum):
    USD = "USD"
    EUR = "EUR"
    AUD = "AUD"
    CAD = "CAD"
    ARS = "ARS"
    PLN = "PLN"
    BTC = "BTC"
    ETH = "ETH"
    DOGE = "DOGE"
    USDT = "USDT"


class UserStatusEnum(StrEnum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"


class TransactionStatusEnum(StrEnum):
    processed = "PROCESSED"
    roll_backed = "ROLLBACKED"


class RequestUserModel(BaseModel):
    email: str


class RequestUserUpdateModel(BaseModel):
    status: UserStatusEnum


class ResponseUserBalanceModel(BaseModel):
    currency: Optional[CurrencyEnum] = None
    amount: Optional[float] = None


class ResponseUserModel(BaseModel):
    id: Optional[int]
    email: Optional[str] = None
    status: Optional[UserStatusEnum] = None
    created: Optional[datetime] = None
    balances: Optional[list[ResponseUserBalanceModel]] = None


class UserModel(BaseModel):
    id: Optional[int]
    email: Optional[str] = None
    status: Optional[UserStatusEnum] = None
    created: Optional[datetime] = None


class UserBalanceModel(BaseModel):
    id: Optional[int]
    user_id: Optional[int] = None
    currency: Optional[CurrencyEnum] = None
    amount: Optional[float] = None

    @root_validator(pre=True)
    def validate_not_negative(self, values: dict[str, Any]) -> dict[str, Any]:
        if "amount" in values and values.get("amount"):
            if values["amount"] < 0:
                raise ValueError("Amount cannot be negative")

        return values


class RequestTransactionModel(BaseModel):
    currency: CurrencyEnum
    amount: float


class TransactionModel(BaseModel):
    id: Optional[int]
    user_id: Optional[int] = None
    currency: Optional[CurrencyEnum] = None
    amount: Optional[float] = None
    status: Optional[TransactionStatusEnum] = None
    created: Optional[datetime] = None

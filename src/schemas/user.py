from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from src.core.enums import CurrencyEnum, UserStatusEnum


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
    created_at: Optional[datetime] = None
    balances: Optional[list[ResponseUserBalanceModel]] = None


class UserModel(BaseModel):
    id: Optional[int]
    email: Optional[str] = None
    status: Optional[UserStatusEnum] = None
    created_at: Optional[datetime] = None


class UserBalanceModel(BaseModel):
    id: Optional[int]
    user_id: Optional[int] = None
    currency: Optional[CurrencyEnum] = None
    amount: Optional[float] = None

    @field_validator("amount", mode="before")
    def validate_not_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Amount cannot be negative")
        return value

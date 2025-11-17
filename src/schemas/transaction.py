from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.core.enums import CurrencyEnum, TransactionStatusEnum


class RequestTransactionModel(BaseModel):
    currency: CurrencyEnum
    amount: float


class TransactionModel(BaseModel):
    id: Optional[int]
    user_id: Optional[int] = None
    currency: Optional[CurrencyEnum] = None
    amount: Optional[float] = None
    status: Optional[TransactionStatusEnum] = None
    created_at: Optional[datetime] = None

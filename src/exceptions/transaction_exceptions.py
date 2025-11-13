from fastapi import HTTPException


class TransactionNotExistsException(HTTPException):
    pass


class TransactionDoesNotBelongToUserException(HTTPException):
    pass


class CreateTransactionForBlockedUserException(HTTPException):
    pass


class UpdateTransactionForBlockedUserException(HTTPException):
    pass


class TransactionAlreadyRollbackedException(HTTPException):
    pass


class NegativeBalanceException(HTTPException):
    pass

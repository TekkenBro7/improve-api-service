from fastapi import HTTPException


class UserAlreadyExistsException(HTTPException):
    pass


class UserNotExistsException(HTTPException):
    pass


class UserAlreadyBlockedException(HTTPException):
    pass


class UserAlreadyActiveException(HTTPException):
    pass


class BadRequestDataException(HTTPException):
    pass


class NegativeBalanceException(HTTPException):
    pass


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

from fastapi import HTTPException


class UserAlreadyExistsException(HTTPException):
    pass


class UserNotExistsException(HTTPException):
    pass


class UserAlreadyBlockedException(HTTPException):
    pass


class UserAlreadyActiveException(HTTPException):
    pass

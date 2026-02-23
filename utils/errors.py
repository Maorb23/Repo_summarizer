# /utils/errors.py
# raised when the client sends a bad request, e.g. missing required fields, invalid data types, etc.
from dataclasses import dataclass


@dataclass
class AppError(Exception):
    status_code: int
    message: str


def bad_request(msg: str) -> AppError:
    return AppError(400, msg)


def not_found(msg: str) -> AppError:
    return AppError(404, msg)


def upstream_error(msg: str) -> AppError:
    return AppError(502, msg)
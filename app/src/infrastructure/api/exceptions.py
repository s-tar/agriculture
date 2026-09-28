from typing import Any

from fastapi.exceptions import RequestValidationError
from pydantic_core import ErrorDetails


class ValidationError(RequestValidationError):
    def __init__(self, field_name: str, field_value: Any, message: str):
        super().__init__(
            [
                ErrorDetails(
                    type="not_valid",
                    msg=message,
                    loc=("body", field_name),
                    input=field_value,
                )
            ],
        )

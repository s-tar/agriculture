from fastapi.exceptions import RequestValidationError
from pydantic_core import ErrorDetails


class ValidationError(RequestValidationError):
    def __init__(self, field_name: str, message: str):
        super().__init__(
            [
                ErrorDetails(
                    type="not_valid",
                    msg=message,
                    loc=("body", field_name),
                )
            ],
        )

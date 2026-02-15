from fastapi import status


class AppError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(message)
        self.message = message


class PortInUseError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "PORT_IN_USE"
"""Error envelope per docs/07 §3: {"error": {code, message, details?}}."""


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def err(status: int, code: str, message: str, details: dict | None = None) -> ApiError:
    return ApiError(status, code, message, details)

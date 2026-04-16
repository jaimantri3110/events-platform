import logging

from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(exc, ValidationError):
        if isinstance(response.data, dict):
            messages = []
            for field, errors in response.data.items():
                if isinstance(errors, list):
                    messages.append(f"{field}: {' '.join(str(e) for e in errors)}")
                else:
                    messages.append(f"{field}: {errors}")
            response.data = {
                "detail": " ".join(messages),
                "code": "validation_error",
            }
    elif isinstance(response.data, dict):
        detail = response.data.get("detail", str(response.data))
        code = response.data.get("code", getattr(exc, "default_code", "error"))
        response.data = {"detail": str(detail), "code": str(code)}

    logger.warning(
        "api_error",
        extra={
            "status_code": response.status_code,
            "detail": response.data.get("detail", "") if isinstance(response.data, dict) else "",
            "code": response.data.get("code", "") if isinstance(response.data, dict) else "",
            "view": str(context.get("view", "")),
        },
    )
    return response

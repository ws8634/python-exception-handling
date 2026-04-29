"""Application/orchestration layer.

This layer:
- Collects domain exceptions
- Transforms them into stable forms
- Does NOT print traceback to users
- Logs full stack traces for debugging
"""

from resilient_app.application.service import (
    AppResult,
    ApplicationError,
    ExternalService,
    ExternalServiceError,
)

__all__ = [
    "AppResult",
    "ApplicationError",
    "ExternalService",
    "ExternalServiceError",
]

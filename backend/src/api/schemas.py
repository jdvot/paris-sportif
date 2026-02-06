"""Shared API schemas."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response for OpenAPI documentation."""

    detail: str

    model_config = {"json_schema_extra": {"examples": [{"detail": "Not found"}]}}

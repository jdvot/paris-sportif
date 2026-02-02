"""Common HTTP error response models for OpenAPI documentation.

These models help FastAPI generate proper OpenAPI schema for authentication errors.
"""

from pydantic import BaseModel


class HTTPErrorResponse(BaseModel):
    """Standard HTTP error response."""
    detail: str


# Common response definitions for route decorators
AUTH_RESPONSES = {
    401: {
        "model": HTTPErrorResponse,
        "description": "Authentification requise - Token manquant ou invalide",
    },
}

PREMIUM_RESPONSES = {
    401: {
        "model": HTTPErrorResponse,
        "description": "Authentification requise - Token manquant ou invalide",
    },
    403: {
        "model": HTTPErrorResponse,
        "description": "Accès refusé - Abonnement premium requis",
    },
}

ADMIN_RESPONSES = {
    401: {
        "model": HTTPErrorResponse,
        "description": "Authentification requise - Token manquant ou invalide",
    },
    403: {
        "model": HTTPErrorResponse,
        "description": "Accès refusé - Droits administrateur requis",
    },
}

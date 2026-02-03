"""Debug endpoints for diagnosing configuration and API connectivity.

Admin only endpoints.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter

from src.auth import ADMIN_RESPONSES, AdminUser
from src.core.config import settings
from src.data.sources.football_data import get_football_data_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api-status", responses=ADMIN_RESPONSES)
async def debug_api_status(user: AdminUser) -> dict[str, Any]:
    """
    Debug endpoint to verify football-data.org API configuration.

    Returns detailed information about:
    - API key configuration
    - HTTP header status
    - Live API connectivity test
    """
    client = get_football_data_client()

    # Check API key
    api_key_present = bool(settings.football_data_api_key)
    api_key_length = len(settings.football_data_api_key) if api_key_present else 0
    api_key_last_4 = settings.football_data_api_key[-4:] if api_key_present else "N/A"

    # Check client headers
    headers_configured = bool(client.headers)
    token_in_headers = "X-Auth-Token" in client.headers if client.headers else False

    # Test actual connectivity to API
    connectivity_status = "unknown"
    connectivity_error = None
    response_status_code = None

    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"{client.BASE_URL}/competitions",
                headers=client.headers,
                timeout=10.0,
            )
            response_status_code = response.status_code

            if response_status_code == 200:
                connectivity_status = "success"
            elif response_status_code == 401:
                connectivity_status = "unauthorized"
                connectivity_error = "Invalid API key (401 Unauthorized)"
            elif response_status_code == 403:
                connectivity_status = "forbidden"
                connectivity_error = "API key rejected (403 Forbidden)"
            elif response_status_code == 429:
                connectivity_status = "rate_limited"
                connectivity_error = "Rate limit exceeded (429)"
            else:
                connectivity_status = "error"
                connectivity_error = f"HTTP {response_status_code}"

    except httpx.ConnectError as e:
        connectivity_status = "connection_error"
        connectivity_error = f"Cannot connect: {str(e)}"
    except httpx.TimeoutException as e:
        connectivity_status = "timeout"
        connectivity_error = f"Request timeout: {str(e)}"
    except Exception as e:
        connectivity_status = "unknown_error"
        connectivity_error = f"{type(e).__name__}: {str(e)}"

    return {
        "football_api": {
            "base_url": client.BASE_URL,
            "api_key_configured": api_key_present,
            "api_key_length": api_key_length,
            "api_key_preview": f"...{api_key_last_4}" if api_key_present else "NOT_SET",
            "client_headers": {
                "configured": headers_configured,
                "x_auth_token_present": token_in_headers,
            },
            "connectivity_test": {
                "status": connectivity_status,
                "http_status_code": response_status_code,
                "error": connectivity_error,
            },
        },
        "settings": {
            "app_env": settings.app_env,
            "app_version": settings.app_version,
            "debug_mode": settings.debug,
            "log_level": settings.log_level,
        },
    }

"""LLM Client using Groq (Free tier with Llama 3.3 70B).

Groq provides free access to Llama models with very fast inference.
API is OpenAI-compatible.

Free tier limits:
- 30 requests/minute
- 14,400 requests/day
- 1M tokens/hour

Get API key at: https://console.groq.com/
"""

import json
from typing import Any

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.exceptions import LLMError, RateLimitError
from src.core.http_client import get_http_client


class LLMResponse(BaseModel):
    """LLM response model."""

    content: str
    model: str
    usage: dict[str, Any] = {}


class GroqClient:
    """
    Client for Groq API (OpenAI-compatible).

    Uses Llama 3.3 70B for analysis tasks.
    Falls back to Llama 3.1 8B for simpler tasks.
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    # Model options
    MODEL_LARGE = "llama-3.3-70b-versatile"  # For complex analysis
    MODEL_SMALL = "llama-3.1-8b-instant"  # For simple extraction

    def __init__(self, api_key: str | None = None):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key. Get one free at https://console.groq.com/
        """
        self.api_key = api_key or settings.groq_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        messages: list[dict[str, str]],
        model: str = MODEL_LARGE,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        response_format: dict[str, str] | None = None,
    ) -> LLMResponse:
        """
        Make API request to Groq with comprehensive error handling.

        Includes:
        - Automatic retry on transient failures
        - Rate limit detection with backoff
        - Detailed error logging
        - Response validation
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        client = get_http_client()
        try:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60.0,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "unknown")
                raise RateLimitError(
                    "Groq rate limit exceeded - waiting before retry",
                    details={"retry_after": retry_after, "model": model},
                )

            if response.status_code == 401:
                raise LLMError(
                    "Groq authentication failed - invalid API key",
                    details={"status": 401},
                )

            if response.status_code == 500:
                raise LLMError(
                    "Groq service temporarily unavailable",
                    details={"status": 500},
                )

            if response.status_code != 200:
                raise LLMError(
                    f"Groq API error: {response.status_code}",
                    details={"status": response.status_code, "response": response.text[:200]},
                )

            data = response.json()

            # Validate response structure
            if "choices" not in data or not data["choices"]:
                raise LLMError(
                    "Invalid Groq response structure",
                    details={"data": str(data)[:200]},
                )

            return LLMResponse(
                content=data["choices"][0]["message"]["content"] or "",
                model=data.get("model") or model,
                usage=data.get("usage") or {},
            )
        except httpx.TimeoutException as e:
            raise LLMError(
                "Groq request timeout - LLM took too long to respond",
                details={"error": str(e)},
            )

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        json_mode: bool = False,
    ) -> str:
        """
        Simple completion.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            model: Model to use (default: large model)
            temperature: Creativity (0-1)
            max_tokens: Max response length
            json_mode: Return JSON response

        Returns:
            LLM response content
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response_format = {"type": "json_object"} if json_mode else None

        response: LLMResponse = await self._request(
            messages=messages,
            model=model or self.MODEL_LARGE,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        return response.content

    async def analyze_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """
        Get structured JSON response.

        Args:
            prompt: User prompt (should ask for JSON)
            system_prompt: System instructions
            model: Model to use

        Returns:
            Parsed JSON dict
        """
        content = await self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            json_mode=True,
        )

        try:
            result: dict[str, Any] = json.loads(content)
            return result
        except json.JSONDecodeError as e:
            raise LLMError(
                "Failed to parse JSON response",
                details={"content": content, "error": str(e)},
            )


# Will be initialized with API key from settings
groq_client: GroqClient | None = None


def get_llm_client() -> GroqClient:
    """Get or create LLM client."""
    global groq_client
    if groq_client is None:
        groq_client = GroqClient()
    return groq_client

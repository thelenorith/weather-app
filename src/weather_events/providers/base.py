"""Base weather provider abstraction.

This module defines the interface for weather data providers and the canonical
format that all providers must translate their data into.

## Canonical Data Format

All weather providers must translate their API responses into our internal
canonical format defined in `weather_events.models.weather`. This ensures
consistent data handling regardless of the source.

### Canonical Units (SI-based)
- Temperature: Celsius (°C)
- Wind speed: meters per second (m/s)
- Pressure: hectopascals (hPa)
- Precipitation: millimeters (mm) for amount, mm/h for intensity
- Visibility: meters (m)
- Cloud cover: percentage (0-100)
- Humidity: percentage (0-100)
- Wind direction: degrees (0-359, where 0=N, 90=E, 180=S, 270=W)

### Translation Requirements
Each provider must implement `_translate_response()` to convert their
specific API response format into our canonical `Forecast` model.

## Supported Providers

### MET Norway (api.met.no)
- Endpoint: https://api.met.no/weatherapi/locationforecast/2.0/
- Auth: User-Agent header required (no API key)
- Rate limit: No hard limit, but requires caching via If-Modified-Since
- Native units: Already SI (Celsius, m/s, hPa, mm, %)
- Key response path: properties.timeseries[].data.instant.details

### Pirate Weather (pirateweather.net)
- Endpoint: https://api.pirateweather.net/forecast/{apikey}/{lat},{lon}
- Auth: API key in URL path
- Rate limit: Varies by plan (free tier available)
- Native units: Configurable (si, us, ca, uk)
- Key response path: currently, hourly.data[], daily.data[]

### Open-Meteo (open-meteo.com)
- Endpoint: https://api.open-meteo.com/v1/forecast
- Auth: None required for basic use
- Rate limit: 10,000 requests/day (non-commercial)
- Native units: Configurable
- Key response path: hourly, daily objects with arrays
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from weather_events.models.location import Coordinates
from weather_events.models.weather import Forecast


class ProviderError(Exception):
    """Base exception for weather provider errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.response_body = response_body


class RateLimitError(ProviderError):
    """Raised when provider rate limit is exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after: int | None = None,
        status_code: int | None = None,
    ):
        super().__init__(
            f"Rate limit exceeded for {provider}",
            provider=provider,
            status_code=status_code,
        )
        self.retry_after = retry_after


class AuthenticationError(ProviderError):
    """Raised when authentication fails."""

    pass


class WeatherProvider(ABC):
    """Abstract base class for weather data providers.

    All weather providers must implement this interface to fetch weather
    data and translate it into our canonical format.

    Attributes:
        name: Human-readable provider name
        base_url: Base URL for the API
        requires_api_key: Whether this provider requires an API key

    Example:
        ```python
        class MyProvider(WeatherProvider):
            name = "my_provider"
            base_url = "https://api.example.com"

            async def get_forecast(self, coords, start, end):
                response = await self._fetch(...)
                return self._translate_response(response, coords)
        ```
    """

    name: str
    base_url: str
    requires_api_key: bool = False

    def __init__(
        self,
        api_key: str | None = None,
        user_agent: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize the provider.

        Args:
            api_key: API key if required by the provider
            user_agent: User-Agent string for requests
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.user_agent = user_agent or "weather-event-recommendations/0.1.0"
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

        # Cache for conditional requests
        self._etag_cache: dict[str, str] = {}
        self._last_modified_cache: dict[str, str] = {}
        self._response_cache: dict[str, Forecast] = {}

    async def __aenter__(self) -> WeatherProvider:
        """Enter async context manager."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _fetch(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Fetch data from the API with retry logic.

        Args:
            url: Full URL to fetch
            params: Query parameters
            headers: Additional headers

        Returns:
            HTTP response

        Raises:
            ProviderError: If request fails after retries
            RateLimitError: If rate limit is exceeded
        """
        client = self._get_client()
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)

        # Add conditional request headers if we have cached data
        cache_key = f"{url}:{params}"
        if cache_key in self._etag_cache:
            request_headers["If-None-Match"] = self._etag_cache[cache_key]
        if cache_key in self._last_modified_cache:
            request_headers["If-Modified-Since"] = self._last_modified_cache[cache_key]

        response = await client.get(url, params=params, headers=request_headers)

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                self.name,
                retry_after=int(retry_after) if retry_after else None,
                status_code=429,
            )

        # Handle 304 Not Modified - return cached response
        if response.status_code == 304 and cache_key in self._response_cache:
            return response  # Caller should check for 304

        # Handle other errors
        if response.status_code >= 400:
            raise ProviderError(
                f"API request failed: {response.status_code}",
                provider=self.name,
                status_code=response.status_code,
                response_body=response.text,
            )

        # Cache response metadata
        if "ETag" in response.headers:
            self._etag_cache[cache_key] = response.headers["ETag"]
        if "Last-Modified" in response.headers:
            self._last_modified_cache[cache_key] = response.headers["Last-Modified"]

        return response

    @abstractmethod
    async def get_forecast(
        self,
        coordinates: Coordinates,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Forecast:
        """Get weather forecast for a location.

        Args:
            coordinates: Location coordinates
            start_time: Start of forecast period (optional)
            end_time: End of forecast period (optional)

        Returns:
            Forecast data in canonical format

        Raises:
            ProviderError: If forecast cannot be retrieved
        """
        pass

    @abstractmethod
    def _translate_response(
        self,
        response_data: dict[str, Any],
        coordinates: Coordinates,
    ) -> Forecast:
        """Translate provider-specific response to canonical format.

        This method must be implemented by each provider to handle their
        specific API response format and translate it to our internal
        Forecast model.

        Args:
            response_data: Raw JSON response from provider
            coordinates: Location coordinates

        Returns:
            Forecast in canonical format
        """
        pass

    def supports_historical(self) -> bool:
        """Check if provider supports historical data."""
        return False

    def supports_minute_forecast(self) -> bool:
        """Check if provider supports minute-by-minute forecasts."""
        return False

    def get_max_forecast_days(self) -> int:
        """Get maximum forecast days supported."""
        return 7

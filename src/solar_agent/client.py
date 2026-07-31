import json
import logging
import random
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenMeteoError(Exception):
    pass


class OpenMeteoAPIError(OpenMeteoError):
    def __init__(self, status_code: int, reason: str):
        self.status_code = status_code
        self.reason = reason
        super().__init__(f"Open-Meteo API error ({status_code}): {reason}")


class OpenMeteoConnectionError(OpenMeteoError):
    pass


class OpenMeteoTimeoutError(OpenMeteoError):
    pass


class OpenMeteoInvalidResponseError(OpenMeteoError):
    pass


class OpenMeteoClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        retry_attempts: int,
        retry_backoff_seconds: float,
    ):
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout_seconds)
        self.retry_attempts = retry_attempts
        self.retry_backoff_seconds = retry_backoff_seconds
        self.client = httpx.Client(base_url=base_url, timeout=self.timeout)

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "OpenMeteoClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def fetch_primary(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int,
        model: str,
    ) -> dict:
        hourly_vars = (
            "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,"
            "direct_radiation,global_tilted_irradiance"
        )
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "forecast_days": forecast_days,
            "models": model,
            "hourly": hourly_vars,
        }
        return self._request_with_retry(params)

    def fetch_dwd_icon(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        forecast_days: int,
    ) -> dict:
        hourly_vars = (
            "shortwave_radiation,direct_normal_irradiance,diffuse_radiation,"
            "direct_radiation,global_tilted_irradiance"
        )
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "forecast_days": forecast_days,
            "models": "dwd_icon",
            "hourly": hourly_vars,
        }
        return self._request_with_retry(params)

    def _request_with_retry(self, params: dict) -> dict:
        last_error: Exception | None = None

        for attempt in range(self.retry_attempts):
            try:
                response = self.client.get("", params=params)

                if response.status_code == 400:
                    try:
                        error_data = response.json()
                        raise OpenMeteoAPIError(400, error_data.get("reason", "Unknown error"))
                    except (json.JSONDecodeError, KeyError) as e:
                        raise OpenMeteoAPIError(400, "Invalid request") from e

                if response.status_code in {429, 500, 502, 503, 504}:
                    if attempt < self.retry_attempts - 1:
                        base = self.retry_backoff_seconds * (2 ** attempt)
                        backoff = base + random.uniform(0, 0.1)
                        logger.warning(
                            f"Open-Meteo {response.status_code}, retry in {backoff:.2f}s "
                            f"(attempt {attempt + 1}/{self.retry_attempts})"
                        )
                        time.sleep(backoff)
                        continue
                    else:
                        try:
                            error_data = response.json()
                            reason = error_data.get("reason", "Server error")
                            raise OpenMeteoAPIError(response.status_code, reason)
                        except (json.JSONDecodeError, KeyError) as e:
                            raise OpenMeteoAPIError(
                                response.status_code, "Server error"
                            ) from e

                response.raise_for_status()

                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    raise OpenMeteoInvalidResponseError(
                        f"Invalid JSON response: {e}"
                    ) from e

                if "hourly" not in data:
                    raise OpenMeteoInvalidResponseError("Missing 'hourly' key in response")

                return data

            except httpx.TimeoutException as e:
                last_error = OpenMeteoTimeoutError(str(e))
                if attempt < self.retry_attempts - 1:
                    backoff = (
                        self.retry_backoff_seconds * (2 ** attempt)
                        + random.uniform(0, 0.1)
                    )
                    logger.warning(
                        f"Open-Meteo timeout, retry in {backoff:.2f}s "
                        f"(attempt {attempt + 1}/{self.retry_attempts})"
                    )
                    time.sleep(backoff)
                    continue
                else:
                    if last_error:
                        raise last_error from last_error

            except (httpx.ConnectError, httpx.NetworkError) as e:
                last_error = OpenMeteoConnectionError(str(e))
                if attempt < self.retry_attempts - 1:
                    backoff = (
                        self.retry_backoff_seconds * (2 ** attempt)
                        + random.uniform(0, 0.1)
                    )
                    logger.warning(
                        f"Open-Meteo connection error, retry in {backoff:.2f}s "
                        f"(attempt {attempt + 1}/{self.retry_attempts})"
                    )
                    time.sleep(backoff)
                    continue
                else:
                    if last_error:
                        raise last_error from last_error

        if last_error:
            raise last_error from last_error

        raise OpenMeteoError("All retry attempts exhausted")

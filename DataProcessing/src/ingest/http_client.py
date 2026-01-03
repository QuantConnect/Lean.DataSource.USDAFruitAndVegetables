# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import Any, cast

import requests  # type: ignore[reportMissingImports]
from requests.adapters import HTTPAdapter  # type: ignore[reportMissingImports,reportMissingModuleSource]
from urllib3.util.retry import Retry  # type: ignore[reportMissingImports,reportUnknownVariableType]

from src.core.constants import DOWNLOADER_LOG_PREFIX
from src.core.logging_utils import Logger
from src.ingest.rate_gate import RateGate

# Cast needed: urllib3.util.retry.Retry lacks type stubs
RetryType = cast(Any, Retry)


class HttpError(Exception):
    """Raised when an HTTP request fails with a non-2xx status code.

    Per Constitution: Explicit over implicit (Constraint) - callers must handle
    HTTP errors explicitly rather than receiving silent empty responses.
    """

    def __init__(self, status_code: int, url: str, reason: str = "") -> None:
        self.status_code = status_code
        self.url = url
        self.reason = reason
        super().__init__(f"HTTP {status_code} for {url}: {reason}")

    def is_not_found(self) -> bool:
        """Returns True if this is a 404 Not Found error."""
        return self.status_code == 404

    def is_payment_required(self) -> bool:
        """Returns True if this is a 402 Payment Required error."""
        return self.status_code == 402

    def is_rate_limited(self) -> bool:
        """Returns True if this is a 429 Rate Limited error."""
        return self.status_code == 429


class HttpClient:
    def __init__(
        self,
        timeout_seconds: int,
        max_retries: int,
        rate_gate: RateGate,
        logger: Logger,
        api_key: str | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._rate_gate = rate_gate
        self._logger = logger
        self._session: Any = requests.Session()
        self._session.headers.update(
            {
                "Accept": "*/*",
                "User-Agent": "QuantConnect-Lean.DataSource.USDAFruitAndVegetables/1.0",
            }
        )
        if api_key:
            self._session.headers.update({"X-Api-Key": api_key})

        retry_total = max(0, max_retries - 1)
        retry: Any = RetryType(
            total=retry_total,
            connect=retry_total,
            read=retry_total,
            status=retry_total,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def get_text(self, url: str) -> str:
        """Fetch URL content as text. Raises HttpError on non-2xx responses."""
        response = self._request(url)
        self._handle_response(response, url)
        return response.text

    def get_bytes(self, url: str) -> bytes:
        """Fetch URL content as bytes. Raises HttpError on non-2xx responses."""
        response = self._request(url)
        self._handle_response(response, url)
        return response.content

    def _request(self, url: str) -> Any:
        self._rate_gate.wait_to_proceed()
        try:
            return self._session.get(url, timeout=self._timeout_seconds)
        except requests.RequestException as err:
            self._logger.error(f"{DOWNLOADER_LOG_PREFIX}: HTTP error", err)
            raise RuntimeError(f"{DOWNLOADER_LOG_PREFIX}: Request failed") from err

    def _handle_response(self, response: Any, url: str) -> None:
        """Validates HTTP response. Raises HttpError on non-2xx status codes.

        Per Constitution: Fail-fast principle - errors are raised immediately
        rather than returning sentinel values that could be silently ignored.
        """
        status = response.status_code
        reason = getattr(response, "reason", "") or ""

        if status == 404:
            self._logger.error(f"{DOWNLOADER_LOG_PREFIX}: File not found at {url}")
            raise HttpError(status, url, "Not Found")

        if status == 402:
            self._logger.error(f"{DOWNLOADER_LOG_PREFIX}: API payment required - {reason}")
            raise HttpError(status, url, reason or "Payment Required")

        if status == 429:
            self._logger.error(f"{DOWNLOADER_LOG_PREFIX}: Rate limited (429) at {url}")
            raise HttpError(status, url, "Rate Limited")

        try:
            response.raise_for_status()
        except requests.RequestException as err:
            self._logger.error(f"{DOWNLOADER_LOG_PREFIX}: HTTP error", err)
            raise HttpError(status, url, str(err)) from err

    def close(self) -> None:
        self._session.close()

    def __del__(self) -> None:
        # Best-effort cleanup in destructor; swallow errors since the object is being destroyed.
        try:
            self.close()
        except OSError:  # noqa: BLE001 - intentional swallow for destructor cleanup
            pass

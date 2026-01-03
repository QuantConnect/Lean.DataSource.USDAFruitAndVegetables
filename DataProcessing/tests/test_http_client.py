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

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import requests

from src.ingest.http_client import HttpClient, HttpError
from src.ingest.rate_gate import RateGate
from tests.test_helpers import NullLogger


class HttpClientTests(unittest.TestCase):
    def _create_client(self) -> HttpClient:
        rate_gate = RateGate(max_requests=0, interval_seconds=0)  # bypass rate limiting
        return HttpClient(
            timeout_seconds=30,
            max_retries=1,
            rate_gate=rate_gate,
            logger=NullLogger(),
            api_key=None,
        )

    def _mock_response(self, status_code: int, text: str = "", content: bytes = b"") -> Any:
        response = MagicMock()
        response.status_code = status_code
        response.text = text
        response.content = content
        response.reason = "Test reason"
        response.raise_for_status = MagicMock()
        return response

    def test_get_text_returns_content_on_200(self) -> None:
        client = self._create_client()
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = self._mock_response(200, text="Hello World")
            result = client.get_text("https://example.com")
            self.assertEqual(result, "Hello World")

    def test_get_text_raises_on_404(self) -> None:
        """Per Constitution: Fail-fast - 404 raises HttpError instead of silent empty."""
        client = self._create_client()
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = self._mock_response(404)
            with self.assertRaises(HttpError) as context:
                client.get_text("https://example.com")
            self.assertEqual(context.exception.status_code, 404)
            self.assertTrue(context.exception.is_not_found())

    def test_get_text_raises_on_402(self) -> None:
        """Per Constitution: Fail-fast - 402 raises HttpError instead of silent empty."""
        client = self._create_client()
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = self._mock_response(402)
            with self.assertRaises(HttpError) as context:
                client.get_text("https://example.com")
            self.assertEqual(context.exception.status_code, 402)
            self.assertTrue(context.exception.is_payment_required())

    def test_get_text_raises_on_429(self) -> None:
        """429 rate limit raises HttpError with is_rate_limited() helper."""
        client = self._create_client()
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = self._mock_response(429)
            with self.assertRaises(HttpError) as context:
                client.get_text("https://example.com")
            self.assertEqual(context.exception.status_code, 429)
            self.assertTrue(context.exception.is_rate_limited())

    def test_get_bytes_returns_bytes_on_200(self) -> None:
        client = self._create_client()
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = self._mock_response(200, content=b"\x00\x01\x02")
            result = client.get_bytes("https://example.com")
            self.assertEqual(result, b"\x00\x01\x02")

    def test_get_bytes_raises_on_404(self) -> None:
        """Per Constitution: Fail-fast - 404 raises HttpError instead of silent empty."""
        client = self._create_client()
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = self._mock_response(404)
            with self.assertRaises(HttpError) as context:
                client.get_bytes("https://example.com")
            self.assertEqual(context.exception.status_code, 404)

    def test_get_bytes_raises_on_402(self) -> None:
        """Per Constitution: Fail-fast - 402 raises HttpError instead of silent empty."""
        client = self._create_client()
        with patch.object(client, "_request") as mock_request:
            mock_request.return_value = self._mock_response(402)
            with self.assertRaises(HttpError) as context:
                client.get_bytes("https://example.com")
            self.assertEqual(context.exception.status_code, 402)

    def test_get_text_raises_on_request_exception(self) -> None:
        client = self._create_client()
        with patch("requests.Session.get", side_effect=requests.RequestException("boom")):
            with self.assertRaises(RuntimeError):
                client.get_text("https://example.com")

    def test_get_text_raises_on_server_error(self) -> None:
        """Server errors (5xx) raise HttpError with status code."""
        client = self._create_client()
        response = self._mock_response(500)
        response.raise_for_status.side_effect = requests.RequestException("error")
        with patch.object(client, "_request", return_value=response):
            with self.assertRaises(HttpError) as context:
                client.get_text("https://example.com")
            self.assertEqual(context.exception.status_code, 500)

    def test_request_calls_rate_gate(self) -> None:
        rate_gate = MagicMock()
        client = HttpClient(
            timeout_seconds=30,
            max_retries=1,
            rate_gate=rate_gate,
            logger=NullLogger(),
            api_key=None,
        )
        with patch("requests.Session.get") as mock_get:
            mock_get.return_value = self._mock_response(200)
            client._request("https://example.com")  # pyright: ignore[reportPrivateUsage]
            rate_gate.wait_to_proceed.assert_called_once()


if __name__ == "__main__":
    unittest.main()

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
from unittest.mock import patch

from src.ingest.rate_gate import RateGate


class RateGateTests(unittest.TestCase):
    def test_first_request_passes_immediately(self) -> None:
        gate = RateGate(max_requests=5, interval_seconds=1.0)
        with patch("src.ingest.rate_gate.time.sleep") as mock_sleep:
            gate.wait_to_proceed()
            mock_sleep.assert_not_called()

    def test_bypass_when_max_requests_zero(self) -> None:
        gate = RateGate(max_requests=0, interval_seconds=1.0)
        with patch("src.ingest.rate_gate.time.sleep") as mock_sleep:
            gate.wait_to_proceed()
            gate.wait_to_proceed()
            mock_sleep.assert_not_called()

    def test_bypass_when_interval_zero(self) -> None:
        gate = RateGate(max_requests=5, interval_seconds=0)
        with patch("src.ingest.rate_gate.time.sleep") as mock_sleep:
            gate.wait_to_proceed()
            gate.wait_to_proceed()
            mock_sleep.assert_not_called()

    def test_bypass_when_max_requests_negative(self) -> None:
        gate = RateGate(max_requests=-1, interval_seconds=1.0)
        with patch("src.ingest.rate_gate.time.sleep") as mock_sleep:
            gate.wait_to_proceed()
            mock_sleep.assert_not_called()

    def test_requests_within_limit_pass_without_sleep(self) -> None:
        gate = RateGate(max_requests=3, interval_seconds=1.0)
        with patch("src.ingest.rate_gate.time.sleep") as mock_sleep:
            gate.wait_to_proceed()
            gate.wait_to_proceed()
            gate.wait_to_proceed()
            mock_sleep.assert_not_called()

    def test_blocks_when_limit_reached(self) -> None:
        gate = RateGate(max_requests=2, interval_seconds=1.0)
        with patch("src.ingest.rate_gate.time.monotonic") as mock_time:
            with patch("src.ingest.rate_gate.time.sleep") as mock_sleep:
                # First two requests at time 0
                mock_time.side_effect = [0.0, 0.0, 0.0, 0.0, 1.1]
                gate.wait_to_proceed()
                gate.wait_to_proceed()

                # Third request should trigger sleep
                gate.wait_to_proceed()
                mock_sleep.assert_called()

    def test_sliding_window_removes_old_timestamps(self) -> None:
        gate = RateGate(max_requests=2, interval_seconds=1.0)
        with patch("src.ingest.rate_gate.time.monotonic") as mock_time:
            with patch("src.ingest.rate_gate.time.sleep"):
                # First two requests at time 0
                mock_time.return_value = 0.0
                gate.wait_to_proceed()
                gate.wait_to_proceed()

                # Move time forward past the interval
                mock_time.return_value = 1.5

                # Should pass without sleeping (old timestamps expired)
                with patch("src.ingest.rate_gate.time.sleep") as mock_sleep_2:
                    gate.wait_to_proceed()
                    mock_sleep_2.assert_not_called()

    def test_sleep_duration_matches_interval(self) -> None:
        gate = RateGate(max_requests=1, interval_seconds=1.0)
        with patch("src.ingest.rate_gate.time.monotonic") as mock_time:
            with patch("src.ingest.rate_gate.time.sleep") as mock_sleep:
                mock_time.side_effect = [0.0, 0.0, 1.1]
                gate.wait_to_proceed()
                gate.wait_to_proceed()
                mock_sleep.assert_called_once_with(1.0)


if __name__ == "__main__":
    unittest.main()

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

import time
from collections import deque
from threading import Lock


class RateGate:
    def __init__(self, max_requests: int, interval_seconds: float) -> None:
        self._max_requests = max_requests
        self._interval_seconds = interval_seconds
        self._timestamps: deque[float] = deque()
        self._lock = Lock()

    def wait_to_proceed(self) -> None:
        if self._max_requests <= 0 or self._interval_seconds <= 0:
            return

        while True:
            with self._lock:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._interval_seconds:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max_requests:
                    self._timestamps.append(now)
                    return
                next_allowed = self._timestamps[0] + self._interval_seconds
                sleep_for = max(0.0, next_allowed - now)
            if sleep_for > 0:
                time.sleep(sleep_for)

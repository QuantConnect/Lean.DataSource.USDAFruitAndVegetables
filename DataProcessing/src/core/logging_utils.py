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

import logging


class Logger:
    def trace(self, message: str) -> None:
        raise NotImplementedError

    def error(self, message: str, exc: BaseException | None = None) -> None:
        raise NotImplementedError


class StdLogger(Logger):
    """Standard library logging adapter for the Logger interface."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def trace(self, message: str) -> None:
        # Maps to info(), not debug(), because trace is "operational trace" (what's
        # happening) not "debug trace". QC runtime may not expose debug-level logs.
        self._logger.info(message)

    def error(self, message: str, exc: BaseException | None = None) -> None:
        if exc is None:
            self._logger.error(message)
        else:
            self._logger.exception(message)


def select_logger() -> Logger:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return StdLogger(logging.getLogger("USDAFruitAndVegetables"))

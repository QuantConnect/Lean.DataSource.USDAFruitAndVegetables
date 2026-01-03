from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType
from typing import Any

from src.core import config_provider
from src.core.logging_utils import Logger


class NullLogger(Logger):
    def trace(self, message: str) -> None:
        pass

    def error(self, message: str, exc: BaseException | None = None) -> None:
        pass


class ConfigOverride:
    """Context manager for config overrides in tests.

    Usage:
        with ConfigOverride({"process-start-date": "20200101", "process-end-date": "20200201"}):
            config = load_config()
            # config uses overridden values
        # config override is cleared automatically
    """

    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = values

    def __enter__(self) -> "ConfigOverride":
        config_provider.set_config_override(self._values)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        config_provider.clear_config_override()

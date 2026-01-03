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

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.core.constants import (
    CONFIG_DATA_FOLDER_DEFAULT,
    CONFIG_DATA_FOLDER_KEY,
    CONFIG_HTTP_TIMEOUT_SECONDS_KEY,
    CONFIG_LISTING_URL_KEY,
    CONFIG_MAX_RETRIES_KEY,
    CONFIG_MAX_XLSX_DOWNLOADS_KEY,
    CONFIG_NORMALIZE_CUP_EQUIVALENT_UNIT_KEY,
    CONFIG_OUTPUT_ROOT_DEFAULT,
    CONFIG_OUTPUT_ROOT_KEY,
    CONFIG_PROCESS_END_DATE_KEY,
    CONFIG_PROCESS_START_DATE_KEY,
    CONFIG_RATE_LIMIT_REQUESTS_KEY,
    CONFIG_RATE_LIMIT_SECONDS_KEY,
    CONFIG_RUN_LIVE_TESTS_KEY,
    CONFIG_VENDOR_AUTH_TOKEN_KEY,
    CONFIG_XLSX_DIRECTORY_KEY,
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_NORMALIZE_CUP_EQUIVALENT_UNIT,
    DEFAULT_RATE_LIMIT_REQUESTS,
    DEFAULT_RATE_LIMIT_SECONDS,
)


class ProcessorConfig(BaseModel):
    """Configuration for USDA data processing pipeline.

    Fields are loaded from QuantConnect's Config.Get system (or test overrides).
    Required fields must be set; optional fields use documented defaults.

    Required:
        process_start_date: Start of date range to process (yyyyMMdd format)
        process_end_date: End of date range to process (yyyyMMdd format)

    Optional (with defaults):
        data_folder: Root data folder for QC runtime (default: "../../../Data/")
        output_root: Where to write output CSVs (default: same as data_folder)
        max_retries: HTTP retry count for transient failures (default: 5)
        rate_limit_requests: Max requests per rate_limit_seconds (default: 10)
        rate_limit_seconds: Rate limit window in seconds (default: 1.1)
        http_timeout_seconds: HTTP request timeout (default: 60)
        normalize_cup_equivalent_unit: Convert fluid_ounces to pints (default: True)

    Optional (no default - empty string if not set):
        xlsx_directory: Local directory with XLSX files (bypasses download)
        listing_url: Override USDA ERS listing page URL
        max_xlsx_downloads: Limit number of XLSX files to download (0 = no limit)
        vendor_auth_token: Authentication token if required
        run_live_tests: Enable live HTTP tests (default: False)
    """

    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    data_folder: str = Field(default=CONFIG_DATA_FOLDER_DEFAULT, alias=CONFIG_DATA_FOLDER_KEY)
    output_root: str = Field(default=CONFIG_OUTPUT_ROOT_DEFAULT, alias=CONFIG_OUTPUT_ROOT_KEY)
    process_start_date: str = Field(alias=CONFIG_PROCESS_START_DATE_KEY, min_length=1)
    process_end_date: str = Field(alias=CONFIG_PROCESS_END_DATE_KEY, min_length=1)
    max_retries: int = Field(default=DEFAULT_MAX_RETRIES, alias=CONFIG_MAX_RETRIES_KEY, ge=0)
    rate_limit_requests: int = Field(default=DEFAULT_RATE_LIMIT_REQUESTS, alias=CONFIG_RATE_LIMIT_REQUESTS_KEY, ge=1)
    rate_limit_seconds: float = Field(
        default=float(DEFAULT_RATE_LIMIT_SECONDS),
        alias=CONFIG_RATE_LIMIT_SECONDS_KEY,
        gt=0,
    )
    http_timeout_seconds: int = Field(default=DEFAULT_HTTP_TIMEOUT_SECONDS, alias=CONFIG_HTTP_TIMEOUT_SECONDS_KEY, ge=1)
    xlsx_directory: str = Field(default="", alias=CONFIG_XLSX_DIRECTORY_KEY)
    max_xlsx_downloads: int = Field(default=0, alias=CONFIG_MAX_XLSX_DOWNLOADS_KEY, ge=0)
    listing_url: str = Field(default="", alias=CONFIG_LISTING_URL_KEY)
    normalize_cup_equivalent_unit: bool = Field(
        default=DEFAULT_NORMALIZE_CUP_EQUIVALENT_UNIT,
        alias=CONFIG_NORMALIZE_CUP_EQUIVALENT_UNIT_KEY,
    )
    vendor_auth_token: str = Field(default="", alias=CONFIG_VENDOR_AUTH_TOKEN_KEY)
    run_live_tests: bool = Field(default=False, alias=CONFIG_RUN_LIVE_TESTS_KEY)


# --- Test Infrastructure ---
# These functions allow tests to override Config.Get values without requiring the
# QC runtime. Production code should NOT use these directly.
# Per Constitution: Separation of concerns - test utilities are documented but kept
# here to avoid module dependency cycles.
_config_override: Mapping[str, str] | None = None


def set_config_override(values: Mapping[str, Any] | None) -> None:
    """Set config overrides for testing. DO NOT use in production code."""
    global _config_override
    if values is None:
        _config_override = None
        return
    _config_override = {str(key): "" if value is None else str(value) for key, value in values.items()}


def clear_config_override() -> None:
    """Clear config overrides. Call in test tearDown to ensure clean state."""
    set_config_override(None)


def _get_config_value(key: str) -> str:
    if _config_override is not None:
        return _config_override.get(key, "")
    try:
        from QuantConnect.Configuration import Config  # type: ignore[reportMissingImports,reportUnknownVariableType]
    except ImportError as exc:
        raise RuntimeError(
            "QuantConnect Config.Get is required for DataProcessing. Ensure the QC/Lean python runtime is available."
        ) from exc
    return str(Config.Get(key))  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]


def _require_value(key: str) -> str:
    value = _get_config_value(key).strip()
    if not value:
        raise ValueError(f"Missing Config.Get value for '{key}'")
    return value


def _get_optional_value(key: str) -> str:
    return _get_config_value(key).strip()


def _parse_int(key: str, raw_value: str) -> int:
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Config.Get '{key}' must be an integer") from exc


def _parse_float(key: str, raw_value: str) -> float:
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Config.Get '{key}' must be a number") from exc


def _parse_bool(key: str, raw_value: str) -> bool:
    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Config.Get '{key}' must be a boolean")


def get_optional_bool(key: str, default: bool = False) -> bool:
    try:
        raw_value = _get_optional_value(key)
    except RuntimeError:
        return default
    if not raw_value:
        return default
    return _parse_bool(key, raw_value)


def _optional_int(key: str) -> int | None:
    """Parse optional int config value. Returns None if not set (uses Pydantic default).

    Per Constitution: Explicit over implicit - defaults are documented in ProcessorConfig,
    and this function only provides overrides when explicitly configured.
    """
    raw = _get_optional_value(key)
    if not raw:
        return None
    return _parse_int(key, raw)


def _optional_float(key: str) -> float | None:
    """Parse optional float config value. Returns None if not set (uses Pydantic default)."""
    raw = _get_optional_value(key)
    if not raw:
        return None
    return _parse_float(key, raw)


def _optional_bool(key: str) -> bool | None:
    """Parse optional bool config value. Returns None if not set (uses Pydantic default)."""
    raw = _get_optional_value(key)
    if not raw:
        return None
    return _parse_bool(key, raw)


def load_config() -> ProcessorConfig:
    """Load config from QC Config.Get or test override.

    Required fields: process-start-date, process-end-date
    Optional fields with defaults (see ProcessorConfig for values):
        - data-folder, output-root, max-retries, rate-limit-requests,
          rate-limit-seconds, http-timeout-seconds, max-xlsx-downloads,
          normalize-cup-equivalent-unit, xlsx-directory, listing-url,
          vendor-auth-token, run-live-tests
    """
    # Start with required fields
    data: dict[str, Any] = {
        CONFIG_PROCESS_START_DATE_KEY: _require_value(CONFIG_PROCESS_START_DATE_KEY),
        CONFIG_PROCESS_END_DATE_KEY: _require_value(CONFIG_PROCESS_END_DATE_KEY),
    }

    # Add optional overrides (None values will use Pydantic defaults)
    optional_values: dict[str, Any] = {
        CONFIG_DATA_FOLDER_KEY: _get_optional_value(CONFIG_DATA_FOLDER_KEY) or None,
        CONFIG_MAX_RETRIES_KEY: _optional_int(CONFIG_MAX_RETRIES_KEY),
        CONFIG_RATE_LIMIT_REQUESTS_KEY: _optional_int(CONFIG_RATE_LIMIT_REQUESTS_KEY),
        CONFIG_RATE_LIMIT_SECONDS_KEY: _optional_float(CONFIG_RATE_LIMIT_SECONDS_KEY),
        CONFIG_HTTP_TIMEOUT_SECONDS_KEY: _optional_int(CONFIG_HTTP_TIMEOUT_SECONDS_KEY),
        CONFIG_MAX_XLSX_DOWNLOADS_KEY: _optional_int(CONFIG_MAX_XLSX_DOWNLOADS_KEY),
        CONFIG_NORMALIZE_CUP_EQUIVALENT_UNIT_KEY: _optional_bool(CONFIG_NORMALIZE_CUP_EQUIVALENT_UNIT_KEY),
        CONFIG_XLSX_DIRECTORY_KEY: _get_optional_value(CONFIG_XLSX_DIRECTORY_KEY) or None,
        CONFIG_LISTING_URL_KEY: _get_optional_value(CONFIG_LISTING_URL_KEY) or None,
        CONFIG_VENDOR_AUTH_TOKEN_KEY: _get_optional_value(CONFIG_VENDOR_AUTH_TOKEN_KEY) or None,
        CONFIG_RUN_LIVE_TESTS_KEY: _optional_bool(CONFIG_RUN_LIVE_TESTS_KEY),
    }

    # Only include non-None values (Pydantic will use defaults for missing keys)
    for key, value in optional_values.items():
        if value is not None:
            data[key] = value

    # Handle output_root special case
    output_root_override = _get_optional_value(CONFIG_OUTPUT_ROOT_KEY)
    if output_root_override:
        data[CONFIG_OUTPUT_ROOT_KEY] = output_root_override
    elif CONFIG_DATA_FOLDER_KEY in data:
        data[CONFIG_OUTPUT_ROOT_KEY] = data[CONFIG_DATA_FOLDER_KEY]

    return ProcessorConfig.model_validate(data)

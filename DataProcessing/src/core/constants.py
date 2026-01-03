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

import re
from pathlib import Path

from src.core.schema import CSV_COLUMN_COUNT

# USDA ERS listing pages - tried in order until one succeeds
LISTING_URLS: tuple[str, ...] = (
    "https://www.ers.usda.gov/data-products/fruit-and-vegetable-prices",
    "https://www.ers.usda.gov/data-products/fruit-and-vegetable-prices.aspx",
    "http://www.ers.usda.gov/data-products/fruit-and-vegetable-prices.aspx",
)

# Year extraction regex patterns:
# - 19xx or 20xx: USDA data ranges from 2000s-present; 1900s included for historical archives
# - FILE_YEAR_REGEX: Filename pattern like "fruit-2020.xlsx" (no adjacent digits)
# - SHEET_YEAR_REGEX: Sheet title pattern like "Apples 2022" (word boundary)
FILE_YEAR_REGEX = re.compile(r"(?<!\d)(?P<year>(?:19|20)\d{2})(?!\d)")
SHEET_YEAR_REGEX = re.compile(r"\b(?P<year>(?:19|20)\d{2})\b")

# Trailing footnote markers like "Fresh1" or "Juice, ready to drink2,3"
TRAILING_FOOTNOTE_REGEX = re.compile(r"\s*\d+(?:,\d+)*\s*$")

EXPECTED_XLSX_COLUMN_COUNT = CSV_COLUMN_COUNT

XLSX_ALLOWED_GROUP_HEADERS = {
    "canned",
    "fresh",
    "juice",
    "peas & carrots",
    "green peas & carrots",
    "succotash",
}
XLSX_FOOTNOTE_PREFIX_REGEX = re.compile(r"^\d")
XLSX_SOURCE_PREFIX_REGEX = re.compile(r"^source\b", re.IGNORECASE)
XLSX_CONTACT_PREFIX_REGEX = re.compile(r"^contact\b", re.IGNORECASE)
XLSX_ERRATA_PREFIX_REGEX = re.compile(r"^errata\b", re.IGNORECASE)
XLSX_SOURCE_KEYWORDS = {
    "usda",
    "economic research service",
}

DATE_FORMAT_YYYYMMDD = "%Y%m%d"

MANIFEST_STATUS_OK = "ok"
MANIFEST_STATUS_NO_SOURCES = "no_sources"
MANIFEST_STATUS_NO_FILES = "no_files"
MANIFEST_STATUS_NO_DATA = "no_data"

UNKNOWN_TEXT = "unknown"
DOWNLOADER_LOG_PREFIX = "USDAFruitAndVegetablesDownloader"

CONFIG_DATA_FOLDER_KEY = "data-folder"
CONFIG_DATA_FOLDER_DEFAULT = "../../../Data/"
CONFIG_OUTPUT_ROOT_KEY = "temp-output-directory"
CONFIG_OUTPUT_ROOT_DEFAULT = CONFIG_DATA_FOLDER_DEFAULT
CONFIG_PROCESS_START_DATE_KEY = "process-start-date"
CONFIG_PROCESS_END_DATE_KEY = "process-end-date"
CONFIG_MAX_RETRIES_KEY = "max-retries"
CONFIG_RATE_LIMIT_REQUESTS_KEY = "rate-limit-requests"
CONFIG_RATE_LIMIT_SECONDS_KEY = "rate-limit-seconds"
CONFIG_HTTP_TIMEOUT_SECONDS_KEY = "http-timeout-seconds"
CONFIG_XLSX_DIRECTORY_KEY = "usda-fruitandvegetables-xlsx-directory"
CONFIG_MAX_XLSX_DOWNLOADS_KEY = "usda-fruitandvegetables-max-xlsx-downloads"
CONFIG_LISTING_URL_KEY = "usda-fruitandvegetables-listing-url"
CONFIG_NORMALIZE_CUP_EQUIVALENT_UNIT_KEY = "normalize-cup-equivalent-unit"
CONFIG_VENDOR_AUTH_TOKEN_KEY = "vendor-auth-token"
CONFIG_RUN_LIVE_TESTS_KEY = "usda-run-live-tests"

# HTTP retry/rate-limit defaults:
# - MAX_RETRIES=5: Balance between resilience and fast failure
# - RATE_LIMIT_REQUESTS=10: USDA doesn't publish rate limits; 10/sec is conservative
# - RATE_LIMIT_SECONDS=1.1: Slightly over 1s to avoid clock drift edge cases
# - HTTP_TIMEOUT=60: Default timeout for USDA XLSX downloads (~1-5MB files)
DEFAULT_MAX_RETRIES = 5
DEFAULT_RATE_LIMIT_REQUESTS = 10
DEFAULT_RATE_LIMIT_SECONDS = "1.1"
DEFAULT_HTTP_TIMEOUT_SECONDS = 60

# Normalize fluid_ounces to pints for consistent cup-equivalent units across series
DEFAULT_NORMALIZE_CUP_EQUIVALENT_UNIT = True

OUTPUT_SUBDIRECTORY = Path("alternative") / "usda" / "fruitandvegetables"

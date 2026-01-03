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

from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import TracebackType

from src.ingest.series_parser import SeriesParseResult

from src.core.config_provider import ProcessorConfig
from src.core.constants import (
    CONFIG_HTTP_TIMEOUT_SECONDS_KEY,
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    DOWNLOADER_LOG_PREFIX,
    MANIFEST_STATUS_NO_DATA,
    MANIFEST_STATUS_NO_FILES,
    MANIFEST_STATUS_NO_SOURCES,
    MANIFEST_STATUS_OK,
)
from src.core.date_utils import validate_date_range
from src.core.logging_utils import Logger
from src.ingest.http_client import HttpClient
from src.ingest.rate_gate import RateGate
from src.ingest.series_parser import SeriesParser
from src.ingest.series_writer import SeriesWriter
from src.ingest.source_catalog import SourceCatalog, cleanup_temp_folder
from src.model.dataset_types import SeriesMetadata


@dataclass(frozen=True)
class SeriesManifestResult:
    metadata_by_series: Mapping[str, SeriesMetadata]
    source_files_count: int
    parsed_files: int
    relevant_files: int
    total_points_parsed: int
    total_points_selected: int
    status: str


def _create_manifest_result(
    *,
    metadata_by_series: Mapping[str, SeriesMetadata] | None = None,
    source_files_count: int = 0,
    parsed_files: int = 0,
    relevant_files: int = 0,
    total_points_parsed: int = 0,
    total_points_selected: int = 0,
    status: str,
) -> SeriesManifestResult:
    return SeriesManifestResult(
        metadata_by_series=metadata_by_series or {},
        source_files_count=source_files_count,
        parsed_files=parsed_files,
        relevant_files=relevant_files,
        total_points_parsed=total_points_parsed,
        total_points_selected=total_points_selected,
        status=status,
    )


def _with_prefix(message: str) -> str:
    return f"{DOWNLOADER_LOG_PREFIX}: {message}"


@dataclass(frozen=True)
class _SourcesResult:
    """Result from source processing with automatic cleanup.

    Used by _process_sources context manager to encapsulate:
    - Source resolution (listing page or local directory)
    - XLSX parsing (via SeriesParser)
    - Temp folder lifecycle

    Attributes:
        parse_result: Parsed data from XLSX files, or None if sources unavailable
        source_files_count: Number of source XLSX files found
        status: MANIFEST_STATUS_* constant indicating outcome
    """

    parse_result: SeriesParseResult | None
    source_files_count: int
    status: str


class USDAFruitAndVegetablesDownloader:
    """Orchestrates USDA XLSX download, parsing, and CSV output.

    This class coordinates the full data pipeline:
    1. Source resolution (listing page scrape or local directory)
    2. XLSX parsing via SeriesParser
    3. CSV output via SeriesWriter

    The constructor uses a factory pattern for testability. Production code can
    instantiate with just (output_directory, config, logger) - factories create
    defaults. Tests can inject mocks via the factory parameters or direct instances.

    Example (production):
        with USDAFruitAndVegetablesDownloader(output_dir, config, logger) as downloader:
            downloader.process(start_date, end_date)

    Example (testing):
        downloader = USDAFruitAndVegetablesDownloader(
            output_dir, config, logger,
            source_catalog=mock_catalog,  # Inject mock directly
        )
    """

    def __init__(
        self,
        output_directory: Path,
        config: ProcessorConfig,
        logger: Logger,
        http_client: HttpClient | None = None,
        source_catalog: SourceCatalog | None = None,
        series_parser: SeriesParser | None = None,
        series_writer: SeriesWriter | None = None,
        rate_gate_factory: Callable[[ProcessorConfig], RateGate] | None = None,
        http_client_factory: Callable[[ProcessorConfig, RateGate, Logger], HttpClient] | None = None,
        source_catalog_factory: Callable[[ProcessorConfig, HttpClient, Logger], SourceCatalog] | None = None,
        series_parser_factory: Callable[[ProcessorConfig, Logger], SeriesParser] | None = None,
        series_writer_factory: Callable[[Path, Logger], SeriesWriter] | None = None,
    ) -> None:
        """Initialize the downloader with required dependencies and optional factories.

        Args:
            output_directory: Directory where CSV files will be written
            config: Processing configuration (dates, rate limits, etc.)
            logger: Logger for trace/error messages

            http_client: Pre-configured HTTP client (bypasses factory creation)
            source_catalog: Pre-configured source catalog (bypasses factory creation)
            series_parser: Pre-configured parser (bypasses factory creation)
            series_writer: Pre-configured writer (bypasses factory creation)

            rate_gate_factory: Factory to create rate limiter (default: RateGate)
            http_client_factory: Factory to create HTTP client (default: HttpClient)
            source_catalog_factory: Factory to create source catalog (default: SourceCatalog)
            series_parser_factory: Factory to create series parser (default: SeriesParser)
            series_writer_factory: Factory to create series writer (default: SeriesWriter)
        """
        self._output_directory = output_directory
        self._logger = logger
        self._http_client: HttpClient | None = http_client
        self._owns_http_client = False

        rate_gate_factory = rate_gate_factory or _default_rate_gate_factory
        http_client_factory = http_client_factory or _default_http_client_factory
        source_catalog_factory = source_catalog_factory or SourceCatalog
        series_parser_factory = series_parser_factory or SeriesParser
        series_writer_factory = series_writer_factory or SeriesWriter

        if source_catalog is None:
            if self._http_client is None:
                rate_gate = rate_gate_factory(config)
                self._http_client = http_client_factory(config, rate_gate, logger)
                self._owns_http_client = True
            self._source_catalog = source_catalog_factory(config, self._http_client, logger)
        else:
            self._source_catalog = source_catalog
        self._series_parser = series_parser or series_parser_factory(config, logger)
        self._series_writer = series_writer or series_writer_factory(output_directory, logger)
        self._output_directory.mkdir(parents=True, exist_ok=True)

    def process(self, start_date: date, end_date: date) -> bool:
        """Process USDA data for date range: resolve sources, parse XLSX, and write CSVs."""
        start_date, end_date = validate_date_range(start_date, end_date)
        self._logger.trace(_with_prefix(f"Processing data from {start_date:%Y-%m-%d} to {end_date:%Y-%m-%d}"))

        start_year = start_date.year
        end_year = end_date.year

        with self._process_sources(start_year, end_year) as result:
            if result.status == MANIFEST_STATUS_NO_SOURCES:
                return True
            if result.status == MANIFEST_STATUS_NO_FILES:
                self._logger.error(_with_prefix("No XLSX sources available to process"))
                return False

            # parse_result guaranteed non-None when status is OK
            parse_result = result.parse_result
            assert parse_result is not None

            if parse_result.parsed_files == 0:
                self._logger.error(_with_prefix("No XLSX files were processed successfully"))
                return False

            accumulator = parse_result.accumulator
            if not accumulator.content_by_series:
                self._logger.trace(_with_prefix(f"No data found for requested years {start_year}-{end_year}"))
                return True

            total_rows_to_write = sum(len(value) for value in accumulator.content_by_series.values())
            self._logger.trace(
                _with_prefix(
                    "Parsed {parsed} points from {parsed_files}/{source_files} file(s); "
                    "selected {selected} points from {relevant} file(s); writing {series_count} series file(s) with "
                    "{total_rows} row(s) total"
                ).format(
                    parsed=parse_result.total_points_parsed,
                    parsed_files=parse_result.parsed_files,
                    source_files=result.source_files_count,
                    selected=parse_result.total_points_selected,
                    relevant=parse_result.relevant_files,
                    series_count=len(accumulator.content_by_series),
                    total_rows=total_rows_to_write,
                )
            )

            self._series_writer.write(accumulator.content_by_series)

            self._logger.trace(_with_prefix("Processing complete"))
            return True

    def collect_series_metadata(self, start_date: date, end_date: date) -> SeriesManifestResult:
        """Collect metadata for all series in the date range without writing files."""
        start_date, end_date = validate_date_range(start_date, end_date)
        start_year = start_date.year
        end_year = end_date.year

        with self._process_sources(start_year, end_year) as result:
            if result.status == MANIFEST_STATUS_NO_SOURCES:
                return _create_manifest_result(status=MANIFEST_STATUS_NO_SOURCES)
            if result.status == MANIFEST_STATUS_NO_FILES:
                return _create_manifest_result(status=MANIFEST_STATUS_NO_FILES)

            # parse_result guaranteed non-None when status is OK
            parse_result = result.parse_result
            assert parse_result is not None

            if parse_result.parsed_files == 0:
                return _create_manifest_result(
                    source_files_count=result.source_files_count,
                    parsed_files=parse_result.parsed_files,
                    relevant_files=parse_result.relevant_files,
                    total_points_parsed=parse_result.total_points_parsed,
                    total_points_selected=parse_result.total_points_selected,
                    status=MANIFEST_STATUS_NO_FILES,
                )

            accumulator = parse_result.accumulator
            if not accumulator.metadata_by_series:
                return _create_manifest_result(
                    source_files_count=result.source_files_count,
                    parsed_files=parse_result.parsed_files,
                    relevant_files=parse_result.relevant_files,
                    total_points_parsed=parse_result.total_points_parsed,
                    total_points_selected=parse_result.total_points_selected,
                    status=MANIFEST_STATUS_NO_DATA,
                )

            return _create_manifest_result(
                metadata_by_series=accumulator.metadata_by_series,
                source_files_count=result.source_files_count,
                parsed_files=parse_result.parsed_files,
                relevant_files=parse_result.relevant_files,
                total_points_parsed=parse_result.total_points_parsed,
                total_points_selected=parse_result.total_points_selected,
                status=MANIFEST_STATUS_OK,
            )

    def _get_source_files(
        self,
        start_year: int,
        end_year: int,
    ) -> tuple[list[tuple[Path, str]] | None, Path | None]:
        result = self._source_catalog.resolve_source_files(start_year, end_year)
        return result.source_files, result.temp_folder

    @contextmanager
    def _process_sources(
        self,
        start_year: int,
        end_year: int,
    ) -> Generator[_SourcesResult, None, None]:
        """Resolve and parse XLSX sources for a year range.

        Context manager that handles temp folder cleanup automatically.
        Yields a _SourcesResult containing either:
        - status == MANIFEST_STATUS_NO_SOURCES: Source listing unavailable
        - status == MANIFEST_STATUS_NO_FILES: No XLSX files found
        - status == MANIFEST_STATUS_OK: parse_result contains parsed data

        Example:
            with self._process_sources(2020, 2022) as result:
                if result.status != MANIFEST_STATUS_OK:
                    return handle_early_exit(result.status)
                # Use result.parse_result
        """
        source_files, temp_folder = self._get_source_files(start_year, end_year)
        try:
            if source_files is None:
                yield _SourcesResult(None, 0, MANIFEST_STATUS_NO_SOURCES)
                return
            if not source_files:
                yield _SourcesResult(None, 0, MANIFEST_STATUS_NO_FILES)
                return

            parse_result = self._series_parser.parse(source_files, start_year, end_year)
            yield _SourcesResult(parse_result, len(source_files), MANIFEST_STATUS_OK)
        finally:
            if temp_folder is not None:
                cleanup_temp_folder(temp_folder)

    def close(self) -> None:
        if self._owns_http_client and self._http_client is not None:
            self._http_client.close()

    def __enter__(self) -> USDAFruitAndVegetablesDownloader:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


def _resolve_http_timeout_seconds(config: ProcessorConfig, logger: Logger) -> int:
    config_value = config.http_timeout_seconds
    if config_value <= 0:
        logger.error(
            _with_prefix(f"Invalid {CONFIG_HTTP_TIMEOUT_SECONDS_KEY}; using default {DEFAULT_HTTP_TIMEOUT_SECONDS}")
        )
        return DEFAULT_HTTP_TIMEOUT_SECONDS
    return config_value


def _default_rate_gate_factory(config: ProcessorConfig) -> RateGate:
    return RateGate(config.rate_limit_requests, config.rate_limit_seconds)


def _default_http_client_factory(config: ProcessorConfig, rate_gate: RateGate, logger: Logger) -> HttpClient:
    max_retries = config.max_retries
    http_timeout_seconds = _resolve_http_timeout_seconds(config, logger)
    return HttpClient(
        http_timeout_seconds,
        max_retries,
        rate_gate,
        logger,
    )

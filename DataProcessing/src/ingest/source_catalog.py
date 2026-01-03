from __future__ import annotations

import io
import shutil
import tempfile
import uuid
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from src.core.config_provider import ProcessorConfig
from src.core.constants import (
    DOWNLOADER_LOG_PREFIX,
    FILE_YEAR_REGEX,
    LISTING_URLS,
)
from src.core.logging_utils import Logger
from src.ingest.html_parser import extract_links
from src.ingest.http_client import HttpClient, HttpError


@dataclass(frozen=True)
class SourceFilesResult:
    source_files: list[tuple[Path, str]] | None
    temp_folder: Path | None


class SourceCatalog:
    def __init__(
        self,
        config: ProcessorConfig,
        http_client: HttpClient,
        logger: Logger,
        html_parser: Callable[[str, str, tuple[str, ...]], list[str]] | None = None,
        uuid_factory: Callable[[], uuid.UUID] | None = None,
    ) -> None:
        self._config = config
        self._http_client = http_client
        self._logger = logger
        self._html_parser = html_parser or extract_links
        self._uuid_factory = uuid_factory or uuid.uuid4

    def resolve_source_files(self, start_year: int, end_year: int) -> SourceFilesResult:
        """Resolve source files: local directory or download from USDA listing page."""
        local_result = self._load_local_sources()
        if local_result.source_files:
            return local_result
        if local_result.temp_folder is not None:
            cleanup_temp_folder(local_result.temp_folder)
        return self._download_remote_sources(start_year, end_year)

    def _load_local_sources(self) -> SourceFilesResult:
        local_xlsx_directory = self._config.xlsx_directory.strip()
        if not local_xlsx_directory:
            return SourceFilesResult([], None)

        directory = Path(local_xlsx_directory)
        if not directory.exists():
            return SourceFilesResult([], None)

        source_files: list[tuple[Path, str]] = []
        local_zip_files: list[Path] = []
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".xlsx":
                if _try_extract_year_from_file_name(path.name) is None:
                    raise ValueError(_with_prefix(f"Local XLSX filename missing year: {path.name}"))
                source_files.append((path, path.name))
                continue
            if path.suffix.lower() == ".zip":
                local_zip_files.append(path)

        temp_folder: Path | None = None
        if local_zip_files:
            temp_folder = self._create_temp_folder()
            for zip_path in local_zip_files:
                bytes_data = zip_path.read_bytes()
                _extract_zip_xlsx_sources(
                    bytes_data,
                    zip_path.name,
                    temp_folder,
                    source_files,
                    self._logger,
                    self._uuid_factory,
                )

        if source_files:
            self._logger.trace(_with_prefix(f"Using {len(source_files)} local .xlsx file(s) from {directory}"))

        return SourceFilesResult(source_files, temp_folder)

    def _download_remote_sources(self, start_year: int, end_year: int) -> SourceFilesResult:
        listing = _try_download_listing(self._http_client, self._logger, self._config)
        if listing is None:
            self._logger.error(_with_prefix("Failed to download listing page"))
            return SourceFilesResult([], None)

        listing_html, listing_base_uri = listing
        xlsx_urls = self._extract_xlsx_urls(listing_html, listing_base_uri)
        zip_urls = self._extract_zip_urls(listing_html, listing_base_uri)

        if not xlsx_urls and not zip_urls:
            self._logger.error(_with_prefix(f"No .xlsx or .zip links found on {listing_base_uri}"))
            return SourceFilesResult([], None)

        self._logger.trace(
            _with_prefix(f"Found {len(xlsx_urls)} candidate .xlsx URL(s) and {len(zip_urls)} candidate .zip URL(s)")
        )

        filtered_xlsx_urls, filtered_zip_urls = _filter_source_urls(
            xlsx_urls,
            zip_urls,
            start_year,
            end_year,
            self._config,
        )

        self._logger.trace(
            _with_prefix(
                f"Selected {len(filtered_xlsx_urls)}/{len(xlsx_urls)} .xlsx URL(s) "
                f"and {len(filtered_zip_urls)}/{len(zip_urls)} archived .zip URL(s) for years {start_year}-{end_year}"
            )
        )

        if not filtered_xlsx_urls and not filtered_zip_urls:
            self._logger.trace(_with_prefix(f"No files found for requested years {start_year}-{end_year}"))
            return SourceFilesResult(None, None)

        self._logger.trace(
            _with_prefix(
                f"Downloading {len(filtered_xlsx_urls)} .xlsx file(s) and "
                f"{len(filtered_zip_urls)} archived .zip file(s) for requested years {start_year}-{end_year}"
            )
        )

        temp_folder = self._create_temp_folder()
        source_files: list[tuple[Path, str]] = []

        for url in filtered_zip_urls:
            bytes_data = _download_bytes(self._http_client, self._logger, url)
            if bytes_data is None:
                continue
            _extract_zip_xlsx_sources(
                bytes_data,
                url,
                temp_folder,
                source_files,
                self._logger,
                self._uuid_factory,
            )

        for url in filtered_xlsx_urls:
            file_name = _extract_file_name(url) or f"usda-fruitveg-{self._uuid_factory().hex}.xlsx"
            bytes_data = _download_bytes(self._http_client, self._logger, url)
            if bytes_data is None:
                continue
            file_path = temp_folder / file_name
            file_path.write_bytes(bytes_data)
            source_files.append((file_path, url))

        return SourceFilesResult(source_files, temp_folder)

    def _extract_xlsx_urls(self, html_text: str, base_url: str) -> list[str]:
        return self._html_parser(html_text, base_url, (".xlsx",))

    def _extract_zip_urls(self, html_text: str, base_url: str) -> list[str]:
        return self._html_parser(html_text, base_url, (".zip",))

    def _create_temp_folder(self) -> Path:
        temp_root = Path(tempfile.gettempdir()) / "USDAFruitAndVegetables"
        temp_folder = temp_root / self._uuid_factory().hex
        temp_folder.mkdir(parents=True, exist_ok=True)
        return temp_folder


def cleanup_temp_folder(folder: Path) -> None:
    shutil.rmtree(folder, ignore_errors=True)


def _with_prefix(message: str) -> str:
    return f"{DOWNLOADER_LOG_PREFIX}: {message}"


def _filter_source_urls(
    xlsx_urls: list[str],
    zip_urls: list[str],
    start_year: int,
    end_year: int,
    config: ProcessorConfig,
) -> tuple[list[str], list[str]]:
    yearless_xlsx_urls = [url for url in xlsx_urls if _try_extract_year_from_url(url) is None]
    if yearless_xlsx_urls:
        sample = ", ".join(yearless_xlsx_urls[:3])
        message = _with_prefix(
            f"Yearless .xlsx URL(s) found on listing (count: {len(yearless_xlsx_urls)}). Example(s): {sample}"
        )
        raise ValueError(message)

    years = set(range(start_year, end_year + 1))
    filtered_zip_urls: list[str] = []
    for url in zip_urls:
        if not _is_archived_fruit_and_vegetable_zip(url):
            continue
        year = _try_extract_year_from_url(url)
        if year is None or year in years:
            filtered_zip_urls.append(url)
    filtered_zip_urls.sort(key=lambda item: item.lower())

    filtered_xlsx_urls = _filter_urls_by_year(xlsx_urls, years)
    filtered_xlsx_urls.sort(key=lambda item: item.lower())

    max_xlsx_downloads = config.max_xlsx_downloads
    if max_xlsx_downloads > 0 and len(filtered_xlsx_urls) > max_xlsx_downloads:
        filtered_xlsx_urls = filtered_xlsx_urls[:max_xlsx_downloads]

    return filtered_xlsx_urls, filtered_zip_urls


def _filter_urls_by_year(urls: Sequence[str], years: set[int]) -> list[str]:
    filtered: list[str] = []
    for url in urls:
        year = _try_extract_year_from_url(url)
        if year is None or year in years:
            filtered.append(url)
    return filtered


def _try_download_listing(
    http_client: HttpClient,
    logger: Logger,
    config: ProcessorConfig,
) -> tuple[str, str] | None:
    """Try each listing URL until one succeeds with valid links.

    Per Constitution: Explicit over implicit - HttpError is caught and logged,
    allowing fallback to alternative URLs.
    """
    for url in _get_listing_urls(config):
        try:
            response = http_client.get_text(url)
            if not _has_listing_links(response):
                logger.trace(_with_prefix(f"No listing links found at {url}"))
                continue
            return response, url
        except HttpError as err:
            # Expected for some URLs (404 for missing resources, 402 for paywalls)
            logger.trace(_with_prefix(f"HTTP {err.status_code} at {url}"))
            continue
        except RuntimeError as err:
            # Network/transport errors
            logger.error(_with_prefix(f"Error downloading listing page {url}"), err)
    return None


def _get_listing_urls(config: ProcessorConfig) -> Sequence[str]:
    override_url = config.listing_url.strip()
    if override_url:
        return [override_url]
    return list(LISTING_URLS)


def _has_listing_links(html_text: str) -> bool:
    lowered = html_text.lower()
    return ".xlsx" in lowered or ".zip" in lowered or ".csv" in lowered


def _is_archived_fruit_and_vegetable_zip(url: str) -> bool:
    file_name = _extract_file_name(url)
    if not file_name:
        return False
    lower = file_name.lower()
    return lower.startswith("fruit-") or lower.startswith("vegetables-")


def _try_extract_year_from_url(url: str) -> int | None:
    file_name = _extract_file_name(url)
    if not file_name:
        return None
    return _try_extract_year_from_file_name(file_name)


def _try_extract_year_from_file_name(file_name: str) -> int | None:
    match = FILE_YEAR_REGEX.search(file_name)
    if not match:
        return None
    try:
        parsed = int(match.group("year"))
    except ValueError:
        return None
    if parsed < 1900 or parsed > datetime.now(UTC).year + 1:
        return None
    return parsed


def _extract_zip_xlsx_sources(
    zip_bytes: bytes,
    zip_source: str,
    temp_folder: Path,
    source_files: list[tuple[Path, str]],
    logger: Logger,
    uuid_factory: Callable[[], uuid.UUID],
) -> None:
    extracted = 0
    with zipfile.ZipFile(_io_bytes(zip_bytes)) as archive:
        for entry in archive.infolist():
            if not entry.filename or entry.filename.endswith("/") or not entry.filename.lower().endswith(".xlsx"):
                continue
            file_name = Path(entry.filename).name
            if not file_name:
                continue
            destination = temp_folder / file_name
            if destination.exists():
                destination = temp_folder / f"{destination.stem}-{uuid_factory().hex}.xlsx"
            with archive.open(entry) as entry_stream, destination.open("wb") as output:
                output.write(entry_stream.read())
            source_files.append((destination, f"{zip_source}::{entry.filename}"))
            extracted += 1
    logger.trace(_with_prefix(f"Extracted {extracted} .xlsx file(s) from {zip_source}"))


def _extract_file_name(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    path = parsed.path
    if not path:
        return None
    return Path(path).name


def _download_bytes(http_client: HttpClient, logger: Logger, url: str) -> bytes | None:
    """Download file bytes. Returns None on HttpError (logged at caller).

    Per Constitution: Explicit over implicit - HttpError indicates specific failure,
    empty bytes indicates empty file (both valid states for caller to handle).
    """
    try:
        bytes_data = http_client.get_bytes(url)
        if not bytes_data:
            logger.error(_with_prefix(f"Empty response downloading {url}"))
            return None
        return bytes_data
    except HttpError as err:
        logger.error(_with_prefix(f"HTTP {err.status_code} downloading {url}: {err.reason}"))
        return None


def _io_bytes(content: bytes) -> io.BytesIO:
    return io.BytesIO(content)

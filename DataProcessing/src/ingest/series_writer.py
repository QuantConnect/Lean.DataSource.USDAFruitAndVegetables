from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.core.constants import DATE_FORMAT_YYYYMMDD, DOWNLOADER_LOG_PREFIX
from src.core.logging_utils import Logger
from src.core.schema import (
    CSV_AVERAGE_RETAIL_PRICE_INDEX,
    CSV_COLUMN_COUNT,
    CSV_CUP_EQUIVALENT_SIZE_INDEX,
    CSV_CUP_EQUIVALENT_UNIT_INDEX,
    CSV_DATE_INDEX,
    CSV_PREPARATION_YIELD_FACTOR_INDEX,
    CSV_PRICE_PER_CUP_EQUIVALENT_INDEX,
    CSV_UNIT_INDEX,
    CupEquivalentUnit,
    PriceUnit,
)
from src.model.dataset_types import SeriesPoint


def format_series_row(
    row_date: date,
    average_retail_price: Decimal,
    unit: PriceUnit,
    preparation_yield_factor: Decimal,
    cup_equivalent_size: Decimal,
    cup_equivalent_unit: CupEquivalentUnit,
    price_per_cup_equivalent: Decimal,
) -> str:
    values = [""] * CSV_COLUMN_COUNT
    values[CSV_DATE_INDEX] = row_date.strftime(DATE_FORMAT_YYYYMMDD)
    values[CSV_AVERAGE_RETAIL_PRICE_INDEX] = _format_decimal(average_retail_price)
    values[CSV_UNIT_INDEX] = unit.value
    values[CSV_PREPARATION_YIELD_FACTOR_INDEX] = _format_decimal(preparation_yield_factor)
    values[CSV_CUP_EQUIVALENT_SIZE_INDEX] = _format_decimal(cup_equivalent_size)
    values[CSV_CUP_EQUIVALENT_UNIT_INDEX] = cup_equivalent_unit.value
    values[CSV_PRICE_PER_CUP_EQUIVALENT_INDEX] = _format_decimal(price_per_cup_equivalent)
    return ",".join(values)


def save_series_file(
    output_directory: Path,
    series_code: str,
    points_by_date: Mapping[date, SeriesPoint],
    logger: Logger,
) -> None:
    normalized_series = series_code.strip().lower()
    output_directory.mkdir(parents=True, exist_ok=True)
    path = output_directory / f"{normalized_series}.csv"

    output_lines = [
        _format_validated_row(point, source=normalized_series)
        for _, point in sorted(points_by_date.items())
        if _has_series_data(point)
    ]
    content = "\n".join(output_lines)

    # Atomic write: write to temp file in same directory, then rename.
    # On any failure, clean up temp file before re-raising the original exception.
    temp_path = path.with_suffix(".tmp")
    try:
        temp_path.write_text(content)
        temp_path.replace(path)  # Atomic on POSIX
    except OSError:
        temp_path.unlink(missing_ok=True)
        raise

    logger.trace(f"{DOWNLOADER_LOG_PREFIX}: Saved {len(output_lines)} rows to {path}")


class SeriesWriter:
    def __init__(self, output_directory: Path, logger: Logger) -> None:
        self._output_directory = output_directory
        self._logger = logger

    def write(self, content_by_series: Mapping[str, Mapping[date, SeriesPoint]]) -> None:
        normalized_by_series: dict[str, tuple[str, Mapping[date, SeriesPoint]]] = {}
        for series_code, points_by_date in content_by_series.items():
            normalized = series_code.strip().lower()
            existing = normalized_by_series.get(normalized)
            if existing is not None and existing[0] != series_code:
                raise ValueError(
                    f"Normalized series code collision for {existing[0]} and {series_code}: '{normalized}'"
                )
            normalized_by_series[normalized] = (series_code, points_by_date)

        for _normalized_series, (series_code, points_by_date) in sorted(normalized_by_series.items()):
            save_series_file(
                self._output_directory,
                series_code,
                points_by_date,
                self._logger,
            )


def _format_decimal(value: Decimal) -> str:
    formatted = format(value, "f")
    return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted


def _has_series_data(point: SeriesPoint) -> bool:
    return bool(point.series_code.strip())


def _format_validated_row(point: SeriesPoint, *, source: str) -> str:
    row = format_series_row(
        point.date,
        point.average_retail_price,
        point.unit,
        point.preparation_yield_factor,
        point.cup_equivalent_size,
        point.cup_equivalent_unit,
        point.price_per_cup_equivalent,
    )
    _validate_row(row, source=source)
    return row


def _validate_row(row: str, *, source: str) -> None:
    columns = row.split(",")
    if len(columns) != CSV_COLUMN_COUNT:
        raise ValueError(f"Expected {CSV_COLUMN_COUNT} columns but found {len(columns)} for {source}: {row}")

    date_text = columns[CSV_DATE_INDEX]
    if len(date_text) != 8 or not date_text.isdigit():
        raise ValueError(f"Invalid date value '{date_text}' for {source}: {row}")

    _validate_enum(PriceUnit, columns[CSV_UNIT_INDEX], source, row)
    _validate_enum(CupEquivalentUnit, columns[CSV_CUP_EQUIVALENT_UNIT_INDEX], source, row)

    _validate_decimal(columns[CSV_AVERAGE_RETAIL_PRICE_INDEX], source, row)
    _validate_decimal(columns[CSV_PREPARATION_YIELD_FACTOR_INDEX], source, row)
    _validate_decimal(columns[CSV_CUP_EQUIVALENT_SIZE_INDEX], source, row)
    _validate_decimal(columns[CSV_PRICE_PER_CUP_EQUIVALENT_INDEX], source, row)


def _validate_enum(enum_type: type[PriceUnit] | type[CupEquivalentUnit], value: str, source: str, row: str) -> None:
    if value not in {item.value for item in enum_type}:
        raise ValueError(f"Invalid {enum_type.__name__} value '{value}' for {source}: {row}")


def _validate_decimal(value: str, source: str, row: str) -> None:
    if value == "":
        raise ValueError(f"Missing decimal value for {source}: {row}")
    try:
        Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid decimal '{value}' for {source}: {row}") from exc

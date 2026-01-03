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
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.core.constants import (
    EXPECTED_XLSX_COLUMN_COUNT,
    SHEET_YEAR_REGEX,
    XLSX_ALLOWED_GROUP_HEADERS,
    XLSX_CONTACT_PREFIX_REGEX,
    XLSX_ERRATA_PREFIX_REGEX,
    XLSX_FOOTNOTE_PREFIX_REGEX,
    XLSX_SOURCE_KEYWORDS,
    XLSX_SOURCE_PREFIX_REGEX,
)
from src.model.dataset_types import CupEquivalentUnit, PriceUnit, SeriesPoint
from src.model.series_code import get_series_code, normalize_form
from src.parsing.xlsx_reader import read_sheets


class _SeriesPointModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    series_code: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    form: str = Field(min_length=1)
    date: date
    average_retail_price: Decimal
    unit: PriceUnit
    preparation_yield_factor: Decimal
    cup_equivalent_size: Decimal
    cup_equivalent_unit: CupEquivalentUnit
    price_per_cup_equivalent: Decimal

    @field_validator(
        "average_retail_price", "preparation_yield_factor", "cup_equivalent_size", "price_per_cup_equivalent"
    )
    @classmethod
    def _ensure_decimal_values(cls, value: Decimal) -> Decimal:
        return value


def parse_xlsx(file_path: Path) -> list[SeriesPoint]:
    """Parse USDA XLSX workbook into SeriesPoints.

    Per Constitution: Fail-fast - all validation errors raise ValueError with context.

    Structure:
    1. Read all sheets from workbook (xlsx_reader.read_sheets)
    2. For each sheet:
       a. Find header row (Form, Average retail price, ...)
       b. Extract year from title or sheet name
       c. Parse data rows into SeriesPoints
       d. Handle non-data rows: group headers (Fresh, Canned, Juice) and footnotes
    3. Return accumulated points

    Helpers:
    - _find_header_row_index: Locate header in first rows (may be split across 2 rows)
    - _try_get_year: Extract 4-digit year from text
    - _parse_price_unit / _parse_cup_equivalent_unit: Map text to enum values
    - _is_group_header_row / _is_footnote_row: Identify non-data rows

    Args:
        file_path: Path to XLSX workbook

    Returns:
        List of validated SeriesPoint objects

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If validation fails (missing year, header, units, etc.)
    """
    if not Path(file_path).exists():
        raise FileNotFoundError("XLSX file not found", file_path)

    sheets = read_sheets(Path(file_path), EXPECTED_XLSX_COLUMN_COUNT)
    if not sheets:
        raise ValueError(f"XLSX file has no worksheets: {file_path}")

    points: list[SeriesPoint] = []

    for sheet_name, rows in sheets:
        if not rows:
            raise ValueError(f"XLSX worksheet has no rows: {file_path} ({sheet_name})")

        header_row_index = _find_header_row_index(rows)
        if header_row_index < 0:
            raise ValueError(f"XLSX worksheet missing expected header row: {file_path} ({sheet_name})")

        title = _get_title(rows, header_row_index)
        year_text = title or sheet_name
        year = _try_get_year(year_text)
        if year is None:
            raise ValueError(f"XLSX worksheet missing year in title: {file_path} ({sheet_name})")

        # USDA data is annual; use Jan 1 as the observation date for the year
        row_date = date(year, 1, 1)
        product_name = _get_product_name(sheet_name, title)
        if not product_name:
            raise ValueError(f"XLSX worksheet missing product name: {file_path} ({sheet_name})")

        current_group: str | None = None

        for row_index, row in enumerate(rows[header_row_index + 1 :], start=header_row_index + 1):
            row_number = row_index + 1
            form_value = (row[0] or "").strip()
            if not form_value:
                if _row_has_any_non_form_value(row):
                    raise ValueError(
                        f"XLSX row missing form value but has other data: {file_path} ({sheet_name}) row {row_number}"
                    )
                continue

            average_retail_price = _try_parse_decimal(row[1])
            price_per_cup_equivalent = _try_parse_decimal(row[6])
            cup_equivalent_size = _try_parse_decimal(row[4])
            preparation_yield_factor = _try_parse_decimal(row[3])

            if (
                average_retail_price is None
                or price_per_cup_equivalent is None
                or cup_equivalent_size is None
                or preparation_yield_factor is None
            ):
                if _is_group_header_row(row, form_value):
                    current_group = normalize_form(form_value)
                    continue
                if _is_footnote_row(row, form_value):
                    continue
                raise ValueError(
                    f"XLSX row missing numeric fields: {file_path} ({sheet_name}) row {row_number} form '{form_value}'"
                )

            form_with_context = _apply_form_context(form_value, current_group)
            unit_text = (row[2] or "").strip()
            if not unit_text:
                raise ValueError(
                    f"XLSX row missing price unit: {file_path} ({sheet_name}) row {row_number} form '{form_with_context}'"
                )
            unit = _parse_price_unit(unit_text)
            if unit == PriceUnit.UNKNOWN:
                raise ValueError(
                    f"XLSX row has unknown price unit '{unit_text}': {file_path} ({sheet_name}) row {row_number} form '{form_with_context}'"
                )

            cup_unit_text = (row[5] or "").strip()
            if not cup_unit_text:
                raise ValueError(
                    f"XLSX row missing cup equivalent unit: {file_path} ({sheet_name}) row {row_number} form '{form_with_context}'"
                )
            cup_unit = _parse_cup_equivalent_unit(cup_unit_text)
            if cup_unit == CupEquivalentUnit.UNKNOWN:
                raise ValueError(
                    f"XLSX row has unknown cup equivalent unit '{cup_unit_text}': {file_path} ({sheet_name}) row {row_number} form '{form_with_context}'"
                )
            series_code = get_series_code(product_name, form_with_context)
            normalized_form = normalize_form(form_with_context)
            try:
                model = _SeriesPointModel(
                    series_code=series_code,
                    product_name=product_name,
                    form=normalized_form,
                    date=row_date,
                    average_retail_price=average_retail_price,
                    unit=unit,
                    preparation_yield_factor=preparation_yield_factor,
                    cup_equivalent_size=cup_equivalent_size,
                    cup_equivalent_unit=cup_unit,
                    price_per_cup_equivalent=price_per_cup_equivalent,
                )
            except ValidationError as err:
                error_details = "; ".join([f"{e['loc'][0]}: {e['msg']}" for e in err.errors()])
                raise ValueError(
                    f"XLSX row failed validation: {file_path} ({sheet_name}) row {row_number} "
                    f"form '{form_with_context}' - {error_details}"
                ) from err
            points.append(SeriesPoint(**model.model_dump()))

    return points


def _find_header_row_index(rows: Sequence[Sequence[str | None]]) -> int:
    for i, row in enumerate(rows):
        if _is_expected_header_row(row):
            return i
        if i + 1 < len(rows):
            merged = _merge_header_rows(row, rows[i + 1])
            if _is_expected_header_row(merged):
                return i + 1
    return -1


def _is_expected_header_row(row: Sequence[str | None]) -> bool:
    if len(row) < EXPECTED_XLSX_COLUMN_COUNT:
        return False

    normalized = [_normalize_header_cell(cell) for cell in row[:EXPECTED_XLSX_COLUMN_COUNT]]
    if normalized[0] != "form":
        return False
    if normalized[1] != "average retail price":
        return False
    if normalized[2] not in {"", "average retail price unit of measure"}:
        return False
    if normalized[3] != "preparation yield factor":
        return False
    if normalized[4] not in {"size of a cup equivalent", "size of cup equivalent"}:
        return False
    if normalized[5] not in {"", "cup equivalent unit of measure"}:
        return False
    if normalized[6] != "average price per cup equivalent":
        return False
    return True


def _normalize_header_cell(value: str | None) -> str:
    if value is None:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", value.strip().lower())
    return " ".join(normalized.split())


def _get_title(rows: Sequence[Sequence[str | None]], header_row_index: int) -> str | None:
    for i in range(header_row_index):
        value = rows[i][0]
        if value and value.strip():
            return value.strip()
    return None


def _try_get_year(text: str) -> int | None:
    if not text:
        return None
    matches = list(SHEET_YEAR_REGEX.finditer(text))
    if not matches:
        return None
    # USDA fruit/vegetable data starts ~2000; 1900 lower bound for historical archives
    max_year = datetime.now(UTC).year + 1
    for match in reversed(matches):
        year_text = match.group("year")
        try:
            parsed = int(year_text)
        except ValueError:
            continue
        if 1900 <= parsed <= max_year:
            return parsed
    return None


def _get_product_name(sheet_name: str, title: str | None) -> str:
    if title:
        trimmed = title.strip()
        split_title = _split_title(trimmed)
        if split_title:
            return split_title
    return sheet_name.strip()


def _split_title(title: str) -> str | None:
    for delimiter in ("\u2014", " - "):
        dash_index = title.find(delimiter)
        if dash_index > 0:
            return title[:dash_index].strip()
    return None


def _try_parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _normalize_unit_text(value: str | None) -> str:
    if value is None:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", value.strip().lower())
    return " ".join(normalized.split())


def _parse_price_unit(value: str | None) -> PriceUnit:
    normalized = _normalize_unit_text(value)
    if normalized == "per pound":
        return PriceUnit.PER_POUND
    if normalized in {
        "per pint",
        "per pint 16 fluid ounces ready to drink",
        "per pint 16 fluid ounces concentrate",
    }:
        return PriceUnit.PER_PINT
    return PriceUnit.UNKNOWN


def _parse_cup_equivalent_unit(value: str | None) -> CupEquivalentUnit:
    normalized = _normalize_unit_text(value)
    if normalized in {"fl oz", "floz", "fluid ounce", "fluid ounces"}:
        return CupEquivalentUnit.FLUID_OUNCES
    if normalized == "pints":
        return CupEquivalentUnit.PINTS
    if normalized in {"pound", "pounds"}:
        return CupEquivalentUnit.POUNDS
    return CupEquivalentUnit.UNKNOWN


def _merge_header_rows(
    primary: Sequence[str | None],
    secondary: Sequence[str | None],
) -> list[str | None]:
    merged: list[str | None] = []
    for index in range(EXPECTED_XLSX_COLUMN_COUNT):
        merged.append(_merge_header_cell(_safe_cell(primary, index), _safe_cell(secondary, index)))
    return merged


def _safe_cell(row: Sequence[str | None], index: int) -> str | None:
    if index >= len(row):
        return None
    return row[index]


def _merge_header_cell(primary: str | None, secondary: str | None) -> str | None:
    primary_text = (primary or "").strip()
    secondary_text = (secondary or "").strip()
    if primary_text and secondary_text:
        return f"{primary_text} {secondary_text}"
    if primary_text:
        return primary_text
    if secondary_text:
        return secondary_text
    return None


def _row_has_only_form_value(row: Sequence[str | None]) -> bool:
    for cell in row[1:EXPECTED_XLSX_COLUMN_COUNT]:
        if cell and str(cell).strip():
            return False
    return True


def _row_has_any_non_form_value(row: Sequence[str | None]) -> bool:
    for cell in row[1:EXPECTED_XLSX_COLUMN_COUNT]:
        if cell and str(cell).strip():
            return True
    return False


def _get_form_text(row: Sequence[str | None], form_value: str) -> str | None:
    if not form_value:
        return None
    if not _row_has_only_form_value(row):
        return None
    text = form_value.strip()
    if not text:
        return None
    return text


def _is_group_header_row(row: Sequence[str | None], form_value: str) -> bool:
    header = _get_form_text(row, form_value)
    if not header:
        return False
    normalized = normalize_form(header).strip().lower()
    return normalized in XLSX_ALLOWED_GROUP_HEADERS


def _is_footnote_row(row: Sequence[str | None], form_value: str) -> bool:
    text = _get_form_text(row, form_value)
    if not text:
        return False
    if XLSX_FOOTNOTE_PREFIX_REGEX.match(text):
        return True
    if XLSX_SOURCE_PREFIX_REGEX.match(text):
        return True
    if XLSX_CONTACT_PREFIX_REGEX.match(text):
        return True
    if XLSX_ERRATA_PREFIX_REGEX.match(text):
        return True
    lower = text.lower()
    for keyword in XLSX_SOURCE_KEYWORDS:
        if keyword in lower:
            return True
    return False


def _apply_form_context(form: str, context: str | None) -> str:
    if not context:
        return form
    if context.lower() in form.lower():
        return form
    return f"{context}, {form}"

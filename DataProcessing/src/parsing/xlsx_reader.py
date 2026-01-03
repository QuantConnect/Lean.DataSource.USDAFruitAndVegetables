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

from pathlib import Path
from typing import Any

try:
    import pandas as pd  # type: ignore[reportMissingImports]
except ImportError as err:  # pragma: no cover - depends on environment
    pd = None
    _pandas_import_error = err
else:
    _pandas_import_error = None


def read_sheets(file_path: Path, max_columns: int) -> list[tuple[str, list[list[str | None]]]]:
    if pd is None:
        raise RuntimeError(
            "pandas is required to parse XLSX files; install pandas and openpyxl."
        ) from _pandas_import_error

    try:
        sheet_map: dict[str, Any] = pd.read_excel(  # type: ignore[reportUnknownMemberType]
            file_path,
            sheet_name=None,
            header=None,
            dtype=str,
            engine="openpyxl",
            keep_default_na=False,
            na_filter=False,
            usecols=list(range(max_columns)),
        )
    except ImportError as err:
        raise RuntimeError("pandas requires openpyxl to read XLSX files.") from err
    except ValueError as err:
        raise ValueError(f"Failed to read XLSX workbook: {file_path}") from err

    result: list[tuple[str, list[list[str | None]]]] = []
    for sheet_name, frame in sheet_map.items():
        if frame is None:
            continue
        rows = _dataframe_to_rows(frame, max_columns)
        result.append((str(sheet_name), rows))
    return result


def _dataframe_to_rows(frame: Any, max_columns: int) -> list[list[str | None]]:
    rows: list[list[str | None]] = []
    for row in frame.itertuples(index=False, name=None):
        values = list(row[:max_columns])
        if len(values) < max_columns:
            values.extend([None] * (max_columns - len(values)))
        rows.append([_normalize_cell_value(value) for value in values])
    return rows


def _normalize_cell_value(value: Any) -> str | None:
    if value is None:
        return None
    if pd is not None:
        try:
            if pd.isna(value):  # type: ignore[reportUnknownMemberType]
                return None
        except (TypeError, ValueError):
            # Some objects are not compatible with pandas.isna; fall back to str().
            pass
    if isinstance(value, str):
        return value
    return str(value)

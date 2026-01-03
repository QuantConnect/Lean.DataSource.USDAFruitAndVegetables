from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from src.core.config_provider import ProcessorConfig
from src.core.constants import (
    DOWNLOADER_LOG_PREFIX,
)
from src.core.logging_utils import Logger
from src.ingest.series_accumulator import SeriesAccumulator
from src.model.dataset_types import SeriesPoint
from src.parsing.xlsx_parser import parse_xlsx


@dataclass(frozen=True)
class SeriesParseResult:
    accumulator: SeriesAccumulator
    parsed_files: int
    relevant_files: int
    total_points_parsed: int
    total_points_selected: int


class SeriesParser:
    def __init__(
        self,
        config: ProcessorConfig,
        logger: Logger,
        accumulator_factory: type[SeriesAccumulator] = SeriesAccumulator,
    ) -> None:
        self._config = config
        self._logger = logger
        self._accumulator_factory = accumulator_factory

    def parse(
        self,
        source_files: list[tuple[Path, str]],
        start_year: int,
        end_year: int,
    ) -> SeriesParseResult:
        parsed_files = 0
        relevant_files = 0
        total_points_parsed = 0
        total_points_selected = 0

        accumulator = self._accumulator_factory(self._config.normalize_cup_equivalent_unit)

        for path, source_name in sorted(source_files, key=lambda entry: entry[1].lower()):
            try:
                points = parse_xlsx(path)
                if not points:
                    message = _with_prefix(f"No data points parsed from {source_name}")
                    raise ValueError(message)

                parsed_files += 1
                total_points_parsed += len(points)

                selected_points = _filter_points_by_year(points, start_year, end_year)

                if not selected_points:
                    continue

                relevant_files += 1
                total_points_selected += len(selected_points)

                accumulator.add_points(selected_points, source_name)

            except (ValueError, OSError) as err:
                # Log context (source_name) before re-raising for debugging.
                self._logger.error(
                    _with_prefix(f"Failed processing {source_name}"),
                    err,
                )
                raise

        return SeriesParseResult(
            accumulator=accumulator,
            parsed_files=parsed_files,
            relevant_files=relevant_files,
            total_points_parsed=total_points_parsed,
            total_points_selected=total_points_selected,
        )


def _filter_points_by_year(points: Sequence[SeriesPoint], start_year: int, end_year: int) -> list[SeriesPoint]:
    return [point for point in points if start_year <= point.date.year <= end_year]


def _with_prefix(message: str) -> str:
    return f"{DOWNLOADER_LOG_PREFIX}: {message}"

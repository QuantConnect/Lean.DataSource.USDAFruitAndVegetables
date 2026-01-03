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

"""
USDAFruitAndVegetables data processor (Python).

This script downloads and processes USDA ERS Fruit & Vegetable Prices XLSX
workbooks and emits Lean-ready per-series CSV files.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from src.core.config_provider import ProcessorConfig, load_config
from src.core.constants import OUTPUT_SUBDIRECTORY
from src.core.date_utils import resolve_dates
from src.core.logging_utils import Logger, select_logger
from src.ingest.downloader import USDAFruitAndVegetablesDownloader


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:0.2f}s"
    minutes = seconds / 60.0
    if minutes < 60:
        return f"{minutes:0.2f}m"
    hours = minutes / 60.0
    return f"{hours:0.2f}h"


def _log_startup(logger: Logger, destination_directory: Path) -> None:
    logger.trace("USDAFruitAndVegetables Data Processor")
    logger.trace(f"Output: {destination_directory}")


def _default_downloader_factory(
    output_directory: Path,
    config: ProcessorConfig,
    logger: Logger,
) -> USDAFruitAndVegetablesDownloader:
    return USDAFruitAndVegetablesDownloader(output_directory, config, logger)


def main(
    *,
    config: ProcessorConfig | None = None,
    logger: Logger | None = None,
    downloader_factory: Callable[[Path, ProcessorConfig, Logger], USDAFruitAndVegetablesDownloader] | None = None,
) -> int:
    config = config or load_config()
    logger = logger or select_logger()

    output_directory = Path(config.output_root)
    destination_directory = output_directory / OUTPUT_SUBDIRECTORY

    start_date, end_date = resolve_dates(config)

    _log_startup(logger, destination_directory)
    logger.trace(f"Process Date: {start_date:%Y-%m-%d}")
    logger.trace(f"Process End Date: {end_date:%Y-%m-%d}")

    downloader_factory = downloader_factory or _default_downloader_factory

    with downloader_factory(destination_directory, config, logger) as processor:
        timer_start = time.perf_counter()
        success = processor.process(start_date, end_date)
        duration = time.perf_counter() - timer_start
        logger.trace(f"USDAFruitAndVegetables Program: Full run completed in {_format_duration(duration)}")

        if not success:
            logger.error("USDAFruitAndVegetables Program: Processing failed")
            return 1

    logger.trace("USDAFruitAndVegetables Program: Processing complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

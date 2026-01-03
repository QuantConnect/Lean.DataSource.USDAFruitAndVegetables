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

from datetime import date, datetime

from src.core.config_provider import ProcessorConfig
from src.core.constants import (
    DATE_FORMAT_YYYYMMDD,
)


def parse_yyyymmdd(value: str) -> date:
    return datetime.strptime(value, DATE_FORMAT_YYYYMMDD).date()


def resolve_dates(config: ProcessorConfig) -> tuple[date, date]:
    start_text = config.process_start_date
    end_text = config.process_end_date
    if not start_text or not end_text:
        raise ValueError("process-start-date and process-end-date are required")
    return parse_yyyymmdd(start_text), parse_yyyymmdd(end_text)


def validate_date_range(start_date: date, end_date: date) -> tuple[date, date]:
    if end_date < start_date:
        raise ValueError(f"End date {end_date:%Y-%m-%d} is before start date {start_date:%Y-%m-%d}.")
    return start_date, end_date

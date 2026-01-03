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

import json
from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.model.dataset_types import SeriesMetadata


class _SeriesManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    series_code: str = Field(min_length=1, alias="seriesCode")
    product_name: str = Field(min_length=1, alias="productName")
    form: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    cup_equivalent_unit: str = Field(min_length=1, alias="cupEquivalentUnit")


def write_series_manifest(path: Path, metadata_by_series: Mapping[str, SeriesMetadata]) -> None:
    entries = [
        _SeriesManifestEntry(
            seriesCode=series_code,
            productName=metadata.product_name,
            form=metadata.form,
            unit=metadata.unit.value,
            cupEquivalentUnit=metadata.cup_equivalent_unit.value,
        )
        for series_code, metadata in sorted(metadata_by_series.items(), key=lambda kvp: kvp[0].lower())
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([entry.model_dump(by_alias=True) for entry in entries], indent=2))

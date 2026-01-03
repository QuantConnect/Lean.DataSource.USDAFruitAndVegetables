from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal

from src.core.constants import DATE_FORMAT_YYYYMMDD, UNKNOWN_TEXT
from src.model.dataset_types import CupEquivalentUnit, SeriesMetadata, SeriesPoint


class SeriesAccumulator:
    def __init__(self, normalize_cup_units: bool) -> None:
        self._normalize_cup_units = normalize_cup_units
        self._content_by_series: dict[str, dict[date, SeriesPoint]] = {}
        self._seen_by_series_and_date: dict[tuple[str, str], tuple[SeriesPoint, str]] = {}
        self._metadata_by_series: dict[str, SeriesMetadata] = {}
        self._metadata_source_by_series: dict[str, str] = {}

    @property
    def content_by_series(self) -> Mapping[str, Mapping[date, SeriesPoint]]:
        return self._content_by_series

    @property
    def metadata_by_series(self) -> Mapping[str, SeriesMetadata]:
        return self._metadata_by_series

    def add_points(self, points: Sequence[SeriesPoint], source_name: str) -> None:
        for point in points:
            self.ingest_point(point, source_name)

    def ingest_point(self, point: SeriesPoint, source_name: str) -> None:
        """Ingest a point: normalize cup units, validate metadata, detect collisions."""
        if self._normalize_cup_units:
            cup_equivalent_size, cup_equivalent_unit = _normalize_cup_equivalent(
                point.cup_equivalent_size,
                point.cup_equivalent_unit,
            )
        else:
            cup_equivalent_size, cup_equivalent_unit = (
                point.cup_equivalent_size,
                point.cup_equivalent_unit,
            )

        normalized_point = SeriesPoint(
            series_code=point.series_code,
            product_name=point.product_name,
            form=point.form,
            date=point.date,
            average_retail_price=point.average_retail_price,
            unit=point.unit,
            preparation_yield_factor=point.preparation_yield_factor,
            cup_equivalent_size=cup_equivalent_size,
            cup_equivalent_unit=cup_equivalent_unit,
            price_per_cup_equivalent=point.price_per_cup_equivalent,
        )

        date_key = point.date.strftime(DATE_FORMAT_YYYYMMDD)
        unique_key = (point.series_code, date_key)

        existing_metadata = self._metadata_by_series.get(point.series_code)
        if existing_metadata is not None and (
            existing_metadata.product_name != point.product_name or existing_metadata.form != point.form
        ):
            existing_source = self._metadata_source_by_series.get(point.series_code, UNKNOWN_TEXT)
            message = (
                f"Series code collision for {point.series_code}: existing ({existing_source}) "
                f"product '{existing_metadata.product_name}', form '{existing_metadata.form}' vs "
                f"new ({source_name}) product '{point.product_name}', form '{point.form}'"
            )
            raise ValueError(message)

        existing = self._seen_by_series_and_date.get(unique_key)
        if existing and existing[0] != normalized_point:
            message = (
                f"Duplicate series/date collision for {point.series_code} on {date_key} - "
                f"existing ({existing[1]}): {existing[0]} | new ({source_name}): {normalized_point}"
            )
            raise ValueError(message)

        self._seen_by_series_and_date[unique_key] = (normalized_point, source_name)
        self._content_by_series.setdefault(point.series_code, {})[point.date] = normalized_point

        if existing_metadata is None:
            self._metadata_by_series[point.series_code] = SeriesMetadata(
                product_name=point.product_name,
                form=point.form,
                unit=point.unit,
                cup_equivalent_unit=cup_equivalent_unit,
            )
            self._metadata_source_by_series[point.series_code] = source_name
            return

        if existing_metadata.unit != point.unit or not _are_equivalent_cup_units(
            existing_metadata.cup_equivalent_unit, cup_equivalent_unit
        ):
            existing_source = self._metadata_source_by_series.get(point.series_code, UNKNOWN_TEXT)
            message = (
                f"Metadata mismatch for {point.series_code}: unit {existing_metadata.unit}->{point.unit}, "
                f"cup unit {existing_metadata.cup_equivalent_unit}->{cup_equivalent_unit} "
                f"(existing: {existing_source}, new: {source_name})"
            )
            raise ValueError(message)


def _are_equivalent_cup_units(left: CupEquivalentUnit, right: CupEquivalentUnit) -> bool:
    if left == right:
        return True
    return _is_volume_unit(left) and _is_volume_unit(right)


def _is_volume_unit(unit: CupEquivalentUnit) -> bool:
    return unit in {CupEquivalentUnit.PINTS, CupEquivalentUnit.FLUID_OUNCES}


def _normalize_cup_equivalent(size: Decimal, unit: CupEquivalentUnit) -> tuple[Decimal, CupEquivalentUnit]:
    if unit == CupEquivalentUnit.FLUID_OUNCES:
        return (size / Decimal("16"), CupEquivalentUnit.PINTS)
    return (size, unit)

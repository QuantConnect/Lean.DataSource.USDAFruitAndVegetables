# This file is auto-generated. Do not edit by hand.
# Source: datasources/USDAFruitAndVegetables/datasource-fruitandvegetables.yaml
# Generator: datasources/USDAFruitAndVegetables/scripts/generate_schema_artifacts.py

from __future__ import annotations

from enum import Enum

CSV_COLUMN_COUNT = 7
CSV_DATE_INDEX = 0
CSV_AVERAGE_RETAIL_PRICE_INDEX = 1
CSV_UNIT_INDEX = 2
CSV_PREPARATION_YIELD_FACTOR_INDEX = 3
CSV_CUP_EQUIVALENT_SIZE_INDEX = 4
CSV_CUP_EQUIVALENT_UNIT_INDEX = 5
CSV_PRICE_PER_CUP_EQUIVALENT_INDEX = 6

CSV_COLUMN_NAMES = (
    "Date",
    "AverageRetailPrice",
    "Unit",
    "PreparationYieldFactor",
    "CupEquivalentSize",
    "CupEquivalentUnit",
    "PricePerCupEquivalent",
)


class PriceUnit(Enum):
    UNKNOWN = "unknown"
    PER_POUND = "per_pound"
    PER_PINT = "per_pint"


class CupEquivalentUnit(Enum):
    UNKNOWN = "unknown"
    POUNDS = "pounds"
    PINTS = "pints"
    FLUID_OUNCES = "fluid_ounces"

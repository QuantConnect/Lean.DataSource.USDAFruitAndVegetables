import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.core.schema import CupEquivalentUnit, PriceUnit
from src.ingest.series_writer import save_series_file
from src.model.dataset_types import SeriesPoint
from tests.test_helpers import NullLogger


class USDAFruitAndVegetablesOutputLayoutTests(unittest.TestCase):
    def test_save_series_file_writes_single_series_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            points_by_date = {
                date(2020, 1, 1): SeriesPoint(
                    series_code="apples_fresh",
                    product_name="Apples",
                    form="Fresh",
                    date=date(2020, 1, 1),
                    average_retail_price=Decimal("1.23"),
                    unit=PriceUnit.PER_POUND,
                    preparation_yield_factor=Decimal("0.9"),
                    cup_equivalent_size=Decimal("0.25"),
                    cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                    price_per_cup_equivalent=Decimal("0.50"),
                ),
                date(2022, 1, 1): SeriesPoint(
                    series_code="apples_fresh",
                    product_name="Apples",
                    form="Fresh",
                    date=date(2022, 1, 1),
                    average_retail_price=Decimal("0.89"),
                    unit=PriceUnit.PER_POUND,
                    preparation_yield_factor=Decimal("0.75"),
                    cup_equivalent_size=Decimal("0.30"),
                    cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                    price_per_cup_equivalent=Decimal("0.36"),
                ),
            }

            save_series_file(output_folder, "apples_fresh", points_by_date, NullLogger())

            series_path = output_folder / "apples_fresh.csv"
            self.assertTrue(series_path.exists())

            lines = series_path.read_text().splitlines()
            expected = [
                "20200101,1.23,per_pound,0.9,0.25,pounds,0.5",
                "20220101,0.89,per_pound,0.75,0.3,pounds,0.36",
            ]
            self.assertEqual(lines, expected)

    def test_save_series_file_normalizes_series_code_and_ignores_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            points_by_date = {
                date(2020, 1, 1): SeriesPoint(
                    series_code="apples_fresh",
                    product_name="Apples",
                    form="Fresh",
                    date=date(2020, 1, 1),
                    average_retail_price=Decimal("1.23"),
                    unit=PriceUnit.PER_POUND,
                    preparation_yield_factor=Decimal("0.9"),
                    cup_equivalent_size=Decimal("0.25"),
                    cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                    price_per_cup_equivalent=Decimal("0.50"),
                ),
                date(2021, 1, 1): SeriesPoint(
                    series_code=" ",
                    product_name="Apples",
                    form="Fresh",
                    date=date(2021, 1, 1),
                    average_retail_price=Decimal("1.00"),
                    unit=PriceUnit.PER_POUND,
                    preparation_yield_factor=Decimal("1"),
                    cup_equivalent_size=Decimal("0.25"),
                    cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                    price_per_cup_equivalent=Decimal("4.00"),
                ),
                date(2022, 1, 1): SeriesPoint(
                    series_code="apples_fresh",
                    product_name="Apples",
                    form="Fresh",
                    date=date(2022, 1, 1),
                    average_retail_price=Decimal("0.89"),
                    unit=PriceUnit.PER_POUND,
                    preparation_yield_factor=Decimal("0.75"),
                    cup_equivalent_size=Decimal("0.30"),
                    cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                    price_per_cup_equivalent=Decimal("0.36"),
                ),
            }

            save_series_file(output_folder, "APPLES_FRESH", points_by_date, NullLogger())

            series_path = output_folder / "apples_fresh.csv"
            self.assertTrue(series_path.exists())

            lines = series_path.read_text().splitlines()
            expected = [
                "20200101,1.23,per_pound,0.9,0.25,pounds,0.5",
                "20220101,0.89,per_pound,0.75,0.3,pounds,0.36",
            ]
            self.assertEqual(lines, expected)

    def test_series_output_matches_runtime_contract_sample(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            points_by_date = {
                date(2013, 1, 1): SeriesPoint(
                    series_code="apples_fresh",
                    product_name="Apples",
                    form="Fresh",
                    date=date(2013, 1, 1),
                    average_retail_price=Decimal("1.5675153914496354"),
                    unit=PriceUnit.PER_POUND,
                    preparation_yield_factor=Decimal("0.9"),
                    cup_equivalent_size=Decimal("0.24250848840336534"),
                    cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                    price_per_cup_equivalent=Decimal("0.42237309792162286"),
                )
            }

            save_series_file(output_folder, "apples_fresh", points_by_date, NullLogger())

            series_path = output_folder / "apples_fresh.csv"
            self.assertTrue(series_path.exists())

            lines = series_path.read_text().splitlines()
            self.assertEqual(
                lines,
                ["20130101,1.5675153914496354,per_pound,0.9,0.24250848840336534,pounds,0.42237309792162286"],
            )

            csv = lines[0].split(",")
            self.assertEqual(len(csv), 7)
            self.assertEqual(csv[0], "20130101")
            self.assertEqual(csv[2], "per_pound")
            self.assertEqual(csv[5], "pounds")
            self.assertEqual(Decimal(csv[1]), Decimal("1.5675153914496354"))
            self.assertEqual(Decimal(csv[3]), Decimal("0.9"))
            self.assertEqual(Decimal(csv[4]), Decimal("0.24250848840336534"))
            self.assertEqual(Decimal(csv[6]), Decimal("0.42237309792162286"))


if __name__ == "__main__":
    unittest.main()

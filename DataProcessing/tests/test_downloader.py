import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.core.config_provider import ProcessorConfig, get_optional_bool, set_config_override
from src.core.constants import (
    CONFIG_RUN_LIVE_TESTS_KEY,
    MANIFEST_STATUS_NO_DATA,
    MANIFEST_STATUS_NO_FILES,
    MANIFEST_STATUS_NO_SOURCES,
    MANIFEST_STATUS_OK,
)
from src.ingest import downloader as downloader_module  # pyright: ignore[reportPrivateUsage]
from src.ingest import series_parser as series_parser_module  # pyright: ignore[reportPrivateUsage]
from src.ingest import source_catalog as source_catalog_module  # pyright: ignore[reportPrivateUsage]
from src.ingest.downloader import USDAFruitAndVegetablesDownloader
from src.ingest.http_client import HttpClient
from src.ingest.rate_gate import RateGate
from src.ingest.series_accumulator import SeriesAccumulator
from src.ingest.series_parser import SeriesParser, SeriesParseResult
from src.ingest.series_writer import SeriesWriter
from src.ingest.source_catalog import SourceCatalog, SourceFilesResult
from src.model.dataset_types import CupEquivalentUnit, PriceUnit, SeriesPoint
from tests.test_helpers import NullLogger

override_value = os.getenv("USDA_RUN_LIVE_TESTS")
if override_value is not None:
    set_config_override({CONFIG_RUN_LIVE_TESTS_KEY: override_value})
else:
    set_config_override({CONFIG_RUN_LIVE_TESTS_KEY: "false"})
RUN_LIVE_TESTS = get_optional_bool(CONFIG_RUN_LIVE_TESTS_KEY, default=False)


def _make_config() -> ProcessorConfig:
    return ProcessorConfig.model_validate(
        {
            "process-start-date": "20200101",
            "process-end-date": "20200101",
        }
    )


class _FakeSourceCatalog(SourceCatalog):
    def __init__(self, result: SourceFilesResult) -> None:
        self._result = result

    def resolve_source_files(self, start_year: int, end_year: int) -> SourceFilesResult:  # type: ignore[override]
        return self._result


class _FakeSeriesParser(SeriesParser):
    def __init__(self, result: SeriesParseResult) -> None:
        self._result = result

    def parse(self, source_files: list[tuple[Path, str]], start_year: int, end_year: int) -> SeriesParseResult:
        return self._result


class _FakeSeriesWriter(SeriesWriter):
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def write(self, content_by_series: object) -> None:
        self.calls.append({"content": content_by_series})


class _FakeRateGate(RateGate):
    def __init__(self) -> None:
        self.wait_calls = 0

    def wait_to_proceed(self) -> None:
        self.wait_calls += 1


class _FakeHttpClient(HttpClient):
    def __init__(self, rate_gate: RateGate) -> None:
        self.rate_gate = rate_gate

    def close(self) -> None:
        return


class _FakeSourceCatalogFactory:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, config: ProcessorConfig, http_client: HttpClient, logger: object) -> SourceCatalog:
        self.calls.append({"config": config, "http_client": http_client, "logger": logger})
        return _FakeSourceCatalog(SourceFilesResult(None, None))


class USDAFruitAndVegetablesDownloaderTests(unittest.TestCase):
    def test_creates_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir) / "nested"
            self.assertFalse(output_folder.exists())
            config = _make_config()
            with USDAFruitAndVegetablesDownloader(output_folder, config, NullLogger()):
                pass
            self.assertTrue(output_folder.exists())

    def test_download_uses_factories_when_default_dependencies_needed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            fake_rate_gate = _FakeRateGate()
            fake_http_client = _FakeHttpClient(fake_rate_gate)
            source_catalog_factory = _FakeSourceCatalogFactory()

            def rate_gate_factory(_: ProcessorConfig) -> RateGate:
                return fake_rate_gate

            def http_client_factory(_: ProcessorConfig, rate_gate: RateGate, __: object) -> HttpClient:
                self.assertIs(rate_gate, fake_rate_gate)
                return fake_http_client

            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                rate_gate_factory=rate_gate_factory,
                http_client_factory=http_client_factory,
                source_catalog_factory=source_catalog_factory,
            ):
                pass

            self.assertEqual(len(source_catalog_factory.calls), 1)
            self.assertIs(source_catalog_factory.calls[0]["http_client"], fake_http_client)

    def test_process_returns_true_when_no_sources_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult(None, None))
            accumulator = SeriesAccumulator(normalize_cup_units=False)
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=accumulator,
                    parsed_files=0,
                    relevant_files=0,
                    total_points_parsed=0,
                    total_points_selected=0,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                success = downloader.process(date(2022, 1, 1), date(2022, 1, 1))

            self.assertTrue(success)

    def test_process_returns_false_when_no_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult([], None))
            accumulator = SeriesAccumulator(normalize_cup_units=False)
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=accumulator,
                    parsed_files=1,
                    relevant_files=0,
                    total_points_parsed=0,
                    total_points_selected=0,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                success = downloader.process(date(2022, 1, 1), date(2022, 1, 1))

            self.assertFalse(success)

    def test_process_returns_false_when_no_parsed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult([(output_folder / "file.xlsx", "file.xlsx")], None))
            accumulator = SeriesAccumulator(normalize_cup_units=False)
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=accumulator,
                    parsed_files=0,
                    relevant_files=0,
                    total_points_parsed=0,
                    total_points_selected=0,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                success = downloader.process(date(2022, 1, 1), date(2022, 1, 1))

            self.assertFalse(success)

    def test_process_returns_true_when_no_points_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult([(output_folder / "file.xlsx", "file.xlsx")], None))
            accumulator = SeriesAccumulator(normalize_cup_units=False)
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=accumulator,
                    parsed_files=1,
                    relevant_files=1,
                    total_points_parsed=3,
                    total_points_selected=0,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                success = downloader.process(date(2022, 1, 1), date(2022, 1, 1))

            self.assertTrue(success)

    def test_process_writes_series_when_points_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult([(output_folder / "file.xlsx", "file.xlsx")], None))
            accumulator = SeriesAccumulator(normalize_cup_units=False)
            accumulator.ingest_point(
                SeriesPoint(
                    series_code="apples_fresh",
                    product_name="Apples",
                    form="Fresh",
                    date=date(2022, 1, 1),
                    average_retail_price=Decimal("1.00"),
                    unit=PriceUnit.PER_POUND,
                    preparation_yield_factor=Decimal("1"),
                    cup_equivalent_size=Decimal("0.25"),
                    cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                    price_per_cup_equivalent=Decimal("4.00"),
                ),
                "source-one",
            )
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=accumulator,
                    parsed_files=1,
                    relevant_files=1,
                    total_points_parsed=1,
                    total_points_selected=1,
                )
            )
            writer = _FakeSeriesWriter()
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
                series_writer=writer,
            ) as downloader:
                success = downloader.process(date(2022, 1, 1), date(2022, 1, 1))

            self.assertTrue(success)
            self.assertEqual(len(writer.calls), 1)

    def test_collect_series_metadata_no_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult(None, None))
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=SeriesAccumulator(normalize_cup_units=False),
                    parsed_files=0,
                    relevant_files=0,
                    total_points_parsed=0,
                    total_points_selected=0,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                result = downloader.collect_series_metadata(date(2022, 1, 1), date(2022, 1, 1))

            self.assertEqual(result.status, MANIFEST_STATUS_NO_SOURCES)

    def test_collect_series_metadata_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult([], None))
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=SeriesAccumulator(normalize_cup_units=False),
                    parsed_files=0,
                    relevant_files=0,
                    total_points_parsed=0,
                    total_points_selected=0,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                result = downloader.collect_series_metadata(date(2022, 1, 1), date(2022, 1, 1))

            self.assertEqual(result.status, MANIFEST_STATUS_NO_FILES)

    def test_collect_series_metadata_no_parsed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult([(output_folder / "file.xlsx", "file.xlsx")], None))
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=SeriesAccumulator(normalize_cup_units=False),
                    parsed_files=0,
                    relevant_files=1,
                    total_points_parsed=3,
                    total_points_selected=3,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                result = downloader.collect_series_metadata(date(2022, 1, 1), date(2022, 1, 1))

            self.assertEqual(result.status, MANIFEST_STATUS_NO_FILES)
            self.assertEqual(result.source_files_count, 1)

    def test_collect_series_metadata_no_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult([(output_folder / "file.xlsx", "file.xlsx")], None))
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=SeriesAccumulator(normalize_cup_units=False),
                    parsed_files=1,
                    relevant_files=1,
                    total_points_parsed=3,
                    total_points_selected=0,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                result = downloader.collect_series_metadata(date(2022, 1, 1), date(2022, 1, 1))

            self.assertEqual(result.status, MANIFEST_STATUS_NO_DATA)

    def test_collect_series_metadata_ok(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            source_catalog = _FakeSourceCatalog(SourceFilesResult([(output_folder / "file.xlsx", "file.xlsx")], None))
            accumulator = SeriesAccumulator(normalize_cup_units=False)
            accumulator.ingest_point(
                SeriesPoint(
                    series_code="apples_fresh",
                    product_name="Apples",
                    form="Fresh",
                    date=date(2022, 1, 1),
                    average_retail_price=Decimal("1.00"),
                    unit=PriceUnit.PER_POUND,
                    preparation_yield_factor=Decimal("1"),
                    cup_equivalent_size=Decimal("0.25"),
                    cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                    price_per_cup_equivalent=Decimal("4.00"),
                ),
                "source-one",
            )
            parser = _FakeSeriesParser(
                SeriesParseResult(
                    accumulator=accumulator,
                    parsed_files=1,
                    relevant_files=1,
                    total_points_parsed=1,
                    total_points_selected=1,
                )
            )
            with USDAFruitAndVegetablesDownloader(
                output_folder,
                config,
                NullLogger(),
                source_catalog=source_catalog,
                series_parser=parser,
            ) as downloader:
                result = downloader.collect_series_metadata(date(2022, 1, 1), date(2022, 1, 1))

            self.assertEqual(result.status, MANIFEST_STATUS_OK)
            self.assertIn("apples_fresh", result.metadata_by_series)

    def test_resolve_http_timeout_seconds_uses_config_value(self) -> None:
        config = ProcessorConfig.model_construct(http_timeout_seconds=90)
        resolved = downloader_module._resolve_http_timeout_seconds(  # pyright: ignore[reportPrivateUsage]
            config,
            NullLogger(),
        )

        self.assertEqual(resolved, 90)

    def test_resolve_http_timeout_seconds_falls_back_on_invalid_config(self) -> None:
        config = ProcessorConfig.model_construct(http_timeout_seconds=0)
        resolved = downloader_module._resolve_http_timeout_seconds(  # pyright: ignore[reportPrivateUsage]
            config,
            NullLogger(),
        )

        self.assertEqual(resolved, 60)

    @unittest.skipUnless(RUN_LIVE_TESTS, "Set usda-run-live-tests=1 to run live downloader tests.")
    def test_can_process_single_day(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            with USDAFruitAndVegetablesDownloader(output_folder, config, NullLogger()) as downloader:
                success = downloader.process(date(2022, 1, 1), date(2022, 1, 1))
                self.assertTrue(success)
                files = list(output_folder.rglob("*.csv"))
                self.assertGreater(len(files), 0)

    @unittest.skipUnless(RUN_LIVE_TESTS, "Set usda-run-live-tests=1 to run live downloader tests.")
    def test_can_process_date_range(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            with USDAFruitAndVegetablesDownloader(output_folder, config, NullLogger()) as downloader:
                success = downloader.process(date(2022, 1, 1), date(2023, 1, 1))
                self.assertTrue(success)

    @unittest.skipUnless(RUN_LIVE_TESTS, "Set usda-run-live-tests=1 to run live downloader tests.")
    def test_handles_no_data_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_folder = Path(temp_dir)
            config = _make_config()
            with USDAFruitAndVegetablesDownloader(output_folder, config, NullLogger()) as downloader:
                future_year = date.today().year + 10
                success = downloader.process(date(future_year, 1, 1), date(future_year, 1, 1))
                self.assertTrue(success)

    def test_series_code_collision_raises_on_product_form_mismatch(self) -> None:
        accumulator = SeriesAccumulator(normalize_cup_units=True)
        first_point = SeriesPoint(
            series_code="apples_fresh",
            product_name="Apples",
            form="Fresh",
            date=date(2022, 1, 1),
            average_retail_price=Decimal("1.00"),
            unit=PriceUnit.PER_POUND,
            preparation_yield_factor=Decimal("1"),
            cup_equivalent_size=Decimal("0.25"),
            cup_equivalent_unit=CupEquivalentUnit.POUNDS,
            price_per_cup_equivalent=Decimal("4.00"),
        )
        second_point = SeriesPoint(
            series_code="apples_fresh",
            product_name="Apples!",
            form="Fresh",
            date=date(2023, 1, 1),
            average_retail_price=Decimal("1.10"),
            unit=PriceUnit.PER_POUND,
            preparation_yield_factor=Decimal("1"),
            cup_equivalent_size=Decimal("0.25"),
            cup_equivalent_unit=CupEquivalentUnit.POUNDS,
            price_per_cup_equivalent=Decimal("4.40"),
        )

        accumulator.ingest_point(first_point, "source-one")
        with self.assertRaises(ValueError):
            accumulator.ingest_point(second_point, "source-two")

    def test_normalizes_fluid_ounces_to_pints(self) -> None:
        accumulator = SeriesAccumulator(normalize_cup_units=True)
        point = SeriesPoint(
            series_code="apples_juice",
            product_name="Apples",
            form="Juice",
            date=date(2022, 1, 1),
            average_retail_price=Decimal("1.00"),
            unit=PriceUnit.PER_PINT,
            preparation_yield_factor=Decimal("1"),
            cup_equivalent_size=Decimal("8"),
            cup_equivalent_unit=CupEquivalentUnit.FLUID_OUNCES,
            price_per_cup_equivalent=Decimal("0.50"),
        )

        accumulator.ingest_point(point, "source-one")

        metadata = accumulator.metadata_by_series["apples_juice"]
        self.assertEqual(metadata.cup_equivalent_unit, CupEquivalentUnit.PINTS)

        stored_points = accumulator.content_by_series["apples_juice"]
        stored_point = stored_points[date(2022, 1, 1)]
        self.assertEqual(stored_point.cup_equivalent_unit, CupEquivalentUnit.PINTS)
        self.assertEqual(stored_point.cup_equivalent_size, Decimal("0.5"))

    def test_series_date_collision_raises_on_different_data(self) -> None:
        """Per Constitution: Fail-fast - duplicate series/date with different values should raise."""
        accumulator = SeriesAccumulator(normalize_cup_units=False)
        first_point = SeriesPoint(
            series_code="apples_fresh",
            product_name="Apples",
            form="Fresh",
            date=date(2022, 1, 1),
            average_retail_price=Decimal("1.00"),
            unit=PriceUnit.PER_POUND,
            preparation_yield_factor=Decimal("1"),
            cup_equivalent_size=Decimal("0.25"),
            cup_equivalent_unit=CupEquivalentUnit.POUNDS,
            price_per_cup_equivalent=Decimal("4.00"),
        )
        second_point = SeriesPoint(
            series_code="apples_fresh",
            product_name="Apples",
            form="Fresh",
            date=date(2022, 1, 1),  # Same date
            average_retail_price=Decimal("1.50"),  # Different price
            unit=PriceUnit.PER_POUND,
            preparation_yield_factor=Decimal("1"),
            cup_equivalent_size=Decimal("0.25"),
            cup_equivalent_unit=CupEquivalentUnit.POUNDS,
            price_per_cup_equivalent=Decimal("6.00"),
        )

        accumulator.ingest_point(first_point, "source-one")
        with self.assertRaises(ValueError) as context:
            accumulator.ingest_point(second_point, "source-two")
        self.assertIn("collision", str(context.exception).lower())

    def test_filter_source_urls_raises_on_yearless_xlsx(self) -> None:
        config = _make_config()
        xlsx_urls = ["https://example.com/fruitveg.xlsx"]
        zip_urls: list[str] = []

        with self.assertRaises(ValueError):
            source_catalog_module._filter_source_urls(  # pyright: ignore[reportPrivateUsage]
                xlsx_urls,
                zip_urls,
                2020,
                2021,
                config,
            )

    def test_filter_source_urls_filters_zip_names_and_years(self) -> None:
        config = _make_config()
        xlsx_urls = [
            "https://example.com/fruit-2020.xlsx",
            "https://example.com/vegetables-2021.xlsx",
        ]
        zip_urls = [
            "https://example.com/fruit-2020.zip",
            "https://example.com/vegetables-2021.zip",
            "https://example.com/other-2020.zip",
        ]

        filtered_xlsx, filtered_zip = source_catalog_module._filter_source_urls(  # pyright: ignore[reportPrivateUsage]
            xlsx_urls,
            zip_urls,
            2020,
            2020,
            config,
        )

        self.assertEqual(filtered_xlsx, ["https://example.com/fruit-2020.xlsx"])
        self.assertEqual(filtered_zip, ["https://example.com/fruit-2020.zip"])

    def test_filter_urls_by_year_allows_missing_years(self) -> None:
        urls = ["https://example.com/fruit-2020.xlsx", "https://example.com/fruit-foo.xlsx"]

        filtered = source_catalog_module._filter_urls_by_year(urls, {2020})  # pyright: ignore[reportPrivateUsage]

        self.assertEqual(filtered, urls)

    def test_filter_points_by_year_filters_outside_range(self) -> None:
        points = [
            SeriesPoint(
                series_code="apples_fresh",
                product_name="Apples",
                form="Fresh",
                date=date(2020, 1, 1),
                average_retail_price=Decimal("1.00"),
                unit=PriceUnit.PER_POUND,
                preparation_yield_factor=Decimal("1"),
                cup_equivalent_size=Decimal("0.25"),
                cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                price_per_cup_equivalent=Decimal("4.00"),
            ),
            SeriesPoint(
                series_code="apples_fresh",
                product_name="Apples",
                form="Fresh",
                date=date(2022, 1, 1),
                average_retail_price=Decimal("1.10"),
                unit=PriceUnit.PER_POUND,
                preparation_yield_factor=Decimal("1"),
                cup_equivalent_size=Decimal("0.25"),
                cup_equivalent_unit=CupEquivalentUnit.POUNDS,
                price_per_cup_equivalent=Decimal("4.40"),
            ),
        ]

        filtered = series_parser_module._filter_points_by_year(points, 2021, 2023)  # pyright: ignore[reportPrivateUsage]

        self.assertEqual(filtered, [points[1]])


if __name__ == "__main__":
    unittest.main()

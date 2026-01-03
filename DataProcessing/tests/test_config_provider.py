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

import unittest
from unittest.mock import patch

from src.core import config_provider as config_module


class ConfigProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        config_module.clear_config_override()

    def tearDown(self) -> None:
        config_module.clear_config_override()

    # _parse_int tests
    def test_parse_int_valid_returns_int(self) -> None:
        result = config_module._parse_int("test-key", "42")  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(result, 42)

    def test_parse_int_invalid_raises(self) -> None:
        with self.assertRaises(ValueError) as context:
            config_module._parse_int("test-key", "not-a-number")  # pyright: ignore[reportPrivateUsage]
        self.assertIn("test-key", str(context.exception))
        self.assertIn("integer", str(context.exception))

    # _parse_float tests
    def test_parse_float_valid_returns_float(self) -> None:
        result = config_module._parse_float("test-key", "3.14")  # pyright: ignore[reportPrivateUsage]
        self.assertAlmostEqual(result, 3.14)

    def test_parse_float_integer_returns_float(self) -> None:
        result = config_module._parse_float("test-key", "42")  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(result, 42.0)

    def test_parse_float_invalid_raises(self) -> None:
        with self.assertRaises(ValueError) as context:
            config_module._parse_float("test-key", "not-a-number")  # pyright: ignore[reportPrivateUsage]
        self.assertIn("test-key", str(context.exception))

    # _parse_bool tests
    def test_parse_bool_truthy_values(self) -> None:
        for value in ["1", "true", "True", "TRUE", "yes", "Yes", "y", "Y", "on", "ON"]:
            result = config_module._parse_bool("test-key", value)  # pyright: ignore[reportPrivateUsage]
            self.assertTrue(result, f"Expected True for '{value}'")

    def test_parse_bool_falsy_values(self) -> None:
        for value in ["0", "false", "False", "FALSE", "no", "No", "n", "N", "off", "OFF"]:
            result = config_module._parse_bool("test-key", value)  # pyright: ignore[reportPrivateUsage]
            self.assertFalse(result, f"Expected False for '{value}'")

    def test_parse_bool_invalid_raises(self) -> None:
        with self.assertRaises(ValueError) as context:
            config_module._parse_bool("test-key", "maybe")  # pyright: ignore[reportPrivateUsage]
        self.assertIn("test-key", str(context.exception))
        self.assertIn("boolean", str(context.exception))

    # _require_value tests
    def test_require_value_empty_raises(self) -> None:
        config_module.set_config_override({"test-key": ""})
        with self.assertRaises(ValueError) as context:
            config_module._require_value("test-key")  # pyright: ignore[reportPrivateUsage]
        self.assertIn("test-key", str(context.exception))

    def test_require_value_whitespace_only_raises(self) -> None:
        config_module.set_config_override({"test-key": "   "})
        with self.assertRaises(ValueError) as context:
            config_module._require_value("test-key")  # pyright: ignore[reportPrivateUsage]
        self.assertIn("test-key", str(context.exception))

    def test_require_value_returns_trimmed(self) -> None:
        config_module.set_config_override({"test-key": "  value  "})
        result = config_module._require_value("test-key")  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(result, "value")

    # set_config_override / clear_config_override tests
    def test_set_config_override_clears_on_none(self) -> None:
        config_module.set_config_override({"test-key": "value"})
        config_module.set_config_override(None)
        with patch.object(config_module, "_get_config_value", return_value=""):
            result = config_module._get_optional_value("test-key")  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(result, "")

    def test_set_config_override_converts_values_to_strings(self) -> None:
        config_module.set_config_override({"int-key": 42, "bool-key": True})  # type: ignore[dict-item]
        result_int = config_module._get_optional_value("int-key")  # pyright: ignore[reportPrivateUsage]
        result_bool = config_module._get_optional_value("bool-key")  # pyright: ignore[reportPrivateUsage]
        self.assertEqual(result_int, "42")
        self.assertEqual(result_bool, "True")

    # load_config required fields
    def test_load_config_missing_required_values_raises(self) -> None:
        config_module.set_config_override(
            {
                "process-start-date": "",
                "process-end-date": "",
            }
        )
        with self.assertRaises(ValueError) as context:
            config_module.load_config()
        message = str(context.exception)
        self.assertIn("process-start-date", message)

    def test_load_config_requires_end_date(self) -> None:
        config_module.set_config_override(
            {
                "process-start-date": "20200101",
                "process-end-date": "",
            }
        )
        with self.assertRaises(ValueError) as context:
            config_module.load_config()
        self.assertIn("process-end-date", str(context.exception))

    def test_load_config_raises_when_start_date_missing(self) -> None:
        config_module.set_config_override(
            {
                "process-start-date": "",
                "process-end-date": "20200101",
            }
        )
        with self.assertRaises(ValueError) as context:
            config_module.load_config()
        self.assertIn("process-start-date", str(context.exception))

    # get_optional_bool tests
    def test_get_optional_bool_returns_default_when_empty(self) -> None:
        config_module.set_config_override({"test-key": ""})
        result = config_module.get_optional_bool("test-key", default=True)
        self.assertTrue(result)

    def test_get_optional_bool_parses_value(self) -> None:
        config_module.set_config_override({"test-key": "true"})
        result = config_module.get_optional_bool("test-key", default=False)
        self.assertTrue(result)

    def test_get_optional_bool_returns_default_on_runtime_error(self) -> None:
        with patch.object(config_module, "_get_optional_value", side_effect=RuntimeError("boom")):
            result = config_module.get_optional_bool("test-key", default=True)
            self.assertTrue(result)

    def test_parse_bool_trims_whitespace(self) -> None:
        result = config_module._parse_bool("test-key", "  on ")  # pyright: ignore[reportPrivateUsage]
        self.assertTrue(result)

    # Test that defaults work (Constitution: Explicit over implicit)
    def test_load_config_uses_defaults_for_optional_fields(self) -> None:
        """Per Constitution: Only required fields are mandatory; optional fields use Pydantic defaults."""
        config_module.set_config_override(
            {
                "process-start-date": "20200101",
                "process-end-date": "20210101",
            }
        )
        config = config_module.load_config()

        # Verify required fields were set
        self.assertEqual(config.process_start_date, "20200101")
        self.assertEqual(config.process_end_date, "20210101")

        # Verify defaults are used (from ProcessorConfig Pydantic model)
        self.assertEqual(config.max_retries, 5)  # DEFAULT_MAX_RETRIES
        self.assertEqual(config.rate_limit_requests, 10)  # DEFAULT_RATE_LIMIT_REQUESTS
        self.assertAlmostEqual(config.rate_limit_seconds, 1.1)  # DEFAULT_RATE_LIMIT_SECONDS
        self.assertEqual(config.http_timeout_seconds, 60)  # DEFAULT_HTTP_TIMEOUT_SECONDS
        self.assertEqual(config.max_xlsx_downloads, 0)  # default
        self.assertTrue(config.normalize_cup_equivalent_unit)  # DEFAULT_NORMALIZE_CUP_EQUIVALENT_UNIT
        self.assertEqual(config.xlsx_directory, "")  # default empty
        self.assertEqual(config.listing_url, "")  # default empty

    def test_load_config_allows_override_of_defaults(self) -> None:
        """Verify that optional fields can be overridden when explicitly set."""
        config_module.set_config_override(
            {
                "process-start-date": "20200101",
                "process-end-date": "20210101",
                "max-retries": "10",
                "http-timeout-seconds": "120",
                "normalize-cup-equivalent-unit": "false",
            }
        )
        config = config_module.load_config()

        self.assertEqual(config.max_retries, 10)
        self.assertEqual(config.http_timeout_seconds, 120)
        self.assertFalse(config.normalize_cup_equivalent_unit)


    # Negative tests for date format validation
    def test_load_config_accepts_yyyymmdd_format(self) -> None:
        """Date must be yyyyMMdd format (e.g., 20200101), not ISO format."""
        config_module.set_config_override(
            {
                "process-start-date": "20200101",
                "process-end-date": "20200201",
            }
        )
        config = config_module.load_config()
        self.assertEqual(config.process_start_date, "20200101")
        self.assertEqual(config.process_end_date, "20200201")

    def test_load_config_validates_date_format(self) -> None:
        """Pydantic validates min_length=1, but format is only validated at runtime.

        Per Constitution: Fail-fast - document expected format in docs, but
        validation happens at parsing time in date_utils.parse_date_range().
        This test documents that config accepts the string, downstream validates.
        """
        config_module.set_config_override(
            {
                "process-start-date": "2020-01-01",  # ISO format, not yyyyMMdd
                "process-end-date": "2020-02-01",
            }
        )
        # Config loads (min_length=1 passes), format validation is downstream
        config = config_module.load_config()
        self.assertEqual(config.process_start_date, "2020-01-01")


if __name__ == "__main__":
    unittest.main()

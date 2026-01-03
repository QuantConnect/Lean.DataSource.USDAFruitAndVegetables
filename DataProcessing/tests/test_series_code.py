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

from src.model.series_code import get_series_code, normalize_form, slugify


class SeriesCodeTests(unittest.TestCase):
    # slugify tests
    def test_slugify_empty_string_returns_unknown(self) -> None:
        self.assertEqual(slugify(""), "unknown")

    def test_slugify_whitespace_only_returns_unknown(self) -> None:
        self.assertEqual(slugify("   "), "unknown")

    def test_slugify_special_chars_only_returns_unknown(self) -> None:
        self.assertEqual(slugify("!!!@@@###"), "unknown")

    def test_slugify_collapses_consecutive_underscores(self) -> None:
        self.assertEqual(slugify("hello   world"), "hello_world")

    def test_slugify_strips_trailing_underscores(self) -> None:
        self.assertEqual(slugify("hello!"), "hello")

    def test_slugify_lowercases(self) -> None:
        self.assertEqual(slugify("Hello World"), "hello_world")

    def test_slugify_preserves_alphanumeric(self) -> None:
        self.assertEqual(slugify("apples2024"), "apples2024")

    # normalize_form tests
    def test_normalize_form_removes_footnotes(self) -> None:
        self.assertEqual(normalize_form("Fresh1"), "Fresh")
        self.assertEqual(normalize_form("Dried (Prunes)2"), "Dried (Prunes)")

    def test_normalize_form_empty_returns_unknown(self) -> None:
        self.assertEqual(normalize_form(""), "unknown")

    def test_normalize_form_whitespace_only_returns_unknown(self) -> None:
        self.assertEqual(normalize_form("   "), "unknown")

    def test_normalize_form_handles_comma_segments(self) -> None:
        result = normalize_form("Fresh, Whole")
        self.assertEqual(result, "Fresh, Whole")

    def test_normalize_form_trims_and_removes_trailing_footnotes(self) -> None:
        result = normalize_form("  Canned, Low sodium 3 ")
        self.assertEqual(result, "Canned, Low sodium")

    def test_normalize_form_preserves_parenthetical_text(self) -> None:
        result = normalize_form("Frozen (with sauce)")
        self.assertEqual(result, "Frozen (with sauce)")

    # get_series_code tests
    def test_get_series_code_combines_product_and_form(self) -> None:
        self.assertEqual(get_series_code("Apples", "Fresh"), "apples_fresh")

    def test_get_series_code_handles_complex_names(self) -> None:
        self.assertEqual(
            get_series_code("Green Peas", "Frozen, canned (low sodium)"),
            "green_peas_frozen_canned_low_sodium",
        )

    def test_get_series_code_empty_form_uses_product(self) -> None:
        result = get_series_code("Apples", "")
        self.assertEqual(result, "apples_unknown")


if __name__ == "__main__":
    unittest.main()

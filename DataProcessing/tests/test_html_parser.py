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

from src.ingest.html_parser import extract_links


class HtmlParserTests(unittest.TestCase):
    def test_extract_links_returns_sorted_unique_urls(self) -> None:
        html = """
        <html>
        <body>
            <a href="https://example.com/b.xlsx">B</a>
            <a href="https://example.com/a.xlsx">A</a>
            <a href="https://example.com/a.xlsx">A duplicate</a>
        </body>
        </html>
        """
        links = extract_links(html, "https://example.com/", [".xlsx"])
        self.assertEqual(
            links,
            [
                "https://example.com/a.xlsx",
                "https://example.com/b.xlsx",
            ],
        )

    def test_extract_links_joins_relative_urls(self) -> None:
        html = '<html><body><a href="data/file.xlsx">File</a></body></html>'
        links = extract_links(html, "https://example.com/path/", [".xlsx"])
        self.assertEqual(links, ["https://example.com/path/data/file.xlsx"])

    def test_extract_links_filters_by_extension(self) -> None:
        html = """
        <html><body>
            <a href="file.xlsx">XLSX</a>
            <a href="file.zip">ZIP</a>
            <a href="file.pdf">PDF</a>
        </body></html>
        """
        links = extract_links(html, "https://example.com/", [".xlsx", ".zip"])
        self.assertEqual(
            links,
            [
                "https://example.com/file.xlsx",
                "https://example.com/file.zip",
            ],
        )

    def test_extract_links_handles_empty_html(self) -> None:
        links = extract_links("", "https://example.com/", [".xlsx"])
        self.assertEqual(links, [])

    def test_extract_links_handles_no_matching_links(self) -> None:
        html = '<html><body><a href="file.pdf">PDF only</a></body></html>'
        links = extract_links(html, "https://example.com/", [".xlsx"])
        self.assertEqual(links, [])

    def test_extract_links_case_insensitive_extension(self) -> None:
        html = '<html><body><a href="FILE.XLSX">File</a></body></html>'
        links = extract_links(html, "https://example.com/", [".xlsx"])
        self.assertEqual(links, ["https://example.com/FILE.XLSX"])

    def test_extract_links_ignores_query_params_in_extension_match(self) -> None:
        html = '<html><body><a href="file.xlsx?v=2">File</a></body></html>'
        links = extract_links(html, "https://example.com/", [".xlsx"])
        self.assertEqual(links, ["https://example.com/file.xlsx?v=2"])

    def test_extract_links_unescapes_html_entities(self) -> None:
        html = '<html><body><a href="file&amp;v=1.xlsx">File</a></body></html>'
        links = extract_links(html, "https://example.com/", [".xlsx"])
        self.assertEqual(links, ["https://example.com/file&v=1.xlsx"])

    def test_extract_links_keeps_query_string_when_extension_matches_path(self) -> None:
        html = '<html><body><a href="dir/file.xlsx?download=true">File</a></body></html>'
        links = extract_links(html, "https://example.com/base/", [".xlsx"])
        self.assertEqual(links, ["https://example.com/base/dir/file.xlsx?download=true"])


if __name__ == "__main__":
    unittest.main()

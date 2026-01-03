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

import html
from collections.abc import Sequence
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError as err:  # pragma: no cover - optional dependency
    raise RuntimeError("beautifulsoup4 is required to parse listing HTML.") from err


def extract_links(
    html_text: str,
    base_url: str,
    extensions: Sequence[str],
) -> list[str]:
    parser = _select_parser()
    return _extract_links_bs4(html_text, base_url, extensions, parser)


def _select_parser() -> str:
    # Probe each parser with test HTML; BeautifulSoup raises FeatureNotFound or other
    # errors when the backend is unavailable. Catch broadly to ensure fallback works.
    for parser in ("lxml", "html.parser"):
        try:
            BeautifulSoup("<html></html>", parser)
            return parser
        except Exception:  # noqa: BLE001 - intentional fallback for parser availability
            continue

    raise RuntimeError("No compatible HTML parser is available for BeautifulSoup.")


def _extract_links_bs4(
    html_text: str,
    base_url: str,
    extensions: Sequence[str],
    parser: str,
) -> list[str]:
    soup = BeautifulSoup(html_text, parser)
    urls: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href = html.unescape(str(tag.get("href")))
        if not href:
            continue
        if not _matches_extension(href, extensions):
            continue
        urls.add(urljoin(base_url, href))

    return sorted(urls, key=str.lower)


def _matches_extension(href: str, extensions: Sequence[str]) -> bool:
    lower = href.lower()
    parsed_path = urlparse(href).path.lower()
    return any(parsed_path.endswith(ext) or ext in lower for ext in extensions)

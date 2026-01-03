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

from src.core.constants import TRAILING_FOOTNOTE_REGEX, UNKNOWN_TEXT


def normalize_form(form: str) -> str:
    trimmed = form.strip()
    if not trimmed:
        return UNKNOWN_TEXT
    without_footnotes = TRAILING_FOOTNOTE_REGEX.sub("", trimmed).strip()
    if not without_footnotes:
        return UNKNOWN_TEXT
    return _normalize_form_case(without_footnotes)


def _normalize_form_case(form: str) -> str:
    parts = [part.strip() for part in form.split(",")]
    normalized_parts = [_normalize_segment_case(part) for part in parts]
    return ", ".join(normalized_parts)


def _normalize_segment_case(value: str) -> str:
    result: list[str] = []
    seen_alpha = False
    in_parens = 0
    for char in value:
        if char == "(":
            in_parens += 1
            result.append(char)
            continue
        if char == ")":
            if in_parens > 0:
                in_parens -= 1
            result.append(char)
            continue
        if in_parens:
            result.append(char)
            continue
        if not seen_alpha and char.isalpha():
            result.append(char.upper())
            seen_alpha = True
            continue
        if seen_alpha and char.isalpha():
            result.append(char.lower())
            continue
        result.append(char)
    return "".join(result)


def slugify(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return UNKNOWN_TEXT

    buffer: list[str] = []
    previous_underscore = False
    for char in trimmed:
        if char.isalnum():
            buffer.append(char.lower())
            previous_underscore = False
            continue
        if previous_underscore:
            continue
        buffer.append("_")
        previous_underscore = True

    while buffer and buffer[-1] == "_":
        buffer.pop()

    slug = "".join(buffer)
    return slug if slug else UNKNOWN_TEXT


def get_series_code(product_name: str, form: str) -> str:
    clean_form = normalize_form(form)
    product_slug = slugify(product_name)
    form_slug = slugify(clean_form)
    return f"{product_slug}_{form_slug}"

import json
import re
import unittest
from collections import Counter
from pathlib import Path


class USDAFruitAndVegetablesSeriesCatalogSyncTests(unittest.TestCase):
    def test_symbols_match_series_manifest(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        manifest_path = project_root / "docs" / "series-manifest.json"
        symbols_path = project_root / "USDAFruitAndVegetables.Symbols.cs"

        self.assertTrue(manifest_path.exists(), f"Missing manifest: {manifest_path}")
        self.assertTrue(symbols_path.exists(), f"Missing symbols file: {symbols_path}")

        manifest = json.loads(manifest_path.read_text())
        self.assertIsInstance(manifest, list)

        manifest_codes = [entry["seriesCode"] for entry in manifest]
        symbols_text = symbols_path.read_text()
        symbols_codes = re.findall(r'=>\s+"([^"]+)"', symbols_text)

        self.assertTrue(manifest_codes, "Manifest contains no series codes.")
        self.assertTrue(symbols_codes, "Symbols file contains no series codes.")

        self.assertEqual(
            len(set(manifest_codes)),
            len(manifest_codes),
            "Duplicate seriesCode values found in the manifest.",
        )
        self.assertEqual(
            len(set(symbols_codes)),
            len(symbols_codes),
            "Duplicate series codes found in USDAFruitAndVegetables.Symbols.cs.",
        )

        self.assertEqual(
            Counter(symbols_codes),
            Counter(manifest_codes),
            "Series manifest and Symbols.cs are out of sync.",
        )

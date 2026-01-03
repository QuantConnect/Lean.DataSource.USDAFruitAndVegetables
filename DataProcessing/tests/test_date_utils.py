import unittest
from datetime import date

from src.core.date_utils import validate_date_range


class DateUtilsTests(unittest.TestCase):
    def test_validate_date_range_raises_on_reversed_dates(self) -> None:
        with self.assertRaises(ValueError):
            validate_date_range(date(2024, 2, 1), date(2024, 1, 1))

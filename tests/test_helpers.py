from __future__ import annotations

import unittest

from crypto_report.helpers import build_change_meta, get_structured_weekly_trend


class HelperTests(unittest.TestCase):
    def test_build_change_meta_formats_positive_value(self) -> None:
        self.assertEqual(
            build_change_meta(12),
            {"text": "+12", "css_class": "trend-positive"},
        )

    def test_build_change_meta_handles_missing_value(self) -> None:
        self.assertEqual(
            build_change_meta(None),
            {"text": "N/A", "css_class": "trend-neutral"},
        )

    def test_get_structured_weekly_trend_derives_change_percent(self) -> None:
        sentiment = {
            "value": 50,
            "weekly_trend": {"change": "10"},
        }
        result = get_structured_weekly_trend(sentiment)
        self.assertEqual(result["change_value"], 10)
        self.assertEqual(result["change_percent"], 20.0)


if __name__ == "__main__":
    unittest.main()

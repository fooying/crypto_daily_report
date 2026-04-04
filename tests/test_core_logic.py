from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

from crypto_report.generator import CryptoReportGenerator
from crypto_report.config import ScriptConfig


class CoreLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        cfg = ScriptConfig(base_dir=Path('.').resolve(), generate_screenshots=False)
        self.analyst = CryptoReportGenerator(config=cfg)

    def test_extract_report_date_from_filename(self) -> None:
        self.assertEqual(
            self.analyst._extract_report_date_from_filename('modern_2026-04-03.html'),
            datetime(2026, 4, 3),
        )

    def test_get_sentiment_bucket(self) -> None:
        self.assertEqual(self.analyst._get_sentiment_bucket(20), 'extreme_fear')
        self.assertEqual(self.analyst._get_sentiment_bucket(40), 'fear')
        self.assertEqual(self.analyst._get_sentiment_bucket(60), 'neutral')
        self.assertEqual(self.analyst._get_sentiment_bucket(80), 'greed')
        self.assertEqual(self.analyst._get_sentiment_bucket(90), 'extreme_greed')


if __name__ == '__main__':
    unittest.main()

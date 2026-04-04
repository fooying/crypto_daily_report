from __future__ import annotations

import json
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from crypto_report.config import ScriptConfig
from crypto_report.logging_utils import configure_logging, get_logger
from crypto_report.services.market import MarketService
from crypto_report.services import news as news_module
from crypto_report.services.news import NewsService
from crypto_report.services.storage import TrendStorage


class RealFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_dir = Path('.').resolve()
        self.fixture_dir = self.base_dir / 'tests' / 'fixtures'
        self.config = ScriptConfig(base_dir=self.base_dir, generate_screenshots=False)
        configure_logging(self.config)
        self.logger = get_logger(__name__)
        self.http = Mock()
        self.storage = TrendStorage(self.base_dir / 'tests' / 'tmp_trend_data.json', datetime(2026, 4, 3), self.logger)
        self.news_service = NewsService(
            self.config,
            self.http,
            self.logger,
            now_provider=lambda: datetime(2026, 4, 3, 12, 0),
        )
        self.market_service = MarketService(
            self.config,
            self.http,
            self.logger,
            datetime(2026, 4, 3, 12, 0),
            self.storage,
        )

    def _skip_if_no_bs4(self) -> None:
        if news_module.BeautifulSoup is None:
            self.skipTest("缺少 bs4 依赖，跳过新闻解析相关测试")

    def tearDown(self) -> None:
        if self.storage.trend_data_file.exists():
            self.storage.trend_data_file.unlink()

    def test_parse_cointelegraph_listing_fixture(self) -> None:
        self._skip_if_no_bs4()
        html = (self.fixture_dir / 'cointelegraph_latest_news.html').read_text(encoding='utf-8')
        items = self.news_service.parse_primary_news_html(html)
        self.assertGreaterEqual(len(items), 3)
        self.assertEqual(items[0]['source'], 'CoinTelegraph')
        self.assertIn('比特币矿企Riot', items[0]['title'])
        self.assertTrue(items[0]['url'].startswith('https://cointelegraph-cn.com/news/'))
        self.assertTrue(items[0]['time'].startswith('2026-04-03'))
        self.assertNotEqual(items[0]['summary'], '点击查看详情')

    def test_parse_cointelegraph_detail_fixture_for_summary_fallback(self) -> None:
        self._skip_if_no_bs4()
        listing_html = (self.fixture_dir / 'cointelegraph_latest_news.html').read_text(encoding='utf-8')
        detail_html = (self.fixture_dir / 'cointelegraph_article_detail.html').read_text(encoding='utf-8')
        self.http.fetch_html.return_value = detail_html
        items = self.news_service.parse_primary_news_html(listing_html)
        self.assertGreaterEqual(len(items), 1)
        self.assertIn('Arkham', items[0]['summary'])
        self.assertEqual(self.http.fetch_html.call_count, 0)

    def test_parse_backup_news_fixture(self) -> None:
        self._skip_if_no_bs4()
        html = (self.fixture_dir / 'coinmarketcap_headlines_sample.html').read_text(encoding='utf-8')
        items = self.news_service.parse_backup_news_html(html)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['source'], 'CoinMarketCap')
        self.assertTrue(items[0]['url'].startswith('https://coinmarketcap.com/zh/news/'))

    def test_news_service_falls_back_to_coinmarketcap_when_primary_fetch_fails(self) -> None:
        self._skip_if_no_bs4()
        backup_html = (self.fixture_dir / 'coinmarketcap_headlines_sample.html').read_text(encoding='utf-8')
        self.http.fetch_html.side_effect = [
            RuntimeError('primary source down'),
            backup_html,
        ]

        items = self.news_service.get_crypto_news()

        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]['source'], 'CoinMarketCap')
        self.assertEqual(self.news_service.last_source_used, 'coinmarketcap_backup')

    def test_parse_fear_greed_fixture(self) -> None:
        payload = json.loads((self.fixture_dir / 'alternative_fng_limit7.json').read_text(encoding='utf-8'))
        result = self.market_service.parse_fear_greed_response(payload, limit=7)
        self.assertEqual(result['source'], 'alternative.me')
        self.assertIn(result['classification'], {'极度恐惧', '恐惧', '中性', '贪婪', '极度贪婪'})
        self.assertEqual(result['daily_change'], -3)
        self.assertEqual(result['weekly_change'], -3)
        self.assertIsNone(result['monthly_change'])
        self.assertEqual(len(result['historical_data']), 7)

    def test_fear_greed_history_backfills_7d_and_30d_when_local_data_insufficient(self) -> None:
        payload_7d = json.loads(
            (self.fixture_dir / 'alternative_fng_limit7.json').read_text(encoding='utf-8')
        )
        payload_30d = {
            'data': [
                {
                    'value': str(40 - index),
                    'value_classification': 'Fear',
                    'timestamp': str(1712100000 - index * 86400),
                    'time_until_update': '3600',
                }
                for index in range(30)
            ]
        }
        self.http.fetch_json.side_effect = [payload_7d, payload_30d]

        result = self.market_service.get_fear_greed_index(limit=2)

        self.assertEqual(self.http.fetch_json.call_count, 2)
        self.assertEqual(result['daily_change'], -3)
        self.assertEqual(result['weekly_change'], -3)
        self.assertEqual(result['monthly_change'], -2)
        self.assertEqual(len(result['historical_data']), 30)
        stored = self.storage.load()['fear_greed_index']
        self.assertGreaterEqual(len(stored), 30)


if __name__ == '__main__':
    unittest.main()

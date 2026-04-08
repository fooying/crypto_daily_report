from __future__ import annotations

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from crypto_report.config import ScriptConfig
from crypto_report.logging_utils import configure_logging, get_logger
from crypto_report.services.market import MarketService
from crypto_report.services import news as news_module
from crypto_report.services.news import NewsService
from crypto_report.services.storage import TrendStorage
from crypto_report.services.trend_repository import TrendRepository


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
        backup_path = self.storage.trend_data_file.with_suffix('.json.bak')
        if backup_path.exists():
            backup_path.unlink()

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
        self.assertIn(items[0]['impact'], {'高影响', '中影响', '一般'})

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
        self.assertIn(items[0]['impact'], {'高影响', '中影响', '一般'})

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

    def test_news_service_deduplicates_items(self) -> None:
        items = [
            {'title': 'Same Title', 'url': 'https://example.com/a'},
            {'title': 'Same   Title', 'url': 'https://example.com/a'},
            {'title': 'Another Title', 'url': 'https://example.com/b'},
        ]

        deduped = self.news_service.deduplicate_news(items)

        self.assertEqual(len(deduped), 2)

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

    def test_fear_greed_history_uses_local_cache_after_writing_today(self) -> None:
        current_date = datetime(2026, 4, 3, 12, 0)
        history = {}
        for offset in range(1, 31):
            date_key = (current_date - timedelta(days=offset)).strftime('%Y-%m-%d')
            history[date_key] = {
                'value': 30 - offset,
                'classification': '恐惧',
                'timestamp': str(1775174400 - offset * 86400),
                'source': 'alternative.me',
            }
        self.storage.save({'fear_greed_index': history})

        self.http.fetch_json.return_value = {
            'data': [
                {
                    'value': '15',
                    'value_classification': 'Fear',
                    'timestamp': '1775174400',
                    'time_until_update': '3600',
                },
                {
                    'value': '12',
                    'value_classification': 'Fear',
                    'timestamp': '1775088000',
                },
            ]
        }

        result = self.market_service.get_fear_greed_index(limit=7)

        self.assertEqual(self.http.fetch_json.call_count, 1)
        first_url = self.http.fetch_json.call_args_list[0].args[0]
        self.assertTrue(first_url.endswith('limit=2'))
        self.assertEqual(result['daily_change'], 3)
        self.assertIsNotNone(result['weekly_change'])
        self.assertGreaterEqual(len(result['historical_data']), 7)
        stored = self.storage.load()['fear_greed_index']
        self.assertEqual(stored['2026-04-03']['value'], 15)

    def test_trend_repository_trims_histories_to_30_days_and_keeps_key_order(self) -> None:
        history = {}
        for offset in range(35):
            date_key = (datetime(2026, 4, 3, 12, 0) - timedelta(days=offset)).strftime('%Y-%m-%d')
            history[date_key] = {
                'value': offset,
                'classification': '恐惧',
                'timestamp': str(1775174400 - offset * 86400),
                'source': 'alternative.me',
            }

        self.storage.save(
            {
                'metadata': {'version': '1.0'},
                'fear_greed_index': history,
                'market_cap': history,
                'bitcoin_price': history,
                'ethereum_price': history,
            }
        )

        raw = json.loads(self.storage.trend_data_file.read_text(encoding='utf-8'))

        self.assertEqual(list(raw.keys())[:4], [
            'fear_greed_index',
            'market_cap',
            'bitcoin_price',
            'ethereum_price',
        ])
        self.assertEqual(len(raw['fear_greed_index']), 30)
        self.assertEqual(len(raw['market_cap']), 30)
        self.assertEqual(len(raw['bitcoin_price']), 30)
        self.assertEqual(len(raw['ethereum_price']), 30)
        self.assertEqual(next(iter(raw['fear_greed_index'].keys())), '2026-04-03')
        self.assertNotIn('2026-02-28', raw['fear_greed_index'])

    def test_trend_repository_skips_unchanged_save(self) -> None:
        payload = {
            'fear_greed_index': {
                '2026-04-03': {
                    'value': 15,
                    'classification': '恐惧',
                    'timestamp': '1775174400',
                    'source': 'alternative.me',
                }
            }
        }

        first = self.storage.save(dict(payload))
        second = self.storage.save(dict(payload))

        self.assertTrue(first)
        self.assertFalse(second)

    def test_trend_repository_concurrent_updates_keep_valid_json(self) -> None:
        report_date = datetime(2026, 4, 3, 12, 0)

        def write_fear_greed(value: int) -> None:
            self.storage.update_fear_greed_trend(value, '恐惧')

        def write_market_cap(index: int) -> None:
            self.storage.update_market_data_trend(
                {
                    'total_market_cap': 1000 + index,
                    'market_cap_change_percentage_24h_usd': index * 0.1,
                    'total_volume': 500 + index,
                    'market_cap_percentage': {'btc': 52.0, 'eth': 17.0},
                }
            )

        def write_snapshot(index: int) -> None:
            self.storage.update_cached_snapshot(
                'macro_context_cache',
                {'index': index, 'date': report_date.strftime('%Y-%m-%d')},
                'unit-test',
            )

        with ThreadPoolExecutor(max_workers=6) as executor:
            for index in range(12):
                executor.submit(write_fear_greed, 10 + index)
                executor.submit(write_market_cap, index)
                executor.submit(write_snapshot, index)

        raw_text = self.storage.trend_data_file.read_text(encoding='utf-8')
        data = json.loads(raw_text)

        self.assertIn('fear_greed_index', data)
        self.assertIn('market_cap', data)
        self.assertIn('macro_context_cache', data)
        self.assertIn(data['fear_greed_index']['2026-04-03']['value'], range(10, 22))
        self.assertIn(data['market_cap']['2026-04-03']['value'], range(1000, 1012))
        self.assertIn(data['macro_context_cache']['payload']['index'], range(12))

    def test_trend_repository_restores_primary_file_from_backup_on_init(self) -> None:
        valid_backup = {
            'fear_greed_index': {
                '2026-04-03': {
                    'value': 15,
                    'classification': '恐惧',
                    'timestamp': '1775174400',
                    'source': 'alternative.me',
                }
            }
        }
        self.storage.trend_data_file.write_text('{"broken": true}\n{"extra": true}', encoding='utf-8')
        backup_path = self.storage.trend_data_file.with_suffix('.json.bak')
        backup_path.write_text(json.dumps(valid_backup, ensure_ascii=False, indent=2), encoding='utf-8')

        repository = TrendRepository(self.storage.trend_data_file, datetime(2026, 4, 3), self.logger)
        restored = repository.load()

        self.assertEqual(restored['fear_greed_index']['2026-04-03']['value'], 15)
        persisted = json.loads(self.storage.trend_data_file.read_text(encoding='utf-8'))
        self.assertEqual(persisted['fear_greed_index']['2026-04-03']['value'], 15)


if __name__ == '__main__':
    unittest.main()

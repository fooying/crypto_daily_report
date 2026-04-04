from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from crypto_report.config import ScriptConfig
from crypto_report.http_client import HTTPRequestError
from crypto_report.logging_utils import configure_logging, get_logger
from crypto_report.services.market import MarketService
from crypto_report.services.storage import TrendStorage


class MarketServiceFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base_dir = Path('.').resolve()
        self.config = ScriptConfig(base_dir=self.base_dir, generate_screenshots=False)
        configure_logging(self.config)
        self.logger = get_logger(__name__)
        self.http = Mock()
        self.storage = TrendStorage(
            self.base_dir / 'tests' / 'tmp_market_trend_data.json',
            datetime(2026, 4, 3),
            self.logger,
        )
        self.service = MarketService(
            self.config,
            self.http,
            self.logger,
            datetime(2026, 4, 3),
            self.storage,
        )

    def tearDown(self) -> None:
        if self.storage.trend_data_file.exists():
            self.storage.trend_data_file.unlink()

    def test_market_overview_falls_back_to_coinmarketcap(self) -> None:
        self.http.fetch_json.side_effect = [
            HTTPRequestError(url='https://coingecko.test', reason='bad_status', status_code=503),
            {
                'data': {
                    'active_cryptocurrencies': 12345,
                    'btc_dominance': 61.2,
                    'eth_dominance': 9.4,
                    'quote': {
                        'USD': {
                            'total_market_cap': 2_500_000_000_000,
                            'total_volume_24h': 120_000_000_000,
                            'total_market_cap_yesterday_percentage_change': 1.56,
                        }
                    },
                }
            },
        ]

        result = self.service.get_market_overview()

        self.assertEqual(result['active_cryptocurrencies'], 12345)
        self.assertEqual(result['market_cap_percentage']['btc'], 61.2)
        self.assertEqual(result['market_cap_percentage']['eth'], 9.4)
        self.assertEqual(result['total_market_cap'], 2_500_000_000_000)
        self.assertEqual(result['total_volume'], 120_000_000_000)
        self.assertEqual(result['market_cap_change_percentage_24h_usd'], 1.56)
        self.assertEqual(self.http.fetch_json.call_count, 2)
        self.assertEqual(self.service.last_market_overview_source, 'coinmarketcap_backup')
        fallback_headers = self.http.fetch_json.call_args_list[1].kwargs['headers']
        self.assertIn('X-CMC_PRO_API_KEY', fallback_headers)

    def test_top_cryptocurrencies_fall_back_to_coinmarketcap(self) -> None:
        self.http.fetch_json.side_effect = [
            HTTPRequestError(url='https://coingecko.test', reason='request_failed'),
            {
                'data': [
                    {
                        'id': 1,
                        'name': 'Bitcoin',
                        'symbol': 'BTC',
                        'cmc_rank': 1,
                        'circulating_supply': 19_800_000,
                        'quote': {
                            'USD': {
                                'price': 65000,
                                'market_cap': 1_280_000_000_000,
                                'percent_change_24h': 2.1,
                                'percent_change_7d': 4.2,
                                'volume_24h': 35_000_000_000,
                            }
                        },
                    }
                ]
            },
            {
                'data': {
                    '1': {
                        'logo': 'https://s2.coinmarketcap.com/static/img/coins/64x64/1.png',
                    }
                }
            },
        ]

        result = self.service.get_top_cryptocurrencies(limit=1)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'Bitcoin')
        self.assertEqual(result[0]['symbol'], 'BTC')
        self.assertEqual(result[0]['market_cap_rank'], 1)
        self.assertEqual(result[0]['current_price'], 65000)
        self.assertEqual(result[0]['price_change_percentage_24h'], 2.1)
        self.assertEqual(result[0]['price_change_percentage_7d'], 4.2)
        self.assertEqual(result[0]['total_volume'], 35_000_000_000)
        self.assertEqual(
            result[0]['image'],
            'https://s2.coinmarketcap.com/static/img/coins/64x64/1.png',
        )
        self.assertEqual(self.http.fetch_json.call_count, 3)
        self.assertEqual(self.service.last_top_cryptos_source, 'coinmarketcap_backup')

    def test_top_cryptocurrencies_keep_empty_image_when_logo_lookup_fails(self) -> None:
        self.http.fetch_json.side_effect = [
            HTTPRequestError(url='https://coingecko.test', reason='request_failed'),
            {
                'data': [
                    {
                        'id': 1,
                        'name': 'Bitcoin',
                        'symbol': 'BTC',
                        'cmc_rank': 1,
                        'circulating_supply': 19_800_000,
                        'quote': {
                            'USD': {
                                'price': 65000,
                                'market_cap': 1_280_000_000_000,
                                'percent_change_24h': 2.1,
                                'percent_change_7d': 4.2,
                                'volume_24h': 35_000_000_000,
                            }
                        },
                    }
                ]
            },
            HTTPRequestError(url='https://cmc.test/info', reason='bad_status', status_code=500),
        ]

        result = self.service.get_top_cryptocurrencies(limit=1)

        self.assertEqual(result[0]['image'], '')

    def test_market_cap_history_uses_coinmarketcap_historical_quotes(self) -> None:
        self.http.fetch_json.return_value = {
            'data': {
                'quotes': [
                    {
                        'timestamp': '2026-03-01T00:00:00.000Z',
                        'quote': {'USD': {'total_market_cap': 1_000, 'total_volume_24h': 100}},
                    },
                    {
                        'timestamp': '2026-03-02T00:00:00.000Z',
                        'quote': {'USD': {'total_market_cap': 1_100, 'total_volume_24h': 110}},
                    },
                ]
            }
        }

        result = self.service.get_market_cap_history(days=30)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['market_cap'], 1000.0)
        self.assertEqual(result[1]['volume_24h'], 110.0)
        self.assertEqual(self.service.last_market_history_source, 'coinmarketcap_historical')

    def test_technical_context_uses_coinmarketcap_ohlcv_historical(self) -> None:
        self.http.fetch_json.return_value = {
            'data': {
                '1': {
                    'quotes': [
                        {'quote': {'USD': {'close': 60000, 'volume': 10}}},
                        {'quote': {'USD': {'close': 66000, 'volume': 20}}},
                    ]
                },
                '1027': {
                    'quotes': [
                        {'quote': {'USD': {'close': 3000, 'volume': 30}}},
                        {'quote': {'USD': {'close': 3300, 'volume': 60}}},
                    ]
                },
            }
        }

        result = self.service.get_technical_context()

        self.assertIn('BTC', result)
        self.assertIn('ETH', result)
        self.assertEqual(result['BTC']['price_change_30d'], 10.0)
        self.assertEqual(result['ETH']['avg_volume_30d'], 45.0)
        self.assertEqual(self.service.last_technical_context_source, 'coinmarketcap_ohlcv')


if __name__ == '__main__':
    unittest.main()

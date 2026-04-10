from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

from crypto_report.generator import CryptoReportGenerator
from crypto_report.config import ScriptConfig


class ReportSnapshotTests(unittest.TestCase):
    def test_rendered_report_matches_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = ScriptConfig(
                base_dir=Path('.').resolve(),
                generate_screenshots=False,
                deepseek_api_key='replace-me',
                trend_data_filename=str(Path(tmpdir) / 'snapshot_trend_data.json'),
            )
            obj = CryptoReportGenerator(config=cfg)
            if obj.template_env is None:
                self.skipTest("jinja2 未安装，跳过快照测试")
            obj.report_date = datetime(2026, 4, 3, 9, 30, 0)
            obj.news_date_range = '04月02日'
            obj.crypto_news = [
                {
                    'title': '测试新闻',
                    'summary': '测试摘要',
                    'sentiment': '中性',
                    'impact': '一般',
                    'time': '2026-04-03 10:00',
                    'url': 'https://example.com/news',
                    'source': 'UnitTest',
                    'tags': ['监管'],
                }
            ]
            obj.market_overview = {
                'total_market_cap': 1_000_000_000,
                'total_volume': 500_000_000,
                'active_cryptocurrencies': 100,
                'market_cap_percentage': {'btc': 50.0, 'eth': 20.0},
                'market_cap_change_percentage_24h_usd': 1.23,
                'alt_market_cap_percentage': 30.0,
                'volume_to_market_cap_ratio': 50.0,
                'btc_dominance_daily_change': 0.5,
                'btc_dominance_weekly_change': -1.2,
            }
            obj.top_cryptos = [{
                'name': 'Bitcoin', 'symbol': 'BTC', 'current_price': 1.0, 'market_cap': 2.0,
                'market_cap_rank': 1, 'price_change_percentage_24h': 1.0,
                'price_change_percentage_7d': 2.0, 'total_volume': 3.0,
                'circulating_supply': 4.0, 'fully_diluted_valuation': 5.0,
                'high_24h': 1.1, 'low_24h': 0.9, 'image': ''
            }]
            obj.market_cap_history = [
                {'timestamp': '2026-03-01T00:00:00.000Z', 'market_cap': 1.0, 'volume_24h': 2.0},
                {'timestamp': '2026-03-02T00:00:00.000Z', 'market_cap': 2.0, 'volume_24h': 3.0},
            ]
            obj.technical_context = {
                'BTC': {
                    'price_change_30d': 1.0,
                    'high_30d': 2.0,
                    'low_30d': 0.5,
                    'latest_close': 1.2,
                    'avg_volume_30d': 3.0,
                    'ma7': 1.1,
                    'ma30': 1.0,
                    'rsi14': 52.3,
                    'bollinger_upper': 1.4,
                    'bollinger_lower': 0.8,
                    'bollinger_status': '区间中部',
                }
            }
            obj.fear_greed_index = {
                'value': 50,
                'classification': '中性',
                'daily_change': 1,
                'weekly_change': 2,
                'monthly_change': 3,
            }
            obj.sentiment = {
                'value': 50,
                'classification': '中性',
                'description': '测试描述',
                'recommendation': '测试建议',
                'timestamp': '1710000000',
                'source': 'test',
                'url': 'https://example.com',
                'trend_analysis': '测试趋势',
                'daily_change': 1,
                'weekly_change': 2,
                'monthly_change': 3,
                'weekly_trend': {'trend': 'stable', 'change': '0'},
            }

            html = obj.generate_html_report()
            snapshot = Path('tests/fixtures/report_snapshot.html').read_text(encoding='utf-8')
            self.assertEqual(html, snapshot)

    def test_inline_css_mode_embeds_styles(self) -> None:
        cfg = ScriptConfig(
            base_dir=Path('.').resolve(),
            generate_screenshots=False,
            deepseek_api_key='replace-me',
            report_css_mode='inline',
        )
        obj = CryptoReportGenerator(config=cfg)
        if obj.template_env is None:
            self.skipTest("jinja2 未安装，跳过快照测试")
        obj.report_date = datetime(2026, 4, 3, 9, 30, 0)
        obj.news_date_range = '04月02日'
        obj.crypto_news = [{
            'title': '测试新闻',
            'summary': '测试摘要',
            'sentiment': '中性',
            'impact': '一般',
            'time': '2026-04-03 10:00',
            'url': 'https://example.com/news',
            'source': 'UnitTest',
            'tags': ['监管'],
        }]
        obj.market_overview = {
            'total_market_cap': 1_000_000_000,
            'total_volume': 500_000_000,
            'active_cryptocurrencies': 100,
            'market_cap_percentage': {'btc': 50.0, 'eth': 20.0},
            'market_cap_change_percentage_24h_usd': 1.23,
            'alt_market_cap_percentage': 30.0,
            'volume_to_market_cap_ratio': 50.0,
            'btc_dominance_daily_change': 0.5,
            'btc_dominance_weekly_change': -1.2,
        }
        obj.top_cryptos = [{
            'name': 'Bitcoin', 'symbol': 'BTC', 'current_price': 1.0, 'market_cap': 2.0,
            'market_cap_rank': 1, 'price_change_percentage_24h': 1.0,
            'price_change_percentage_7d': 2.0, 'total_volume': 3.0,
            'circulating_supply': 4.0, 'fully_diluted_valuation': 5.0,
            'high_24h': 1.1, 'low_24h': 0.9, 'image': ''
        }]
        obj.market_cap_history = [
            {'timestamp': '2026-03-01T00:00:00.000Z', 'market_cap': 1.0, 'volume_24h': 2.0},
            {'timestamp': '2026-03-02T00:00:00.000Z', 'market_cap': 2.0, 'volume_24h': 3.0},
        ]
        obj.technical_context = {
            'BTC': {
                'price_change_30d': 1.0,
                'high_30d': 2.0,
                'low_30d': 0.5,
                'latest_close': 1.2,
                'avg_volume_30d': 3.0,
                'ma7': 1.1,
                'ma30': 1.0,
                'rsi14': 52.3,
                'bollinger_upper': 1.4,
                'bollinger_lower': 0.8,
                'bollinger_status': '区间中部',
            }
        }
        obj.fear_greed_index = {
            'value': 50,
            'classification': '中性',
            'daily_change': 1,
            'weekly_change': 2,
            'monthly_change': 3,
        }
        obj.sentiment = {
            'value': 50,
            'classification': '中性',
            'description': '测试描述',
            'recommendation': '测试建议',
            'timestamp': '1710000000',
            'source': 'test',
            'url': 'https://example.com',
            'trend_analysis': '测试趋势',
            'daily_change': 1,
            'weekly_change': 2,
            'monthly_change': 3,
            'weekly_trend': {'trend': 'stable', 'change': '0'},
        }

        html = obj.generate_html_report()
        self.assertIn('<style>', html)
        self.assertIn('.header {', html)
        self.assertNotIn('<link rel="stylesheet"', html)

    def test_cleanup_old_reports_ignores_png_deleted_in_html_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir) / 'reports'
            report_dir.mkdir(parents=True, exist_ok=True)
            html_file = report_dir / '2026-03-06.html'
            png_file = report_dir / '2026-03-06.png'
            latest_file = report_dir / 'latest.html'
            html_file.write_text('<html></html>', encoding='utf-8')
            png_file.write_text('png', encoding='utf-8')
            latest_file.write_text('<html></html>', encoding='utf-8')

            cfg = ScriptConfig(
                base_dir=Path('.').resolve(),
                generate_screenshots=False,
                deepseek_api_key='replace-me',
                report_output_dir=report_dir,
            )
            obj = CryptoReportGenerator(config=cfg, report_date=datetime(2026, 4, 6, 12, 0, 0))

            obj.cleanup_old_reports(days_to_keep=30)

            self.assertFalse(html_file.exists())
            self.assertFalse(png_file.exists())
            self.assertTrue(latest_file.exists())

    def test_prepare_crypto_assets_downloads_and_reuses_local_icon(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report_dir = Path(tmpdir) / 'reports'
            cfg = ScriptConfig(
                base_dir=Path('.').resolve(),
                generate_screenshots=False,
                deepseek_api_key='replace-me',
                report_output_dir=report_dir,
            )
            obj = CryptoReportGenerator(config=cfg, report_date=datetime(2026, 4, 6, 12, 0, 0))
            response = Mock()
            response.content = b'png-bytes'
            response.headers = {'Content-Type': 'image/png'}
            obj.http.fetch_response = Mock(return_value=response)
            obj.top_cryptos = [
                {
                    'id': 'bitcoin',
                    'symbol': 'BTC',
                    'name': 'Bitcoin',
                    'image': 'https://example.com/bitcoin.png',
                }
            ]

            obj._prepare_crypto_assets()
            first_image = obj.top_cryptos[0]['image']
            self.assertEqual(first_image, 'assets/coin-icons/bitcoin.png')
            self.assertTrue((report_dir / first_image).exists())
            obj.http.fetch_response.reset_mock()

            obj.top_cryptos[0]['image'] = 'https://example.com/bitcoin.png'
            obj._prepare_crypto_assets()
            self.assertEqual(obj.top_cryptos[0]['image'], 'assets/coin-icons/bitcoin.png')
            obj.http.fetch_response.assert_not_called()

    def test_build_report_context_excludes_stablecoins_from_focus_assets(self) -> None:
        cfg = ScriptConfig(
            base_dir=Path('.').resolve(),
            generate_screenshots=False,
            deepseek_api_key='replace-me',
        )
        obj = CryptoReportGenerator(config=cfg, report_date=datetime(2026, 4, 6, 12, 0, 0))
        obj.sentiment = {'value': 50, 'daily_change': 0, 'weekly_change': 0, 'monthly_change': 0}
        obj.crypto_news = []
        obj.market_overview = {}
        obj.market_cap_history = []
        obj.technical_context = {}
        obj.top_cryptos = [
            {'symbol': 'BTC', 'name': 'Bitcoin'},
            {'symbol': 'USDT', 'name': 'Tether'},
            {'symbol': 'ETH', 'name': 'Ethereum'},
            {'symbol': 'BNB', 'name': 'BNB'},
            {'symbol': 'USDC', 'name': 'USD Coin'},
            {'symbol': 'XRP', 'name': 'XRP'},
        ]
        obj.analysis_service.get_ai_analysis = lambda *args, **kwargs: {}

        context = obj._build_report_context()

        symbols = [item['symbol'] for item in context['top_focus_assets']]
        self.assertNotIn('USDT', symbols)
        self.assertNotIn('USDC', symbols)
        self.assertEqual(symbols, ['BTC', 'ETH', 'BNB', 'XRP'])

    def test_build_report_context_limits_display_news_only(self) -> None:
        cfg = ScriptConfig(
            base_dir=Path('.').resolve(),
            generate_screenshots=False,
            deepseek_api_key='replace-me',
            max_news_display_items=2,
            max_news_analysis_items=5,
        )
        obj = CryptoReportGenerator(config=cfg, report_date=datetime(2026, 4, 6, 12, 0, 0))
        obj.sentiment = {'value': 50, 'daily_change': 0, 'weekly_change': 0, 'monthly_change': 0}
        obj.market_overview = {}
        obj.market_cap_history = []
        obj.technical_context = {}
        obj.top_cryptos = []
        obj.crypto_news = [
            {'title': 'n1', 'summary': 's1', 'sentiment': '中性', 'time': 't1', 'url': 'u1', 'source': 'A'},
            {'title': 'n2', 'summary': 's2', 'sentiment': '中性', 'time': 't2', 'url': 'u2', 'source': 'A'},
            {'title': 'n3', 'summary': 's3', 'sentiment': '中性', 'time': 't3', 'url': 'u3', 'source': 'A'},
        ]
        obj.analysis_service.get_ai_analysis = lambda *args, **kwargs: {}

        context = obj._build_report_context()

        self.assertEqual(len(context['news']), 2)
        self.assertEqual(len(obj.crypto_news), 3)

    def test_deploy_report_to_netlify_skips_when_site_id_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = ScriptConfig(
                base_dir=Path('.').resolve(),
                generate_screenshots=False,
                deepseek_api_key='replace-me',
                enable_netlify_deploy=True,
                trend_data_filename=str(Path(tmpdir) / 'netlify_skip_trend_data.json'),
            )
            obj = CryptoReportGenerator(config=cfg, report_date=datetime(2026, 4, 6, 12, 0, 0))
            with patch('crypto_report.generator.shutil.which', return_value='/usr/local/bin/netlify'):
                result = obj._deploy_report_to_netlify([])
        self.assertIsNone(result)

    def test_deploy_report_to_netlify_returns_website_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = ScriptConfig(
                base_dir=Path('.').resolve(),
                generate_screenshots=False,
                deepseek_api_key='replace-me',
                enable_netlify_deploy=True,
                netlify_site_id='site-123',
                netlify_auth_token='token-abc',
                trend_data_filename=str(Path(tmpdir) / 'netlify_ok_trend_data.json'),
            )
            obj = CryptoReportGenerator(config=cfg, report_date=datetime(2026, 4, 6, 12, 0, 0))
            completed = Mock(returncode=0, stdout='Website URL: https://demo-site.netlify.app\n', stderr='')
            with patch('crypto_report.generator.shutil.which', return_value='/usr/local/bin/netlify'):
                with patch('crypto_report.generator.subprocess.run', return_value=completed) as mocked_run:
                    deploy_url = obj._deploy_report_to_netlify(['a.html', 'a.png'])

        self.assertEqual(deploy_url, 'https://demo-site.netlify.app')
        self.assertEqual(obj.last_netlify_deploy_url, 'https://demo-site.netlify.app')
        args, kwargs = mocked_run.call_args
        self.assertIn('--site', args[0])
        self.assertEqual(kwargs['env']['NETLIFY_AUTH_TOKEN'], 'token-abc')


if __name__ == "__main__":
    unittest.main()

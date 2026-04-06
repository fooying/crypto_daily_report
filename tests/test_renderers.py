from __future__ import annotations

import unittest

from crypto_report.renderers import (
    generate_ai_analysis_section,
    generate_financial_analyst_section,
    generate_market_overview_section,
    generate_market_pulse_section,
    generate_sentiment_analysis_section,
    generate_technical_context_section,
    generate_top_focus_assets_section,
)


class RendererTests(unittest.TestCase):
    def test_market_overview_section_contains_expected_values(self) -> None:
        html = generate_market_overview_section(
            {
                'total_market_cap': 1_000_000_000,
                'total_volume': 500_000_000,
                'active_cryptocurrencies': 100,
                'market_cap_percentage': {'btc': 50.0, 'eth': 20.0},
                'market_cap_change_percentage_24h_usd': 1.23,
            }
        )
        self.assertIn('总市值', html)
        self.assertIn('1.23% (24h)', html)
        self.assertIn('50.0%', html)

    def test_crypto_table_rows_use_local_icons_and_handle_missing_values(self) -> None:
        from crypto_report.renderers import generate_crypto_table_rows

        html = generate_crypto_table_rows(
            [
                {
                    'name': 'Bitcoin',
                    'symbol': 'BTC',
                    'current_price': 100.0,
                    'market_cap': 1000.0,
                    'market_cap_rank': 1,
                    'price_change_percentage_24h': None,
                    'price_change_percentage_7d': 2.0,
                    'total_volume': 100.0,
                    'image': 'assets/coin-icons/bitcoin.png',
                },
                {
                    'name': 'Ethereum',
                    'symbol': 'ETH',
                    'current_price': 50.0,
                    'market_cap': 500.0,
                    'market_cap_rank': 2,
                    'price_change_percentage_24h': -1.0,
                    'price_change_percentage_7d': None,
                    'total_volume': None,
                    'image': '',
                },
            ]
        )
        self.assertIn('assets/coin-icons/bitcoin.png', html)
        self.assertIn('crypto-icon-fallback', html)
        self.assertIn('+0.00%', html)
        self.assertIn('$0', html)

    def test_ai_analysis_section_escapes_risk_text(self) -> None:
        html = generate_ai_analysis_section(
            {
                'market_overview': 'overview',
                'technical_analysis': '<div>tech</div>',
                'risk_assessment': '<risk>',
                'sentiment_summary': {'positive': 1, 'neutral': 2, 'negative': 3},
                'trend_enhanced_analysis': 'trend1\ntrend2',
            },
            '<li>signal</li>',
        )
        self.assertIn('&lt;risk&gt;', html)
        self.assertIn('<li>signal</li>', html)

    def test_sentiment_analysis_section_contains_summary(self) -> None:
        html = generate_sentiment_analysis_section(
            sentiment={
                'value': 50,
                'classification': '中性',
                'description': 'desc',
                'trend_analysis': 'trend',
                'recommendation': 'rec',
                'source': 'src',
                'url': 'https://example.com',
            },
            report_time='2026-04-03 10:00',
            daily_change_str='+1',
            weekly_change_str='+2',
            monthly_change_str='+3',
            daily_change_class='trend-positive',
            weekly_change_class='trend-positive',
            monthly_change_class='trend-positive',
            sentiment_bar_color='linear-gradient(red, blue)',
            sentiment_updated_at='2026-04-03 10:00:00',
            deep_analysis={
                'historical_comparison': 'history',
                'market_impact': 'impact',
                'investor_behavior': 'behavior',
                'current_interpretation': 'custom desc',
                'weekly_trend': 'custom trend',
                'trading_advice': 'custom advice',
            },
        )
        self.assertIn('市场情绪指数分析', html)
        self.assertIn('history', html)
        self.assertIn('impact', html)
        self.assertIn('查看完整指数说明', html)
        self.assertNotIn('更新时间：</strong> 2026-04-03 10:00:00', html)

    def test_financial_analyst_section_renders_lists(self) -> None:
        html = generate_financial_analyst_section(
            {
                'overall_points': ['点1', '点2'],
                'short_term': {'stance': '谨慎', 'summary': '短期总结', 'action_items': ['A']},
                'long_term': {'stance': '机会', 'summary': '长期总结', 'action_items': ['B']},
            }
        )
        self.assertIn('金融分析师视角', html)
        self.assertIn('短期总结', html)
        self.assertIn('长期总结', html)

    def test_top_focus_assets_section_contains_cards(self) -> None:
        html = generate_top_focus_assets_section(
            [
                {
                    'name': 'Bitcoin',
                    'symbol': 'BTC',
                    'current_price': 100.0,
                    'price_change_percentage_24h': 1.5,
                    'image': 'assets/coin-icons/bitcoin.png',
                    'sparkline_7d': [90, 92, 95, 100],
                }
            ]
        )
        self.assertIn('主流币速览', html)
        self.assertIn('Bitcoin', html)
        self.assertIn('assets/coin-icons/bitcoin.png', html)
        self.assertIn('focus-asset-sparkline', html)

    def test_top_focus_assets_section_hides_missing_sparkline(self) -> None:
        html = generate_top_focus_assets_section(
            [
                {
                    'name': 'Bitcoin',
                    'symbol': 'BTC',
                    'current_price': 100.0,
                    'price_change_percentage_24h': 1.5,
                    'image': 'assets/coin-icons/bitcoin.png',
                    'sparkline_7d': [],
                }
            ]
        )
        self.assertNotIn('focus-asset-sparkline', html)

    def test_market_pulse_section_contains_summary(self) -> None:
        html = generate_market_pulse_section(
            {
                'total_market_cap': 1_000_000_000,
                'total_volume': 500_000_000,
                'active_cryptocurrencies': 100,
                'market_cap_percentage': {'btc': 50.0, 'eth': 20.0},
            },
            [
                {'market_cap': 900_000_000, 'volume_24h': 450_000_000},
                {'market_cap': 1_000_000_000, 'volume_24h': 500_000_000},
            ],
        )
        self.assertIn('市场脉搏', html)
        self.assertIn('BTC主导率', html)
        self.assertNotIn('总市值走势', html)
        self.assertNotIn('24小时交易量走势', html)
        self.assertIn('展示近 2 天的总市值与 24 小时交易量变化', html)

    def test_market_pulse_section_shows_charts_when_history_is_enough(self) -> None:
        html = generate_market_pulse_section(
            {
                'total_market_cap': 1_000_000_000,
                'total_volume': 500_000_000,
                'active_cryptocurrencies': 100,
                'market_cap_percentage': {'btc': 50.0, 'eth': 20.0},
            },
            [
                {'market_cap': 850_000_000, 'volume_24h': 420_000_000},
                {'market_cap': 900_000_000, 'volume_24h': 450_000_000},
                {'market_cap': 950_000_000, 'volume_24h': 470_000_000},
                {'market_cap': 1_000_000_000, 'volume_24h': 500_000_000},
            ],
        )
        self.assertIn('总市值走势', html)
        self.assertIn('24小时交易量走势', html)
        self.assertIn('<svg', html)

    def test_technical_context_section_contains_asset_metrics(self) -> None:
        html = generate_technical_context_section(
            {
                'BTC': {
                    'price_change_30d': 10.5,
                    'high_30d': 70000,
                    'low_30d': 62000,
                    'latest_close': 68000,
                    'avg_volume_30d': 35_000_000_000,
                }
            }
        )
        self.assertIn('技术背景摘要', html)
        self.assertIn('BTC 30天技术摘要', html)
        self.assertIn('+10.50%', html)


if __name__ == "__main__":
    unittest.main()

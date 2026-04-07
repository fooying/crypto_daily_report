from __future__ import annotations

import unittest

from crypto_report.renderers import (
    generate_ai_analysis_section,
    generate_financial_analyst_section,
    generate_market_leadership_section,
    generate_market_overview_section,
    generate_market_pulse_section,
    generate_sector_overview_section,
    generate_sentiment_analysis_section,
    generate_technical_context_section,
    generate_top_focus_assets_section,
    generate_news_html,
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
                'alt_market_cap_percentage': 30.0,
                'volume_to_market_cap_ratio': 50.0,
            }
        )
        self.assertIn('总市值', html)
        self.assertIn('单位：十亿', html)
        self.assertIn('50.0%', html)
        self.assertIn('山寨币占比', html)
        self.assertIn('成交额 / 市值', html)

    def test_market_leadership_section_contains_highlights(self) -> None:
        html = generate_market_leadership_section(
            [
                {
                    'name': 'Bitcoin',
                    'symbol': 'BTC',
                    'image': 'assets/coin-icons/bitcoin.png',
                    'market_cap': 1_200_000_000_000,
                    'total_volume': 60_000_000_000,
                    'price_change_percentage_24h': 2.5,
                    'price_change_percentage_7d': 6.5,
                },
                {
                    'name': 'Ethereum',
                    'symbol': 'ETH',
                    'image': '',
                    'market_cap': 500_000_000_000,
                    'total_volume': 40_000_000_000,
                    'price_change_percentage_24h': 4.0,
                    'price_change_percentage_7d': 5.0,
                },
                {
                    'name': 'Solana',
                    'symbol': 'SOL',
                    'image': '',
                    'market_cap': 80_000_000_000,
                    'total_volume': 16_000_000_000,
                    'price_change_percentage_24h': 3.2,
                    'price_change_percentage_7d': 12.0,
                },
                {
                    'name': 'Tether',
                    'symbol': 'USDT',
                    'image': '',
                    'market_cap': 100_000_000_000,
                    'total_volume': 90_000_000_000,
                    'price_change_percentage_24h': 0.0,
                    'price_change_percentage_7d': 0.0,
                },
            ],
            {
                'total_market_cap': 2_500_000_000_000,
            },
        )
        self.assertIn('市场风向', html)
        self.assertIn('24h 领涨', html)
        self.assertIn('7天 强势', html)
        self.assertIn('流动性最强', html)
        self.assertIn('Ethereum', html)
        self.assertIn('Solana', html)
        self.assertNotIn('Tether', html)

    def test_market_leadership_section_hides_when_data_is_insufficient(self) -> None:
        html = generate_market_leadership_section(
            [
                {
                    'name': 'Bitcoin',
                    'symbol': 'BTC',
                    'market_cap': 1_200_000_000_000,
                    'total_volume': 60_000_000_000,
                    'price_change_percentage_24h': 2.5,
                    'price_change_percentage_7d': 6.5,
                }
            ],
            {
                'total_market_cap': 2_500_000_000_000,
            },
        )
        self.assertEqual('', html)

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
                    'circulating_supply': 21_000_000,
                    'fully_diluted_valuation': 1200.0,
                    'high_24h': 110.0,
                    'low_24h': 90.0,
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
        self.assertIn('FDV', html)
        self.assertIn('24h 区间', html)
        self.assertIn('成交 / 市值', html)

    def test_ai_analysis_section_escapes_risk_text(self) -> None:
        html = generate_ai_analysis_section(
            {
                'market_overview': 'overview',
                'technical_analysis': '<div>market uptrend</div>',
                'risk_assessment': '<risk>',
                'sentiment_summary': {'positive': 1, 'neutral': 2, 'negative': 3},
                'trend_enhanced_analysis': '⚖️ market consolidation',
            },
            '<li>signal</li>',
        )
        self.assertIn('&lt;risk&gt;', html)
        self.assertIn('<li>signal</li>', html)
        self.assertIn('上涨趋势', html)
        self.assertIn('盘整阶段', html)

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
            sentiment_composite={
                'score': 61,
                'label': '风险偏好回升',
                'summary': '情绪和盘面同步改善，可关注量价是否继续确认。',
                'drivers': ['恐惧贪婪指数为50，情绪仍处于常态区间。', '新闻面以正面/中性为主。'],
            },
        )
        self.assertIn('市场情绪指数分析', html)
        self.assertIn('history', html)
        self.assertIn('impact', html)
        self.assertIn('查看完整指数说明', html)
        self.assertNotIn('更新时间：</strong> 2026-04-03 10:00:00', html)
        self.assertIn('综合市场情绪分', html)
        self.assertIn('风险偏好回升', html)
        self.assertIn('驱动因子', html)

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

    def test_news_html_renders_tag_summary(self) -> None:
        html = generate_news_html(
            [
                {
                    'title': '测试新闻',
                    'summary': '测试摘要',
                    'sentiment': '中性',
                    'time': '2026-04-03 10:00',
                    'url': 'https://example.com',
                    'source': 'UnitTest',
                    'tags': ['监管', 'ETF/机构'],
                }
            ],
            {'监管': 3, 'ETF/机构': 2, '技术升级': 1},
        )
        self.assertIn('新闻标签摘要', html)
        self.assertIn('监管', html)
        self.assertIn('3', html)
        self.assertIn('风险事件', html)
        self.assertIn('资金动向', html)

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

    def test_sector_overview_section_groups_assets(self) -> None:
        html = generate_sector_overview_section(
            [
                {'symbol': 'BTC', 'market_cap': 100.0, 'total_volume': 10.0, 'price_change_percentage_24h': 1.0},
                {'symbol': 'ETH', 'market_cap': 80.0, 'total_volume': 12.0, 'price_change_percentage_24h': 2.0},
                {'symbol': 'SOL', 'market_cap': 60.0, 'total_volume': 15.0, 'price_change_percentage_24h': 5.0},
                {'symbol': 'ADA', 'market_cap': 30.0, 'total_volume': 4.0, 'price_change_percentage_24h': 1.5},
                {'symbol': 'DOGE', 'market_cap': 20.0, 'total_volume': 6.0, 'price_change_percentage_24h': 3.5},
                {'symbol': 'USDT', 'market_cap': 120.0, 'total_volume': 90.0, 'price_change_percentage_24h': 0.0},
            ]
        )
        self.assertIn('板块观察', html)
        self.assertIn('主流资产', html)
        self.assertIn('公链生态', html)
        self.assertIn('Meme', html)
        self.assertNotIn('USDT', html)

    def test_sector_overview_section_hides_when_sectors_too_few(self) -> None:
        html = generate_sector_overview_section(
            [
                {'symbol': 'BTC', 'market_cap': 100.0, 'total_volume': 10.0, 'price_change_percentage_24h': 1.0},
                {'symbol': 'ETH', 'market_cap': 80.0, 'total_volume': 12.0, 'price_change_percentage_24h': 2.0},
                {'symbol': 'USDT', 'market_cap': 120.0, 'total_volume': 90.0, 'price_change_percentage_24h': 0.0},
                {'symbol': 'USDC', 'market_cap': 50.0, 'total_volume': 20.0, 'price_change_percentage_24h': 0.0},
            ]
        )
        self.assertEqual('', html)

    def test_market_pulse_section_contains_summary(self) -> None:
        html = generate_market_pulse_section(
            {
                'total_market_cap': 1_000_000_000,
                'total_volume': 500_000_000,
                'active_cryptocurrencies': 100,
                'market_cap_percentage': {'btc': 50.0, 'eth': 20.0},
                'alt_market_cap_percentage': 30.0,
                'volume_to_market_cap_ratio': 50.0,
                'btc_dominance_daily_change': None,
                'btc_dominance_weekly_change': None,
            },
            [
                {'market_cap': 900_000_000, 'volume_24h': 450_000_000},
                {'market_cap': 1_000_000_000, 'volume_24h': 500_000_000},
            ],
        )
        self.assertIn('市场脉搏', html)
        self.assertIn('BTC主导率', html)
        self.assertNotIn('日变', html)
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
                'alt_market_cap_percentage': 30.0,
                'volume_to_market_cap_ratio': 50.0,
                'btc_dominance_daily_change': 0.5,
                'btc_dominance_weekly_change': -1.2,
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
        self.assertIn('日变 +0.50pct / 周变 -1.20pct', html)

    def test_technical_context_section_contains_asset_metrics(self) -> None:
        html = generate_technical_context_section(
            {
                'BTC': {
                    'price_change_30d': 10.5,
                    'high_30d': 70000,
                    'low_30d': 62000,
                    'latest_close': 68000,
                    'avg_volume_30d': 35_000_000_000,
                    'ma7': 67500,
                    'ma30': 66000,
                    'rsi14': 54.2,
                    'bollinger_upper': 71000,
                    'bollinger_lower': 63000,
                    'bollinger_status': '区间中部',
                }
            }
        )
        self.assertIn('技术背景摘要', html)
        self.assertIn('BTC 30天技术摘要', html)
        self.assertIn('+10.50%', html)
        self.assertIn('MA7 / MA30', html)
        self.assertIn('RSI14', html)
        self.assertIn('布林带', html)

    def test_news_html_renders_tags(self) -> None:
        from crypto_report.renderers import generate_news_html

        html = generate_news_html(
            [
                {
                    'title': '测试新闻',
                    'summary': '测试摘要',
                    'sentiment': '中性',
                    'time': '2026-04-03 10:00',
                    'url': 'https://example.com/news',
                    'source': 'UnitTest',
                    'tags': ['监管', 'ETF/机构'],
                }
            ]
        )
        self.assertIn('news-tag', html)
        self.assertIn('监管', html)


if __name__ == "__main__":
    unittest.main()

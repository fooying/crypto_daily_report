from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock

from crypto_report.config import ScriptConfig
from crypto_report.logging_utils import configure_logging, get_logger
from crypto_report.services.analysis import AIAnalysisService
from crypto_report.services.sentiment import SentimentService


class AIAnalysisServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        config = ScriptConfig(
            base_dir=Path('.').resolve(),
            generate_screenshots=False,
            deepseek_api_key='test-key',
        )
        configure_logging(config)
        logger = get_logger(__name__)
        self.http = Mock()
        self.sentiment_service = SentimentService(logger)
        self.service = AIAnalysisService(
            config,
            self.http,
            logger,
            self.sentiment_service,
        )
        self.fear_greed_index = {
            'value': 35,
            'classification': '恐惧',
            'daily_change': -2,
            'weekly_change': 4,
            'monthly_change': 9,
        }
        self.market_overview = {
            'market_cap_change_percentage_24h_usd': 1.5,
            'market_cap_percentage': {'btc': 52.4},
            'total_market_cap': 100,
            'total_volume': 50,
        }
        self.crypto_news = [
            {
                'title': '比特币 ETF 资金回流',
                'summary': '资金面转暖',
                'sentiment': '积极',
                'source': 'CoinTelegraph',
            },
            {
                'title': '监管仍存不确定性',
                'summary': '市场维持谨慎',
                'sentiment': '谨慎',
                'source': 'CoinMarketCap',
            },
        ]
        self.technical_context = {
            'BTC': {'price_change_30d': 12.3, 'high_30d': 72000, 'low_30d': 61000},
            'ETH': {'price_change_30d': 8.4, 'high_30d': 4200, 'low_30d': 3500},
        }

    def test_get_ai_analysis_prefers_deepseek(self) -> None:
        self.http.post_json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': (
                            '{"market_overview":"AI市场综述",'
                            '"technical_analysis":"<div>AI技术分析</div>",'
                            '"risk_assessment":"AI风险评估",'
                            '"trading_signals":["信号1","信号2"],'
                            '"trend_enhanced_analysis":"AI趋势增强",'
                            '"sentiment_deep_analysis":{"current_interpretation":"AI情绪解读","weekly_trend":"AI周趋势","historical_comparison":"AI历史对比","market_impact":"AI市场影响","investor_behavior":"AI投资者行为","trading_advice":"AI交易建议"},'
                            '"financial_analyst":{"overall_points":["点1","点2","点3","点4","点5"],"short_term":{"stance":"谨慎","summary":"AI短期","action_items":["a","b"]},"long_term":{"stance":"机会","summary":"AI长期","action_items":["c","d"]}}}'
                        )
                    }
                }
            ]
        }

        result = self.service.get_ai_analysis(
            self.fear_greed_index,
            self.crypto_news,
            self.market_overview,
            self.technical_context,
        )

        self.assertEqual(result['market_overview'], 'AI市场综述')
        self.assertEqual(result['risk_assessment'], 'AI风险评估')
        self.assertEqual(result['trading_signals'], ['信号1', '信号2'])
        self.assertEqual(result['trend_enhanced_analysis'], 'AI趋势增强')
        self.assertEqual(
            result['sentiment_deep_analysis']['current_interpretation'],
            'AI情绪解读',
        )
        self.assertEqual(result['financial_analyst']['short_term']['summary'], 'AI短期')
        self.http.post_json.assert_called_once()
        self.assertEqual(self.http.post_json.call_args.kwargs['timeout'], 30)
        self.assertEqual(
            self.http.post_json.call_args.args[0],
            'https://api.deepseek.com/chat/completions',
        )
        self.assertIs(self.http.post_json.call_args.args[1]['stream'], False)

    def test_get_ai_analysis_falls_back_when_deepseek_fails(self) -> None:
        self.http.post_json.side_effect = RuntimeError('deepseek down')

        result = self.service.get_ai_analysis(
            self.fear_greed_index,
            self.crypto_news,
            self.market_overview,
            self.technical_context,
        )

        self.assertIn('市场情绪', result['market_overview'])
        self.assertIsInstance(result['trading_signals'], list)
        self.assertGreater(len(result['trading_signals']), 0)
        self.assertIn('current_interpretation', result['sentiment_deep_analysis'])
        self.assertIn('overall_points', result['financial_analyst'])
        self.assertIn('sentiment_composite', result)
        self.assertIn('news_tag_summary', result)

    def test_get_ai_analysis_accepts_wrapped_json_content(self) -> None:
        self.http.post_json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': (
                            '下面是结果\\n```json\\n'
                            '{"market_overview":"AI市场综述",'
                            '"technical_analysis":"AI技术分析",'
                            '"risk_assessment":"AI风险评估",'
                            '"trading_signals":["信号1","信号2"],'
                            '"sentiment_deep_analysis":{"current_interpretation":"AI情绪解读","weekly_trend":"AI周趋势","historical_comparison":"AI历史对比","market_impact":"AI市场影响","investor_behavior":"AI投资者行为","trading_advice":"AI交易建议"},'
                            '"financial_analyst":{"overall_points":["点1","点2","点3","点4","点5"],"short_term":{"stance":"谨慎","summary":"AI短期","action_items":["a","b"]},"long_term":{"stance":"机会","summary":"AI长期","action_items":["c","d"]}}}'
                            '\\n```\\n备注'
                        )
                    }
                }
            ]
        }

        result = self.service.get_ai_analysis(
            self.fear_greed_index,
            self.crypto_news,
            self.market_overview,
            self.technical_context,
        )

        self.assertEqual(result['market_overview'], 'AI市场综述')
        self.assertEqual(result['financial_analyst']['long_term']['summary'], 'AI长期')

    def test_collect_news_features_includes_tag_summary(self) -> None:
        sentiment_counts, keywords, tag_summary, event_summary = self.service._collect_news_features(
            [
                {
                    'title': '监管与 ETF 同步推进',
                    'summary': '机构继续关注',
                    'sentiment': '积极',
                    'tags': ['监管', 'ETF/机构'],
                },
                {
                    'title': '交易所安全事件引发讨论',
                    'summary': '社区保持谨慎',
                    'sentiment': '谨慎',
                    'tags': ['安全事件', '交易所'],
                },
            ]
        )
        self.assertEqual(sentiment_counts, {'positive': 1, 'neutral': 0, 'negative': 1})
        self.assertIn('监管', keywords)
        self.assertEqual(tag_summary['监管'], 1)
        self.assertEqual(tag_summary['交易所'], 1)
        self.assertEqual(event_summary['监管与合规'], 1)
        self.assertEqual(event_summary['安全风险'], 1)

    def test_build_sentiment_composite_returns_summary(self) -> None:
        result = self.service.build_sentiment_composite(
            self.fear_greed_index,
            {
                **self.market_overview,
                'btc_dominance_daily_change': 0.6,
            },
            {'positive': 3, 'neutral': 1, 'negative': 0},
        )
        self.assertIn('score', result)
        self.assertIn('label', result)
        self.assertIn('summary', result)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)
        self.assertTrue(result['drivers'])

    def test_summarize_news_focus_returns_top_theme_summary(self) -> None:
        result = self.service.summarize_news_focus({'监管': 3, 'ETF/机构': 2, 'DeFi': 1})
        self.assertIn('监管', result)
        self.assertIn('ETF/机构', result)

    def test_build_event_watchlist_returns_structured_items(self) -> None:
        result = self.service.build_event_watchlist(
            [
                {
                    'title': '比特币 ETF 资金回流',
                    'time': '2026-04-07 09:00',
                    'impact': '高影响',
                    'source': 'CoinTelegraph',
                    'tags': ['ETF/机构'],
                }
            ]
        )
        self.assertEqual(result[0]['theme'], '机构资金')
        self.assertEqual(result[0]['impact'], '高影响')


if __name__ == '__main__':
    unittest.main()

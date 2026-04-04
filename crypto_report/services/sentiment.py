from __future__ import annotations

import time
from typing import Any, Dict

from ..models import FearGreedIndex


class SentimentService:
    """Build sentiment summaries and reusable sentiment profiles."""

    CHINESE_CLASSIFICATION = {
        "Extreme Fear": "极度恐惧",
        "Fear": "恐惧",
        "Neutral": "中性",
        "Greed": "贪婪",
        "Extreme Greed": "极度贪婪",
        "极度恐惧": "极度恐惧",
        "恐惧": "恐惧",
        "中性": "中性",
        "贪婪": "贪婪",
        "极度贪婪": "极度贪婪",
    }

    SENTIMENT_LEVELS = {
        "极度恐惧": {"color": "#dc3545", "description": "市场极度悲观，可能处于超卖状态"},
        "恐惧": {"color": "#fd7e14", "description": "市场悲观，谨慎情绪主导"},
        "中性": {"color": "#ffc107", "description": "市场情绪平衡，多空力量均衡"},
        "贪婪": {"color": "#28a745", "description": "市场乐观，风险偏好上升"},
        "极度贪婪": {"color": "#20c997", "description": "市场极度乐观，可能处于超买状态"},
    }

    PROFILES = {
        "extreme_fear": {
            "market_impact": "市场极度恐惧，可能出现超跌反弹机会",
            "investor_behavior": "投资者普遍观望，等待更明确信号",
            "risk_level": "高风险",
            "risk_assessment": "高风险 - 市场极度悲观且负面新闻较多，需严格控制仓位",
            "risk_assessment_light": "中高风险 - 市场情绪极度悲观，但负面新闻相对有限",
            "base_signals": [
                "逆向投资机会：市场极度恐惧可能提供中长期布局机会",
                "分批建仓：建议采用金字塔式分批买入策略",
                "严格止损：设置5-8%的止损位控制风险",
            ],
        },
        "fear": {
            "market_impact": "恐惧情绪主导，市场可能接近阶段性底部",
            "investor_behavior": "投资者采取防御性策略",
            "risk_level": "中等偏高风险",
            "risk_assessment": "中等风险 - 市场情绪谨慎，建议采取防御性策略",
            "base_signals": [
                "谨慎观望：等待更明确的技术信号",
                "关注支撑：重点观察关键支撑位是否有效",
                "控制仓位：建议仓位不超过50%",
            ],
        },
        "neutral": {
            "market_impact": "市场情绪平衡，等待方向选择",
            "investor_behavior": "投资者保持观望",
            "risk_level": "中等风险",
            "risk_assessment": "中低风险 - 市场情绪平衡，可采取均衡配置",
            "base_signals": [
                "均衡配置：分散投资不同板块",
                "趋势跟踪：跟随主要趋势方向操作",
                "灵活调整：根据市场变化及时调整策略",
            ],
        },
        "greed": {
            "market_impact": "贪婪情绪上升，需注意回调风险",
            "investor_behavior": "投资者风险偏好上升",
            "risk_level": "中等偏低风险",
            "risk_assessment": "中高风险 - 市场情绪贪婪，需警惕回调风险",
            "base_signals": [
                "获利了结：考虑部分获利了结",
                "降低杠杆：避免使用高杠杆",
                "设置止盈：明确获利目标",
            ],
        },
        "extreme_greed": {
            "market_impact": "极度贪婪，警惕大幅回调",
            "investor_behavior": "投资者过度乐观",
            "risk_level": "高风险",
            "risk_assessment": "高风险 - 市场情绪极度贪婪，历史经验显示回调概率较高",
            "base_signals": [
                "大幅减仓：市场极度贪婪，建议大幅降低仓位",
                "空仓观望：等待市场回调后再考虑入场",
                "风险警示：警惕市场快速回调风险",
            ],
        },
    }

    def __init__(self, logger) -> None:
        self.logger = logger

    def get_sentiment_bucket(self, value: int) -> str:
        if value <= 20:
            return "extreme_fear"
        if value <= 40:
            return "fear"
        if value <= 60:
            return "neutral"
        if value <= 80:
            return "greed"
        return "extreme_greed"

    def get_sentiment_profile(self, value: int) -> Dict[str, Any]:
        return self.PROFILES[self.get_sentiment_bucket(value)]

    def get_sentiment_analysis(self, fgi: FearGreedIndex) -> FearGreedIndex:
        classification_cn = self.CHINESE_CLASSIFICATION.get(
            fgi["classification"], fgi["classification"]
        )
        level_info = self.SENTIMENT_LEVELS.get(
            classification_cn,
            {"color": "#6c757d", "description": "未知市场状态"},
        )
        weekly_trend = self.analyze_sentiment_weekly_trend(fgi)
        trend_analysis = self.generate_sentiment_trend_analysis(fgi["value"], weekly_trend)
        return {
            "value": fgi["value"],
            "classification": classification_cn,
            "color": level_info["color"],
            "description": level_info["description"],
            "timestamp": fgi.get("timestamp", int(time.time())),
            "recommendation": self.get_sentiment_recommendation(fgi["value"], weekly_trend),
            "source": fgi.get("source", "币安恐惧贪婪指数"),
            "url": fgi.get("url", "https://www.binance.com/zh-CN/square/fear-and-greed-index"),
            "weekly_trend": weekly_trend,
            "trend_analysis": trend_analysis,
            "daily_change": fgi.get("daily_change"),
            "weekly_change": fgi.get("weekly_change"),
            "monthly_change": fgi.get("monthly_change"),
            "historical_data": fgi.get("historical_data"),
        }

    def analyze_sentiment_weekly_trend(self, fgi_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            weekly_change = fgi_data.get("weekly_change")
            if weekly_change is None:
                return {
                    "trend": "stable",
                    "change": "0",
                    "change_value": 0,
                    "change_percent": 0.0,
                    "volatility": "medium",
                    "key_observations": ["暂无周度变化数据", "请检查API连接"],
                    "source": "weekly_analysis",
                }

            if weekly_change > 5:
                trend = "improving"
                change_str = f"+{weekly_change}"
                observations = [
                    f"本周情绪改善{weekly_change}点",
                    "市场恐慌情绪有所缓解",
                    "投资者信心逐步恢复",
                ]
            elif weekly_change < -5:
                trend = "declining"
                change_str = f"{weekly_change}"
                observations = [
                    f"本周情绪恶化{abs(weekly_change)}点",
                    "市场恐慌情绪加剧",
                    "投资者需保持谨慎",
                ]
            else:
                trend = "stable"
                change_str = f"{weekly_change:+d}"
                observations = [
                    f"本周情绪变化{weekly_change:+d}点，基本稳定",
                    "市场情绪无明显变化",
                    "等待催化剂",
                ]

            volatility = "high" if abs(weekly_change) > 10 else "medium" if abs(weekly_change) > 5 else "low"
            return {
                "trend": trend,
                "change": change_str,
                "change_value": weekly_change,
                "change_percent": round((weekly_change / fgi_data.get("value", 0) * 100), 1)
                if fgi_data.get("value")
                else 0.0,
                "volatility": volatility,
                "key_observations": observations,
                "source": "weekly_analysis",
            }
        except Exception as exc:
            self.logger.warning(f"情绪周度趋势分析失败: {exc}")
            return {}

    @staticmethod
    def generate_sentiment_trend_analysis(current_value: int, weekly_trend: Dict[str, Any]) -> str:
        del current_value
        if not weekly_trend:
            return "暂无周度趋势数据"
        trend = weekly_trend.get("trend", "stable")
        change = weekly_trend.get("change", "0")
        if trend == "improving":
            return f"情绪趋势改善（周度变化{change}），市场恐慌情绪缓解，投资者信心恢复"
        if trend == "declining":
            return f"情绪趋势恶化（周度变化{change}），市场恐慌加剧，需保持谨慎"
        return f"情绪趋势稳定（周度变化{change}），市场情绪无明显变化"

    @staticmethod
    def get_sentiment_recommendation(value: int, weekly_trend: Dict[str, Any] | None = None) -> str:
        if value <= 20:
            base = "市场极度恐惧，可能处于超卖状态，适合长期投资者分批建仓"
        elif value <= 40:
            base = "市场恐惧，建议谨慎观望，等待更明确信号"
        elif value <= 60:
            base = "市场情绪中性，适合平衡配置"
        elif value <= 80:
            base = "市场贪婪，注意风险控制，避免追高"
        else:
            base = "市场极度贪婪，风险较高，建议减仓或设置止损"

        if not weekly_trend:
            return base
        trend = weekly_trend.get("trend", "stable")
        change = weekly_trend.get("change", "0")
        if trend == "improving":
            return f"{base}。从周度趋势看，情绪正在改善（变化{change}），恐慌情绪有所缓解。"
        if trend == "declining":
            return f"{base}。周度趋势显示情绪恶化（变化{change}），需保持高度谨慎。"
        return f"{base}。周度情绪趋势稳定（变化{change}），市场无明显变化。"

    @staticmethod
    def get_volatility_text(volatility: str) -> str:
        return {
            "low": "低波动性（市场相对稳定）",
            "medium": "中等波动性（市场正常波动）",
            "high": "高波动性（市场波动剧烈）",
        }.get(volatility, "未知波动性")

    @staticmethod
    def get_financial_sentiment_trend_text(weekly_trend: Dict[str, Any]) -> str:
        if not weekly_trend:
            return ""
        trend = weekly_trend.get("trend", "stable")
        change = weekly_trend.get("change", "0")
        if trend == "improving":
            return f"从周度趋势看，情绪正在改善（变化{change}），恐慌情绪有所缓解。"
        if trend == "declining":
            return f"周度趋势显示情绪恶化（变化{change}），需保持高度谨慎。"
        return f"周度情绪趋势稳定（变化{change}），市场无明显变化。"

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .trend_repository import TrendRepository


class TrendAnalytics:
    """Compute derived metrics from persisted trend data."""

    def __init__(self, repository: TrendRepository, report_date: datetime, logger) -> None:
        self.repository = repository
        self.report_date = report_date
        self.logger = logger

    def calculate_weekly_change_from_trend(self, current_value: int) -> Optional[int]:
        return self.calculate_change_from_trend(current_value, days=7)

    def calculate_change_from_trend(self, current_value: int, days: int) -> Optional[int]:
        try:
            fgi_data = self.repository.load().get("fear_greed_index", {})
            dates = sorted(fgi_data.keys(), reverse=True)
            if len(dates) < days:
                self.logger.info("趋势数据不足%s天，无法计算%s天变化", len(dates), days)
                return None

            target_value = fgi_data[dates[days - 1]]["value"]
            change_value = current_value - target_value
            self.logger.info(
                "从趋势数据计算%s天变化: 当前%s - %s天前%s = %s",
                days,
                current_value,
                days,
                target_value,
                change_value,
            )
            return change_value
        except Exception as exc:
            self.logger.warning("从趋势数据计算%s天变化失败: %s", days, exc)
            return None

    def calculate_30day_average_from_trend(
        self,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[float]:
        try:
            if historical_data:
                values = [
                    int(item["value"])
                    for item in historical_data[:30]
                    if item.get("value") is not None
                ]
                if values:
                    average = sum(values) / len(values)
                    self.logger.info(
                        "使用API历史数据计算30天平均值: 使用%s天数据，平均值=%.1f",
                        len(values),
                        average,
                    )
                    return average

            fgi_data = self.repository.load().get("fear_greed_index", {})
            dates = sorted(fgi_data.keys(), reverse=True)
            recent_dates = dates[:30] if len(dates) >= 30 else dates
            if not recent_dates:
                return None

            values = [fgi_data[date]["value"] for date in recent_dates]
            average = sum(values) / len(values)
            self.logger.info("计算30天平均值: 使用%s天数据，平均值=%.1f", len(values), average)
            return average
        except Exception as exc:
            self.logger.warning("计算30天平均值失败: %s", exc)
            return None

    def generate_historical_comparison(
        self,
        current_value: int,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        avg_30day = self.calculate_30day_average_from_trend(historical_data=historical_data)
        if avg_30day is None:
            return "暂无足够历史数据进行比较"

        diff = current_value - avg_30day
        diff_percent = (diff / avg_30day * 100) if avg_30day > 0 else 0
        if diff < -10:
            level = "远低于"
            description = "市场情绪极度低迷"
        elif diff < -5:
            level = "低于"
            description = "市场情绪较为悲观"
        elif diff > 10:
            level = "远高于"
            description = "市场情绪异常高涨"
        elif diff > 5:
            level = "高于"
            description = "市场情绪较为乐观"
        else:
            level = "接近"
            description = "市场情绪处于正常水平"

        return (
            f"过去30天平均指数：{avg_30day:.1f}，当前指数{level}平均水平"
            f"（{diff:+.1f}，{diff_percent:+.1f}%），{description}"
        )

    def get_yesterday_sentiment(self) -> Dict[str, Any]:
        try:
            trend_data = self.repository.load()
            yesterday = (self.report_date - timedelta(days=1)).strftime("%Y-%m-%d")
            fear_greed_data = trend_data.get("fear_greed_index", {})
            if yesterday in fear_greed_data:
                return {
                    "value": fear_greed_data[yesterday]["value"],
                    "classification": fear_greed_data[yesterday]["classification"],
                    "date": yesterday,
                    "source": "historical_data",
                }
        except Exception as exc:
            self.logger.error(f"获取昨日情绪数据失败: {exc}")
            return {
                "value": 50,
                "classification": "中性",
                "date": "错误",
                "source": "error",
            }

        return {
            "value": 50,
            "classification": "中性",
            "date": "数据不足",
            "source": "default",
        }

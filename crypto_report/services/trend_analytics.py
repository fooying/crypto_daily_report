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
        average, _sample_days = self.calculate_average_with_sample_days(
            historical_data=historical_data,
            max_days=30,
        )
        return average

    def calculate_average_with_sample_days(
        self,
        historical_data: Optional[List[Dict[str, Any]]] = None,
        max_days: int = 30,
    ) -> tuple[Optional[float], int]:
        try:
            if historical_data:
                values = [
                    int(item["value"])
                    for item in historical_data[:max_days]
                    if item.get("value") is not None
                ]
                if len(values) >= max_days:
                    average = sum(values) / len(values)
                    self.logger.info(
                        "使用API历史数据计算%s天平均值: 使用%s天数据，平均值=%.1f",
                        max_days,
                        len(values),
                        average,
                    )
                    return average, len(values)

            fgi_data = self.repository.load().get("fear_greed_index", {})
            dates = sorted(fgi_data.keys(), reverse=True)
            recent_dates = dates[:max_days] if len(dates) >= max_days else dates
            if not recent_dates:
                return None, 0

            values = [fgi_data[date]["value"] for date in recent_dates]
            average = sum(values) / len(values)
            label = f"{max_days}天" if len(values) >= max_days else f"{len(values)}天样本"
            self.logger.info("计算%s平均值: 使用%s天数据，平均值=%.1f", label, len(values), average)
            return average, len(values)
        except Exception as exc:
            self.logger.warning("计算平均值失败: %s", exc)
            return None, 0

    def generate_historical_comparison(
        self,
        current_value: int,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        average_value, sample_days = self.calculate_average_with_sample_days(
            historical_data=historical_data,
            max_days=30,
        )
        if average_value is None:
            return "暂无足够历史数据进行比较"

        diff = current_value - average_value
        diff_percent = (diff / average_value * 100) if average_value > 0 else 0
        sample_label = "过去30天平均指数" if sample_days >= 30 else f"过去{sample_days}天样本平均指数"
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
            f"{sample_label}：{average_value:.1f}，当前指数{level}平均水平"
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

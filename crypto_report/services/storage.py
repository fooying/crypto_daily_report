from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .trend_analytics import TrendAnalytics
from .trend_repository import TrendRepository


class TrendStorage:
    """Facade for trend persistence and derived analytics."""

    def __init__(self, trend_data_file: Path, report_date: datetime, logger) -> None:
        self.repository = TrendRepository(trend_data_file, report_date, logger)
        self.analytics = TrendAnalytics(self.repository, report_date, logger)

    @property
    def trend_data_file(self) -> Path:
        return self.repository.trend_data_file

    def load(self) -> Dict[str, Any]:
        return self.repository.load()

    def save(self, data: Dict[str, Any]) -> bool:
        return self.repository.save(data)

    def update_fear_greed_trend(self, current_value: int, classification: str) -> Dict[str, Any]:
        return self.repository.update_fear_greed_trend(current_value, classification)

    def backfill_fear_greed_history(
        self,
        historical_data: List[Dict[str, Any]],
        source: str = "alternative.me",
    ) -> Dict[str, Any]:
        return self.repository.backfill_fear_greed_history(historical_data, source=source)

    def update_market_data_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.repository.update_market_data_trend(market_data)

    def update_price_trend(self, symbol: str, price: float, change_24h: float) -> Dict[str, Any]:
        return self.repository.update_price_trend(symbol, price, change_24h)

    def update_cached_snapshot(self, key: str, payload: Dict[str, Any], source: str) -> Dict[str, Any]:
        return self.repository.update_cached_snapshot(key, payload, source)

    def get_cached_snapshot(self, key: str) -> Dict[str, Any]:
        return self.repository.get_cached_snapshot(key)

    def calculate_weekly_change_from_trend(self, current_value: int) -> Optional[int]:
        return self.analytics.calculate_weekly_change_from_trend(current_value)

    def calculate_change_from_trend(self, current_value: int, days: int) -> Optional[int]:
        return self.analytics.calculate_change_from_trend(current_value, days)

    def calculate_30day_average_from_trend(
        self,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[float]:
        return self.analytics.calculate_30day_average_from_trend(historical_data=historical_data)

    def generate_historical_comparison(
        self,
        current_value: int,
        historical_data: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        return self.analytics.generate_historical_comparison(
            current_value,
            historical_data=historical_data,
        )

    def get_yesterday_sentiment(self) -> Dict[str, Any]:
        return self.analytics.get_yesterday_sentiment()

    @staticmethod
    def _price_storage_key(symbol: str) -> str:
        symbol_lower = symbol.lower()
        if symbol_lower in {"bitcoin", "btc"}:
            return "bitcoin_price"
        if symbol_lower in {"ethereum", "eth"}:
            return "ethereum_price"
        return f"{symbol_lower}_price"

from __future__ import annotations

import time
from typing import Any, Dict, Optional

DEFAULT_FGI_URL = "https://alternative.me/crypto/fear-and-greed-index/"


def build_default_market_overview() -> Dict[str, Any]:
    return {
        "total_market_cap": 0,
        "total_volume": 0,
        "active_cryptocurrencies": 0,
        "market_cap_percentage": {},
        "market_cap_change_percentage_24h_usd": 0,
        "alt_market_cap_percentage": 0,
        "volume_to_market_cap_ratio": 0,
        "btc_dominance_daily_change": None,
        "btc_dominance_weekly_change": None,
    }


def build_default_fear_greed_index() -> Dict[str, Any]:
    return {
        "value": 0,
        "classification": "数据获取失败",
        "timestamp": str(int(time.time())),
        "time_until_update": "",
        "source": "error",
        "url": DEFAULT_FGI_URL,
        "daily_change": None,
        "weekly_change": None,
        "monthly_change": None,
        "historical_data": None,
    }


def build_change_meta(value: Optional[float], precision: int = 0) -> Dict[str, str]:
    if value is None:
        return {"text": "N/A", "css_class": "trend-neutral"}
    text = f"{value:+.{precision}f}" if precision else f"{value:+.0f}"
    if value > 0:
        css_class = "trend-positive"
    elif value < 0:
        css_class = "trend-negative"
    else:
        css_class = "trend-neutral"
    return {"text": text, "css_class": css_class}


def get_structured_weekly_trend(sentiment: Dict[str, Any]) -> Dict[str, Any]:
    weekly_trend = dict(sentiment.get("weekly_trend") or {})
    if not weekly_trend:
        return {}

    change_value = weekly_trend.get("change_value")
    if change_value is None:
        change_text = str(weekly_trend.get("change", "")).strip()
        if change_text:
            try:
                change_value = int(change_text)
            except ValueError:
                change_value = None

    if change_value is not None:
        weekly_trend["change_value"] = change_value
        current_value = sentiment.get("value")
        if current_value:
            weekly_trend["change_percent"] = round(change_value / current_value * 100, 1)

    return weekly_trend


def format_large_number(num: float) -> str:
    if num >= 1_000_000_000_000:
        return f"${num/1_000_000_000_000:.2f}T (万亿)"
    if num >= 1_000_000_000:
        return f"${num/1_000_000_000:.2f}B (十亿)"
    if num >= 1_000_000:
        return f"${num/1_000_000:.2f}M (百万)"
    return f"${num:,.0f}"


def get_sentiment_color(value: int) -> str:
    if value <= 20:
        return "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)"
    if value <= 40:
        return "linear-gradient(90deg, #f59e0b 0%, #d97706 100%)"
    if value <= 60:
        return "linear-gradient(90deg, #3b82f6 0%, #2563eb 100%)"
    if value <= 80:
        return "linear-gradient(90deg, #10b981 0%, #059669 100%)"
    return "linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%)"

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class MarketOverview(TypedDict):
    total_market_cap: float
    total_volume: float
    active_cryptocurrencies: int
    market_cap_percentage: Dict[str, float]
    market_cap_change_percentage_24h_usd: float
    alt_market_cap_percentage: float
    volume_to_market_cap_ratio: float
    btc_dominance_daily_change: Optional[float]
    btc_dominance_weekly_change: Optional[float]


class WeeklyTrend(TypedDict, total=False):
    trend: str
    change: str
    change_value: int
    change_percent: float
    market_trend: str
    volatility_trend: str
    sentiment_trend: str
    key_observations: List[str]
    key_patterns: List[str]


class FearGreedIndex(TypedDict, total=False):
    value: int
    classification: str
    timestamp: str
    time_until_update: str
    source: str
    url: str
    daily_change: Optional[float]
    weekly_change: Optional[float]
    monthly_change: Optional[float]
    historical_data: Optional[List[Dict[str, Any]]]
    weekly_trend: WeeklyTrend
    description: str
    recommendation: str
    trend_analysis: str


class NewsItem(TypedDict):
    title: str
    summary: str
    sentiment: str
    time: str
    url: str
    source: str
    tags: List[str]


class ChangeMeta(TypedDict):
    text: str
    css_class: str


class SentimentSummary(TypedDict):
    positive: int
    neutral: int
    negative: int


class AIAnalysis(TypedDict, total=False):
    market_overview: str
    technical_analysis: str
    risk_assessment: str
    trading_signals: List[str]
    sentiment_summary: SentimentSummary
    weekly_trend: WeeklyTrend
    trend_enhanced_analysis: str
    sentiment_deep_analysis: Dict[str, Any]
    financial_analyst: Dict[str, Any]


class ReportContext(TypedDict):
    report_time: str
    market_overview: MarketOverview
    all_top_cryptos: List[Dict[str, Any]]
    top_cryptos: List[Dict[str, Any]]
    top_focus_assets: List[Dict[str, Any]]
    market_cap_history: List[Dict[str, Any]]
    technical_context: Dict[str, Any]
    news: List[NewsItem]
    sentiment: FearGreedIndex
    daily_change_meta: ChangeMeta
    weekly_change_meta: ChangeMeta
    monthly_change_meta: ChangeMeta
    weekly_trend: WeeklyTrend
    dynamic_analysis: Dict[str, str]
    ai_analysis: AIAnalysis

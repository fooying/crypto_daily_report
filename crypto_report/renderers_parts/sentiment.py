from __future__ import annotations

import html
from typing import Any, Dict

from .common import render_key_value_list


def _get_composite_level(score: int) -> tuple[str, str]:
    if score <= 25:
        return "极度防御", "sentiment-level-risk"
    if score <= 45:
        return "偏防御", "sentiment-level-caution"
    if score <= 60:
        return "中性平衡", "sentiment-level-neutral"
    if score <= 75:
        return "风险偏好回升", "sentiment-level-positive"
    return "偏热", "sentiment-level-warm"


def generate_sentiment_analysis_section(
    sentiment: Dict[str, Any],
    report_time: str,
    daily_change_str: str,
    weekly_change_str: str,
    monthly_change_str: str,
    daily_change_class: str,
    weekly_change_class: str,
    monthly_change_class: str,
    sentiment_bar_color: str,
    sentiment_updated_at: str,
    deep_analysis: Dict[str, str],
    sentiment_composite: Dict[str, Any] | None = None,
) -> str:
    del sentiment_updated_at
    source_url = html.escape(
        str(sentiment.get("url", "https://www.binance.com/zh-CN/square/fear-and-greed-index")),
        quote=True,
    )
    source_name = html.escape(str(sentiment.get("source", "币安恐惧贪婪指数")))
    classification = html.escape(str(sentiment.get("classification", "")))
    description = html.escape(str(sentiment.get("description", "")))
    current_interpretation = html.escape(
        str(deep_analysis.get("current_interpretation", description))
    )
    trend_analysis = html.escape(
        str(deep_analysis.get("weekly_trend", sentiment.get("trend_analysis", "暂无周度趋势数据")))
    )
    historical_comparison = html.escape(
        str(deep_analysis.get("historical_comparison", "暂无足够历史数据进行比较"))
    )
    market_impact = html.escape(str(deep_analysis.get("market_impact", "")))
    investor_behavior = html.escape(str(deep_analysis.get("investor_behavior", "")))
    recommendation = html.escape(str(deep_analysis.get("trading_advice", sentiment.get("recommendation", ""))))
    composite = sentiment_composite or {}
    composite_score = int(composite.get("score", sentiment.get("value", 0)) or 0)
    default_label, composite_level_class = _get_composite_level(composite_score)
    composite_label = html.escape(str(composite.get("label", default_label)))
    composite_summary = html.escape(str(composite.get("summary", "")))
    composite_drivers = composite.get("drivers") or []
    composite_drivers_html = ""
    if composite_drivers:
        driver_items = "".join(
            f"<li>{html.escape(str(item))}</li>"
            for item in composite_drivers[:3]
            if str(item).strip()
        )
        if driver_items:
            composite_drivers_html = (
                '<div class="sentiment-driver-list-wrapper">'
                '<div class="sentiment-driver-title">驱动因子</div>'
                f'<ul class="sentiment-driver-list">{driver_items}</ul>'
                "</div>"
            )
    summary_items = (
        '<div class="compact-summary">'
        '<div class="compact-line"><span>快速判断</span>'
        "<span>0-20 极度恐惧 / 21-40 恐惧 / 41-60 中性 / 61-80 贪婪 / 81-100 极度贪婪</span></div>"
        '<div class="compact-line"><span>综合情绪分</span>'
        "<span>0-25 极度防御 / 26-45 偏防御 / 46-60 中性平衡 / 61-75 风险偏好回升 / 76-100 偏热</span></div>"
        f'<div class="compact-line"><span>数据来源</span>'
        f'<a href="{source_url}" target="_blank">{source_name}</a></div>'
        '<div class="compact-line"><span>综合分来源</span>'
        "<span>恐惧贪婪指数、新闻情绪统计、市场总市值24小时变化、BTC主导率变化</span></div>"
        "</div>"
    )
    sentiment_headline = (
        f"综合情绪当前为 {composite_label}，"
        f"恐惧贪婪指数处于 {classification}，"
        f"{trend_analysis}"
    )
    deep_analysis_items = render_key_value_list(
        [
            ("当前解读", current_interpretation),
            ("周度趋势", trend_analysis),
            ("历史对比", historical_comparison),
            ("市场影响", market_impact),
            ("投资者行为", investor_behavior),
            ("交易建议", recommendation),
        ],
        css_class="analysis-grid",
    )

    return f"""
    <div class="section">
        <h2>市场情绪指数分析</h2>
        <div class="sentiment-headline">{sentiment_headline}</div>

        <div class="sentiment-dashboard">
            <div class="sentiment-score-pair">
                <div class="sentiment-gauge">
                    <div class="gauge-title">加密货币恐惧贪婪指数</div>
                    <div class="gauge-value">{sentiment.get('value', 0)}</div>
                    <div class="gauge-classification">{classification}</div>

                    <div class="sentiment-bar">
                        <div class="sentiment-bar-fill" style="width: {sentiment.get('value', 0)}%; background: {sentiment_bar_color};"></div>
                    </div>
                </div>

                <div class="sentiment-gauge sentiment-gauge-composite">
                    <div class="gauge-title">综合市场情绪分</div>
                    <div class="gauge-value">{composite_score}</div>
                    <div class="gauge-classification {composite_level_class}">{composite_label}</div>
                    <div class="composite-summary-card">{composite_summary}</div>
                </div>
            </div>

            <div class="sentiment-trends">
                <div class="trends-title">
                    <span>恐惧贪婪指数变化趋势</span>
                </div>

                <div class="trend-grid">
                    <div class="trend-card">
                        <div class="trend-period">日变化</div>
                        <div class="trend-value {daily_change_class}">{html.escape(daily_change_str)}</div>
                        <div class="trend-change">昨日 → 今日</div>
                    </div>

                    <div class="trend-card">
                        <div class="trend-period">周变化</div>
                        <div class="trend-value {weekly_change_class}">{html.escape(weekly_change_str)}</div>
                        <div class="trend-change">过去7天</div>
                    </div>

                    <div class="trend-card">
                        <div class="trend-period">月变化</div>
                        <div class="trend-value {monthly_change_class}">{html.escape(monthly_change_str)}</div>
                        <div class="trend-change">过去30天</div>
                    </div>
                </div>

                <div class="trend-note">趋势统计基于 {html.escape(report_time)} 生成。</div>
                <div class="trend-panel-summary">情绪变化节奏用于观察短线修复或继续走弱，需结合综合市场情绪分一起判断。</div>
            </div>
        </div>
        {composite_drivers_html}
        <div class="sentiment-inline-note">
            {summary_items}
        </div>

        <div class="sentiment-details">
            <h3>深度分析</h3>
            <div class="analysis-content">{deep_analysis_items}</div>
        </div>
    </div>
    """

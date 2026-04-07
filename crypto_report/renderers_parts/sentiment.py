from __future__ import annotations

import html
from typing import Any, Dict

from .common import render_key_value_list


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
    composite_label = html.escape(str(composite.get("label", sentiment.get("classification", "中性"))))
    composite_summary = html.escape(str(composite.get("summary", "")))
    summary_items = (
        '<div class="compact-summary">'
        '<div class="compact-line"><span>快速判断</span>'
        "<span>0-20 极度恐惧 / 21-40 恐惧 / 41-60 中性 / 61-80 贪婪 / 81-100 极度贪婪</span></div>"
        f'<div class="compact-line"><span>数据来源</span>'
        f'<a href="{source_url}" target="_blank">{source_name}</a></div>'
        "</div>"
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

        <div class="sentiment-dashboard">
                <div class="sentiment-gauge">
                    <div class="gauge-title">加密货币恐惧贪婪指数</div>
                    <div class="gauge-value">{sentiment.get('value', 0)}</div>
                    <div class="gauge-classification">{classification}</div>

                    <div class="sentiment-bar">
                        <div class="sentiment-bar-fill" style="width: {sentiment.get('value', 0)}%; background: {sentiment_bar_color};"></div>
                    </div>
                </div>

            <div class="sentiment-trends">
                <div class="trends-title">
                    <span>指数变化趋势</span>
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

                    <div class="trend-card trend-card-emphasis">
                        <div class="trend-period">综合市场情绪分</div>
                        <div class="trend-value trend-neutral">{composite_score}</div>
                        <div class="trend-change">{composite_label}</div>
                    </div>
                </div>

                <div class="trend-note">趋势统计基于 {html.escape(report_time)} 生成。</div>
                <div class="trend-note trend-note-strong">{composite_summary}</div>
            </div>
        </div>

        <div class="sentiment-details">
            <h3>指数说明</h3>
            <div class="source-info">
                {summary_items}
                <details>
                    <summary class="sentiment-details-summary">查看完整指数说明</summary>
                    <p>该指数结合市场数据、社交媒体情绪、波动率和交易量等多维度数据，综合反映加密货币市场情绪。</p>
                    <ul>
                        <li><span class="sentiment-level-label">0-20 极度恐惧：</span>市场极度悲观，通常对应超卖区间</li>
                        <li><span class="sentiment-level-label">21-40 恐惧：</span>投资者偏谨慎，市场接近底部区域</li>
                        <li><span class="sentiment-level-label">41-60 中性：</span>多空力量相对均衡</li>
                        <li><span class="sentiment-level-label">61-80 贪婪：</span>风险偏好回升，需防回调</li>
                        <li><span class="sentiment-level-label">81-100 极度贪婪：</span>过热概率升高，需控制仓位</li>
                    </ul>
                </details>
            </div>

            <h3>深度分析</h3>
            <div class="analysis-content">{deep_analysis_items}</div>
        </div>
    </div>
    """

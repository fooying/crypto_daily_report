from __future__ import annotations

import html
import re
from typing import Any, Dict, List

from .common import split_non_empty_lines


TERM_MAP = {
    "uptrend": "上涨趋势",
    "downtrend": "下跌趋势",
    "consolidation": "盘整阶段",
    "stable": "稳定",
    "improving": "改善",
    "declining": "走弱",
}


def _localize_terms(value: str) -> str:
    text = str(value or "")
    for source, target in TERM_MAP.items():
        text = re.sub(rf"\b{re.escape(source)}\b", target, text, flags=re.IGNORECASE)
    return text


def _normalize_plain_text(value: str) -> str:
    return re.sub(r"\s+", " ", _localize_terms(value)).strip()


def generate_trading_signals_html(signals: List[str]) -> str:
    signal_html = ""
    signal_icons = {
        "逆向投资": "📈",
        "分批建仓": "💰",
        "严格止损": "🛡️",
        "谨慎观望": "👀",
        "关注支撑": "📊",
        "控制仓位": "⚖️",
        "均衡配置": "🔄",
        "趋势跟踪": "🎯",
        "灵活调整": "⚡",
        "获利了结": "💸",
        "降低杠杆": "📉",
        "设置止盈": "🎯",
        "大幅减仓": "⚠️",
        "空仓观望": "⏸️",
        "风险警示": "🚨",
        "关注比特币": "₿",
        "政策敏感": "🏛️",
        "技术驱动": "🔧",
    }
    signal_types = {
        "逆向投资": "signal-buy",
        "分批建仓": "signal-buy",
        "严格止损": "signal-neutral",
        "谨慎观望": "signal-neutral",
        "关注支撑": "signal-watch",
        "控制仓位": "signal-neutral",
        "均衡配置": "signal-neutral",
        "趋势跟踪": "signal-watch",
        "灵活调整": "signal-neutral",
        "获利了结": "signal-sell",
        "降低杠杆": "signal-sell",
        "设置止盈": "signal-sell",
        "大幅减仓": "signal-sell",
        "空仓观望": "signal-neutral",
        "风险警示": "signal-sell",
        "关注比特币": "signal-watch",
        "政策敏感": "signal-neutral",
        "技术驱动": "signal-watch",
    }
    for signal in signals:
        icon = "📊"
        signal_type = "signal-neutral"
        for keyword in signal_icons:
            if keyword in signal:
                icon = signal_icons[keyword]
                signal_type = signal_types.get(keyword, "signal-neutral")
                break
        if "：" in signal:
            title, desc = signal.split("：", 1)
        elif ":" in signal:
            title, desc = signal.split(":", 1)
        else:
            title, desc = signal, ""
        desc_html = (
            f'<div class="signal-desc">{html.escape(desc.strip())}</div>'
            if desc.strip()
            else ""
        )
        signal_html += f"""
                <li class="{signal_type}">
                    <div class="signal-title-row">
                        <span class="signal-icon">{icon}</span>
                        <span class="signal-title">{html.escape(title)}</span>
                    </div>
                    {desc_html}
                </li>
            """
    return signal_html


def generate_ai_analysis_section(ai_analysis: Dict[str, Any], trading_signals_html: str) -> str:
    sentiment_summary = ai_analysis.get("sentiment_summary", {})
    news_tag_summary = ai_analysis.get("news_tag_summary", {})
    overview = html.escape(_normalize_plain_text(str(ai_analysis.get("market_overview", "暂无市场概况"))))
    technical_analysis = _localize_terms(str(ai_analysis.get("technical_analysis", "")))
    risk_assessment = html.escape(_normalize_plain_text(str(ai_analysis.get("risk_assessment", "暂无风险评估"))))
    trend_raw = _normalize_plain_text(str(ai_analysis.get("trend_enhanced_analysis", "暂无趋势增强分析")))
    trend_lines = split_non_empty_lines(trend_raw)
    trend_summary_lines = [
        line for line in trend_lines
        if line.startswith(("⚖️", "📈", "📉", "😐", "😊", "😨"))
    ]
    trend_summary = "；".join(trend_summary_lines)
    trend_summary_html = ""
    if trend_summary:
        trend_summary_html = f'<p class="ai-trend-summary">{html.escape(trend_summary)}</p>'
    risk_tags = [
        (tag, count)
        for tag, count in sorted(
            news_tag_summary.items(),
            key=lambda item: (-item[1], item[0]),
        )
        if tag in {"监管", "安全事件", "交易所", "ETF/机构", "技术升级"}
    ][:3]
    risk_focus_html = ""
    if risk_tags:
        risk_focus_items = "".join(
            (
                '<span class="news-summary-tag">'
                f'<span class="news-summary-tag-label">{html.escape(str(tag))}</span>'
                f'<span class="news-summary-tag-count">{count}</span>'
                "</span>"
            )
            for tag, count in risk_tags
        )
        risk_focus_html = (
            '<div class="ai-risk-focus">'
            '<span class="ai-risk-focus-label">对应主题</span>'
            f'<div class="news-tag-summary-list">{risk_focus_items}</div>'
            "</div>"
        )
    return f"""
    <div class="section">
        <h2>AI智能分析</h2>
        <div class="ai-analysis">
            <div class="content-panel ai-panel ai-panel-overview">
                <div class="analysis-kicker">综合判断</div>
                <div class="ai-merged-block">
                    <p>{overview}</p>
                    {technical_analysis}
                    {trend_summary_html}
                </div>
            </div>

            <div class="content-panel ai-panel ai-panel-risk">
                <div class="panel-title-row">
                    <h3>风险评估</h3>
                    <div class="ai-sentiment-mini">
                        <span>新闻情绪</span>
                        <div class="ai-sentiment-metrics">
                            <span class="ai-sentiment-positive">正面 {sentiment_summary.get('positive', 0)}</span>
                            <span class="ai-sentiment-neutral">中性 {sentiment_summary.get('neutral', 0)}</span>
                            <span class="ai-sentiment-negative">负面 {sentiment_summary.get('negative', 0)}</span>
                        </div>
                    </div>
                </div>
                <p class="risk-level">{risk_assessment}</p>
                {risk_focus_html}
            </div>

            <div class="content-panel ai-panel ai-panel-signals">
                <h3>交易信号</h3>
                <ul class="signal-list">
                    {trading_signals_html}
                </ul>
            </div>
        </div>
    </div>
    """

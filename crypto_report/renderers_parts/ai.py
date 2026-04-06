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
        signal_html += f"""
                <li class="{signal_type}">
                    <div class="signal-title-row">
                        <span class="signal-icon">{icon}</span>
                        <span class="signal-title">{html.escape(title)}</span>
                    </div>
                    <div class="signal-desc">{html.escape(desc)}</div>
                </li>
            """
    return signal_html


def generate_ai_analysis_section(ai_analysis: Dict[str, Any], trading_signals_html: str) -> str:
    sentiment_summary = ai_analysis.get("sentiment_summary", {})
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
    return f"""
    <div class="section">
        <h2>AI智能分析</h2>
        <div class="ai-analysis">
            <div class="content-panel">
                <div class="ai-merged-block">
                    <p>{overview}</p>
                    {technical_analysis}
                    {trend_summary_html}
                </div>
            </div>

            <div class="content-panel">
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
            </div>

            <div class="content-panel">
                <h3>交易信号</h3>
                <ul class="signal-list">
                    {trading_signals_html}
                </ul>
            </div>
        </div>
    </div>
    """

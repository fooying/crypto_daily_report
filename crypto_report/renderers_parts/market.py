from __future__ import annotations

import html
from typing import Any, Dict, List

from ..helpers import format_large_number
from .common import build_svg_sparkline


def _build_fallback_icon_html(symbol: str) -> str:
    return (
        '<span class="crypto-icon-fallback" '
        f'aria-label="{html.escape(symbol)}"></span>'
    )


def _build_icon_html(image_src: str, symbol: str) -> str:
    if not image_src:
        return _build_fallback_icon_html(symbol)
    return (
        f'<img src="{html.escape(image_src)}" alt="{html.escape(symbol)}" '
        'class="crypto-icon" loading="lazy">'
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def generate_top_focus_assets_section(cryptos: List[Dict[str, Any]]) -> str:
    cards = []
    for crypto in cryptos[:5]:
        symbol = html.escape(str(crypto.get("symbol", "")))
        name = html.escape(str(crypto.get("name", "")))
        price = f"${_safe_float(crypto.get('current_price', 0)):,.2f}"
        change = _safe_float(crypto.get("price_change_percentage_24h", 0))
        raw_spark_values = crypto.get("sparkline_7d") or []
        spark_values = [
            _safe_float(value)
            for value in raw_spark_values
            if value is not None
        ]
        sparkline = ""
        if len(spark_values) >= 4:
            sparkline = build_svg_sparkline(spark_values)
        image_html = _build_icon_html(str(crypto.get("image", "")), str(crypto.get("symbol", "")))
        change_class = "green" if change >= 0 else "red"
        sparkline_html = (
            f'<div class="focus-asset-sparkline">{sparkline}</div>'
            if sparkline
            else ""
        )
        cards.append(
            f"""
            <div class="focus-asset-card">
                <div class="focus-asset-header"><strong>{image_html}{name}</strong> <span>({symbol})</span></div>
                <div class="focus-asset-price">{price}</div>
                <div class="focus-asset-change {change_class}">{change:+.2f}%</div>
                {sparkline_html}
            </div>
            """
        )
    return f"""
    <div class="section">
        <h2>主流币速览</h2>
        <div class="focus-asset-grid">
            {''.join(cards)}
        </div>
    </div>
    """


def generate_market_pulse_section(
    market_overview: Dict[str, Any],
    market_cap_history: List[Dict[str, Any]],
) -> str:
    history = market_cap_history[-30:]
    market_values = [
        float(item.get("market_cap", 0))
        for item in history
        if item.get("market_cap") is not None
    ]
    volume_values = [
        float(item.get("volume_24h", 0))
        for item in history
        if item.get("volume_24h") is not None
    ]
    history_days = len(history)
    period_text = f"近{history_days}天" if history_days else "暂无历史数据"
    market_chart = ""
    volume_chart = ""
    if len(market_values) >= 4:
        market_chart = build_svg_sparkline(market_values, width=640, height=180)
    if len(volume_values) >= 4:
        volume_chart = build_svg_sparkline(volume_values, width=640, height=72)

    chart_sections = []
    if market_chart:
        chart_sections.append(
            f"""
        <div class="market-pulse-chart">
            <div class="market-pulse-chart-header">
                <h3>总市值走势</h3>
                <span>{period_text}</span>
            </div>
            {market_chart}
        </div>
        """
        )
    if volume_chart:
        chart_sections.append(
            f"""
        <div class="market-pulse-volume">
            <div class="market-pulse-chart-header">
                <h3>24小时交易量走势</h3>
                <span>{period_text}</span>
            </div>
            {volume_chart}
        </div>
        """
        )
    latest_market_cap = format_large_number(float(market_overview.get("total_market_cap", 0)))
    latest_volume = format_large_number(float(market_overview.get("total_volume", 0)))
    return f"""
    <div class="section">
        <h2>市场脉搏</h2>
        <div class="market-pulse-meta">
            展示近 {history_days} 天的总市值与 24 小时交易量变化。
        </div>
        <div class="market-pulse-summary">
            <div><span>市值</span><strong>{latest_market_cap}</strong></div>
            <div><span>交易量</span><strong>{latest_volume}</strong></div>
            <div><span>BTC主导率</span><strong>{market_overview.get('market_cap_percentage', {}).get('btc', 0):.1f}%</strong></div>
            <div><span>ETH主导率</span><strong>{market_overview.get('market_cap_percentage', {}).get('eth', 0):.1f}%</strong></div>
            <div><span>活跃币种</span><strong>{market_overview.get('active_cryptocurrencies', 0):,}</strong></div>
        </div>
        {''.join(chart_sections)}
    </div>
    """


def generate_technical_context_section(technical_context: Dict[str, Any]) -> str:
    if not technical_context:
        return ""

    cards = []
    for symbol, metrics in technical_context.items():
        price_change_30d = float(metrics.get("price_change_30d", 0))
        high_30d = float(metrics.get("high_30d", 0))
        low_30d = float(metrics.get("low_30d", 0))
        latest_close = float(metrics.get("latest_close", 0))
        avg_volume_30d = float(metrics.get("avg_volume_30d", 0))
        change_class = "green" if price_change_30d >= 0 else "red"
        cards.append(
            f"""
            <div class="technical-context-card">
                <div class="technical-context-header">{html.escape(str(symbol))} 30天技术摘要</div>
                <div class="technical-context-grid">
                    <div><span>30天涨跌</span><strong class="{change_class}">{price_change_30d:+.2f}%</strong></div>
                    <div><span>区间高点</span><strong>${high_30d:,.2f}</strong></div>
                    <div><span>区间低点</span><strong>${low_30d:,.2f}</strong></div>
                    <div><span>最新收盘</span><strong>${latest_close:,.2f}</strong></div>
                    <div><span>30天均量</span><strong>{format_large_number(avg_volume_30d)}</strong></div>
                </div>
            </div>
            """
        )

    return f"""
    <div class="section">
        <h2>技术背景摘要</h2>
        <div class="technical-context-wrap">
            {''.join(cards)}
        </div>
    </div>
    """


def generate_crypto_table_rows(cryptos: List[Dict[str, Any]]) -> str:
    rows = []
    for crypto in cryptos:
        change_24h = _safe_float(crypto.get("price_change_percentage_24h"), 0.0)
        change_7d = _safe_float(crypto.get("price_change_percentage_7d"), 0.0)
        name = html.escape(str(crypto["name"]))
        symbol = html.escape(str(crypto["symbol"]))
        icon = _build_icon_html(str(crypto.get("image", "")), str(crypto.get("symbol", "")))
        change_24h_color = "green" if change_24h >= 0 else "red"
        change_7d_color = "green" if change_7d >= 0 else "red"
        price = f"${_safe_float(crypto.get('current_price'), 0.0):,.2f}"
        market_cap = format_large_number(_safe_float(crypto.get("market_cap"), 0.0))
        volume = format_large_number(_safe_float(crypto.get("total_volume"), 0.0))
        rows.append(
            f"""
                    <tr>
                        <td>{crypto.get('market_cap_rank', '')}</td>
                        <td><strong>{icon}{name}</strong> ({symbol})</td>
                        <td>{price}</td>
                        <td style=\"color: {change_24h_color}\">{change_24h:+.2f}%</td>
                        <td style=\"color: {change_7d_color}\">{change_7d:+.2f}%</td>
                        <td>{market_cap}</td>
                        <td>{volume}</td>
                    </tr>
            """
        )
    return "".join(rows)


def generate_market_overview_section(market_overview: Dict[str, Any]) -> str:
    market_cap_change = market_overview.get("market_cap_change_percentage_24h_usd", 0)
    negative_class = "negative" if market_cap_change < 0 else ""
    return f"""
    <div class="section">
        <h2>市场概览</h2>
        <div class="market-overview">
            <div class="overview-grid">
                <div class="overview-item">
                    <div class="overview-label">总市值</div>
                    <div class="overview-value">{format_large_number(market_overview.get('total_market_cap', 0))}</div>
                    <div class="overview-change {negative_class}">{market_cap_change:+.2f}% (24h)</div>
                </div>
                <div class="overview-item">
                    <div class="overview-label">24小时交易量</div>
                    <div class="overview-value">{format_large_number(market_overview.get('total_volume', 0))}</div>
                    <div class="overview-sub">活跃币种：{market_overview.get('active_cryptocurrencies', 0):,}</div>
                </div>
                <div class="overview-item">
                    <div class="overview-label">比特币占比</div>
                    <div class="overview-value">{market_overview.get('market_cap_percentage', {}).get('btc', 0):.1f}%</div>
                    <div class="overview-sub">以太坊：{market_overview.get('market_cap_percentage', {}).get('eth', 0):.1f}%</div>
                </div>
            </div>
        </div>
    </div>
    """

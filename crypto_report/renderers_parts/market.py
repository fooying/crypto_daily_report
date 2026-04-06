from __future__ import annotations

import html
from urllib.parse import quote
from typing import Any, Dict, List

from ..helpers import format_large_number
from .common import build_svg_sparkline


def _build_local_icon_data_uri(symbol: str) -> str:
    safe_symbol = (symbol or "?").upper()[:2]
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'>"
        "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0%' stop-color='#3b82f6'/>"
        "<stop offset='100%' stop-color='#22c55e'/>"
        "</linearGradient></defs>"
        "<circle cx='12' cy='12' r='11' fill='url(#g)'/>"
        "<text x='12' y='15' text-anchor='middle' font-size='8' font-family='Arial, sans-serif' "
        "fill='white' font-weight='700'>"
        f"{html.escape(safe_symbol)}"
        "</text></svg>"
    )
    return f"data:image/svg+xml;utf8,{quote(svg)}"


def _build_local_icon_html(symbol: str) -> str:
    icon_uri = _build_local_icon_data_uri(symbol)
    return (
        f'<img src="{icon_uri}" alt="{html.escape(symbol)}" '
        'style="width: 18px; height: 18px; margin-right: 8px; vertical-align: text-bottom;">'
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
        spark_values = crypto.get("sparkline_7d") or [
            _safe_float(crypto.get("current_price", 0)) * 0.98,
            _safe_float(crypto.get("current_price", 0)),
            _safe_float(crypto.get("current_price", 0)) * 1.01,
        ]
        sparkline = build_svg_sparkline(spark_values)
        image_html = _build_local_icon_html(str(crypto.get("symbol", "")))
        change_class = "green" if change >= 0 else "red"
        cards.append(
            f"""
            <div class="focus-asset-card">
                <div class="focus-asset-header"><strong>{image_html}{name}</strong> <span>({symbol})</span></div>
                <div class="focus-asset-price">{price}</div>
                <div class="focus-asset-change {change_class}">{change:+.2f}%</div>
                <div class="focus-asset-sparkline">{sparkline}</div>
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
    market_values = [float(item.get("market_cap", 0)) for item in history if item.get("market_cap") is not None]
    volume_values = [float(item.get("volume_24h", 0)) for item in history if item.get("volume_24h") is not None]
    market_chart = build_svg_sparkline(market_values, width=640, height=220)
    volume_chart = build_svg_sparkline(volume_values, width=640, height=80)
    period_text = "30天" if len(history) >= 20 else "7天"
    latest_market_cap = format_large_number(float(market_overview.get("total_market_cap", 0)))
    latest_volume = format_large_number(float(market_overview.get("total_volume", 0)))
    return f"""
    <div class="section">
        <h2>市场脉搏</h2>
        <div class="market-pulse-toolbar">
            <span class="pulse-chip pulse-chip-active">总览</span>
            <span class="pulse-chip">明细</span>
            <span class="pulse-chip pulse-chip-active">{period_text}</span>
        </div>
        <div class="market-pulse-summary">
            <div><span>市值</span><strong>{latest_market_cap}</strong></div>
            <div><span>交易量</span><strong>{latest_volume}</strong></div>
            <div><span>BTC主导率</span><strong>{market_overview.get('market_cap_percentage', {}).get('btc', 0):.1f}%</strong></div>
            <div><span>ETH主导率</span><strong>{market_overview.get('market_cap_percentage', {}).get('eth', 0):.1f}%</strong></div>
            <div><span>活跃币种</span><strong>{market_overview.get('active_cryptocurrencies', 0):,}</strong></div>
        </div>
        <div class="market-pulse-chart">
            {market_chart}
        </div>
        <div class="market-pulse-volume">
            {volume_chart}
        </div>
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
        icon = _build_local_icon_html(str(crypto.get("symbol", "")))
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

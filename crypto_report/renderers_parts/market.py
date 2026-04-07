from __future__ import annotations

import html
from typing import Any, Dict, List

from ..helpers import format_large_number
from .common import build_svg_sparkline


STABLECOIN_SYMBOLS = {
    "USDT",
    "USDC",
    "DAI",
    "FDUSD",
    "TUSD",
    "USDE",
    "USDD",
    "PYUSD",
}

SECTOR_RULES = {
    "主流资产": {"BTC", "ETH"},
    "公链生态": {"SOL", "ADA", "AVAX", "DOT", "TRX", "SUI", "APT", "ATOM", "NEAR"},
    "DeFi": {"UNI", "AAVE", "LINK", "MKR", "ENA"},
    "交易平台": {"BNB", "OKB", "CRO"},
    "支付与跨境": {"XRP", "XLM"},
    "Meme": {"DOGE", "SHIB", "PEPE", "BONK", "WIF"},
}


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


def _select_non_stable_cryptos(cryptos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        crypto
        for crypto in cryptos
        if str(crypto.get("symbol", "")).upper() not in STABLECOIN_SYMBOLS
    ]


def _classify_sector(symbol: str) -> str:
    upper_symbol = str(symbol or "").upper()
    for sector, symbols in SECTOR_RULES.items():
        if upper_symbol in symbols:
            return sector
    return "其他"


def _build_strength_label(change_value: float, baseline: float) -> str:
    diff = change_value - baseline
    if diff >= 2.0:
        return "强于大盘"
    if diff <= -2.0:
        return "弱于大盘"
    return "跟随大盘"


def _build_liquidity_label(turnover_ratio: float) -> str:
    if turnover_ratio >= 12:
        return "量能活跃"
    if turnover_ratio >= 6:
        return "量能平稳"
    return "量能偏弱"


def _build_technical_takeaway(metrics: Dict[str, Any]) -> str:
    ma7 = metrics.get("ma7")
    ma30 = metrics.get("ma30")
    rsi14 = metrics.get("rsi14")
    bollinger_status = str(metrics.get("bollinger_status", "") or "")
    parts: List[str] = []
    if ma7 is not None and ma30 is not None:
        parts.append("短期强于中期均线" if float(ma7) >= float(ma30) else "短期弱于中期均线")
    if rsi14 is not None:
        rsi_value = float(rsi14)
        if rsi_value < 30:
            parts.append("RSI 接近超卖")
        elif rsi_value > 70:
            parts.append("RSI 偏强")
        else:
            parts.append("RSI 中性")
    if bollinger_status:
        parts.append(f"波动处于{bollinger_status}")
    macd_bias = str(metrics.get("macd_bias", "") or "")
    if macd_bias:
        parts.append(macd_bias)
    return "，".join(parts) if parts else "样本不足，暂无法形成统一结论"


def _build_market_breadth_summary(
    cryptos: List[Dict[str, Any]],
    market_overview: Dict[str, Any],
) -> str:
    candidates = _select_non_stable_cryptos(cryptos)
    if len(candidates) < 3:
        return ""
    market_change = _safe_float(market_overview.get("market_cap_change_percentage_24h_usd"), 0.0)
    advancers = sum(
        1 for item in candidates
        if _safe_float(item.get("price_change_percentage_24h"), 0.0) > 0.5
    )
    decliners = sum(
        1 for item in candidates
        if _safe_float(item.get("price_change_percentage_24h"), 0.0) < -0.5
    )
    flat = max(0, len(candidates) - advancers - decliners)
    outperform = sum(
        1 for item in candidates
        if _safe_float(item.get("price_change_percentage_24h"), -999.0) > market_change
    )
    return f"""
    <div class="market-breadth-grid">
        <div><span>上涨家数</span><strong>{advancers}</strong><small>下跌 {decliners} / 平盘 {flat}</small></div>
        <div><span>跑赢大盘</span><strong>{outperform}</strong><small>按 24h 总市值变化比较</small></div>
        <div><span>扩散强度</span><strong>{advancers - decliners:+d}</strong><small>正值代表广度改善</small></div>
    </div>
    """


def generate_top_focus_assets_section(
    cryptos: List[Dict[str, Any]],
    market_overview: Dict[str, Any] | None = None,
) -> str:
    if not cryptos:
        return ""
    market_change = _safe_float((market_overview or {}).get("market_cap_change_percentage_24h_usd"), 0.0)
    cards = []
    for crypto in cryptos[:5]:
        symbol = html.escape(str(crypto.get("symbol", "")))
        name = html.escape(str(crypto.get("name", "")))
        price = f"${_safe_float(crypto.get('current_price', 0)):,.2f}"
        change = _safe_float(crypto.get("price_change_percentage_24h", 0))
        change_7d = _safe_float(crypto.get("price_change_percentage_7d", 0))
        market_cap = format_large_number(_safe_float(crypto.get("market_cap"), 0.0))
        volume = format_large_number(_safe_float(crypto.get("total_volume"), 0.0))
        high_24h = _safe_float(crypto.get("high_24h"), 0.0)
        low_24h = _safe_float(crypto.get("low_24h"), 0.0)
        circulating_supply = _safe_float(crypto.get("circulating_supply"), 0.0)
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
        turnover_ratio = (
            _safe_float(crypto.get("total_volume"), 0.0)
            / max(_safe_float(crypto.get("market_cap"), 0.0), 1e-9)
            * 100
        )
        strength_label = _build_strength_label(change, market_change)
        liquidity_label = _build_liquidity_label(turnover_ratio)
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
                <div class="focus-asset-change-row">
                    <div class="focus-asset-change {change_class}">24h {change:+.2f}%</div>
                    <div class="focus-asset-change {'green' if change_7d >= 0 else 'red'}">7d {change_7d:+.2f}%</div>
                </div>
                <div class="focus-asset-strength-row">
                    <span>{html.escape(strength_label)}</span>
                    <span>{html.escape(liquidity_label)}</span>
                </div>
                <div class="focus-asset-meta">
                    <span>市值 {market_cap}</span>
                    <span>成交量 {volume}</span>
                    {f'<span>24h 区间 ${low_24h:,.2f} - ${high_24h:,.2f}</span>' if high_24h > 0 and low_24h > 0 else ''}
                    {f'<span>流通量 {circulating_supply:,.0f}</span>' if circulating_supply > 0 else ''}
                </div>
                {sparkline_html}
            </div>
            """
        )
    return f"""
    <div class="focus-assets-block">
        <div class="focus-asset-grid">
            {''.join(cards)}
        </div>
    </div>
    """


def generate_market_leadership_section(
    cryptos: List[Dict[str, Any]],
    market_overview: Dict[str, Any],
) -> str:
    body = _generate_market_leadership_body(cryptos, market_overview)
    if not body:
        return ""
    return f"""
    <div class="section">
        <h2>市场风向</h2>
        {body}
    </div>
    """


def _generate_market_leadership_body(
    cryptos: List[Dict[str, Any]],
    market_overview: Dict[str, Any],
) -> str:
    candidates = _select_non_stable_cryptos(cryptos)
    if len(candidates) < 3:
        return ""

    def turnover_ratio(item: Dict[str, Any]) -> float:
        market_cap = _safe_float(item.get("market_cap"), 0.0)
        if market_cap <= 0:
            return 0.0
        return _safe_float(item.get("total_volume"), 0.0) / market_cap * 100

    strongest_24h = max(
        candidates,
        key=lambda item: _safe_float(item.get("price_change_percentage_24h"), -9999.0),
    )
    strongest_7d = max(
        candidates,
        key=lambda item: _safe_float(item.get("price_change_percentage_7d"), -9999.0),
    )
    highest_turnover = max(candidates, key=turnover_ratio)
    top3_market_cap = sum(
        _safe_float(item.get("market_cap"), 0.0)
        for item in sorted(
            candidates,
            key=lambda item: _safe_float(item.get("market_cap"), 0.0),
            reverse=True,
        )[:3]
    )
    total_market_cap = _safe_float(market_overview.get("total_market_cap"), 0.0)
    if total_market_cap <= 0:
        return ""
    concentration = top3_market_cap / total_market_cap * 100 if total_market_cap else 0.0
    cards = [
        (
            "24h 领涨",
            strongest_24h,
            f"{_safe_float(strongest_24h.get('price_change_percentage_24h'), 0.0):+.2f}%",
            "短线涨幅领先",
        ),
        (
            "7天 强势",
            strongest_7d,
            f"{_safe_float(strongest_7d.get('price_change_percentage_7d'), 0.0):+.2f}%",
            "周度相对强势",
        ),
        (
            "流动性最强",
            highest_turnover,
            f"{turnover_ratio(highest_turnover):.2f}%",
            "成交 / 市值最高",
        ),
    ]
    card_html = []
    for label, crypto, value_text, note in cards:
        change_24h = _safe_float(crypto.get("price_change_percentage_24h"), 0.0)
        change_class = "green" if change_24h >= 0 else "red"
        symbol = html.escape(str(crypto.get("symbol", "")))
        name = html.escape(str(crypto.get("name", "")))
        image_html = _build_icon_html(str(crypto.get("image", "")), symbol)
        card_html.append(
            f"""
            <div class="leadership-card">
                <div class="leadership-label">{label}</div>
                <div class="leadership-asset">{image_html}<strong>{name}</strong><span>{symbol}</span></div>
                <div class="leadership-value {change_class}">{value_text}</div>
                <div class="leadership-note">{note}</div>
            </div>
            """
        )

    return f"""
    <div class="leadership-grid">
        {''.join(card_html)}
    </div>
    <div class="leadership-meta">前 3 大币种市值合计约占整体市场 {concentration:.1f}% 。</div>
    """


def generate_sector_overview_section(cryptos: List[Dict[str, Any]]) -> str:
    body = _generate_sector_overview_body(cryptos)
    if not body:
        return ""
    return f"""
    <div class="section">
        <h2>板块观察</h2>
        {body}
    </div>
    """


def _generate_sector_overview_body(cryptos: List[Dict[str, Any]]) -> str:
    candidates = _select_non_stable_cryptos(cryptos)
    if len(candidates) < 4:
        return ""

    sector_map: Dict[str, Dict[str, Any]] = {}
    for crypto in candidates:
        sector = _classify_sector(str(crypto.get("symbol", "")))
        bucket = sector_map.setdefault(
            sector,
            {
                "items": [],
                "avg_change_24h": 0.0,
                "total_market_cap": 0.0,
                "leader": None,
            },
        )
        bucket["items"].append(crypto)
        bucket["total_market_cap"] += _safe_float(crypto.get("market_cap"), 0.0)

    for bucket in sector_map.values():
        items = bucket["items"]
        bucket["avg_change_24h"] = sum(
            _safe_float(item.get("price_change_percentage_24h"), 0.0)
            for item in items
        ) / len(items)
        bucket["leader"] = max(
            items,
            key=lambda item: _safe_float(item.get("price_change_percentage_24h"), -9999.0),
        )

    ranked = sorted(
        sector_map.items(),
        key=lambda item: (len(item[1]["items"]) >= 1, item[1]["avg_change_24h"]),
        reverse=True,
    )
    if len(ranked) < 2:
        return ""
    cards = []
    for sector, bucket in ranked[:4]:
        leader = bucket["leader"] or {}
        avg_change = bucket["avg_change_24h"]
        change_class = "green" if avg_change >= 0 else "red"
        cards.append(
            f"""
            <div class="sector-card">
                <div class="sector-header">
                    <strong>{html.escape(sector)}</strong>
                    <span>{len(bucket['items'])} 个币种</span>
                </div>
                <div class="sector-value {change_class}">{avg_change:+.2f}%</div>
                <div class="sector-meta">代表币：{html.escape(str(leader.get('symbol', '--')))} / 市值 {format_large_number(bucket['total_market_cap'])}</div>
                <div class="sector-submeta">
                    <span>上涨占比 {sum(1 for item in bucket['items'] if _safe_float(item.get('price_change_percentage_24h'), 0.0) > 0) / max(len(bucket['items']), 1) * 100:.0f}%</span>
                    <span>龙头 {_safe_float(leader.get('price_change_percentage_24h'), 0.0):+.2f}%</span>
                </div>
            </div>
            """
        )

    strongest_sector, strongest_bucket = ranked[0]
    weakest_sector, weakest_bucket = ranked[-1]
    rotation_summary = (
        f"当前板块轮动更偏向{html.escape(str(strongest_sector))}，"
        f"其平均涨跌为{strongest_bucket['avg_change_24h']:+.2f}% ；"
        f"{html.escape(str(weakest_sector))}相对承压（{weakest_bucket['avg_change_24h']:+.2f}%）。"
    )

    return f"""
    <div class="sector-grid">
        {''.join(cards)}
    </div>
    <div class="sector-rotation-summary">{rotation_summary}</div>
    """


def generate_market_pulse_section(
    market_overview: Dict[str, Any],
    market_cap_history: List[Dict[str, Any]],
    sentiment_composite: Dict[str, Any] | None = None,
) -> str:
    body = _generate_market_pulse_body(
        market_overview,
        market_cap_history,
        sentiment_composite=sentiment_composite,
    )
    return f"""
    <div class="section">
        <h2>市场脉搏</h2>
        {body}
    </div>
    """


def _generate_market_pulse_body(
    market_overview: Dict[str, Any],
    market_cap_history: List[Dict[str, Any]],
    sentiment_composite: Dict[str, Any] | None = None,
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
    market_change = _safe_float(market_overview.get("market_cap_change_percentage_24h_usd"), 0.0)
    turnover_ratio = _safe_float(market_overview.get("volume_to_market_cap_ratio"), 0.0)
    market_change_class = "green" if market_change >= 0 else "red"
    btc_dom_change_1d = market_overview.get("btc_dominance_daily_change")
    btc_dom_change_7d = market_overview.get("btc_dominance_weekly_change")
    btc_dom_note_parts = []
    if btc_dom_change_1d is not None:
        btc_dom_note_parts.append(f"日变 {float(btc_dom_change_1d):+.2f}pct")
    if btc_dom_change_7d is not None:
        btc_dom_note_parts.append(f"周变 {float(btc_dom_change_7d):+.2f}pct")
    btc_dom_note_html = (
        f"<small>{' / '.join(btc_dom_note_parts)}</small>"
        if btc_dom_note_parts
        else ""
    )
    composite = sentiment_composite or {}
    composite_label = str(composite.get("label", "") or "").strip()
    composite_summary = str(composite.get("summary", "") or "").strip()
    pulse_state_html = ""
    if composite_label or composite_summary:
        pulse_state_html = (
            '<div class="market-pulse-state">'
            f'<span>市场状态</span><strong>{html.escape(composite_label or "中性平衡")}</strong>'
            f'<small>{html.escape(composite_summary)}</small>'
            "</div>"
        )
    return f"""
    <div class="market-pulse-meta">
        展示近 {history_days} 天的总市值与 24 小时交易量变化。
    </div>
    <div class="market-pulse-summary">
        <div><span>市场24h涨跌</span><strong class="{market_change_class}">{market_change:+.2f}%</strong></div>
        <div><span>成交 / 市值</span><strong>{turnover_ratio:.2f}%</strong></div>
        <div><span>BTC主导率</span><strong>{market_overview.get('market_cap_percentage', {}).get('btc', 0):.1f}%</strong>{btc_dom_note_html}</div>
        <div><span>ETH主导率</span><strong>{market_overview.get('market_cap_percentage', {}).get('eth', 0):.1f}%</strong></div>
        <div><span>活跃币种</span><strong>{market_overview.get('active_cryptocurrencies', 0):,}</strong></div>
        {pulse_state_html}
    </div>
    {''.join(chart_sections)}
    """


def generate_market_insights_section(
    market_overview: Dict[str, Any],
    market_cap_history: List[Dict[str, Any]],
    cryptos: List[Dict[str, Any]],
    sentiment_composite: Dict[str, Any] | None = None,
) -> str:
    pulse_body = _generate_market_pulse_body(
        market_overview,
        market_cap_history,
        sentiment_composite=sentiment_composite,
    )
    leadership_body = _generate_market_leadership_body(cryptos, market_overview)
    sector_body = _generate_sector_overview_body(cryptos)
    breadth_body = _build_market_breadth_summary(cryptos, market_overview)
    panels = []
    for title, body, extra_class in (
        ("市场脉搏", pulse_body, "market-insight-panel-wide"),
        ("市场风向", leadership_body, ""),
        ("板块观察", sector_body, ""),
        ("市场广度", breadth_body, ""),
    ):
        if not body:
            continue
        panel_class = f"content-panel market-insight-panel {extra_class}".strip()
        panels.append(
            f"""
            <div class="{panel_class}">
                <div class="market-insight-eyebrow">{'大盘结构' if title == '市场脉搏' else '主流强弱' if title == '市场风向' else '轮动变化' if title == '板块观察' else '资金扩散'}</div>
                <h3>{title}</h3>
                {body}
            </div>
            """
        )
    if not panels:
        return ""
    return f"""
    <div class="section">
        <h2>市场动向</h2>
        <div class="market-insights-wrap">
            {''.join(panels)}
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
        ma7 = metrics.get("ma7")
        ma30 = metrics.get("ma30")
        rsi14 = metrics.get("rsi14")
        bollinger_status = html.escape(str(metrics.get("bollinger_status", "")))
        bollinger_upper = metrics.get("bollinger_upper")
        bollinger_lower = metrics.get("bollinger_lower")
        macd_bias = html.escape(str(metrics.get("macd_bias", "") or ""))
        volatility_30d = metrics.get("volatility_30d")
        support_level = metrics.get("support_level")
        resistance_level = metrics.get("resistance_level")
        change_class = "green" if price_change_30d >= 0 else "red"
        ma_status = ""
        if ma7 is not None and ma30 is not None:
            ma_status = "短期强于中期" if float(ma7) >= float(ma30) else "短期仍弱于中期"
        cards.append(
            f"""
            <div class="technical-context-card">
                <div class="technical-context-header">{html.escape(str(symbol))} 30天技术摘要</div>
                <div class="technical-context-takeaway">{html.escape(_build_technical_takeaway(metrics))}</div>
                <div class="technical-context-grid">
                    <div><span>30天涨跌</span><strong class="{change_class}">{price_change_30d:+.2f}%</strong></div>
                    <div><span>区间高点</span><strong>${high_30d:,.2f}</strong></div>
                    <div><span>区间低点</span><strong>${low_30d:,.2f}</strong></div>
                    <div><span>最新收盘</span><strong>${latest_close:,.2f}</strong></div>
                    <div><span>30天均量</span><strong>{format_large_number(avg_volume_30d)}</strong></div>
                </div>
                <div class="technical-indicator-row">
                    <div><span>MA7 / MA30</span><strong>{f'${float(ma7):,.2f}' if ma7 is not None else 'N/A'} / {f'${float(ma30):,.2f}' if ma30 is not None else 'N/A'}</strong><small>{ma_status or '样本不足'}</small></div>
                    <div><span>RSI14</span><strong>{f'{float(rsi14):.1f}' if rsi14 is not None else 'N/A'}</strong><small>{'超卖' if rsi14 is not None and float(rsi14) < 30 else '偏强' if rsi14 is not None and float(rsi14) > 70 else '中性区间' if rsi14 is not None else '样本不足'}</small></div>
                    <div><span>布林带</span><strong>{bollinger_status or 'N/A'}</strong><small>{f'${float(bollinger_lower):,.2f} - ${float(bollinger_upper):,.2f}' if bollinger_upper is not None and bollinger_lower is not None else '样本不足'}</small></div>
                </div>
                <div class="technical-indicator-row">
                    <div><span>MACD 动能</span><strong>{macd_bias or 'N/A'}</strong><small>观察趋势延续性</small></div>
                    <div><span>30天波动率</span><strong>{f'{float(volatility_30d):.2f}%' if volatility_30d is not None else 'N/A'}</strong><small>衡量振幅强弱</small></div>
                    <div><span>支撑 / 阻力</span><strong>{f'${float(support_level):,.2f}' if support_level is not None else 'N/A'} / {f'${float(resistance_level):,.2f}' if resistance_level is not None else 'N/A'}</strong><small>近7天价格区间</small></div>
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


def generate_macro_context_section(macro_context: Dict[str, Any]) -> str:
    assets = macro_context.get("assets") or []
    if not assets:
        return ""
    btc = macro_context.get("btc") or {}
    cards = []
    for item in assets:
        change_30d = _safe_float(item.get("change_30d"), 0.0)
        change_class = "green" if change_30d >= 0 else "red"
        corr = item.get("correlation_30d")
        corr_text = f"{float(corr):+.2f}" if corr is not None else "N/A"
        cards.append(
            f"""
            <div class="macro-card">
                <div class="macro-card-label">{html.escape(str(item.get('label', '')))}</div>
                <div class="macro-card-value {change_class}">{change_30d:+.2f}%</div>
                <div class="macro-card-meta">
                    <span>30天相关性 {corr_text}</span>
                    <span>最新 {float(item.get('latest', 0.0)):,.2f}</span>
                </div>
            </div>
            """
        )
    return f"""
    <div class="section">
        <h2>宏观关联观察</h2>
        <div class="macro-summary">
            <div><span>BTC 30天表现</span><strong class="{'green' if _safe_float(btc.get('change_30d'), 0.0) >= 0 else 'red'}">{_safe_float(btc.get('change_30d'), 0.0):+.2f}%</strong></div>
            <p>{html.escape(str(macro_context.get('summary', '')))}</p>
        </div>
        <div class="macro-grid">
            {''.join(cards)}
        </div>
    </div>
    """


def generate_defi_overview_section(defi_overview: Dict[str, Any]) -> str:
    top_chains = defi_overview.get("top_chains") or []
    if not top_chains:
        return ""
    chain_cards = []
    for item in top_chains:
        change_7d = item.get("change_7d")
        change_text = f"{float(change_7d):+.2f}%" if change_7d is not None else "样本不足"
        change_class = "green" if change_7d is not None and float(change_7d) >= 0 else "red"
        chain_cards.append(
            f"""
            <div class="defi-card">
                <div class="defi-card-header">
                    <strong>{html.escape(str(item.get('name', '')))}</strong>
                    <span>{float(item.get('share_pct', 0.0)):.1f}%</span>
                </div>
                <div class="defi-card-value">{format_large_number(_safe_float(item.get('tvl'), 0.0))}</div>
                <div class="defi-card-meta">
                    <span>TVL 占比</span>
                    <strong class="{change_class}">7d {change_text}</strong>
                </div>
            </div>
            """
        )
    return f"""
    <div class="section">
        <h2>DeFi生态概览</h2>
        <div class="defi-summary">
            <div><span>总 TVL</span><strong>{format_large_number(_safe_float(defi_overview.get('total_tvl'), 0.0))}</strong></div>
            <p>{html.escape(str(defi_overview.get('summary', '')))}</p>
        </div>
        <div class="defi-grid">
            {''.join(chain_cards)}
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
        circulating_supply = _safe_float(crypto.get("circulating_supply"), 0.0)
        fully_diluted_valuation = format_large_number(
            _safe_float(crypto.get("fully_diluted_valuation"), 0.0)
        )
        high_24h = _safe_float(crypto.get("high_24h"), 0.0)
        low_24h = _safe_float(crypto.get("low_24h"), 0.0)
        volume_to_market_cap_ratio = (
            _safe_float(crypto.get("total_volume"), 0.0)
            / max(_safe_float(crypto.get("market_cap"), 0.0), 1e-9)
            * 100
        )
        supply_text = f"{circulating_supply:,.0f}" if circulating_supply else "N/A"
        name_meta_parts = []
        if circulating_supply:
            name_meta_parts.append(f"流通量 {supply_text}")
        if _safe_float(crypto.get("fully_diluted_valuation"), 0.0) > 0:
            name_meta_parts.append(f"FDV {fully_diluted_valuation}")
        name_meta_html = (
            f'<div class="table-subtext">{" · ".join(name_meta_parts)}</div>'
            if name_meta_parts
            else ""
        )
        price_meta_html = ""
        if high_24h > 0 and low_24h > 0 and high_24h >= low_24h:
            price_meta_html = (
                f'<div class="table-subtext">24h 区间 ${low_24h:,.2f} - ${high_24h:,.2f}</div>'
            )
        volume_meta_html = ""
        if _safe_float(crypto.get("market_cap"), 0.0) > 0 and _safe_float(crypto.get("total_volume"), 0.0) > 0:
            volume_meta_html = (
                f'<div class="table-subtext">成交 / 市值 {volume_to_market_cap_ratio:.2f}%</div>'
            )
        rows.append(
            f"""
                    <tr>
                        <td>{crypto.get('market_cap_rank', '')}</td>
                        <td>
                            <strong>{icon}{name}</strong> ({symbol})
                            {name_meta_html}
                        </td>
                        <td>
                            {price}
                            {price_meta_html}
                        </td>
                        <td style=\"color: {change_24h_color}\">{change_24h:+.2f}%</td>
                        <td style=\"color: {change_7d_color}\">{change_7d:+.2f}%</td>
                        <td>{market_cap}</td>
                        <td>
                            {volume}
                            {volume_meta_html}
                        </td>
                    </tr>
            """
        )
    return "".join(rows)


def generate_market_overview_section(market_overview: Dict[str, Any]) -> str:
    btc_dominance = market_overview.get('market_cap_percentage', {}).get('btc', 0)
    eth_dominance = market_overview.get('market_cap_percentage', {}).get('eth', 0)
    alt_dominance = market_overview.get('alt_market_cap_percentage', 0)
    turnover_ratio = market_overview.get('volume_to_market_cap_ratio', 0)
    total_market_cap = _safe_float(market_overview.get('total_market_cap', 0))
    total_volume = _safe_float(market_overview.get('total_volume', 0))
    market_change = _safe_float(market_overview.get('market_cap_change_percentage_24h_usd', 0))
    if btc_dominance >= 55 and turnover_ratio < 8:
        structure_summary = "资金继续集中在比特币等主流资产，扩散节奏偏慢，市场更偏防御配置。"
    elif btc_dominance <= 50 and market_change > 0:
        structure_summary = "主流币之外的风险偏好有所抬升，资金有向更高弹性资产扩散的迹象。"
    elif turnover_ratio >= 12:
        structure_summary = "成交活跃度提升，说明短线资金参与意愿增强，但仍需观察持续性。"
    else:
        structure_summary = "资金结构相对均衡，主流资产与山寨资产暂未出现单边主导。"

    def unit_label(value: float) -> str:
        if value >= 1_000_000_000_000:
            return "单位：万亿"
        if value >= 1_000_000_000:
            return "单位：十亿"
        if value >= 1_000_000:
            return "单位：百万"
        return "单位：美元"

    return f"""
    <div class="section">
        <h2>市场概览</h2>
        <div class="market-overview">
            <div class="overview-grid">
                <div class="overview-item">
                    <div class="overview-label">总市值</div>
                    <div class="overview-value">{format_large_number(total_market_cap).split(' ')[0]}</div>
                    <div class="overview-sub">{unit_label(total_market_cap)}</div>
                </div>
                <div class="overview-item">
                    <div class="overview-label">24小时交易量</div>
                    <div class="overview-value">{format_large_number(total_volume).split(' ')[0]}</div>
                    <div class="overview-sub">{unit_label(total_volume)}</div>
                </div>
                <div class="overview-item">
                    <div class="overview-label">比特币占比</div>
                    <div class="overview-value">{btc_dominance:.1f}%</div>
                    <div class="overview-sub">以太坊：{eth_dominance:.1f}%</div>
                </div>
                <div class="overview-item">
                    <div class="overview-label">山寨币占比</div>
                    <div class="overview-value">{alt_dominance:.1f}%</div>
                    <div class="overview-sub">成交额 / 市值：{turnover_ratio:.2f}%</div>
                </div>
            </div>
            <div class="market-overview-summary">{html.escape(structure_summary)}</div>
        </div>
    </div>
    """

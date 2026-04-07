from __future__ import annotations

import html
from typing import Any, Dict, List


TAG_ALIASES = {
    "DeFi生态": "DeFi",
    "DeFi 协议": "DeFi",
    "DeFi 生态": "DeFi",
    "监管与合规": "监管",
    "政策监管": "监管",
    "监管政策": "监管",
    "合规": "监管",
    "交易所": "交易平台",
    "交易平台": "交易平台",
    "中心化交易所": "交易平台",
    "交易平台与交易所": "交易平台",
    "机构资金": "ETF/机构",
    "机构": "ETF/机构",
    "ETF": "ETF/机构",
    "ETF/机构": "ETF/机构",
    "安全风险": "安全事件",
    "安全事故": "安全事件",
    "安全漏洞": "安全事件",
    "黑客事件": "安全事件",
    "技术进展": "技术升级",
    "技术更新": "技术升级",
    "技术发展": "技术升级",
    "链上与矿业": "链上/挖矿",
    "链上与挖矿": "链上/挖矿",
    "链上/矿业": "链上/挖矿",
    "链上与矿工": "链上/挖矿",
    "矿业": "链上/挖矿",
    "矿工": "链上/挖矿",
}


def _normalize_tag(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return TAG_ALIASES.get(text, text)


def _dedupe_tag_sequence(values: List[Any]) -> List[str]:
    results: List[str] = []
    seen: set[str] = set()
    for value in values:
        tag = _normalize_tag(value)
        if not tag or tag in seen:
            continue
        seen.add(tag)
        results.append(tag)
    return results


def _render_news_event_summary(
    news_tag_summary: Dict[str, int],
    news_event_summary: Dict[str, int],
) -> str:
    merged_counts: Dict[str, int] = {}
    for source in (news_event_summary or {}, news_tag_summary or {}):
        for label, count in source.items():
            text = _normalize_tag(label)
            if not text:
                continue
            merged_counts[text] = merged_counts.get(text, 0) + int(count)
    if not merged_counts:
        return ""
    items = "".join(
        (
            '<span class="news-summary-tag">'
            f'<span class="news-summary-tag-label">{html.escape(str(label))}</span>'
            f'<span class="news-summary-tag-count">{count}</span>'
            "</span>"
        )
        for label, count in sorted(
            merged_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    )
    return (
        '<div class="news-tag-summary">'
        '<div class="news-tag-summary-title">新闻标签</div>'
        f'<div class="news-tag-summary-list">{items}</div>'
        "</div>"
    )


def generate_news_html(
    news: List[Dict[str, Any]],
    news_tag_summary: Dict[str, int] | None = None,
    news_event_summary: Dict[str, int] | None = None,
    event_watchlist: List[Dict[str, Any]] | None = None,
) -> str:
    news_items_html = ""
    event_summary_html = _render_news_event_summary(
        news_tag_summary or {},
        news_event_summary or {},
    )
    watch_lookup = {
        str(item.get("title", "")).strip(): item
        for item in (event_watchlist or [])
        if str(item.get("title", "")).strip()
    }
    for i, item in enumerate(news, 1):
        title = html.escape(str(item.get("title", "")))
        summary = html.escape(str(item.get("summary", "")))
        sentiment = html.escape(str(item.get("sentiment", "")))
        impact = html.escape(str(item.get("impact", "")))
        publish_time = html.escape(str(item.get("time", "")))
        source = html.escape(str(item.get("source", "")))
        url = html.escape(str(item.get("url", "#")), quote=True)
        tags = item.get("tags") or []
        event_item = watch_lookup.get(str(item.get("title", "")).strip(), {})
        merged_tags = _dedupe_tag_sequence([*tags, event_item.get("theme", "")])
        tags_html = ""
        if merged_tags:
            tags_html = '<div class="news-tags">' + "".join(
                f'<span class="news-tag">{html.escape(tag)}</span>'
                for tag in merged_tags
            ) + '</div>'
        impact_html = f'<span class="news-impact-badge">{impact}</span>' if impact else ""
        news_items_html += f"""
            <div class="news-item">
                <div class="news-title-row">
                    <div class="news-title">{i}. {title}</div>
                    <div class="news-badge-group">
                        {impact_html}
                        <span class="news-sentiment-badge">{sentiment}</span>
                    </div>
                </div>
                <p class="news-summary">{summary}</p>
                {tags_html}
                <div class="news-meta">
                    <span>{publish_time}</span>
                    <span>{source}</span>
                    <a href="{url}" target="_blank">查看原文</a>
                </div>
            </div>
            """
    summary_wrap = ""
    if event_summary_html:
        summary_wrap = (
            '<div class="news-summary-wrap">'
            f'{event_summary_html}'
            "</div>"
        )
    return summary_wrap + f'<div class="news-list">{news_items_html}</div>'

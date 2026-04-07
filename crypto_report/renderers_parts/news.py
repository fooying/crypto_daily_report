from __future__ import annotations

import html
from typing import Any, Dict, List


def _render_news_event_summary(
    news_tag_summary: Dict[str, int],
    news_event_summary: Dict[str, int],
) -> str:
    merged_counts: Dict[str, int] = {}
    for source in (news_event_summary or {}, news_tag_summary or {}):
        for label, count in source.items():
            text = str(label).strip()
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
        '<div class="news-tag-summary-title">事件主线</div>'
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
        tags_html = ""
        if tags:
            tags_html = '<div class="news-tags">' + "".join(
                f'<span class="news-tag">{html.escape(str(tag))}</span>'
                for tag in tags
            ) + '</div>'
        if event_item.get("theme"):
            tags_html += (
                '<div class="news-event-inline">'
                f'<span class="event-watch-theme">{html.escape(str(event_item.get("theme", "")))}</span>'
                f'<span class="news-event-source">{html.escape(str(event_item.get("source", "")))}</span>'
                '</div>'
            )
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

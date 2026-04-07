from __future__ import annotations

import html
from typing import Any, Dict, List


TAG_GROUPS = {
    "风险事件": {"安全事件", "监管"},
    "资金动向": {"ETF/机构", "交易所"},
    "链上生态": {"DeFi", "链上/挖矿"},
    "技术进展": {"技术升级"},
}


def _render_news_tag_summary(news_tag_summary: Dict[str, int]) -> str:
    grouped_rows = []
    remaining_tags = dict(news_tag_summary)
    for group_label, group_tags in TAG_GROUPS.items():
        members = [
            (tag, remaining_tags.pop(tag))
            for tag in sorted(group_tags)
            if tag in remaining_tags
        ]
        if not members:
            continue
        tags_html = "".join(
            (
                '<span class="news-summary-tag">'
                f'<span class="news-summary-tag-label">{html.escape(str(tag))}</span>'
                f'<span class="news-summary-tag-count">{count}</span>'
                "</span>"
            )
            for tag, count in sorted(members, key=lambda item: (-item[1], item[0]))
        )
        grouped_rows.append(
            '<div class="news-tag-summary-group">'
            f'<div class="news-tag-summary-group-title">{html.escape(group_label)}</div>'
            f'<div class="news-tag-summary-list">{tags_html}</div>'
            "</div>"
        )

    if remaining_tags:
        tags_html = "".join(
            (
                '<span class="news-summary-tag">'
                f'<span class="news-summary-tag-label">{html.escape(str(tag))}</span>'
                f'<span class="news-summary-tag-count">{count}</span>'
                "</span>"
            )
            for tag, count in sorted(
                remaining_tags.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        )
        grouped_rows.append(
            '<div class="news-tag-summary-group">'
            '<div class="news-tag-summary-group-title">其他主题</div>'
            f'<div class="news-tag-summary-list">{tags_html}</div>'
            "</div>"
        )

    if not grouped_rows:
        return ""
    return (
        '<div class="news-tag-summary">'
        '<div class="news-tag-summary-title">新闻标签摘要</div>'
        f'{"".join(grouped_rows)}'
        "</div>"
    )


def _render_news_event_summary(news_event_summary: Dict[str, int]) -> str:
    if not news_event_summary:
        return ""
    items = "".join(
        (
            '<span class="news-summary-tag">'
            f'<span class="news-summary-tag-label">{html.escape(str(label))}</span>'
            f'<span class="news-summary-tag-count">{count}</span>'
            "</span>"
        )
        for label, count in sorted(
            news_event_summary.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    return (
        '<div class="news-tag-summary">'
        '<div class="news-tag-summary-title">事件主线</div>'
        f'<div class="news-tag-summary-list">{items}</div>'
        "</div>"
    )


def _render_event_watchlist(event_watchlist: List[Dict[str, Any]]) -> str:
    if not event_watchlist:
        return ""
    rows = []
    for item in event_watchlist:
        rows.append(
            '<div class="event-watch-item">'
            f'<div class="event-watch-theme">{html.escape(str(item.get("theme", "")))}</div>'
            f'<div class="event-watch-title">{html.escape(str(item.get("title", "")))}</div>'
            '<div class="event-watch-meta">'
            f'<span>{html.escape(str(item.get("time", "")))}</span>'
            f'<span>{html.escape(str(item.get("impact", "")))}</span>'
            f'<span>{html.escape(str(item.get("source", "")))}</span>'
            "</div>"
            "</div>"
        )
    return (
        '<div class="news-event-watch">'
        '<div class="news-tag-summary-title">事件观察</div>'
        f'{"".join(rows)}'
        "</div>"
    )


def generate_event_calendar_section(event_watchlist: List[Dict[str, Any]]) -> str:
    if not event_watchlist:
        return ""
    rows = []
    for item in event_watchlist:
        impact = html.escape(str(item.get("impact", "") or "一般"))
        theme = html.escape(str(item.get("theme", "") or "事件跟踪"))
        title = html.escape(str(item.get("title", "") or ""))
        time_text = html.escape(str(item.get("time", "") or ""))
        source = html.escape(str(item.get("source", "") or ""))
        rows.append(
            '<div class="calendar-item">'
            f'<div class="calendar-time">{time_text}</div>'
            '<div class="calendar-content">'
            f'<div class="calendar-theme-row"><span class="calendar-theme">{theme}</span><span class="calendar-impact">{impact}</span></div>'
            f'<div class="calendar-title">{title}</div>'
            f'<div class="calendar-meta">持续跟踪 | 来源 {source}</div>'
            '</div>'
            '</div>'
        )
    return (
        '<div class="section">'
        '<h2>事件日历</h2>'
        '<div class="calendar-wrap">'
        f'{"".join(rows)}'
        '</div>'
        '</div>'
    )


def generate_news_html(
    news: List[Dict[str, Any]],
    news_tag_summary: Dict[str, int] | None = None,
    news_event_summary: Dict[str, int] | None = None,
    event_watchlist: List[Dict[str, Any]] | None = None,
) -> str:
    news_items_html = ""
    summary_html = ""
    if news_tag_summary:
        summary_html = _render_news_tag_summary(news_tag_summary)
    event_summary_html = _render_news_event_summary(news_event_summary or {})
    watchlist_html = _render_event_watchlist(event_watchlist or [])
    for i, item in enumerate(news, 1):
        title = html.escape(str(item.get("title", "")))
        summary = html.escape(str(item.get("summary", "")))
        sentiment = html.escape(str(item.get("sentiment", "")))
        impact = html.escape(str(item.get("impact", "")))
        publish_time = html.escape(str(item.get("time", "")))
        source = html.escape(str(item.get("source", "")))
        url = html.escape(str(item.get("url", "#")), quote=True)
        tags = item.get("tags") or []
        tags_html = ""
        if tags:
            tags_html = '<div class="news-tags">' + "".join(
                f'<span class="news-tag">{html.escape(str(tag))}</span>'
                for tag in tags
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
    if summary_html or event_summary_html or watchlist_html:
        summary_wrap = (
            '<div class="news-summary-wrap">'
            f'{summary_html}{event_summary_html}{watchlist_html}'
            "</div>"
        )
    return summary_wrap + f'<div class="news-list">{news_items_html}</div>'

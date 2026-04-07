from __future__ import annotations

import html
from typing import Any, Dict, List


def generate_news_html(
    news: List[Dict[str, Any]],
    news_tag_summary: Dict[str, int] | None = None,
) -> str:
    news_html = ""
    summary_html = ""
    if news_tag_summary:
        top_tags = sorted(
            news_tag_summary.items(),
            key=lambda item: (-item[1], item[0]),
        )[:5]
        if top_tags:
            tags_html = "".join(
                (
                    '<span class="news-summary-tag">'
                    f'<span class="news-summary-tag-label">{html.escape(str(tag))}</span>'
                    f'<span class="news-summary-tag-count">{count}</span>'
                    "</span>"
                )
                for tag, count in top_tags
            )
            summary_html = (
                '<div class="news-tag-summary">'
                '<div class="news-tag-summary-title">新闻标签摘要</div>'
                f'<div class="news-tag-summary-list">{tags_html}</div>'
                "</div>"
            )
    for i, item in enumerate(news, 1):
        title = html.escape(str(item.get("title", "")))
        summary = html.escape(str(item.get("summary", "")))
        sentiment = html.escape(str(item.get("sentiment", "")))
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
        news_html += f"""
            <div class="news-item">
                <div class="news-title-row">
                    <div class="news-title">{i}. {title}</div>
                    <span class="news-sentiment-badge">{sentiment}</span>
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
    return summary_html + news_html

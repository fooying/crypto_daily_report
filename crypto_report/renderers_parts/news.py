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


def generate_news_html(
    news: List[Dict[str, Any]],
    news_tag_summary: Dict[str, int] | None = None,
) -> str:
    news_html = ""
    summary_html = ""
    if news_tag_summary:
        summary_html = _render_news_tag_summary(news_tag_summary)
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

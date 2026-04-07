from __future__ import annotations

import html
import re
from typing import Any, Dict

from .common import render_bullet_list


def _normalize_compare_text(value: str) -> str:
    return re.sub(r"[\s，。；、,.!:：\-]+", "", str(value or "")).lower()


def _dedupe_items(items: list[Any]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        normalized = _normalize_compare_text(text)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results.append(text)
    return results


def _filter_overall_points(
    overall_points: list[Any],
    short_summary: str,
    long_summary: str,
) -> list[str]:
    excluded = {
        value
        for value in (
            _normalize_compare_text(short_summary),
            _normalize_compare_text(long_summary),
        )
        if value
    }
    filtered: list[str] = []
    for point in _dedupe_items(overall_points):
        normalized = _normalize_compare_text(point)
        if any(
            normalized == summary
            or normalized in summary
            or summary in normalized
            for summary in excluded
        ):
            continue
        filtered.append(point)
    return filtered


def generate_financial_analyst_section(financial_analyst: Dict[str, Any]) -> str:
    short_term = financial_analyst.get("short_term", {})
    long_term = financial_analyst.get("long_term", {})
    short_summary = str(short_term.get("summary", ""))
    long_summary = str(long_term.get("summary", ""))

    overall_points = render_bullet_list(
        _filter_overall_points(
            financial_analyst.get("overall_points", []),
            short_summary,
            long_summary,
        ),
        css_class="insight-list",
    )
    short_actions = render_bullet_list(
        _dedupe_items(short_term.get("action_items", [])),
        css_class="action-list",
    )
    long_actions = render_bullet_list(
        _dedupe_items(long_term.get("action_items", [])),
        css_class="action-list",
    )
    return f"""
    <div class="section">
        <h2>金融分析师视角</h2>
        <div class="content-panel financial-panel financial-overview">
            <div class="analysis-kicker">策略判断</div>
            <h3>整体解读</h3>
            {overall_points}
        </div>

        <div class="section-subgrid financial-detail-grid">
            <div class="content-panel financial-panel financial-panel-short">
                <div class="panel-title-row">
                    <div class="financial-title-wrap">
                        <span class="financial-horizon">短线执行</span>
                        <h3>短期建议</h3>
                    </div>
                    <div class="ai-sentiment-mini stance-mini">
                        <span>{html.escape(str(short_term.get('stance', '谨慎')))}</span>
                    </div>
                </div>
                <div class="stance-row">
                    <p>{html.escape(str(short_term.get('summary', '')))}</p>
                </div>
                {short_actions}
            </div>

            <div class="content-panel financial-panel financial-panel-long">
                <div class="panel-title-row">
                    <div class="financial-title-wrap">
                        <span class="financial-horizon">中长期配置</span>
                        <h3>长期建议</h3>
                    </div>
                    <div class="ai-sentiment-mini stance-mini">
                        <span>{html.escape(str(long_term.get('stance', '中性')))}</span>
                    </div>
                </div>
                <div class="stance-row">
                    <p>{html.escape(str(long_term.get('summary', '')))}</p>
                </div>
                {long_actions}
            </div>
        </div>
    </div>
    """

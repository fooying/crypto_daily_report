from __future__ import annotations

import html
from typing import Any, Dict

from .common import render_bullet_list


def generate_financial_analyst_section(financial_analyst: Dict[str, Any]) -> str:
    short_term = financial_analyst.get("short_term", {})
    long_term = financial_analyst.get("long_term", {})

    overall_points = render_bullet_list(
        financial_analyst.get("overall_points", []),
        css_class="insight-list",
    )
    short_actions = render_bullet_list(
        short_term.get("action_items", []),
        css_class="action-list",
    )
    long_actions = render_bullet_list(
        long_term.get("action_items", []),
        css_class="action-list",
    )
    return f"""
    <div class="section">
        <h2>金融分析师视角</h2>
        <div class="content-panel financial-panel financial-overview">
            <h3>整体解读</h3>
            {overall_points}
        </div>

        <div class="section-subgrid financial-detail-grid">
            <div class="content-panel financial-panel financial-panel-short">
                <div class="panel-title-row">
                    <h3>短期建议</h3>
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
                    <h3>长期建议</h3>
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

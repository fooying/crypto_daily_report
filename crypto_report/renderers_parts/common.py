from __future__ import annotations

import html
from typing import Any, Callable, List


def split_non_empty_lines(value: Any) -> List[str]:
    return [
        line.strip()
        for line in str(value or "").splitlines()
        if line.strip()
    ]


def render_key_value_list(items: List[tuple[str, str]], css_class: str = "key-value-list") -> str:
    rows = []
    for label, value in items:
        safe_value = html.escape(str(value or "暂无"))
        rows.append(
            f'<div class="{css_class}-item"><span>{html.escape(label)}</span><strong>{safe_value}</strong></div>'
        )
    return f'<div class="{css_class}">{"".join(rows)}</div>'


def render_text_points(text: Any, css_class: str = "point-list") -> str:
    lines = split_non_empty_lines(text)
    if not lines:
        return f'<div class="{css_class} empty">暂无</div>'

    items = []
    for line in lines:
        cleaned = line.lstrip("-• ").strip()
        if "：" in cleaned:
            title, desc = cleaned.split("：", 1)
            items.append(
                "<li>"
                f"<span>{html.escape(title.strip())}</span>"
                f"<strong>{html.escape(desc.strip())}</strong>"
                "</li>"
            )
            continue
        if ":" in cleaned:
            title, desc = cleaned.split(":", 1)
            items.append(
                "<li>"
                f"<span>{html.escape(title.strip())}</span>"
                f"<strong>{html.escape(desc.strip())}</strong>"
                "</li>"
            )
            continue
        items.append(f"<li><strong>{html.escape(cleaned)}</strong></li>")
    return f'<ul class="{css_class}">{"".join(items)}</ul>'


def render_bullet_list(items: List[Any], css_class: str = "action-list") -> str:
    if not items:
        return f'<div class="{css_class} empty">暂无</div>'
    rows = "".join(f"<li>{html.escape(str(item))}</li>" for item in items if str(item).strip())
    return f'<ul class="{css_class}">{rows}</ul>'


def render_mobile_details(
    preview_text: Any,
    body_html: str,
    css_class: str = "mobile-details",
) -> str:
    preview = html.escape(str(preview_text or "").strip() or "展开查看")
    return (
        f'<details class="{css_class}">'
        f'<summary>{preview}</summary>'
        f'<div class="mobile-details-body">{body_html}</div>'
        '</details>'
    )


def build_svg_sparkline(values: List[float], width: int = 160, height: int = 48) -> str:
    if len(values) < 2:
        return ""
    min_value = min(values)
    max_value = max(values)
    spread = max(max_value - min_value, 1e-9)
    step = width / max(len(values) - 1, 1)
    points = []
    for index, value in enumerate(values):
        x = round(index * step, 2)
        y = round(height - ((value - min_value) / spread * height), 2)
        points.append(f"{x},{y}")
    color = "#2e7d32" if values[-1] >= values[0] else "#c62828"
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'preserveAspectRatio="none">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2.5" '
        f'points="{" ".join(points)}"></polyline></svg>'
    )


def build_svg_line_chart(
    values: List[float],
    width: int = 640,
    height: int = 180,
    y_tick_count: int = 4,
    x_labels: List[str] | None = None,
    value_formatter: Callable[[float], str] | None = None,
    chart_id: str = "line-chart",
) -> str:
    if len(values) < 2:
        return ""

    formatter = value_formatter or (lambda value: f"{value:.0f}")
    left_padding = 56
    right_padding = 14
    top_padding = 14
    bottom_padding = 28
    plot_width = max(width - left_padding - right_padding, 1)
    plot_height = max(height - top_padding - bottom_padding, 1)
    min_value = min(values)
    max_value = max(values)
    spread = max(max_value - min_value, 1e-9)

    def project_x(index: int) -> float:
        return left_padding + (plot_width * index / max(len(values) - 1, 1))

    def project_y(value: float) -> float:
        return top_padding + (plot_height - ((value - min_value) / spread * plot_height))

    points = [
        f"{round(project_x(index), 2)},{round(project_y(value), 2)}"
        for index, value in enumerate(values)
    ]
    line_color = "#2f855a" if values[-1] >= values[0] else "#dc2626"
    area_points = " ".join(
        [
            f"{left_padding},{top_padding + plot_height}",
            *points,
            f"{left_padding + plot_width},{top_padding + plot_height}",
        ]
    )

    y_ticks = max(y_tick_count, 2)
    grid_lines = []
    y_tick_labels = []
    for tick_index in range(y_ticks):
        ratio = tick_index / (y_ticks - 1)
        y = top_padding + ratio * plot_height
        tick_value = max_value - ratio * spread
        grid_lines.append(
            f'<line class="chart-grid-line" x1="{left_padding}" y1="{y:.2f}" '
            f'x2="{left_padding + plot_width}" y2="{y:.2f}"></line>'
        )
        y_tick_labels.append(
            f'<text class="chart-axis-label chart-axis-label-y" x="{left_padding - 8}" '
            f'y="{y + 4:.2f}">{html.escape(formatter(tick_value))}</text>'
        )

    labels = x_labels or []
    if len(labels) < 2:
        labels = ["起点", "中位", "最新"]
    x_positions = [0, max((len(values) - 1) // 2, 0), len(values) - 1]
    x_ticks = []
    seen = set()
    for label, value_index in zip(labels, x_positions):
        if value_index in seen:
            continue
        seen.add(value_index)
        x = project_x(value_index)
        x_ticks.append(
            f'<line class="chart-axis-tick" x1="{x:.2f}" y1="{top_padding + plot_height}" '
            f'x2="{x:.2f}" y2="{top_padding + plot_height + 6}"></line>'
            f'<text class="chart-axis-label chart-axis-label-x" x="{x:.2f}" '
            f'y="{height - 8}">{html.escape(label)}</text>'
        )

    return (
        f'<svg class="line-chart-svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'preserveAspectRatio="none" role="img" aria-hidden="true">'
        f'<defs><linearGradient id="{chart_id}-area-gradient" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{line_color}" stop-opacity="0.22"></stop>'
        f'<stop offset="100%" stop-color="{line_color}" stop-opacity="0.03"></stop>'
        '</linearGradient></defs>'
        f'{"".join(grid_lines)}'
        f'<line class="chart-axis-line" x1="{left_padding}" y1="{top_padding}" '
        f'x2="{left_padding}" y2="{top_padding + plot_height}"></line>'
        f'<line class="chart-axis-line" x1="{left_padding}" y1="{top_padding + plot_height}" '
        f'x2="{left_padding + plot_width}" y2="{top_padding + plot_height}"></line>'
        f'{"".join(y_tick_labels)}'
        f'{"".join(x_ticks)}'
        f'<polygon class="chart-area" fill="url(#{chart_id}-area-gradient)" points="{area_points}"></polygon>'
        f'<polyline class="chart-line" fill="none" stroke="{line_color}" stroke-width="3" '
        f'points="{" ".join(points)}"></polyline>'
        f'<circle class="chart-endpoint" cx="{project_x(len(values) - 1):.2f}" '
        f'cy="{project_y(values[-1]):.2f}" r="4.5" fill="{line_color}"></circle>'
        '</svg>'
    )

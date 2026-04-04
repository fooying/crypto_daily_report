from __future__ import annotations

import html
from typing import Any, List


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

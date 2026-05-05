from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the CodePrism benchmark suite as a static SVG chart."
    )
    parser.add_argument(
        "suite_json",
        nargs="?",
        default=".codeprism/benchmarks/suite.json",
        help="Path to a codeprism benchmark-suite JSON report.",
    )
    parser.add_argument(
        "--out",
        default="docs/assets/benchmark-snapshot.svg",
        help="Output SVG path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the output SVG is missing or differs from the rendered chart.",
    )
    args = parser.parse_args()

    suite_path = Path(args.suite_json)
    out_path = Path(args.out)
    payload = json.loads(suite_path.read_text(encoding="utf-8"))
    svg = render_svg(payload)
    if args.check:
        return _check_svg(out_path, svg, suite_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
    print(f"Wrote benchmark chart {out_path}")
    return 0


def _check_svg(out_path: Path, expected_svg: str, suite_path: Path) -> int:
    if not out_path.exists():
        print(f"Benchmark chart is missing: {out_path}", file=sys.stderr)
        print(_regenerate_hint(suite_path, out_path), file=sys.stderr)
        return 1
    actual_svg = out_path.read_text(encoding="utf-8")
    if _normalize_newlines(actual_svg) != _normalize_newlines(expected_svg):
        print(f"Benchmark chart is stale: {out_path}", file=sys.stderr)
        print(_regenerate_hint(suite_path, out_path), file=sys.stderr)
        return 1
    print(f"Benchmark chart is current: {out_path}")
    return 0


def render_svg(payload: dict[str, Any]) -> str:
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("benchmark suite JSON must contain a non-empty fixtures list")

    rows = [_fixture_row(fixture) for fixture in fixtures]
    source_total = sum(row["source_tokens"] for row in rows)
    slice_total = sum(row["slice_tokens"] for row in rows)
    file_total = sum(row["files"] for row in rows)
    fixture_count = len(rows)
    avg_saving = float(
        payload.get("summary", {}).get(
            "average_source_to_slice_saved_percent",
            sum(row["slice_saving"] for row in rows) / fixture_count,
        )
    )
    total_reduction = _percent_saved(source_total, slice_total)

    width = 1200
    top = 260
    row_gap = 54
    height = top + row_gap * len(rows) + 150
    bar_x = 355
    bar_width = 610
    max_source = max(row["source_tokens"] for row in rows)

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            'fill="none" xmlns="http://www.w3.org/2000/svg" role="img" '
            'aria-labelledby="title desc">'
        ),
        "<title id=\"title\">CodePrism Benchmark Snapshot</title>",
        (
            "<desc id=\"desc\">A local-first benchmark chart showing estimated "
            "source-to-slice token reductions across CodePrism fixtures.</desc>"
        ),
        "<defs>",
        (
            '<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#071216"/>'
            '<stop offset="1" stop-color="#101827"/>'
            "</linearGradient>"
        ),
        (
            '<linearGradient id="barSlice" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#42F5B3"/>'
            '<stop offset="1" stop-color="#5AB8FF"/>'
            "</linearGradient>"
        ),
        (
            '<linearGradient id="barContext" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="#FFD166"/>'
            '<stop offset="1" stop-color="#FF5CA8"/>'
            "</linearGradient>"
        ),
        (
            '<pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">'
            '<path d="M48 0H0V48" stroke="#203748" stroke-width="1" opacity="0.35"/>'
            "</pattern>"
        ),
        (
            '<pattern id="scan" width="8" height="8" patternUnits="userSpaceOnUse">'
            '<path d="M0 7H8" stroke="#FFFFFF" stroke-width="1" opacity="0.035"/>'
            "</pattern>"
        ),
        "</defs>",
        f'<rect width="{width}" height="{height}" rx="28" fill="url(#panel)"/>',
        f'<rect width="{width}" height="{height}" rx="28" fill="url(#grid)"/>',
        f'<rect width="{width}" height="{height}" rx="28" fill="url(#scan)"/>',
        '<rect x="34" y="34" width="1132" height="164" rx="20" fill="#0C1720" '
        'stroke="#28445A"/>',
        _text(62, 78, "CODEPRISM BENCHMARK SNAPSHOT", 18, "#42F5B3", weight=700),
        _text(
            62,
            124,
            "Source to focused slices",
            35,
            "#E9F4FF",
            weight=800,
        ),
        _text(
            64,
            163,
            "Fixture data is reproducible and local. Token counts are estimates.",
            20,
            "#9BB0C8",
        ),
        _metric_card(640, 65, "AVG SOURCE -> SLICE", f"{avg_saving:.2f}%", "#42F5B3"),
        _metric_card(815, 65, "TOTAL SOURCE -> SLICE", f"{total_reduction:.2f}%", "#5AB8FF"),
        _metric_card(990, 65, "FIXTURES / FILES", f"{fixture_count} / {file_total}", "#FFD166"),
        _text(66, 235, "Fixture", 15, "#9BB0C8", weight=700),
        _text(bar_x, 235, "Estimated tokens by fixture", 15, "#9BB0C8", weight=700),
        _text(1002, 235, "Saved", 15, "#9BB0C8", weight=700),
        _text(1088, 235, "Pack", 15, "#9BB0C8", weight=700),
    ]

    for index, row in enumerate(rows):
        y = top + index * row_gap
        parts.extend(_row_svg(row, y, bar_x, bar_width, max_source))

    legend_y = height - 85
    parts.extend(
        [
            '<rect x="62" y="{0}" width="1076" height="46" rx="14" fill="#0A151D" '
            'stroke="#243B4D"/>'.format(legend_y),
            _legend_dot(90, legend_y + 23, "#5AB8FF", "estimated source tokens"),
            _legend_dot(330, legend_y + 23, "#42F5B3", "focused slice tokens"),
            _legend_dot(555, legend_y + 23, "#FF5CA8", "source-to-context pack saving"),
            _text(
                795,
                legend_y + 30,
                "Regenerate: python scripts/render_benchmark_chart.py",
                14,
                "#9BB0C8",
            ),
        ]
    )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _fixture_row(fixture: Any) -> dict[str, Any]:
    if not isinstance(fixture, dict):
        raise ValueError("fixture entries must be objects")
    return {
        "name": str(fixture.get("name", "Unnamed fixture")),
        "files": int(fixture.get("files_seen", 0)),
        "source_tokens": int(fixture.get("source_estimated_tokens", 0)),
        "slice_tokens": int(fixture.get("slice_estimated_tokens", 0)),
        "slice_saving": float(fixture.get("source_to_slice_saved_percent", 0.0)),
        "context_saving": float(fixture.get("source_to_context_saved_percent", 0.0)),
    }


def _row_svg(
    row: dict[str, Any],
    y: int,
    bar_x: int,
    bar_width: int,
    max_source: int,
) -> list[str]:
    source_width = max(1, round(bar_width * row["source_tokens"] / max_source))
    slice_width = max(1, round(bar_width * row["slice_tokens"] / max_source))
    context_marker_x = bar_x + round(bar_width * row["context_saving"] / 100)
    label = _short_label(row["name"])
    return [
        f'<rect x="52" y="{y - 25}" width="1096" height="40" rx="10" '
        'fill="#0A151D" opacity="0.68"/>',
        _text(66, y, label, 16, "#E9F4FF", weight=700),
        _text(258, y, f'{row["files"]} files', 13, "#8298B0"),
        f'<rect x="{bar_x}" y="{y - 14}" width="{source_width}" height="12" rx="6" '
        'fill="#254B63"/>',
        f'<rect x="{bar_x}" y="{y + 3}" width="{slice_width}" height="12" rx="6" '
        'fill="url(#barSlice)"/>',
        f'<line x1="{context_marker_x}" y1="{y - 19}" x2="{context_marker_x}" '
        f'y2="{y + 21}" stroke="#FF5CA8" stroke-width="2"/>',
        f'<circle cx="{context_marker_x}" cy="{y + 22}" r="4" fill="#FF5CA8"/>',
        _text(bar_x + bar_width + 24, y + 2, f'{row["slice_saving"]:.2f}%', 16, "#42F5B3"),
        _text(bar_x + bar_width + 112, y + 2, f'{row["context_saving"]:.2f}%', 16, "#FFD166"),
        _text(bar_x + source_width + 8, y - 5, _format_tokens(row["source_tokens"]), 12, "#9BB0C8"),
        _text(bar_x + slice_width + 8, y + 13, _format_tokens(row["slice_tokens"]), 12, "#BFE9FF"),
    ]


def _metric_card(x: int, y: int, label: str, value: str, color: str) -> str:
    return "\n".join(
        [
            f'<rect x="{x}" y="{y}" width="150" height="92" rx="16" '
            'fill="#111F2A" stroke="#28445A"/>',
            _text(x + 16, y + 32, label, 11, "#9BB0C8", weight=700),
            _text(x + 16, y + 68, value, 28, color, weight=800),
        ]
    )


def _legend_dot(x: int, y: int, color: str, label: str) -> str:
    return (
        f'<circle cx="{x}" cy="{y}" r="6" fill="{color}"/>'
        + _text(x + 16, y + 5, label, 14, "#B7C7DA")
    )


def _text(
    x: int,
    y: int,
    text: str,
    size: int,
    color: str,
    *,
    weight: int = 500,
) -> str:
    return (
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
        'font-family="Inter, Segoe UI, Arial, sans-serif" '
        f'font-weight="{weight}">{escape(text)}</text>'
    )


def _format_tokens(value: int) -> str:
    if value >= 1000:
        return f"{value / 1000:.1f}K"
    return str(value)


def _short_label(value: str) -> str:
    return value if len(value) <= 23 else value[:20].rstrip() + "..."


def _percent_saved(source_tokens: int, output_tokens: int) -> float:
    if source_tokens <= 0:
        return 0.0
    return max(0.0, min(100.0, (source_tokens - output_tokens) / source_tokens * 100))


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _regenerate_hint(suite_path: Path, out_path: Path) -> str:
    return f"Regenerate with: python scripts/render_benchmark_chart.py {suite_path} --out {out_path}"


if __name__ == "__main__":
    raise SystemExit(main())

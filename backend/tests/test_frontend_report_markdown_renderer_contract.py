from __future__ import annotations

from pathlib import Path


RENDERER_PATH = Path("frontend/src/app/components/genui/ReportContentRenderer.tsx")


def test_report_content_renderer_handles_markdown_headings_and_lists() -> None:
    source = RENDERER_PATH.read_text(encoding="utf-8")

    assert "renderMarkdownParagraph" in source
    assert "headingMatch" in source
    assert "bulletItems" in source
    assert "numberedItems" in source
    assert "<h2" in source
    assert "<h3" in source
    assert "<ul" in source
    assert "<ol" in source
    assert "# {보고서 제목}" not in source

from __future__ import annotations

from pathlib import Path


RENDERER_PATH = Path("frontend/src/app/components/genui/ReportContentRenderer.tsx")
MARKDOWN_RENDERER_PATH = Path("frontend/src/app/components/genui/MarkdownReportRenderer.tsx")
MARKDOWN_PARSER_PATH = Path("frontend/src/app/components/genui/markdownReportParser.ts")


def test_report_text_content_uses_line_oriented_markdown_flow_renderer() -> None:
    renderer_source = RENDERER_PATH.read_text(encoding="utf-8")
    markdown_source = MARKDOWN_RENDERER_PATH.read_text(encoding="utf-8")
    parser_source = MARKDOWN_PARSER_PATH.read_text(encoding="utf-8")

    assert "renderMarkdownReportContent" in renderer_source
    assert "renderMarkdownReportContent(block.content" in renderer_source
    assert ".split(/\\n{2,}/)" not in renderer_source
    assert "renderMarkdownParagraph" not in renderer_source

    assert "export type MarkdownFlowBlock" in parser_source
    assert "splitMarkdownFlowBlocks" in markdown_source
    assert "isMarkdownBlockStart" in parser_source


def test_markdown_headings_do_not_depend_on_blank_line_paragraph_splitting() -> None:
    markdown_source = MARKDOWN_RENDERER_PATH.read_text(encoding="utf-8")
    parser_source = MARKDOWN_PARSER_PATH.read_text(encoding="utf-8")

    assert "data-markdown-heading-level={block.level}" in markdown_source
    assert "block.kind === \"heading\"" in markdown_source
    assert "headingMatch" in parser_source
    assert "line.match(/^(#{1,3})\\s+(.+)$/)" in parser_source
    assert ".split(/\\n{2,}/)" not in parser_source


def test_markdown_flow_keeps_code_fences_outside_text_block_parsing() -> None:
    renderer_source = RENDERER_PATH.read_text(encoding="utf-8")
    markdown_source = MARKDOWN_RENDERER_PATH.read_text(encoding="utf-8")
    parser_source = MARKDOWN_PARSER_PATH.read_text(encoding="utf-8")

    assert "parseTextBlocks" in renderer_source
    assert "fenceMatch" in renderer_source
    assert "<CodeBlock" in renderer_source
    assert "```" not in markdown_source
    assert "```" not in parser_source

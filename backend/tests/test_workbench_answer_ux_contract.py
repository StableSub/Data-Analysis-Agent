from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSISTANT_PATH = PROJECT_ROOT / "frontend/src/app/components/genui/AssistantReportMessage.tsx"
WORKBENCH_PATH = PROJECT_ROOT / "frontend/src/app/pages/Workbench.tsx"


def _read(path: Path) -> str:
    return path.resolve().read_text(encoding="utf-8")


def test_final_assistant_answers_use_canvas_layout_without_height_cap() -> None:
    assistant_source = _read(ASSISTANT_PATH)
    workbench_source = _read(WORKBENCH_PATH)

    assert 'layout?: "card" | "canvas";' in assistant_source
    assert 'layout = "card"' in assistant_source
    assert 'data-answer-layout={layout}' in assistant_source
    assert 'layout === "canvas"' in assistant_source
    assert "max-w-[860px]" in assistant_source
    assert "max-w-none" in assistant_source

    assert 'layout="canvas"' in workbench_source
    assert "maxBodyHeight={null}" in workbench_source
    ai_answer_index = workbench_source.index('title="AI 답변"')
    ai_answer_block = workbench_source[ai_answer_index : ai_answer_index + 520]
    assert 'layout="canvas"' in ai_answer_block
    assert "maxBodyHeight={null}" in ai_answer_block


def test_analysis_answer_states_use_canvas_layout_without_height_cap() -> None:
    assistant_source = _read(ASSISTANT_PATH)
    workbench_source = _read(WORKBENCH_PATH)

    assert 'layout = "card"' in assistant_source
    assert 'const isCanvas = layout === "canvas";' in assistant_source
    assert 'data-answer-layout={layout}' in assistant_source
    assert '"max-w-none rounded-lg shadow-sm"' in assistant_source

    running_index = workbench_source.index("/* RUNNING */")
    running_block = workbench_source[running_index : running_index + 720]
    assert 'layout="canvas"' in running_block
    assert "maxBodyHeight={null}" in running_block

    needs_user_index = workbench_source.index("/* NEEDS-USER */")
    needs_user_block = workbench_source[needs_user_index : needs_user_index + 1040]
    assert 'layout="canvas"' in needs_user_block
    assert "maxBodyHeight={null}" in needs_user_block

    assert 'variant="error"' in workbench_source
    error_index = workbench_source.index('variant="error"')
    next_error_block = workbench_source[error_index : error_index + 420]
    assert 'layout="canvas"' in next_error_block
    assert "maxBodyHeight={null}" in next_error_block


def test_non_answer_pre_eda_surface_keeps_default_card_layout() -> None:
    assistant_source = _read(ASSISTANT_PATH)
    workbench_source = _read(WORKBENCH_PATH)

    assert 'layout = "card"' in assistant_source

    assert 'title="Pre-EDA Summary"' in workbench_source
    pre_eda_index = workbench_source.index('title="Pre-EDA Summary"')
    pre_eda_block = workbench_source[pre_eda_index : pre_eda_index + 420]
    assert 'layout="canvas"' not in pre_eda_block

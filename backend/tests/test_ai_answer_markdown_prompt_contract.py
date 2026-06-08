from __future__ import annotations

from backend.app.orchestration.ai import PROMPTS


def test_final_answer_prompts_request_markdown_rich_structure() -> None:
    general_prompt = PROMPTS.load_prompt("general.system")
    data_prompt = PROMPTS.load_prompt("data_qa.system")

    for prompt in (general_prompt, data_prompt):
        assert "Markdown" in prompt
        assert "##" in prompt
        assert "bullet" in prompt or "목록" in prompt
        assert "table" in prompt or "표" in prompt

    assert "근거 밖의 숫자/컬럼/결론을 만들지 마라" in data_prompt
    assert "evidence_package.analysis_metrics" in data_prompt
    assert "Markdown 표" in data_prompt

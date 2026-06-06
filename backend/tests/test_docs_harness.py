from pathlib import Path
import re

from backend.app.main import app
from fastapi.routing import APIRoute


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
ARCHITECTURE_DIR = DOCS_DIR / "architecture"
API_SPEC = DOCS_DIR / "system" / "api-spec.md"
EVALUATION_DOCS_DIR = REPO_ROOT / "evaluation" / "docs"
MOLDSET_INDEX_DOC = EVALUATION_DOCS_DIR / "moldset-questions.md"
MOLDSET_ANALYSIS_DOC = EVALUATION_DOCS_DIR / "moldset-analysis-questions.md"
MOLDSET_REPORT_DOC = EVALUATION_DOCS_DIR / "moldset-report-questions.md"
ACTIVE_CONTEXT_FILES = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "backend" / "app" / "orchestration" / "AGENTS.md",
    REPO_ROOT / "backend" / "app" / "modules" / "AGENTS.md",
    REPO_ROOT / "frontend" / "src" / "app" / "AGENTS.md",
    REPO_ROOT / "docs" / "architecture" / "AGENTS.md",
    REPO_ROOT / "docs" / "README.md",
)


MARKDOWN_LINK_RE: re.Pattern[str] = re.compile(
    r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)",
)
WIKI_LINK_RE: re.Pattern[str] = re.compile(r"\[\[([^\]|#]+)")
CODE_PATH_RE: re.Pattern[str] = re.compile(r"`((?:backend|frontend|docs)/[^`]+?)`")


STALE_REFERENCES = (
    "docs/architecture/ai-agent/overview.md",
    "docs/architecture/ai-agent/execution-flow.md",
    "docs/architecture/system/flow-overview.md",
    "docs/architecture/system/architecture.md",
    "docs/architecture/components/planner.md",
    "architecture/ai-agent/overview",
    "architecture/ai-agent/execution-flow",
    "architecture/system/flow-overview",
    "architecture/system/architecture",
    "architecture/components/planner",
    "components/planner.md",
)

PLACEHOLDER_PHRASES = (
    "TODO",
    "TBD",
    "작성 예정",
    "추후 작성",
    "placeholder",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _first_groups(pattern: re.Pattern[str], content: str) -> list[str]:
    return [match.group(1) for match in pattern.finditer(content)]


def _markdown_files() -> list[Path]:
    return sorted(DOCS_DIR.rglob("*.md"))


def test_markdown_relative_links_point_to_existing_files() -> None:
    missing: list[str] = []

    for path in _markdown_files():
        content = _read(path)
        for raw_target in _first_groups(MARKDOWN_LINK_RE, content):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith("<"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{path.relative_to(REPO_ROOT)} -> {raw_target}")

    assert missing == []


def test_obsidian_wiki_links_point_to_existing_docs() -> None:
    missing: list[str] = []

    for path in _markdown_files():
        content = _read(path)
        for raw_target in _first_groups(WIKI_LINK_RE, content):
            target = raw_target.strip()
            candidates = [
                REPO_ROOT / f"{target}.md",
                DOCS_DIR / f"{target}.md",
                ARCHITECTURE_DIR / f"{target}.md",
            ]
            if not any(candidate.exists() for candidate in candidates):
                missing.append(f"{path.relative_to(REPO_ROOT)} -> [[{target}]]")

    assert missing == []


def test_docs_do_not_reference_deleted_architecture_files() -> None:
    offenders: list[str] = []

    for path in _markdown_files():
        content = _read(path)
        for stale_reference in STALE_REFERENCES:
            if stale_reference in content:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {stale_reference}")

    assert offenders == []


def test_architecture_docs_do_not_contain_placeholder_phrases() -> None:
    offenders: list[str] = []

    for path in sorted(ARCHITECTURE_DIR.rglob("*.md")):
        content = _read(path)
        for phrase in PLACEHOLDER_PHRASES:
            if phrase in content:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {phrase}")

    assert offenders == []


def test_architecture_code_path_references_exist() -> None:
    missing: list[str] = []

    for path in sorted(ARCHITECTURE_DIR.rglob("*.md")):
        content = _read(path)
        for raw_ref in _first_groups(CODE_PATH_RE, content):
            ref = raw_ref.split("::", 1)[0].rstrip(".,:")
            if "*" in ref:
                continue
            if not (REPO_ROOT / ref).exists():
                missing.append(f"{path.relative_to(REPO_ROOT)} -> {ref}")

    assert missing == []


def test_active_context_code_path_references_exist() -> None:
    missing: list[str] = []

    for path in ACTIVE_CONTEXT_FILES:
        content = _read(path)
        for raw_ref in _first_groups(CODE_PATH_RE, content):
            ref = raw_ref.split("::", 1)[0].rstrip(".,:")
            if "*" in ref:
                continue
            if not (REPO_ROOT / ref).exists():
                missing.append(f"{path.relative_to(REPO_ROOT)} -> {ref}")

    assert missing == []


def test_api_spec_lists_all_public_fastapi_routes() -> None:
    content = _read(API_SPEC)
    missing: list[str] = []

    for route in app.routes:
        match route:
            case APIRoute() as api_route:
                if api_route.path in {
                    "/openapi.json",
                    "/docs",
                    "/docs/oauth2-redirect",
                    "/redoc",
                }:
                    continue
                for method in sorted(api_route.methods - {"HEAD", "OPTIONS"}):
                    route_ref = f"{method} {api_route.path}"
                    if route_ref not in content:
                        missing.append(route_ref)
            case _:
                continue

    assert missing == []


def test_moldset_defect_reason_primary_questions_include_defect_filter() -> None:
    content = _read(MOLDSET_ANALYSIS_DOC)
    top_questions = content.split("## 우선 테스트 질문 TOP 5", maxsplit=1)[1].split(
        "## 평가 체크리스트",
        maxsplit=1,
    )[0]

    assert "- 불량 사유별 건수를 알려줘." not in content
    assert (
        "PassOrFail=1인 불량 데이터만 대상으로 불량 사유별 건수를 알려줘."
        in content
    )
    assert (
        "PassOrFail=1인 불량 데이터만 대상으로 불량 사유별 건수를 알려줘."
        in top_questions
    )


def test_moldset_index_records_question_clarity_guardrails() -> None:
    content = _read(MOLDSET_INDEX_DOC)

    assert "## 질문 명확성 판단 기준" in content
    assert "불량 사유별 건수" in content
    assert "PassOrFail=1" in content
    assert "한 질문에서 분석, 여러 차트, 레포트를 동시에 요구하지 않는다." in content
    assert "원인을 확정" in content


def test_moldset_report_questions_bound_broad_process_variable_requests() -> None:
    content = _read(MOLDSET_REPORT_DOC)
    ambiguous_questions = (
        "양품과 불량의 공정 변수 차이를 비교해서, 불량과 관련 가능성이 높은 변수 후보를 리포트로 정리해줘.",
        "불량 사유별로 공정 조건이 어떻게 다른지 분석하고, 사유별 특징을 리포트로 정리해줘.",
        "주요 공정 변수의 안정성을 평가하고, 변동성이 큰 항목과 관리가 필요한 항목을 리포트로 정리해줘.",
    )

    for question in ambiguous_questions:
        assert question not in content

    assert "주요 수치형 공정 변수" in content


def test_rag_guideline_docs_record_embedding_fallback_contract() -> None:
    content = _read(ARCHITECTURE_DIR / "modules" / "rag-and-guidelines.md")

    assert "sentence-transformers" in content
    assert "guideline_embedding_error" in content
    assert "raw_text_fallback" in content
    assert "chat SSE" in content


def test_analysis_docs_record_planner_validator_contract() -> None:
    content = _read(ARCHITECTURE_DIR / "modules" / "analysis.md")

    assert "planner-validator contract" in content
    assert "datetime_part" in content
    assert "`date` -> `day`" in content
    assert "PassOrFail" in content
    assert "`not_null`" in content
    assert "JSON-only codegen" in content
    assert "PassOrFail=1인 불량 데이터" in content
    assert "보호/식별 컬럼" in content

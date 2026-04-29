from pathlib import Path
import re

from backend.app.main import app


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
ARCHITECTURE_DIR = DOCS_DIR / "architecture"
API_SPEC = DOCS_DIR / "system" / "api-spec.md"
ACTIVE_CONTEXT_FILES = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "backend" / "app" / "orchestration" / "AGENTS.md",
    REPO_ROOT / "backend" / "app" / "modules" / "AGENTS.md",
    REPO_ROOT / "frontend" / "src" / "app" / "AGENTS.md",
    REPO_ROOT / "docs" / "architecture" / "AGENTS.md",
    REPO_ROOT / "docs" / "README.md",
)


MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)]+)\)")
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)")
CODE_PATH_RE = re.compile(r"`((?:backend|frontend|docs)/[^`]+?)`")


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


def _markdown_files() -> list[Path]:
    return sorted(DOCS_DIR.rglob("*.md"))


def test_markdown_relative_links_point_to_existing_files() -> None:
    missing: list[str] = []

    for path in _markdown_files():
        content = _read(path)
        for raw_target in MARKDOWN_LINK_RE.findall(content):
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
        for raw_target in WIKI_LINK_RE.findall(content):
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
        for raw_ref in CODE_PATH_RE.findall(content):
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
        for raw_ref in CODE_PATH_RE.findall(content):
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
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        if path in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}:
            continue
        for method in sorted(methods - {"HEAD", "OPTIONS"}):
            route_ref = f"{method} {path}"
            if route_ref not in content:
                missing.append(route_ref)

    assert missing == []

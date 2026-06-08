from __future__ import annotations

from pathlib import Path


RENDERER_PATH = Path("frontend/src/app/components/genui/ReportContentRenderer.tsx")
SESSION_STORE_PATH = Path("frontend/src/app/hooks/useWorkbenchSessionStore.ts")
WORKBENCH_PATH = Path("frontend/src/app/pages/Workbench.tsx")
API_PATH = Path("frontend/src/lib/api.ts")



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


def test_report_content_renderer_supports_tables_quotes_and_emphasis() -> None:
    source = RENDERER_PATH.read_text(encoding="utf-8")

    assert "renderMarkdownTable" in source
    assert "parseMarkdownTable" in source
    assert "<table" in source
    assert "<thead" in source
    assert "<tbody" in source
    assert "renderMarkdownBlockquote" in source
    assert "<blockquote" in source
    assert "<strong" in source
    assert "<em" in source
    assert "overflow-wrap:anywhere" in source


def test_workbench_sessions_use_canonical_backend_identity_for_merge_and_delete() -> None:
    store_source = SESSION_STORE_PATH.read_text(encoding="utf-8")
    workbench_source = WORKBENCH_PATH.read_text(encoding="utf-8")

    assert "getCanonicalBackendSessionId" in store_source
    assert "item.backendSessionId ?? item.context.backendSessionId ?? null" in store_source
    assert "syncContextBackendSessionId(context, backendSessionId)" in store_source
    assert "getSessionDeletionIds" in store_source
    assert "getCanonicalBackendSessionId(item) === backendSessionId" in store_source
    assert "dedupeSessionsByCanonicalBackendId" in store_source
    assert "dedupeSessionsByCanonicalBackendId(" in store_source

    assert "const mergedExisting = sessions.flatMap" in store_source
    assert "if (existingBackendIds.has(backendSessionId))" in store_source
    assert "return [];" in store_source
    assert "const serverSession = serverById.get(backendSessionId)" in store_source

    assert "const backendSessionId = getCanonicalBackendSessionId(targetSession)" in workbench_source
    assert "const history = await getChatHistory(backendSessionId)" in workbench_source
    assert "await deleteChatSession(backendSessionId)" in workbench_source
    assert "const deletionIds = getSessionDeletionIds(sessions, targetSessionId)" in workbench_source
    assert "const wasActive = activeSessionId !== null && deletionIds.has(activeSessionId)" in workbench_source
    assert "!deletionIds.has(item.id)" in workbench_source


def test_workbench_session_select_blocks_autosave_until_restore_completes() -> None:
    workbench_source = WORKBENCH_PATH.read_text(encoding="utf-8")

    assert "const [restoringSessionId, setRestoringSessionId]" in workbench_source
    assert "beginSessionRestore(targetSessionId)" in workbench_source
    assert "finishSessionRestore(targetSessionId)" in workbench_source
    assert "restoringSessionId !== null" in workbench_source
    assert "[activeSessionId, state, restoringSessionId" in workbench_source
    assert "[activeSessionId, sessionId, restoringSessionId" in workbench_source


def test_frontend_api_default_matches_dev_backend_host() -> None:
    api_source = API_PATH.read_text(encoding="utf-8")

    assert '"http://127.0.0.1:8000"' in api_source
    assert '"http://localhost:8000"' not in api_source

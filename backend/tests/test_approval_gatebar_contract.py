from pathlib import Path


def test_gatebar_surfaces_approval_details_before_decision_buttons() -> None:
    project_root = Path(__file__).resolve().parents[2]
    gatebar_source = (
        project_root / "frontend/src/app/components/genui/GateBar.tsx"
    ).read_text(encoding="utf-8")
    workbench_source = (
        project_root / "frontend/src/app/pages/Workbench.tsx"
    ).read_text(encoding="utf-8")

    for prop_name in (
        "approvalTitle",
        "approvalDescription",
        "approvalItems",
        "approvalPreview",
    ):
        assert prop_name in gatebar_source

    assert "승인 대상" in gatebar_source
    assert "normalizedApprovalItems.map" in gatebar_source
    assert "approvalPreview" in gatebar_source

    assert "buildPendingApprovalPreview" in workbench_source
    assert "approvalTitle={pendingApproval?.title}" in workbench_source
    assert "approvalDescription={pendingApproval?.summary}" in workbench_source
    assert "approvalItems={pendingApprovalChanges}" in workbench_source
    assert "approvalPreview={pendingApprovalPreview}" in workbench_source


def test_report_approval_summary_includes_actual_draft_content() -> None:
    project_root = Path(__file__).resolve().parents[2]
    workbench_source = (
        project_root / "frontend/src/app/pages/Workbench.tsx"
    ).read_text(encoding="utf-8")

    assert "compactPendingText" in workbench_source
    assert "pendingApproval.draft" in workbench_source
    assert "초안 내용:" in workbench_source

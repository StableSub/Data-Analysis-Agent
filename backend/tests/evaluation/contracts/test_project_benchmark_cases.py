from __future__ import annotations

from eval_cases import CASES_DIR, load_all_cases, load_case_file


REQUIRED_CASE_KEYS = {
    "case_id",
    "priority",
    "dataset",
    "question",
    "expected_route",
    "expected_answer_status",
}


def test_benchmark_case_files_exist() -> None:
    assert (CASES_DIR / "p0_moldset_analysis_cases.jsonl").exists()
    assert (CASES_DIR / "p0_moldset_preprocess_cases.jsonl").exists()
    assert (CASES_DIR / "p1_dataset_quality_cases.jsonl").exists()


def test_case_ids_are_unique_and_have_required_contract_keys() -> None:
    cases = load_all_cases()
    case_ids = [case["case_id"] for case in cases]

    assert len(case_ids) == len(set(case_ids))
    assert cases
    for case in cases:
        missing = REQUIRED_CASE_KEYS - set(case)
        assert not missing, {"case_id": case.get("case_id"), "missing": sorted(missing)}
        assert case["priority"] in {"P0", "P1"}
        assert case["expected_route"] in {"analysis", "preprocess", "rag", "general"}
        assert case["expected_answer_status"] in {
            "answerable",
            "limited",
            "unanswerable",
            "approval_required",
        }


def test_p0_cases_cover_analysis_and_preprocess_paths() -> None:
    p0_analysis = load_case_file("p0_moldset_analysis_cases.jsonl")
    p0_preprocess = load_case_file("p0_moldset_preprocess_cases.jsonl")

    assert {case["expected_route"] for case in p0_analysis} == {"analysis"}
    assert {case["expected_route"] for case in p0_preprocess} == {"preprocess"}
    assert {case["priority"] for case in [*p0_analysis, *p0_preprocess]} == {"P0"}


def test_p1_cases_include_unanswerable_and_scaled_detection() -> None:
    cases = load_case_file("p1_dataset_quality_cases.jsonl")

    assert any(case["expected_answer_status"] == "unanswerable" for case in cases)
    assert any(case.get("expected_scaled_like") is True for case in cases)
    assert {case["priority"] for case in cases} == {"P1"}

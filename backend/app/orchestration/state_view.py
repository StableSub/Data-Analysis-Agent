from __future__ import annotations

from typing import Any, Dict


def _as_dict(value: Any) -> Dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    return None


def build_merged_context(state: Dict[str, Any]) -> Dict[str, Any]:
    merged_context: Dict[str, Any] = {"applied_steps": []}

    request_context = state.get("request_context")
    if isinstance(request_context, str) and request_context.strip():
        merged_context["request_context"] = request_context.strip()

    handoff = state.get("handoff")
    if isinstance(handoff, dict):
        merged_context["request_flags"] = {
            "ask_analysis": bool(handoff.get("ask_analysis", False)),
            "ask_preprocess": bool(handoff.get("ask_preprocess", False)),
            "ask_visualization": bool(handoff.get("ask_visualization", False)),
            "ask_report": bool(handoff.get("ask_report", False)),
            "ask_guideline": bool(handoff.get("ask_guideline", False)),
        }

    preprocess_result = state.get("preprocess_result")
    if isinstance(preprocess_result, dict):
        merged_context["preprocess_result"] = preprocess_result
        if preprocess_result.get("status") == "applied":
            merged_context["applied_steps"].append("preprocess")

    rag_result = state.get("rag_result")
    if isinstance(rag_result, dict):
        merged_context["rag_result"] = rag_result
        if bool(rag_result.get("has_evidence", False)):
            merged_context["applied_steps"].append("rag")

    guideline_index_status = state.get("guideline_index_status")
    if isinstance(guideline_index_status, dict):
        merged_context["guideline_index_status"] = guideline_index_status

    guideline_result = state.get("guideline_result")
    if isinstance(guideline_result, dict):
        merged_context["guideline_result"] = guideline_result
        merged_context["guideline_context"] = {
            "active_source_id": state.get("active_guideline_source_id", ""),
            "status": guideline_result.get("status", ""),
            "retrieved_count": int(guideline_result.get("retrieved_count", 0) or 0),
            "has_evidence": bool(guideline_result.get("has_evidence", False)),
            "filename": guideline_result.get("filename", ""),
            "guideline_id": guideline_result.get("guideline_id", ""),
            "evidence_summary": guideline_result.get("evidence_summary", ""),
        }
        if bool(guideline_result.get("has_evidence", False)):
            merged_context["applied_steps"].append("guideline")

    insight = state.get("insight")
    if isinstance(insight, dict):
        merged_context["insight"] = insight
        summary = insight.get("summary")
        if isinstance(summary, str) and summary.strip():
            merged_context["applied_steps"].append("insight")

    analysis_plan = _as_dict(state.get("analysis_plan"))
    if analysis_plan is not None:
        merged_context["analysis_plan"] = analysis_plan

    analysis_result = _as_dict(state.get("analysis_result"))
    if analysis_result is not None:
        merged_context["analysis_result"] = analysis_result
        if analysis_result.get("execution_status") == "success":
            merged_context["applied_steps"].append("analysis")

    visualization_result = state.get("visualization_result")
    if isinstance(visualization_result, dict):
        merged_context["visualization_result"] = visualization_result
        if visualization_result.get("status") == "generated":
            merged_context["applied_steps"].append("visualization")

    return merged_context


def make_thought_step(*, phase: str, message: str, status: str = "completed") -> Dict[str, str]:
    return {"phase": phase, "message": message, "status": status}


def build_approval_wait_step(stage: str) -> Dict[str, str]:
    if stage == "visualization":
        return make_thought_step(
            phase="visualization_approval",
            message="시각화 계획 승인을 기다리는 중입니다.",
            status="active",
        )
    if stage == "report":
        return make_thought_step(
            phase="report_approval",
            message="리포트 초안 검토를 기다리는 중입니다.",
            status="active",
        )
    return make_thought_step(
        phase="preprocess_approval",
        message="전처리 계획 승인을 기다리는 중입니다.",
        status="active",
    )


def collect_thought_steps(state: Dict[str, Any]) -> list[Dict[str, str]]:
    steps: list[Dict[str, str]] = []

    handoff = state.get("handoff")
    if isinstance(handoff, dict):
        next_step = handoff.get("next_step")
        if next_step == "data_pipeline":
            steps.append(
                make_thought_step(
                    phase="intake",
                    message="데이터셋 기반 파이프라인으로 라우팅했습니다.",
                )
            )
        elif next_step == "dataset_qa":
            steps.append(
                make_thought_step(
                    phase="intake",
                    message="데이터셋 기반 질의응답 경로로 라우팅했습니다.",
                )
            )
        elif next_step == "general_question":
            steps.append(
                make_thought_step(
                    phase="intake",
                    message="일반 질의 경로로 라우팅했습니다.",
                )
            )

        if bool(handoff.get("ask_visualization", False)):
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="시각화 요청이 감지되어 시각화 경로를 준비했습니다.",
                )
            )
        if bool(handoff.get("ask_analysis", False)):
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="분석 요청이 감지되어 분석 단계를 준비했습니다.",
                )
            )
        if bool(handoff.get("ask_report", False)):
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="리포트 요청이 감지되어 리포트 경로를 준비했습니다.",
                )
            )
        if bool(handoff.get("ask_preprocess", False)):
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="전처리 요청이 감지되어 전처리 단계를 준비했습니다.",
                )
            )
        elif "ask_preprocess" in handoff:
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="전처리 요청이 없어 전처리 생략 경로를 준비했습니다.",
                )
            )

    decision = state.get("preprocess_decision")
    if isinstance(decision, dict):
        reason_summary = decision.get("reason_summary")
        if isinstance(reason_summary, str) and reason_summary.strip():
            steps.append(
                make_thought_step(
                    phase="preprocess_decision",
                    message=reason_summary.strip(),
                )
            )
        else:
            decision_step = decision.get("step")
            if decision_step == "run_preprocess":
                steps.append(
                    make_thought_step(
                        phase="preprocess_decision",
                        message="전처리가 필요하다고 판단했습니다.",
                    )
                )
            elif decision_step == "skip_preprocess":
                steps.append(
                    make_thought_step(
                        phase="preprocess_decision",
                        message="전처리를 생략해도 된다고 판단했습니다.",
                    )
                )

    plan = state.get("preprocess_plan")
    if isinstance(plan, dict):
        planner_comment = plan.get("planner_comment")
        if isinstance(planner_comment, str) and planner_comment.strip():
            steps.append(
                make_thought_step(
                    phase="preprocess_plan",
                    message=planner_comment.strip(),
                )
            )
        else:
            operations = plan.get("operations")
            if isinstance(operations, list) and operations:
                steps.append(
                    make_thought_step(
                        phase="preprocess_plan",
                        message=f"전처리 연산 {len(operations)}개를 계획했습니다.",
                    )
                )

    preprocess_result = state.get("preprocess_result")
    if isinstance(preprocess_result, dict):
        preprocess_summary = preprocess_result.get("summary")
        if isinstance(preprocess_summary, str) and preprocess_summary.strip():
            preprocess_status = "failed" if preprocess_result.get("status") == "failed" else "completed"
            steps.append(
                make_thought_step(
                    phase="preprocess_result",
                    message=preprocess_summary.strip(),
                    status=preprocess_status,
                )
            )

    analysis_result = _as_dict(state.get("analysis_result"))
    if analysis_result is not None:
        execution_status = analysis_result.get("execution_status")
        if execution_status == "success":
            summary = analysis_result.get("summary")
            if isinstance(summary, str) and summary.strip():
                steps.append(
                    make_thought_step(
                        phase="analysis",
                        message=summary.strip(),
                    )
                )
            else:
                steps.append(
                    make_thought_step(
                        phase="analysis",
                        message="분석 결과를 생성했습니다.",
                    )
                )
        elif execution_status == "fail":
            error_message = analysis_result.get("error_message")
            if isinstance(error_message, str) and error_message.strip():
                steps.append(
                    make_thought_step(
                        phase="analysis",
                        message=f"분석 단계에서 오류가 발생했습니다: {error_message.strip()}",
                        status="failed",
                    )
                )

    clarification_question = state.get("clarification_question")
    if isinstance(clarification_question, str) and clarification_question.strip():
        steps.append(
            make_thought_step(
                phase="analysis_clarification",
                message=clarification_question.strip(),
            )
        )

    rag_index_status = state.get("rag_index_status")
    if isinstance(rag_index_status, dict):
        index_status = rag_index_status.get("status")
        source_id = rag_index_status.get("source_id")
        source_text = source_id if isinstance(source_id, str) and source_id else "-"
        if index_status == "created":
            steps.append(
                make_thought_step(
                    phase="rag_index",
                    message=f"RAG 인덱스를 생성했습니다. (source_id={source_text})",
                )
            )
        elif index_status == "existing":
            steps.append(
                make_thought_step(
                    phase="rag_index",
                    message=f"기존 RAG 인덱스를 재사용합니다. (source_id={source_text})",
                )
            )
        elif index_status == "dataset_missing":
            steps.append(
                make_thought_step(
                    phase="rag_index",
                    message=f"RAG 인덱싱 대상 데이터셋을 찾지 못했습니다. (source_id={source_text})",
                    status="failed",
                )
            )
        elif index_status == "unsupported_format":
            steps.append(
                make_thought_step(
                    phase="rag_index",
                    message=f"현재 RAG는 해당 파일 형식을 지원하지 않습니다. (source_id={source_text})",
                    status="failed",
                )
            )

    rag_result = state.get("rag_result")
    if isinstance(rag_result, dict):
        if bool(rag_result.get("has_evidence", False)):
            retrieved_count = int(rag_result.get("retrieved_count", 0) or 0)
            source_id = rag_result.get("source_id")
            source_text = source_id if isinstance(source_id, str) and source_id else "-"
            steps.append(
                make_thought_step(
                    phase="rag_retrieval",
                    message=(
                        f"RAG 검색으로 관련 청크 {retrieved_count}개를 찾았습니다. "
                        f"(source_id={source_text})"
                    ),
                )
            )
        else:
            evidence_summary = rag_result.get("evidence_summary")
            if isinstance(evidence_summary, str) and evidence_summary.strip():
                steps.append(
                    make_thought_step(
                        phase="rag_retrieval",
                        message=evidence_summary.strip(),
                    )
                )

    insight = state.get("insight")
    if isinstance(insight, dict):
        insight_summary = insight.get("summary")
        if isinstance(insight_summary, str) and insight_summary.strip():
            steps.append(
                make_thought_step(
                    phase="insight",
                    message=insight_summary.strip(),
                )
            )

    guideline_result = state.get("guideline_result")
    if isinstance(guideline_result, dict):
        guideline_summary = guideline_result.get("evidence_summary")
        guideline_status = guideline_result.get("status")
        step_status = "failed" if guideline_status == "no_active_guideline" else "completed"
        if isinstance(guideline_summary, str) and guideline_summary.strip():
            steps.append(
                make_thought_step(
                    phase="guideline",
                    message=guideline_summary.strip(),
                    status=step_status,
                )
            )

    visualization_result = state.get("visualization_result")
    if isinstance(visualization_result, dict):
        viz_summary = visualization_result.get("summary")
        viz_status = visualization_result.get("status")
        if isinstance(viz_summary, str) and viz_summary.strip():
            steps.append(
                make_thought_step(
                    phase="visualization",
                    message=viz_summary.strip(),
                    status="failed" if viz_status == "unavailable" else "completed",
                )
            )

    merged_context = state.get("merged_context")
    if isinstance(merged_context, dict):
        applied_steps = merged_context.get("applied_steps")
        if isinstance(applied_steps, list):
            steps.append(
                make_thought_step(
                    phase="merge_context",
                    message=f"누적 컨텍스트를 병합했습니다. (steps={len(applied_steps)})",
                )
            )

    report_draft = state.get("report_draft")
    if isinstance(report_draft, dict):
        report_summary = report_draft.get("summary")
        if isinstance(report_summary, str) and report_summary.strip():
            revision_count = int(report_draft.get("revision_count", 0) or 0)
            steps.append(
                make_thought_step(
                    phase="report_draft",
                    message=(
                        "수정 요청을 반영해 리포트 초안을 다시 작성했습니다."
                        if revision_count > 0
                        else "리포트 초안을 작성했습니다."
                    ),
                )
            )

    report_result = state.get("report_result")
    if isinstance(report_result, dict):
        report_status = report_result.get("status")
        if report_status == "generated":
            steps.append(
                make_thought_step(
                    phase="report",
                    message="리포트 응답을 구성했습니다.",
                )
            )
        elif report_status == "failed":
            error = report_result.get("error")
            if isinstance(error, str) and error.strip():
                steps.append(
                    make_thought_step(
                        phase="report",
                        message=f"리포트 생성에 실패했습니다: {error.strip()}",
                        status="failed",
                    )
                )

    revision_request = state.get("revision_request")
    if isinstance(revision_request, dict) and revision_request.get("stage") == "report":
        instruction = revision_request.get("instruction")
        if isinstance(instruction, str) and instruction.strip():
            steps.append(
                make_thought_step(
                    phase="report_revision",
                    message=f"리포트 수정 요청을 반영합니다: {instruction.strip()}",
                )
            )

    data_qa_result = state.get("data_qa_result")
    if isinstance(data_qa_result, dict):
        content = data_qa_result.get("content")
        if isinstance(content, str) and content.strip():
            steps.append(
                make_thought_step(
                    phase="data_qa",
                    message="데이터 QA 응답을 구성했습니다.",
                )
            )

    output = state.get("output")
    if not isinstance(output, dict):
        return steps
    output_type = output.get("type")
    if isinstance(output_type, str) and output_type.strip():
        steps.append(
            make_thought_step(
                phase="output",
                message=f"{output_type} 응답을 구성하고 있습니다.",
            )
        )
    return steps

from __future__ import annotations

from typing import Any, Dict

_DETAIL_MESSAGE_LIMIT = 180
_DISPLAY_COPY = {
    "analysis_active": "질문을 이해하고 있습니다.",
    "intake_dataset_selected": "질문과 데이터를 확인했습니다.",
    "planning_analysis": "분석 경로를 선택했습니다.",
    "planning_fallback_rag": "관련 정보를 함께 확인합니다.",
    "planning_general": "질문에 바로 답변하고 있습니다.",
    "planning_dataset": "데이터 기반 흐름을 준비했습니다.",
    "intent_visualization": "시각화를 준비하고 있습니다.",
    "intent_analysis": "계산을 준비하고 있습니다.",
    "intent_report": "리포트를 준비하고 있습니다.",
    "intent_preprocess": "데이터를 준비하고 있습니다.",
    "intent_skip_preprocess": "바로 계산할 수 있는지 확인했습니다.",
    "preprocess_needed": "데이터 준비가 필요합니다.",
    "preprocess_skipped": "추가 데이터 준비 없이 진행합니다.",
    "preprocess_plan": "데이터 준비 방법을 정리했습니다.",
    "preprocess_result": "데이터 준비를 마쳤습니다.",
    "analysis_success": "계산을 마쳤습니다.",
    "analysis_failed": "계산 중 문제가 발생했습니다.",
    "analysis_clarification": "질문을 조금 더 구체적으로 알려주세요.",
    "rag_index": "관련 정보를 확인하고 있습니다.",
    "rag_found": "질문과 관련된 참고 정보를 찾았습니다.",
    "rag_not_used": "추가 참고 정보는 사용하지 않았습니다.",
    "guideline_used": "추가 참고 기준을 확인했습니다.",
    "guideline_not_used": "추가 참고 기준은 사용하지 않았습니다.",
    "visualization": "시각화를 준비했습니다.",
    "merge_context": "찾은 정보와 계산 결과를 정리하고 있습니다.",
    "report_draft": "리포트 초안을 작성하고 있습니다.",
    "report_generated": "리포트를 정리했습니다.",
    "report_failed": "리포트 생성 중 문제가 발생했습니다.",
    "report_revision": "수정 요청을 반영하고 있습니다.",
    "data_qa": "답변을 정리하고 있습니다.",
    "output": "응답을 준비하고 있습니다.",
    "approval": "검토를 기다리고 있습니다.",
}


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

    dataset_context = state.get("dataset_context")
    if isinstance(dataset_context, dict):
        merged_context["dataset_context"] = dataset_context

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

    guideline_context = state.get("guideline_context")
    if isinstance(guideline_context, dict):
        merged_context["guideline_context"] = guideline_context
        if bool(guideline_context.get("has_evidence", False)):
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


def _truncate_detail_message(value: str) -> str:
    text = value.strip()
    if len(text) <= _DETAIL_MESSAGE_LIMIT:
        return text
    return f"{text[:_DETAIL_MESSAGE_LIMIT]}..."


def make_thought_step(
    *,
    phase: str,
    message: str,
    status: str = "completed",
    display_message: str | None = None,
    detail_message: str | None = None,
    audience: str = "user",
) -> Dict[str, str]:
    step = {
        "phase": phase,
        "message": message,
        "status": status,
        "display_message": (display_message or message).strip(),
        "audience": audience,
    }
    detail = (detail_message or message).strip()
    if detail:
        step["detail_message"] = _truncate_detail_message(detail)
    return step


def build_approval_wait_step(stage: str) -> Dict[str, str]:
    if stage == "visualization":
        return make_thought_step(
            phase="visualization_approval",
            message="시각화 계획 승인을 기다리는 중입니다.",
            status="active",
            display_message=_DISPLAY_COPY["approval"],
        )
    if stage == "report":
        return make_thought_step(
            phase="report_approval",
            message="리포트 초안 검토를 기다리는 중입니다.",
            status="active",
            display_message=_DISPLAY_COPY["approval"],
        )
    return make_thought_step(
        phase="preprocess_approval",
        message="전처리 계획 승인을 기다리는 중입니다.",
        status="active",
        display_message=_DISPLAY_COPY["approval"],
    )


def collect_thought_steps(state: Dict[str, Any]) -> list[Dict[str, str]]:
    steps: list[Dict[str, str]] = []

    handoff = state.get("handoff")
    if isinstance(handoff, dict):
        next_step = handoff.get("next_step")
        if next_step == "dataset_selected":
            steps.append(
                make_thought_step(
                    phase="intake",
                    message="데이터셋 선택 상태를 확인하고 planner 기반 경로를 준비했습니다.",
                    display_message=_DISPLAY_COPY["intake_dataset_selected"],
                )
            )
        elif next_step == "analysis":
            steps.append(
                make_thought_step(
                    phase="planning",
                    message="planner가 기본 분석 경로를 선택했습니다.",
                    display_message=_DISPLAY_COPY["planning_analysis"],
                )
            )
        elif next_step == "fallback_rag":
            steps.append(
                make_thought_step(
                    phase="planning",
                    message="planner가 fallback RAG 경로를 선택했습니다.",
                    display_message=_DISPLAY_COPY["planning_fallback_rag"],
                )
            )
        elif next_step == "general_question":
            steps.append(
                make_thought_step(
                    phase="intake",
                    message="일반 질의 경로로 라우팅했습니다.",
                    display_message=_DISPLAY_COPY["planning_general"],
                )
            )
        elif next_step == "data_pipeline":
            steps.append(
                make_thought_step(
                    phase="intake",
                    message="데이터셋 기반 파이프라인으로 라우팅했습니다.",
                    display_message=_DISPLAY_COPY["planning_dataset"],
                )
            )
        elif next_step == "dataset_qa":
            steps.append(
                make_thought_step(
                    phase="intake",
                    message="데이터셋 기반 질의응답 경로로 라우팅했습니다.",
                    display_message=_DISPLAY_COPY["planning_dataset"],
                )
            )

        if bool(handoff.get("ask_visualization", False)):
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="시각화 요청이 감지되어 시각화 경로를 준비했습니다.",
                    display_message=_DISPLAY_COPY["intent_visualization"],
                )
            )
        if bool(handoff.get("ask_analysis", False)):
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="분석 요청이 감지되어 분석 단계를 준비했습니다.",
                    display_message=_DISPLAY_COPY["intent_analysis"],
                )
            )
        if bool(handoff.get("ask_report", False)):
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="리포트 요청이 감지되어 리포트 경로를 준비했습니다.",
                    display_message=_DISPLAY_COPY["intent_report"],
                )
            )
        if bool(handoff.get("ask_preprocess", False)):
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="전처리 요청이 감지되어 전처리 단계를 준비했습니다.",
                    display_message=_DISPLAY_COPY["intent_preprocess"],
                )
            )
        elif "ask_preprocess" in handoff:
            steps.append(
                make_thought_step(
                    phase="intent",
                    message="전처리 요청이 없어 전처리 생략 경로를 준비했습니다.",
                    display_message=_DISPLAY_COPY["intent_skip_preprocess"],
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
                    display_message=(
                        _DISPLAY_COPY["preprocess_needed"]
                        if decision.get("step") == "run_preprocess"
                        else _DISPLAY_COPY["preprocess_skipped"]
                    ),
                )
            )
        else:
            decision_step = decision.get("step")
            if decision_step == "run_preprocess":
                steps.append(
                    make_thought_step(
                        phase="preprocess_decision",
                        message="전처리가 필요하다고 판단했습니다.",
                        display_message=_DISPLAY_COPY["preprocess_needed"],
                    )
                )
            elif decision_step == "skip_preprocess":
                steps.append(
                    make_thought_step(
                        phase="preprocess_decision",
                        message="전처리를 생략해도 된다고 판단했습니다.",
                        display_message=_DISPLAY_COPY["preprocess_skipped"],
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
                    display_message=_DISPLAY_COPY["preprocess_plan"],
                )
            )
        else:
            operations = plan.get("operations")
            if isinstance(operations, list) and operations:
                steps.append(
                    make_thought_step(
                        phase="preprocess_plan",
                        message=f"전처리 연산 {len(operations)}개를 계획했습니다.",
                        display_message=_DISPLAY_COPY["preprocess_plan"],
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
                    display_message=_DISPLAY_COPY["preprocess_result"],
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
                        display_message=_DISPLAY_COPY["analysis_success"],
                    )
                )
            else:
                steps.append(
                    make_thought_step(
                        phase="analysis",
                        message="분석 결과를 생성했습니다.",
                        display_message=_DISPLAY_COPY["analysis_success"],
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
                        display_message=_DISPLAY_COPY["analysis_failed"],
                    )
                )

    clarification_question = state.get("clarification_question")
    if isinstance(clarification_question, str) and clarification_question.strip():
        steps.append(
            make_thought_step(
                phase="analysis_clarification",
                message=clarification_question.strip(),
                display_message=_DISPLAY_COPY["analysis_clarification"],
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
                    display_message=_DISPLAY_COPY["rag_index"],
                )
            )
        elif index_status == "existing":
            steps.append(
                make_thought_step(
                    phase="rag_index",
                    message=f"기존 RAG 인덱스를 재사용합니다. (source_id={source_text})",
                    display_message=_DISPLAY_COPY["rag_index"],
                )
            )
        elif index_status == "dataset_missing":
            steps.append(
                make_thought_step(
                    phase="rag_index",
                    message=f"RAG 인덱싱 대상 데이터셋을 찾지 못했습니다. (source_id={source_text})",
                    display_message=_DISPLAY_COPY["rag_not_used"],
                )
            )
        elif index_status == "unsupported_format":
            steps.append(
                make_thought_step(
                    phase="rag_index",
                    message=f"현재 RAG는 해당 파일 형식을 지원하지 않습니다. (source_id={source_text})",
                    display_message=_DISPLAY_COPY["rag_not_used"],
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
                    display_message=_DISPLAY_COPY["rag_found"],
                )
            )
        else:
            evidence_summary = rag_result.get("evidence_summary")
            if isinstance(evidence_summary, str) and evidence_summary.strip():
                steps.append(
                    make_thought_step(
                        phase="rag_retrieval",
                        message=evidence_summary.strip(),
                        display_message=_DISPLAY_COPY["rag_not_used"],
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
                    display_message="찾은 참고 정보를 정리했습니다.",
                )
            )

    guideline_result = state.get("guideline_result")
    if isinstance(guideline_result, dict):
        guideline_summary = guideline_result.get("evidence_summary")
        guideline_status = guideline_result.get("status")
        if isinstance(guideline_summary, str) and guideline_summary.strip():
            steps.append(
                make_thought_step(
                    phase="guideline",
                    message=guideline_summary.strip(),
                    display_message=(
                        _DISPLAY_COPY["guideline_not_used"]
                        if guideline_status == "no_active_guideline"
                        else _DISPLAY_COPY["guideline_used"]
                    ),
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
                    display_message=_DISPLAY_COPY["visualization"],
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
                    display_message=_DISPLAY_COPY["merge_context"],
                    detail_message=(
                        f"누적 컨텍스트를 병합했습니다. "
                        f"(steps={len(applied_steps)}, applied_steps={applied_steps})"
                    ),
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
                    display_message=_DISPLAY_COPY["report_draft"],
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
                    display_message=_DISPLAY_COPY["report_generated"],
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
                        display_message=_DISPLAY_COPY["report_failed"],
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
                    display_message=_DISPLAY_COPY["report_revision"],
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
                    display_message=_DISPLAY_COPY["data_qa"],
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
                display_message=_DISPLAY_COPY["output"],
            )
        )
    return steps

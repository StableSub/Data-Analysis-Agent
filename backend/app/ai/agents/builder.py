from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

if __name__ == "__main__" and __package__ is None:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[4]))

from backend.app.ai.agents.intake_router import build_intake_router_workflow
from backend.app.ai.agents.preprocess import build_preprocess_workflow
from backend.app.ai.agents.rag import build_rag_workflow
from backend.app.ai.agents.report import build_report_workflow
from backend.app.ai.agents.state import MainWorkflowState
from backend.app.ai.agents.visualization import build_visualization_workflow
from backend.app.core.db import SessionLocal

load_dotenv()


def build_main_workflow(
    *,
    db: Session,
    default_model: str = "gpt-5-nano",
):
    """
    역할: Intake, Preprocess, RAG, Visualization, Report 서브그래프를 하나의 메인 워크플로우로 조립한다.
    입력: DB 세션(`db`)과 기본 모델명(`default_model`)을 받아 각 서브그래프 빌더에 전달한다.
    출력: LangGraph `compile()` 결과인 실행 가능한 메인 그래프 객체를 반환한다.
    데코레이터: 없음.
    호출 맥락: `AgentClient` 초기화 시 1회 호출되어 전체 에이전트 파이프라인의 진입점으로 사용된다.
    """
    intake_graph = build_intake_router_workflow(default_model=default_model)
    preprocess_graph = build_preprocess_workflow(
        db=db,
        default_model=default_model,
    )
    rag_graph = build_rag_workflow(
        db=db,
        default_model=default_model,
    )
    visualization_graph = build_visualization_workflow(
        db=db,
        default_model=default_model,
    )
    report_graph = build_report_workflow(
        db=db,
        default_model=default_model,
    )

    def route_after_intake(state: MainWorkflowState) -> str:
        """
        역할: intake 단계가 남긴 handoff 정보를 읽어 다음 노드를 `general_question` 또는 `data_pipeline`으로 결정한다.
        입력: `state.handoff.next_step`를 포함한 메인 상태 딕셔너리를 받는다.
        출력: 조건 분기 키 문자열(`general_question` 또는 `data_pipeline`)을 반환한다.
        데코레이터: 없음.
        호출 맥락: 메인 그래프의 `intake_flow` 이후 conditional edge 라우터로 실행된다.
        """
        branch = str((state.get("handoff") or {}).get("next_step", "general_question"))
        return branch

    def route_after_rag(state: MainWorkflowState) -> str:
        """
        역할: RAG 이후 요청 플래그를 확인해 시각화 경로 진입 여부를 판단한다.
        입력: `state.handoff.ask_visualization` 값을 포함한 메인 상태를 받는다.
        출력: `visualization` 또는 `merge_context` 중 하나의 분기 키를 반환한다.
        데코레이터: 없음.
        호출 맥락: 메인 그래프에서 `rag_flow` 다음 conditional edge 라우팅에 사용된다.
        """
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_visualization", False)):
            return "visualization"
        return "merge_context"

    def route_after_merge_context(state: MainWorkflowState) -> str:
        """
        역할: 병합된 컨텍스트 이후 최종 응답 유형을 리포트 또는 데이터 QA로 선택한다.
        입력: `state.handoff.ask_report` 플래그를 포함한 메인 상태를 받는다.
        출력: `report` 또는 `data_qa` 분기 키 문자열을 반환한다.
        데코레이터: 없음.
        호출 맥락: `merge_context` 노드 다음 conditional edge 라우터로 실행된다.
        """
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_report", False)):
            return "report"
        return "data_qa"

    def general_question_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        """
        역할: 데이터셋이 없는 일반 질문 경로에서 LLM 단일 응답을 생성해 워크플로우를 종료한다.
        입력: `state.user_input`, `state.model_id`를 포함한 메인 상태를 받는다.
        출력: `output.type=general_question`과 `output.content`를 담은 상태 업데이트를 반환한다.
        데코레이터: 없음.
        호출 맥락: intake 라우팅 결과가 `general_question`일 때 터미널 노드로 실행된다.
        """
        model_name = state.get("model_id") or default_model
        llm = init_chat_model(model_name)
        result = llm.invoke(
            [
                SystemMessage(
                    content="사용자 질문에 간결하고 정확하게 답하라."
                ),
                HumanMessage(content=state.get("user_input", "")),
            ]
        )
        answer = result.content if isinstance(result.content, str) else str(result.content)

        return {
            "output": {
                "type": "general_question",
                "content": answer,
            }
        }

    def merge_context_node(state: MainWorkflowState) -> Dict[str, Any]:
        """
        역할: 전처리, RAG, 인사이트, 시각화 결과를 하나의 `merged_context` 구조로 정리한다.
        입력: `preprocess_result`, `rag_result`, `insight`, `visualization_result`, `handoff`를 포함한 상태를 받는다.
        출력: `applied_steps`와 세부 결과를 포함한 `merged_context` 딕셔너리를 반환한다.
        데코레이터: 없음.
        호출 맥락: 데이터 파이프라인 공통 합류 지점으로, report/data_qa 분기 직전에 실행된다.
        """
        merged_context: Dict[str, Any] = {"applied_steps": []}

        handoff = state.get("handoff")
        if isinstance(handoff, dict):
            merged_context["request_flags"] = {
                "ask_preprocess": bool(handoff.get("ask_preprocess", False)),
                "ask_visualization": bool(handoff.get("ask_visualization", False)),
                "ask_report": bool(handoff.get("ask_report", False)),
            }

        preprocess_result = state.get("preprocess_result")
        if isinstance(preprocess_result, dict):
            merged_context["preprocess_result"] = preprocess_result
            if preprocess_result.get("status") == "applied":
                merged_context["applied_steps"].append("preprocess")

        rag_result = state.get("rag_result")
        if isinstance(rag_result, dict):
            merged_context["rag_result"] = rag_result
            if int(rag_result.get("retrieved_count", 0) or 0) > 0:
                merged_context["applied_steps"].append("rag")

        insight = state.get("insight")
        if isinstance(insight, dict):
            merged_context["insight"] = insight
            summary = insight.get("summary")
            if isinstance(summary, str) and summary.strip():
                merged_context["applied_steps"].append("insight")

        visualization_result = state.get("visualization_result")
        if isinstance(visualization_result, dict):
            merged_context["visualization_result"] = visualization_result
            if visualization_result.get("status") == "generated":
                merged_context["applied_steps"].append("visualization")

        return {"merged_context": merged_context}

    def data_qa_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        """
        역할: 병합된 컨텍스트를 근거로 데이터 QA 최종 자연어 응답을 생성한다.
        입력: `state.user_input`, `state.merged_context`, `state.model_id`를 포함한 메인 상태를 받는다.
        출력: `data_qa_result.content`와 `output.type=data_qa`를 담은 상태 업데이트를 반환한다.
        데코레이터: 없음.
        호출 맥락: `merge_context` 이후 `ask_report`가 거짓일 때 최종 터미널 노드로 실행된다.
        """
        model_name = state.get("model_id") or default_model
        llm = init_chat_model(model_name)

        question = str(state.get("user_input", ""))
        merged_context = state.get("merged_context")
        context_json = (
            json.dumps(merged_context, ensure_ascii=False)
            if isinstance(merged_context, dict)
            else "{}"
        )

        result = llm.invoke(
            [
                SystemMessage(
                    content="주어진 merged_context를 근거로 사용자 데이터 질문에 간결하게 답하라."
                ),
                HumanMessage(
                    content=(
                        f"question:\n{question}\n\n"
                        f"merged_context:\n{context_json}"
                    )
                ),
            ]
        )
        answer = result.content if isinstance(result.content, str) else str(result.content)
        return {
            "data_qa_result": {"content": answer},
            "output": {
                "type": "data_qa",
                "content": answer,
            },
        }

    graph = StateGraph(MainWorkflowState)
    graph.add_node("intake_flow", intake_graph)
    graph.add_node("general_question_terminal", general_question_terminal)
    graph.add_node("preprocess_flow", preprocess_graph)
    graph.add_node("rag_flow", rag_graph)
    graph.add_node("visualization_flow", visualization_graph)
    graph.add_node("merge_context", merge_context_node)
    graph.add_node("data_qa_terminal", data_qa_terminal)
    graph.add_node("report_flow", report_graph)

    graph.add_edge(START, "intake_flow")
    graph.add_conditional_edges(
        "intake_flow",
        route_after_intake,
        {
            "general_question": "general_question_terminal",
            "data_pipeline": "preprocess_flow",
        },
    )
    graph.add_edge("preprocess_flow", "rag_flow")
    graph.add_conditional_edges(
        "rag_flow",
        route_after_rag,
        {
            "visualization": "visualization_flow",
            "merge_context": "merge_context",
        },
    )
    graph.add_edge("visualization_flow", "merge_context")
    graph.add_conditional_edges(
        "merge_context",
        route_after_merge_context,
        {
            "report": "report_flow",
            "data_qa": "data_qa_terminal",
        },
    )
    graph.add_edge("report_flow", END)
    graph.add_edge("data_qa_terminal", END)
    graph.add_edge("general_question_terminal", END)

    return graph.compile()


if __name__ == "__main__":
    def _save_main_workflow_png(
        *,
        output_path: str = "builder_workflow.png",
        model_name: str = "gpt-5-nano",
    ) -> Path:
        """
        역할: 메인 워크플로우 그래프를 Mermaid PNG로 렌더링해 파일로 저장한다.
        입력: 저장 경로(`output_path`)와 그래프 빌드에 사용할 모델명(`model_name`)을 받는다.
        출력: 저장된 PNG 파일의 절대 경로(`Path`)를 반환한다.
        데코레이터: 없음.
        호출 맥락: 모듈을 스크립트로 실행할 때 시각 확인용 산출물을 만들기 위해 사용된다.
        """
        db = SessionLocal()
        try:
            main_workflow = build_main_workflow(
                db=db,
                default_model=model_name,
            )
            png_bytes = main_workflow.get_graph().draw_mermaid_png()
        finally:
            db.close()

        path = Path(output_path)
        path.write_bytes(png_bytes)
        return path.resolve()

    def _save_all_workflow_pngs(
        *,
        output_dir: str = "graph_outputs",
        model_name: str = "gpt-5-nano",
    ) -> Dict[str, Path]:
        """
        역할: 메인 그래프와 모든 서브그래프를 일괄 렌더링해 PNG 파일 세트로 저장한다.
        입력: 출력 디렉터리(`output_dir`)와 그래프 빌드용 모델명(`model_name`)을 받는다.
        출력: 그래프 이름별 저장 경로를 담은 `Dict[str, Path]` 매핑을 반환한다.
        데코레이터: 없음.
        호출 맥락: `__main__` 실행 시 워크플로우 구조를 문서/디버깅 용도로 추출할 때 호출된다.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        intake_graph = build_intake_router_workflow(default_model=model_name)
        db = SessionLocal()
        try:
            visualization_graph = build_visualization_workflow(
                db=db,
                default_model=model_name,
            )
            report_graph = build_report_workflow(
                db=db,
                default_model=model_name,
            )
            preprocess_graph = build_preprocess_workflow(
                db=db,
                default_model=model_name,
            )
            rag_graph = build_rag_workflow(
                db=db,
                default_model=model_name,
            )
            main_graph = build_main_workflow(
                db=db,
                default_model=model_name,
            )
        finally:
            db.close()

        targets: Dict[str, tuple[Path, Any]] = {
            "main": (out_dir / "main_workflow.png", main_graph),
            "intake": (out_dir / "intake_workflow.png", intake_graph),
            "preprocess": (out_dir / "preprocess_workflow.png", preprocess_graph),
            "rag": (out_dir / "rag_workflow.png", rag_graph),
            "visualization": (out_dir / "visualization_workflow.png", visualization_graph),
            "report": (out_dir / "report_workflow.png", report_graph),
        }

        saved_paths: Dict[str, Path] = {}
        for key, (path, graph_obj) in targets.items():
            png_bytes = graph_obj.get_graph().draw_mermaid_png()
            path.write_bytes(png_bytes)
            saved_paths[key] = path.resolve()

        return saved_paths

    saved = _save_all_workflow_pngs()
    for name, path in saved.items():
        print(f"{name}: {path}")

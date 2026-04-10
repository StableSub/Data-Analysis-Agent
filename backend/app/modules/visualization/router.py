from fastapi import APIRouter, Depends, HTTPException

from ..analysis.dependencies import get_results_repository
from ..analysis.schemas import AnalysisExecutionResult, AnalysisPlan
from ..results.repository import ResultsRepository
from .dependencies import get_visualization_service
from .schemas import (
    ManualVizRequest,
    ManualVizResponse,
    VisualizationFromAnalysisRequest,
    VisualizationFromAnalysisResponse,
)
from .service import VisualizationService

router = APIRouter(prefix="/vizualization", tags=["visualization"])


@router.post("/manual", response_model=ManualVizResponse)
async def create_manual_visualization(
    request: ManualVizRequest,
    service: VisualizationService = Depends(get_visualization_service),
):
    result = service.get_manual_viz_data(request)

    if "error" in result:
        error_code = result["error"]
        if error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result["message"])
        if error_code == "INVALID_COLUMN":
            raise HTTPException(
                status_code=400, detail="존재하지 않는 컬럼이 포함되어 있습니다."
            )
        if error_code == "NO_DATA":
            raise HTTPException(
                status_code=422, detail="데이터가 부족하여 시각화할 수 없습니다."
            )
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.post("/from-analysis", response_model=VisualizationFromAnalysisResponse)
async def create_visualization_from_analysis(
    request: VisualizationFromAnalysisRequest,
    service: VisualizationService = Depends(get_visualization_service),
    results_repository: ResultsRepository = Depends(get_results_repository),
):
    result = results_repository.get_analysis_result(request.analysis_result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="analysis result not found")
    if not result.analysis_plan_json:
        raise HTTPException(status_code=422, detail="analysis plan is missing")
    source_id = results_repository.resolve_analysis_result_source_id(result)
    if source_id is None:
        raise HTTPException(status_code=422, detail="analysis result source is missing")

    analysis_plan = AnalysisPlan.model_validate(result.analysis_plan_json)
    analysis_result = AnalysisExecutionResult(
        execution_status=str(result.execution_status or "fail"),
        summary=(
            (result.result_json or {}).get("summary")
            if isinstance(result.result_json, dict)
            else None
        ),
        table=list(result.table or []),
        raw_metrics=(
            (result.result_json or {}).get("raw_metrics", {})
            if isinstance(result.result_json, dict)
            else {}
        ),
        used_columns=list(result.used_columns or []),
        error_stage=result.error_stage,
        error_message=result.error_message,
    )

    visualization_result = service.build_from_analysis_result(
        source_id=source_id,
        analysis_plan=analysis_plan,
        analysis_result=analysis_result,
    )
    results_repository.update_chart_data(
        request.analysis_result_id,
        visualization_result.get("chart_data"),
    )
    return visualization_result

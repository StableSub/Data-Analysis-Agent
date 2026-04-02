from fastapi import APIRouter, Depends, HTTPException, status

from ..results.repository import ResultsRepository
from .dependencies import get_analysis_service, get_results_repository
from .schemas import AnalysisRunRequest
from .service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/run")
def run_analysis(
    request: AnalysisRunRequest,
    service: AnalysisService = Depends(get_analysis_service),
):
    try:
        return service.run(
            question=request.question,
            source_id=request.source_id,
            session_id=request.session_id,
            model_id=request.model_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        )


@router.get("/results/{analysis_result_id}")
def get_analysis_result(
    analysis_result_id: str,
    results_repository: ResultsRepository = Depends(get_results_repository),
):
    result = results_repository.get_analysis_result(analysis_result_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="analysis result not found",
        )

    return {
        "analysis_result_id": result.id,
        "analysis_plan_json": result.analysis_plan_json,
        "generated_code": result.generated_code,
        "used_columns": result.used_columns,
        "result_json": result.result_json,
        "table": result.table,
        "chart_data": result.chart_data,
        "execution_status": result.execution_status,
        "error_stage": result.error_stage,
        "error_message": result.error_message,
        "created_at": result.created_at,
    }

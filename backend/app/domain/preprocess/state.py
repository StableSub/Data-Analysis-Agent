from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from backend.app.domain.preprocess.schemas import (
    DataSummary,
    PreprocessApplyResponse,
    SummaryDiff,
)


@dataclass
class PreprocessResult:
    """단일 전처리 실행 결과 스냅샷."""

    input_source_id: str
    output_source_id: str
    output_filename: str
    summary_before: Optional[DataSummary] = None
    summary_after: Optional[DataSummary] = None
    summary_diff: Optional[SummaryDiff] = None

    @classmethod
    def from_response(cls, resp: PreprocessApplyResponse) -> "PreprocessResult":
        """PreprocessApplyResponse 로부터 스냅샷을 생성한다."""
        return cls(
            input_source_id=resp.input_source_id,
            output_source_id=resp.output_source_id,
            output_filename=resp.output_filename,
            summary_before=resp.summary_before,
            summary_after=resp.summary_after,
            summary_diff=resp.summary_diff,
        )


class PreprocessState:
    """
    전처리 실행 이력을 관리하는 인메모리 상태 저장소.
    """

    def __init__(self, max_history: int = 50) -> None:
        self._max_history = max_history
        self._history: list[PreprocessResult] = []
        # source_id → 가장 최근 결과 빠른 조회용
        self._latest_by_input: dict[str, PreprocessResult] = {}
        self._latest_by_output: dict[str, PreprocessResult] = {}

    # ── 기록 ──────────────────────────────────────────────────────────────────

    def record(self, resp: PreprocessApplyResponse) -> PreprocessResult:
        """전처리 응답을 상태에 기록하고 스냅샷을 반환한다."""
        result = PreprocessResult.from_response(resp)
        self._history.append(result)

        # 이력 크기 제한
        if len(self._history) > self._max_history:
            oldest = self._history.pop(0)
            # 인덱스 정리: 해당 항목이 여전히 latest 인 경우만 제거
            if self._latest_by_input.get(oldest.input_source_id) is oldest:
                del self._latest_by_input[oldest.input_source_id]
            if self._latest_by_output.get(oldest.output_source_id) is oldest:
                del self._latest_by_output[oldest.output_source_id]

        self._latest_by_input[result.input_source_id] = result
        self._latest_by_output[result.output_source_id] = result
        return result

    # ── 조회 ──────────────────────────────────────────────────────────────────

    def get_latest_by_input(self, source_id: str) -> Optional[PreprocessResult]:
        """입력 source_id 기준으로 가장 최근 전처리 결과를 반환한다."""
        return self._latest_by_input.get(source_id)

    def get_latest_by_output(self, output_source_id: str) -> Optional[PreprocessResult]:
        """출력 source_id 기준으로 가장 최근 전처리 결과를 반환한다."""
        return self._latest_by_output.get(output_source_id)

    def get_history(self) -> list[PreprocessResult]:
        """전체 실행 이력을 시간 순서대로 반환한다 (복사본)."""
        return list(self._history)

    def get_diff(self, source_id: str) -> Optional[SummaryDiff]:
        """입력 source_id 에 대한 summary_diff 를 바로 꺼낸다.

        프론트엔드 변화량 카드 렌더링 시 편의 메서드로 사용한다.
        """
        result = self._latest_by_input.get(source_id)
        return result.summary_diff if result else None

    # ── 초기화 ────────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """상태를 초기화한다 (테스트·재시작 용도)."""
        self._history.clear()
        self._latest_by_input.clear()
        self._latest_by_output.clear()

    def __len__(self) -> int:
        return len(self._history)


# ── 싱글턴 인스턴스 및 DI 헬퍼 ────────────────────────────────────────────────

_default_state = PreprocessState()


def get_preprocess_state() -> PreprocessState:
    """
    FastAPI Depends 로 주입할 전역 PreprocessState 인스턴스를 반환한다.
    """
    return _default_state
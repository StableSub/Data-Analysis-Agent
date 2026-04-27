# 벤치마크 운영 명세

## 문서 목적

이 문서는 캡스톤 발표 전에 사용할 수 있는 최소 benchmark 운영 방식과 기록 규칙을 정의한다.
현재 저장소에는 자동 benchmark runner가 없으므로, 이 문서는 수동 또는 반수동 측정 기준을 정한다.

## 현재 전제

- 자동화된 `benchmark` 스크립트나 `pytest -m benchmark` 체계는 아직 없다.
- 따라서 benchmark 결과를 발표에 사용할 때는 질문셋, 실행 날짜, 실행 커밋, 측정 방식이 함께 남아 있어야 한다.
- 정량 수치는 이 문서의 형식을 만족할 때만 발표 자료에 넣는다.

## 목표

1. routing 정확도
2. 분석 실행 성공률
3. RAG 근거 적합도
4. approval/resume 흐름 재현 가능성
5. 발표 데모용 대표 latency 체감 기록

## 최소 질문셋 구성

### A. 라우팅 질문셋 (20~30개 권장)

분류:
- `general_question`
- `clarification`
- dataset 기반 `analysis`
- dataset 기반 `rag`
- approval이 필요한 시나리오

기록 항목:
- 질문
- 사용 dataset
- 기대 경로
- 실제 경로
- 성공/실패
- 비고

### B. 분석 정확도 질문셋 (10~15개 권장)

기록 항목:
- 질문
- 기대 핵심 지표 또는 정답 범위
- 실제 답변 요약
- 실행 성공 여부
- 수치 일치 여부
- 실패 원인

### C. RAG/근거 질문셋 (10개 내외 권장)

기록 항목:
- 질문
- 기대 근거 문서 또는 chunk 성격
- 실제 evidence summary 품질
- no-evidence 처리 적절성

## 실행 기록 포맷

최소한 아래 구조를 표나 JSON으로 남긴다.

```json
{
  "run_date": "2026-04-27",
  "commit": "<git-sha>",
  "dataset": "<name>",
  "question": "...",
  "expected_route": "analysis",
  "actual_route": "analysis",
  "result": "pass",
  "notes": "..."
}
```

## 집계 지표

### 필수

- routing accuracy = 일치 건수 / 전체 질문 수
- analysis success rate = 성공 실행 수 / 분석 질문 수
- rag evidence pass rate = 근거가 충분하다고 판단된 건수 / RAG 질문 수
- approval resume success rate = 승인 후 정상 완료 건수 / 승인 질문 수

### 선택

- 대표 시나리오별 체감 latency 메모
- 실패 유형 분포(예: column grounding, no evidence, runtime error)

## PASS 기준 제안

발표 전 내부 기준 예시:

- routing accuracy: 80% 이상
- analysis success rate: 70% 이상
- approval/resume success rate: 주요 데모 시나리오 100%
- 각 실패 케이스는 원인 분류 메모 보유

이 수치는 팀 내부 운영 기준일 뿐이며, 달성하지 못하면 숨기지 말고 한계와 함께 설명한다.

## 금지 사항

- 질문 수를 적지 않은 채 퍼센트만 발표하는 것
- 같은 질문을 여러 번 돌린 뒤 좋은 결과만 선택하는 것
- 날짜·커밋·dataset 정보를 빼고 수치만 공유하는 것
- 추정 latency를 실측값처럼 말하는 것

## 발표 자료 반영 규칙

- 표에는 반드시 질문 수(`n`)를 함께 쓴다.
- 정확도/성공률에는 측정 날짜와 커밋을 붙인다.
- benchmark가 수동 측정이면 “수동 benchmark”라고 명시한다.
- 실패 사례 1개 이상을 같이 보여주면 신뢰도가 올라간다.

## 운영 체크리스트

### 실행 전

- [ ] 사용할 커밋을 고정했다.
- [ ] 질문셋과 기대 결과를 미리 적었다.
- [ ] dataset 버전을 기록했다.

### 실행 중

- [ ] 질문별 실제 경로를 기록했다.
- [ ] 실패 원인을 즉시 메모했다.
- [ ] approval/resume 시나리오는 실제로 끝까지 수행했다.

### 실행 후

- [ ] 집계 표를 만들었다.
- [ ] 발표에 쓸 숫자에 출처를 붙였다.
- [ ] 한계와 미측정 항목을 따로 적었다.

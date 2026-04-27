# 데이터 분석 AI 에이전트

## 개요

이 프로젝트는 사용자가 데이터셋을 업로드하고 자연어로 질문하면, AI 에이전트가 데이터 전처리, 분석, RAG 기반 근거 검색, 시각화, 리포트 생성을 조합해 답변하는 웹 기반 데이터 분석 플랫폼이다.

백엔드는 FastAPI와 LangGraph 기반 workflow로 실행 흐름을 구성하고, 프론트엔드는 React/Vite Workbench에서 SSE 스트림을 받아 진행 상태, 승인 요청, 분석 결과를 표시한다.

## 제품 문서

- [제품 요구사항](./docs/product/prd.md): 데이터 분석 AI 에이전트의 목표, 핵심 흐름, 기능 범위
- [현재 구현 기준선](./docs/product/current-state-baseline.md): 현재 코드 기준 제공 기능과 제약
- [구현 로드맵](./docs/product/roadmap.md): 개선 우선순위와 하네스/검증 계획

## 핵심 기능

- CSV 데이터셋 업로드, 목록/상세/샘플 조회
- 데이터셋 프로파일링과 EDA 기반 품질 확인
- 전처리 제안, approval, 적용, resume 흐름
- 자연어 질문 기반 분석 계획 수립과 SQL/Python 실행
- RAG/guideline 기반 문서 검색과 근거 요약
- 분석 결과 기반 시각화 생성
- 리포트 초안 생성, approval, revision, finalize
- SSE 기반 실행 상태 스트리밍과 세션 히스토리
- trace/logging 기반 실행 이력 추적

## 로컬 실행

```bash
bash dev.sh
```

자세한 실행과 검증 기준은 [로컬 실행 환경](./docs/development/local-environment.md)을 확인한다.

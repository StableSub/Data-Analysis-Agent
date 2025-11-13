# 데이터 분석 AI 에이전트

## 개요
이 캡스톤 프로젝트는 학계와 산업계가 협업해 개발한 인터랙티브 AI 에이전트로, 데이터 업로드부터 시각화 추천까지의 분석 과정을 간소화합니다. 안전한 업로드, 지속형 세션, 데이터셋 탐색, 자동 시각화 제안을 제공하여 연구자가 원시 데이터에서 인사이트까지 빠르게 도달하도록 돕습니다.

## 주요 기능
- **데이터 업로드**: CSV, Excel 등 다양한 표 형식을 지원하며 용량 검증, 오류 처리, 암호화 저장으로 안전하게 관리합니다.
- **세션 관리**: 데이터 선택과 환경 설정을 포함한 분석 세션 전체를 저장·복원해 작업 연속성을 보장합니다.
- **데이터 소스 목록**: 업로드된 데이터셋을 메타데이터(업로드 시각, 크기 등)와 함께 보여주고 검색·필터 기능을 제공합니다.
- **데이터 미리보기**: 샘플 뷰를 생성해 결측치나 이상치를 강조하며 빠른 품질 검증이 가능하도록 합니다.
- **데이터 삭제**: 확인 절차와 소프트 복구 경로를 제공해 실수로 인한 데이터 손실을 예방합니다.
- **자동 시각화**: AI 기반 휴리스틱으로 적절한 차트를 추천하고, 내보내기 전 미리보기와 커스터마이징을 지원합니다.

## 사용법
1. UI 또는 API 엔드포인트로 하나 이상의 데이터셋을 업로드합니다.
2. 미리보기 패널에서 포맷 문제나 데이터 품질 이슈를 확인합니다.
3. 현재 세션을 저장해 작업을 일시 중단하거나 협업자와 공유합니다.
4. 시각화 추천을 실행하고 제안된 차트를 요구사항에 맞게 조정합니다.
5. 프로젝트 진행 상황에 맞춰 데이터셋을 관리하거나 삭제합니다.


---

# Data Analysis AI Agent

## Overview
This capstone project delivers an interactive AI agent, co-developed by academia and industry, that streamlines the entire analytics flow from data upload to visualization recommendations. It offers secure ingestion, persistent sessions, dataset exploration, and automated chart suggestions so researchers can move quickly from raw data to insights.

## Features
- **Data Upload**: Supports CSV, Excel, and other tabular formats with size validation, error handling, and encrypted storage.
- **Session Management**: Saves and restores full analysis sessions, including dataset selections and configuration state.
- **Data Source Listing**: Displays uploaded datasets with metadata (timestamp, size) plus search and filtering tools.
- **Data Preview**: Generates sample views that highlight missing values and anomalies for rapid QA.
- **Data Deletion**: Adds guarded delete flows with confirmations and soft-recovery paths to avoid accidental loss.
- **Automated Visualization**: Uses AI heuristics to recommend chart types and provides customizable previews before export.

## Usage
1. Upload one or more datasets through the UI or API endpoint.
2. Review the preview pane to catch formatting issues or data-quality gaps.
3. Save the current session to pause work or share with collaborators.
4. Trigger visualization recommendations and tailor the suggested charts to your needs.
5. Manage or delete datasets as project requirements evolve.
# Trace 및 로깅 구조

## 문서 목적

이 문서는 현재 프로젝트에서 AI Agent 실행 상태를 trace와 로그 기준으로 어떻게 추적하는지 설명한다.
현재 구현 기준의 trace/logging 구조를 바탕으로 정리하며, 기획, 프론트엔드, 백엔드가 함께 참고할 수 있도록 쉬운 언어로 설명한다.

## Trace 및 로깅 구조 개요

현재 시스템은 질문 하나의 실행 과정을 단일 로그로만 남기지 않는다.
대신 실행 전반에서 trace context를 유지하고, 두 가지 형태의 로그를 함께 기록한다.

- 원본 이벤트 로그
- trace별 요약 로그

원본 이벤트 로그는 실행 중 발생한 개별 이벤트를 시간 순서대로 남긴다.
반면 trace별 요약 로그는 하나의 실행을 한 번에 보기 쉽게 정리한 요약 파일이다.

즉, 현재 구조는 “모든 이벤트를 다 보는 방식”과 “실행 하나를 빠르게 파악하는 방식”을 함께 제공하는 형태다.

## 핵심 식별자 역할

AI Agent 실행을 추적할 때 가장 중요한 식별자는 아래 네 가지다.

### 1. `trace_id`

`trace_id`는 하나의 실행 흐름을 끝까지 묶어 보는 기준 식별자다.
질문 시작, thought, 승인 대기, resume, 최종 결과까지 같은 실행에 속한 로그는 같은 `trace_id`로 연결된다.

### 2. `session_id`

`session_id`는 대화 세션 자체를 구분하는 식별자다.
즉, 사용자가 같은 대화방 안에서 여러 번 질문을 주고받더라도 같은 세션 안에 속할 수 있다.

### 3. `run_id`

`run_id`는 특정 실행 단위를 구분하는 식별자다.
하나의 세션 안에서도 질문마다 별도의 실행 단위가 생길 수 있으므로, `run_id`는 “이번 실행”을 구분하는 데 쓰인다.

### 4. `stage`

`stage`는 현재 workflow가 어느 단계에 있는지를 나타내는 값이다.
예를 들어 intake, preprocess, analysis, rag, guideline, merge_context 같은 단계 정보가 여기에 반영된다.

정리하면, `session_id`는 대화 단위, `run_id`는 실행 단위, `trace_id`는 로그 추적 단위, `stage`는 현재 단계 표시라고 이해하면 된다.

## 로그 저장 위치와 파일 역할

현재 trace 관련 로그는 아래 두 경로를 기준으로 관리된다.

### 1. `storage/logs/agent-trace.jsonl`

이 파일은 전체 raw 이벤트 로그다.
로그는 append-only 방식으로 한 줄씩 추가되며, 각 줄은 하나의 JSON 이벤트를 의미한다.

이 파일의 목적은 실행 중 발생한 이벤트를 시간 순서대로 모두 남기는 것이다.
따라서 가장 세밀한 디버깅이 필요할 때 기준이 되는 로그는 이 파일이다.

### 2. `storage/logs/traces/<trace_id>.json`

이 파일은 trace별 요약 파일이다.
하나의 `trace_id`마다 하나의 JSON 파일이 만들어지며, 실행이 진행될수록 최신 상태로 갱신된다.

이 요약 파일에는 보통 아래 정보가 정리된다.

- 현재 status
- 단계별 steps
- final_output
- error

즉, `agent-trace.jsonl`이 원본 이벤트 로그라면, `traces/<trace_id>.json`은 실행 하나를 빠르게 읽기 위한 요약 로그라고 보면 된다.

## 주요 이벤트 레이어와 기록 방식

현재 trace 로그는 크게 `chat` 과 `workflow` 두 레이어로 나뉜다.

### 1. `chat` 레이어

`chat` 레이어는 사용자 요청과 응답, 승인 대기, 최종 완료처럼 사용자 경험과 가까운 이벤트를 기록한다.
대표적인 이벤트는 아래와 같다.

- `ingress`
- `resume_ingress`
- `thought`
- `approval_required`
- `chunk`
- `done`

각 이벤트의 의미는 아래와 같다.

- `ingress`: 질문이 처음 시스템에 들어온 시점
- `resume_ingress`: 승인 이후 실행을 다시 시작한 시점
- `thought`: 사용자에게 보이는 진행 상태 요약
- `approval_required`: 승인 대기 상태 진입
- `chunk`: 스트리밍 응답 조각
- `done`: 최종 응답과 실행 결과 요약

즉, `chat` 레이어를 보면 사용자가 체감한 실행 과정이 어떻게 흘렀는지를 파악할 수 있다.

### 2. `workflow` 레이어

`workflow` 레이어는 실제 orchestration 상태를 요약해서 기록한다.
대표적인 이벤트는 아래와 같다.

- `snapshot`
- `workflow_final_state`
- `workflow_interrupt`

이 레이어는 handoff 결과, 최종 상태, visualization/report 상태, interrupt stage 같은 workflow 내부 상태를 요약하는 데 사용된다.
즉, `chat` 레이어가 사용자 관점에 가깝다면, `workflow` 레이어는 실행 엔진 관점에 더 가깝다.

## 승인 대기와 재개 추적 방식

현재 AI Agent 실행은 한 번에 끝나지 않을 수 있다.
전처리, 시각화, 리포트 단계에서는 사용자 승인이 필요할 수 있고, 이때 실행은 잠시 멈춘다.

승인 대기 상태가 발생하면 아래 흐름으로 추적할 수 있다.

1. `chat/approval_required` 이벤트가 기록된다.
2. summary 파일의 status가 `approval_required`로 바뀐다.
3. 현재 어떤 단계에서 멈췄는지가 step 정보에 남는다.
4. 이후 `resume_ingress` 이벤트가 들어오면 같은 실행 흐름이 다시 이어진다.

즉, 현재 trace 구조는 승인 때문에 실행이 끊겨도, 같은 `trace_id` 기준으로 멈춘 지점과 재개 지점을 이어서 볼 수 있게 설계되어 있다.

## 실패와 오류 기록 방식

현재 구조에서 실패는 단순 문자열 하나로만 기록되지 않는다.
가능한 경우 아래 세 필드로 구조화해서 남긴다.

- `error_stage`
- `error_message`
- `error_type`

이 정보는 주로 아래 이벤트나 요약에 반영된다.

- `workflow/snapshot`
- `workflow/workflow_final_state`
- `chat/done`
- `traces/<trace_id>.json` 의 `error`

예를 들어 planning, analysis, preprocess, output 조합 과정에서 실패가 발생하면, 어느 단계에서 문제가 생겼는지와 실제 오류 메시지를 이 구조화 필드로 확인할 수 있다.

즉, 현재 로깅 구조는 “실패했다”는 사실만 남기는 것이 아니라, “어느 단계에서 왜 실패했는가”까지 추적할 수 있도록 구성되어 있다.

## 디버깅 시 확인 순서

실제 디버깅 시에는 아래 순서로 보는 것이 가장 효율적이다.

### 1. trace summary 먼저 확인

먼저 `storage/logs/traces/<trace_id>.json`을 본다.
여기서 현재 status, 주요 step, final_output, error를 빠르게 확인할 수 있다.

### 2. raw 이벤트 로그 확인

요약만으로 부족하면 `storage/logs/agent-trace.jsonl`에서 같은 `trace_id`를 찾는다.
이 파일에서는 thought, approval, snapshot, done 이벤트가 시간 순서대로 남아 있으므로 세부 흐름을 복원할 수 있다.

### 3. 승인 이슈 확인

승인 단계에서 멈췄다면 `approval_required` 와 `resume_ingress`를 먼저 본다.
어느 단계에서 대기 중이었는지와 실제로 재개 요청이 들어왔는지를 확인할 수 있다.

### 4. 실패 이슈 확인

실패가 발생했다면 `workflow snapshot/final_state` 와 `chat/done`의 `error_stage`, `error_message`, `error_type`를 먼저 본다.
이 값들이 있으면 문제 지점을 빠르게 좁힐 수 있다.

즉, 현재 구조에서는 summary로 큰 그림을 보고, raw 로그로 세부 이벤트를 확인하는 순서가 가장 실용적이다.

## 이 문서를 읽는 방법

이 문서는 AI Agent 실행을 관찰하고 디버깅하기 위한 문서다.
실행 단계 자체를 이해하고 싶다면 `AI Agent 실행 흐름`을 먼저 보는 것이 맞고, 시스템 전체 흐름은 `시스템 플로우 개요`를 참고하는 것이 좋다.

관련 문서는 아래 순서로 이어서 읽는 것이 자연스럽다.

- AI Agent 개요: AI Agent의 역할과 책임
- AI Agent 실행 흐름: 실제 실행 단계와 분기 구조
- Trace 및 로깅 구조: 실행 상태 추적과 디버깅 기준
- 시스템 아키텍처: 전체 구성 요소와 연결 관계
- 백엔드 구조: trace가 연결되는 백엔드 모듈 구조

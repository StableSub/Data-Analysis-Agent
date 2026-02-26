# TraceAgent RBAC 구현 가이드

## 개요

본 문서는 **ISO/IEC/IEEE 29148** 표준에 기반한 TraceAgent RBAC(Role-Based Access Control) 시스템의 구현 내역을 정리합니다.

---

## 1. 역할 및 권한 체계

### 역할 정의 (Role Definitions)

| 역할 | 설명 | 권한 |
|------|------|------|
| **ADMIN** | 시스템 관리자 | TRACE:READ, TRACE:CAPTURE, REPORT:READ, DATA:UPLOAD, CHAT:USE |
| **ANALYST** | 분석 담당자 | REPORT:READ, DATA:UPLOAD, CHAT:USE |
| **USER** | 일반 사용자 | REPORT:READ, CHAT:USE |

### 권한 코드 (Permission Codes)

- `TRACE:READ` - TraceAgent 이벤트 조회
- `TRACE:CAPTURE` - 온디맨드 캡처 실행
- `REPORT:READ` - 분석 리포트 조회
- `DATA:UPLOAD` - 데이터 업로드
- `CHAT:USE` - 챗봇 사용

---

## 2. 데모 계정

시스템 테스트를 위한 3가지 역할별 계정:

| 이메일 | 비밀번호 | 역할 | 이름 |
|--------|----------|------|------|
| admin@manufacturing.ai | admin123 | ADMIN | 이승현 (관리자) |
| analyst@manufacturing.ai | analyst123 | ANALYST | 김분석 (분석가) |
| user@manufacturing.ai | user123 | USER | 박사용 (사용자) |

---

## 3. 구현 구조

### 타입 정의
- `/types/rbac.ts` - 역할, 권한, 사용자 타입 정의

### 상태 관리
- `/store/useStore.ts` - 사용자 정보, 권한, 감사 로그 관리

### 권한 체크 훅
- `/hooks/usePermissions.ts` - 권한 검증 유틸리티

### UI 컴포넌트

#### 인증
- `/components/auth/Login.tsx` - 역할별 로그인

> 참고: 상기 인증/Trace 관련 일부 컴포넌트 경로는 데모 문서상의 예시이며, 현재 리포지토리에는 포함되지 않았습니다(향후 추가 예정).

#### TraceAgent 관련
- `/components/chat/TraceWidget.tsx` - 실시간 모니터링 위젯 (ADMIN 전용)
- `/components/trace/TraceDetailPage.tsx` - 관리자 콘솔 메인 페이지
- `/components/trace/CaptureConsole.tsx` - 온디맨드 캡처 인터페이스
- `/components/trace/AuditLog.tsx` - 감사 로그 뷰어

---

## 4. 접근 제어 흐름

```
1. 사용자 로그인
   ↓
2. JWT 토큰 발급 (role, permissions 포함)
   ↓
3. usePermissions() 훅으로 권한 체크
   ↓
4. 권한이 있으면 → 컴포넌트 렌더링
   권한이 없으면 → 접근 거부 화면
```

---

## 5. 감사 로그 (Audit Log)

모든 관리 작업은 자동으로 감사 로그에 기록됩니다:

```typescript
{
  id: "audit-xxxxx",
  user: "admin@manufacturing.ai",
  action: "TRACE:CAPTURE",
  target: "collector",
  result: "success",
  timestamp: "2025-11-06T10:32:10Z"
}
```

### 기록되는 작업
- 로그인/로그아웃
- 캡처 시작/중단
- 설정 변경
- 데이터 다운로드

---

## 6. 보안 고려사항

### 현재 구현 (프론트엔드 데모)
- 클라이언트 사이드 권한 체크
- Mock 인증 시스템
- 로컬 스토어 기반 세션

### 프로덕션 권장사항
1. **백엔드 API 인증**
   - JWT 토큰 기반 인증
   - HTTPS 필수
   - 토큰 갱신 메커니즘

2. **권한 검증**
   - 모든 API 엔드포인트에 가드 적용
   - 서버 사이드 권한 검증
   - Rate limiting

3. **감사 로그**
   - 데이터베이스 저장
   - 불변성 보장 (Write-once)
   - 정기적인 아카이빙

4. **데이터 보호**
   - TraceAgent 로그 암호화
   - 접근 로그 별도 저장
   - PII 필터링

---

## 7. 테스트 시나리오

### AC-RBAC-1: 관리자 접근
1. admin@manufacturing.ai로 로그인
2. TraceAgent 위젯 표시 확인
3. "Trace 관리" 버튼 표시 확인
4. 온디맨드 캡처 실행 가능 확인

### AC-RBAC-2: 분석가 접근
1. analyst@manufacturing.ai로 로그인
2. TraceAgent 위젯 "접근 권한 없음" 표시 확인
3. "Trace 관리" 버튼 미표시 확인
4. 챗봇 사용 가능 확인

### AC-RBAC-3: 일반 사용자 접근
1. user@manufacturing.ai로 로그인
2. TraceAgent 위젯 접근 거부 확인
3. 챗봇 읽기 전용 확인

### AC-RBAC-4: 감사 로그
1. 관리자로 캡처 실행
2. 감사 로그에 기록 확인
3. 로그아웃 후 재로그인
4. 이전 감사 로그 유지 확인

---

## 8. API 엔드포인트 (프로덕션 구현 시)

```typescript
// 인증
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh

// TraceAgent (ADMIN 전용)
GET  /api/trace/summary          // TRACE:READ
POST /api/trace/capture          // TRACE:CAPTURE
GET  /api/trace/audit            // TRACE:READ
GET  /api/trace/config           // TRACE:READ

// 권한 체크 미들웨어
@RequirePerms('TRACE:READ')
async getTraceSummary() { ... }
```

---

## 9. 모니터링 지표

### 시스템 지표
- 초당 이벤트 처리량: 목표 1,000/s
- CPU 사용률: ≤ 20%
- 메모리 사용량: ≤ 512MB

### 보안 지표
- 권한 없는 접근 시도 횟수
- 의심스러운 이벤트 비율
- 감사 로그 생성 성공률: 100%

---

## 10. 변경 이력

| 버전 | 날짜 | 변경사항 | 작성자 |
|------|------|----------|--------|
| 1.0 | 2025-11-06 | 초기 RBAC 시스템 구현 | 이승현 |
| 1.1 | 2025-11-06 | 감사 로그 및 캡처 콘솔 추가 | 이승현 |

---

## 참고 문서

- FSD-Trace: TraceAgent 기능명세서
- TSD-Trace: TraceAgent 기술명세서
- ISO/IEC/IEEE 29148: Systems and software engineering - Life cycle processes - Requirements engineering

---

**작성자:** 이승현  
**최종 수정일:** 2025년 11월 6일

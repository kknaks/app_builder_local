# App Builder Local — 전체 진행 관리

## 프로젝트 정보
- **경로:** `/Users/kknaks/kknaks/git/app_builder_local/`
- **PRD:** `/Users/kknaks/kknaks/git/app_builder_local/PRD.md`
- **스택:** FastAPI + PostgreSQL (백엔드) / Next.js + TypeScript (프론트엔드)
- **에이전트 정의:** `.claude/agents/backend.md`, `.claude/agents/frontend.md`

---

## PM 공통 운영 규칙

### 스프린트 시작 시
1. 이 파일(`TOTAL_REQUEST.md`) 상태 업데이트 (🔄 진행중)
2. `.progress/S{N}.md` 생성 — 체크리스트 포함
3. 백엔드/프론트 에이전트 dispatch (병렬 가능한 작업은 병렬로)
4. **케케낙 Discord DM 발송** — 스프린트 시작 알림 (내용 + 예상 작업)

### 스프린트 진행 중
- 각 작업 완료 시 `.progress/S{N}.md` 체크 업데이트
- 에러 발생 시 최대 3회 자동 수정 시도 후 케케낙에게 보고
- 작업 내역 + 커밋 해시 `.progress/S{N}.md`에 기록

### 스프린트 완료 시
1. `.progress/S{N}.md` 최종 업데이트 (완료 일시 + 커밋 해시)
2. 이 파일 상태 업데이트 (✅ 완료)
3. **케케낙 Discord DM 발송** — 완료 내용 + 다음 스프린트 예고
4. 다음 스프린트 자동 시작 (별도 지시 없으면)

### 컴팩션/재시작 시
- 이 파일과 `.progress/S{N}.md` 읽어서 현재 상태 파악
- 중단된 스프린트부터 재개

### 에이전트 실행 방식
- `sessions_spawn` 사용 (독립 세션, 백그라운드 실행)
- 상시 연결 X — 필요할 때 spawn → 완료 → 종료
- 병렬: BE/FE 동시 작업 가능한 경우만 (최대 2개 동시)
- 3개 이상 동시 spawn 금지 (rate limit 방지)

### 에이전트 crash/timeout 처리
- 재시도 최대 3회
- 3회 모두 실패 → 케케낙 Discord DM 보고 + 해당 스프린트 고정 재시도
- 다음 스프린트 진행 X (의존성 있으므로 현재 스프린트 완료 후 진행)

### 포트 설정 (고정)
- **백엔드 (FastAPI):** `28888`
- **프론트엔드 (Next.js):** `23000`
- **PostgreSQL:** Docker 내부 `5432` (외부 노출 불필요)

### 스프린트 완료 검증 (필수)
**백엔드:**
- `pytest` 전체 통과
- `ruff check .` lint 통과
- 새 기능 테스트 커버리지 확인

**프론트엔드:**
- `tsc --noEmit` 타입 에러 0
- `next build` 빌드 성공

**통합:**
- API 연동 실제 동작 확인
- `docker compose up` 정상 실행

검증 실패 시 → 자동 수정 최대 3회 → 그래도 실패 시 케케낙 Discord DM 보고 후 다음 스프린트 진행

### 커밋 규칙
- Conventional Commits
- 스프린트 완료 시 반드시 push

---

## 스프린트 목록

| 스프린트 | 내용 | 상태 | 커밋 |
|---------|------|------|------|
| S1 | 프로젝트 세팅 + DB | ✅ 완료 | 9317d52, dc46034 |
| S2-BE | 토큰/프로젝트 CRUD API | ✅ 완료 | a9636b9 |
| S2-FE | 3패널 레이아웃 + 대시보드 기본 | ✅ 완료 | 729c369 |
| S3-BE | 에이전트 엔진 + 채팅/로그 WS | ✅ 완료 | d43b5bc |
| S3-FE | 채팅/로그 UI + 상태 관리 | ✅ 완료 | 685ed91 |
| S4-BE | 기획 플로우 (Planner + 검증) | ✅ 완료 | - |
| S4-FE | 기획 UI + 플로우 시각화 | ✅ 완료 | 45ab879 |
| S5 | 구현 플로우 + 에러 자동 수정 | 🔄 진행중 | - |
| S6 | Docker 실행 + 통합 테스트 + 폴리싱 | ⏳ 대기 | - |

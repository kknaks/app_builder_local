# App Builder Local — 스프린트 플랜

> 작성일: 2026-03-05
> 기준: PRD.md F1~F13

---

## 의존성 그래프

```
S1: 프로젝트 세팅 + DB
 │
 ├──→ S2-BE: API 기반 (토큰/프로젝트 CRUD)    ─┐
 │                                               ├──→ S3: 에이전트 엔진 + 채팅/로그
 └──→ S2-FE: 3패널 레이아웃 + 대시보드 기본     ─┘
                                                  │
                                                  ├──→ S4-BE: 기획 플로우 (Planner + 검증)  ─┐
                                                  │                                           ├──→ S5: 구현 플로우 + 에러 수정
                                                  └──→ S4-FE: 기획 UI + 플로우 시각화        ─┘
                                                                                               │
                                                                                               └──→ S6: Docker 실행 + 통합 테스트
```

---

## Sprint 1: 프로젝트 세팅 + DB (1주)

**목표:** 개발 환경 구축 + DB 스키마 + 기본 프로젝트 구조

| 작업 | 담당 | 기능 | 산출물 |
|------|------|------|--------|
| FastAPI 프로젝트 초기화 | BE | - | `backend/` 구조, pyproject.toml, 의존성 |
| Next.js 프로젝트 초기화 | FE | - | `frontend/` 구조, package.json, Tailwind 설정 |
| PostgreSQL + Alembic 마이그레이션 | BE | - | DB 연결, 마이그레이션 스크립트 |
| 전체 DB 스키마 생성 | BE | - | projects, agent_logs, flow_nodes, settings, chat_messages, agent_tasks |
| Docker Compose (개발용) | BE | - | `docker-compose.dev.yml` (PostgreSQL + 백엔드 + 프론트) |
| 공통 템플릿 작성 | - | F3 | `common/plan_form.md`, `common/plan_phase.md` |

**완료 조건:**
- `docker compose -f docker-compose.dev.yml up`으로 BE/FE/DB 정상 기동
- 마이그레이션 실행 → 6개 테이블 생성 확인
- FastAPI `/docs` 접근 가능, Next.js `localhost:3000` 접근 가능

---

## Sprint 2: 토큰 설정 + 프로젝트 CRUD + 3패널 레이아웃 (2주)

> ⚡ BE/FE 병렬 작업 가능

### Sprint 2-BE: API 기반

| 작업 | 기능 | 산출물 |
|------|------|--------|
| 토큰 저장/검증 API | F1 | `POST /api/settings/token`, `GET /api/settings/token/status` |
| 토큰 AES-256 암호화 모듈 | F1 | `backend/core/crypto.py` |
| 프로젝트 CRUD API | F2, F13 | `POST/GET/DELETE /api/projects` |
| 프로젝트 생성 시 디렉토리 + idea.md 생성 | F2 | 파일시스템 연동 |
| 에이전트/skills 파일 자동 생성 | F3 | `.claude/agent/*.md`, `.claude/skills/*.md` 템플릿 → 프로젝트 디렉토리에 복사 |

**의존성:** S1 완료

### Sprint 2-FE: 3패널 레이아웃

| 작업 | 기능 | 산출물 |
|------|------|--------|
| 3패널 레이아웃 (react-resizable-panels) | F8, F9, F10 | 목록/대시보드/채팅+로그 리사이즈 가능 패널 |
| 좌측 목록 패널 (트리 구조) | F13 | 프로젝트 단계 트리 + 상태 아이콘 |
| 토큰 설정 모달 | F1 | 토큰 입력 + 검증 + 저장 UI |
| 프로젝트 생성 모달 | F2 | 이름 + 아이디어 입력 폼 |
| 프로젝트 목록 (대시보드 기본) | F13 | 프로젝트 카드 리스트 + 삭제 |
| 대시보드 기본 플로우 (React Flow + dagre) | F10 | 빈 플로우 캔버스 + 기본 노드 렌더링 |

**의존성:** S1 완료

**완료 조건:**
- 토큰 입력 → 검증 → 저장 → 이후 접속 시 자동 확인
- 프로젝트 생성 → DB + 디렉토리 + idea.md + 에이전트 파일 확인
- 프로젝트 목록 조회 + 삭제
- 3패널 리사이즈 동작

---

## Sprint 3: 에이전트 엔진 + 채팅/로그 (2주)

**목표:** Claude Code CLI spawn 엔진 + 채팅/로그 실시간 통신

> ⚡ BE/FE 병렬 작업 가능

### Sprint 3-BE: 에이전트 엔진

| 작업 | 기능 | 산출물 |
|------|------|--------|
| Claude Code CLI pty spawn 모듈 | F7 | `backend/core/agent_runner.py` — spawn/모니터/종료 |
| agent_tasks CRUD + 상태 관리 | F7 | 태스크 생성 → running → completed/failed |
| 채팅 WebSocket 엔드포인트 | F9 | `/ws/projects/{id}/chat` — 메시지 프로토콜 구현 |
| 로그 WebSocket 엔드포인트 | F9 | `/ws/projects/{id}/logs` — 실시간 로그 스트리밍 |
| chat_messages 저장/조회 | F9 | 에이전트별 대화 이력 |
| 에이전트 전환 (switch_agent) | F8 | WS 메시지로 에이전트 라우팅 |

**의존성:** S2-BE 완료

### Sprint 3-FE: 채팅/로그 UI

| 작업 | 기능 | 산출물 |
|------|------|--------|
| 에이전트 버튼 바 (원형 5개) | F8 | 대시보드 하단, 클릭 시 채팅 전환 + 상태 색상 |
| 채팅 패널 (상단) | F9 | 에이전트별 1:1 채팅 UI, 메시지 송수신, 히스토리 |
| 로그 패널 (하단, react-window) | F9 | 가상 스크롤 로그 뷰어, 에이전트 태그 + 필터 |
| WebSocket 연결 관리 (채팅 + 로그) | F9 | 자동 재연결, 연결 상태 표시 |

**의존성:** S2-FE 완료

**완료 조건:**
- Claude Code CLI spawn → 실행 → 종료 정상 동작
- 채팅에서 에이전트에게 메시지 전송 → 응답 수신
- 에이전트 버튼 클릭 → 채팅 전환 + 히스토리 로드
- 로그 실시간 스트리밍 확인
- agent_tasks 상태 추적 (pending → running → completed)

---

## Sprint 4: 기획 플로우 + 대시보드 시각화 (2주)

**목표:** F4(기획 구체화) + F5(기획 검증) + 대시보드 플로우 동적 생성

> ⚡ BE/FE 병렬 작업 가능

### Sprint 4-BE: 기획 플로우

| 작업 | 기능 | 산출물 |
|------|------|--------|
| 기획 시작 API | F4 | `POST /api/projects/{id}/plan` → Planner Agent spawn |
| plan_form.md 기반 구체화 프롬프트 | F4 | Planner에게 전달할 시스템 프롬프트 설계 |
| 기획 검토 API | F5 | `POST /api/projects/{id}/review` → BE/FE/Design 병렬 spawn |
| 검토 결과 취합 → PM 로직 | F5 | 3에이전트 결과 수집 → 유저에게 전달 |
| 승인/피드백 API | F5 | `POST /api/projects/{id}/approve`, `/feedback` |
| 피드백 루프 (재검토) | F5 | 피드백 → 에이전트 수정 → 재검토 → 재취합 |
| PRD.md 확정 저장 | F5 | 승인 시 프로젝트 디렉토리에 PRD.md 생성 |
| 플로우 노드 CRUD | F10 | `GET /api/projects/{id}/flow`, 노드 상태 업데이트 |

**의존성:** S3-BE 완료 (에이전트 엔진)

### Sprint 4-FE: 기획 UI + 플로우

| 작업 | 기능 | 산출물 |
|------|------|--------|
| 기획 구체화 화면 (Planner 채팅) | F4 | 기획 단계 진입 → Planner와 대화 |
| 기획 검토 결과 표시 | F5 | PM이 전달하는 검토 결과 카드 UI |
| 승인/피드백 버튼 | F5 | 채팅 내 인라인 액션 버튼 |
| 대시보드 플로우 동적 생성 | F10 | 기획 시작 → 노드 자동 추가, 상태 실시간 업데이트 |
| 플로우 노드 상태 색상 업데이트 | F10 | WS `flow_update` 메시지 → 노드 색상 변경 |
| 목록 패널 상태 연동 | F10 | 진행 단계에 따라 트리 상태 아이콘 업데이트 |

**의존성:** S3-FE 완료

**완료 조건:**
- 기획 시작 → Planner와 대화 → 기획 문서 작성
- 기획 완료 → BE/FE/Design 3에이전트 병렬 검토
- 검토 결과 채팅으로 수신 → 승인 or 피드백
- 피드백 시 재검토 루프 동작
- 승인 → PRD.md 생성 확인
- 대시보드 플로우 노드 실시간 상태 업데이트

---

## Sprint 5: 구현 플로우 + 에러 자동 수정 (2주)

**목표:** F6(스프린트 플랜) + F7(구현) + F11(에러 자동 수정)

| 작업 | 담당 | 기능 | 산출물 |
|------|------|------|--------|
| 스프린트 플랜 API | BE | F6 | `POST /api/projects/{id}/sprint` → Phase.md 생성 |
| plan_phase.md + PRD.md → 스프린트 프롬프트 | BE | F6 | PM Agent가 Phase.md 작성하는 프롬프트 |
| 스프린트 플로우 자동 생성 (대시보드) | BE+FE | F6 | Phase.md 파싱 → 기능별 BE/FE/테스트 노드 생성 |
| 구현 시작 API | BE | F7 | `POST /api/projects/{id}/implement` |
| PM 총괄 로직 — 순차 명령 하달 | BE | F7 | PM → BE/FE Agent 순차 spawn + 태스크 관리 |
| 에이전트 구현→테스트→수정 루프 | BE | F7 | Agent spawn → 빌드 테스트 → 실패 시 에러 로그 전달 → 재시도 |
| 에러 자동 수정 (최대 3회) | BE | F11 | 빌드/테스트 실패 감지 → 에이전트에게 에러 로그 전달 → 자동 재시도 |
| PM → 유저 에스컬레이션 | BE | F7 | 3회 실패 or 결정 필요 시 유저에게 채팅 질문 |
| 구현 진행 상황 대시보드 | FE | F7, F10 | 플로우 노드 실시간 업데이트 + 에이전트 상태 |
| 유저 상황 체크 (PM 질의) | FE | F7 | 채팅에서 PM에게 "지금 진행 상황?" 질문 가능 |

**의존성:** S4 완료

**완료 조건:**
- 스프린트 플랜 생성 → Phase.md + 대시보드 상세 플로우
- PM이 BE/FE Agent에게 순차 명령 → 코드 생성
- 빌드 실패 → 자동 수정 최대 3회 → 성공 or 유저 에스컬레이션
- 유저가 중간에 상황 체크 가능
- 대시보드에서 전체 구현 진행 흐름 실시간 확인

---

## Sprint 6: Docker 실행 + 통합 테스트 + 폴리싱 (2주)

**목표:** F12(앱 실행) + 전체 통합 테스트 + UI 폴리싱

| 작업 | 담당 | 기능 | 산출물 |
|------|------|------|--------|
| Docker Compose 자동 생성 | BE | F12 | 구현 완료 후 docker-compose.yml 자동 생성 |
| 앱 실행/중지 API | BE | F12 | `POST /api/projects/{id}/run`, `/stop` |
| localhost URL 반환 + 상태 모니터링 | BE | F12 | 컨테이너 상태 체크, 포트 할당 |
| 앱 실행 UI | FE | F12 | [앱 실행] 버튼 → URL 표시 + [중지] 버튼 |
| 프로젝트 재실행/삭제 | FE | F13 | 프로젝트 상세에서 재실행, 삭제 (디렉토리 포함) |
| E2E 시나리오 테스트 | 공통 | - | 아이디어 입력 → 기획 → 검토 → 승인 → 구현 → 실행 전체 플로우 |
| 에러 핸들링 + 빈 상태 UI | FE | - | 네트워크 에러, 빈 프로젝트, 로딩 상태 |
| UI 폴리싱 | FE | - | 반응형, 애니메이션, 토스트 알림 |
| 문서 정리 | 공통 | - | README.md 설치 가이드 + 사용법 |

**의존성:** S5 완료

**완료 조건:**
- 전체 플로우 E2E 성공 (아이디어 → 앱 실행)
- Docker Compose로 생성된 앱 localhost에서 접근 가능
- 에러 상황 graceful 처리
- README.md 설치 가이드 완성

---

## 전체 타임라인

```
Week 1        Week 2-3       Week 4-5       Week 6-7       Week 8-9       Week 10-11
┌──────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  S1  │───▶│  S2-BE   │──▶│  S3-BE   │──▶│  S4-BE   │──▶│    S5    │──▶│    S6    │
│세팅+DB│   │  S2-FE   │──▶│  S3-FE   │──▶│  S4-FE   │   │구현+에러  │   │Docker+QA │
│      │   │  ⚡병렬   │   │  ⚡병렬   │   │  ⚡병렬   │   │         │   │         │
└──────┘    └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
  1주          2주            2주            2주            2주            2주
```

**총 예상: 11주**

---

## 기능 → 스프린트 매핑

| 기능 | 스프린트 | 비고 |
|------|---------|------|
| F1 토큰 설정 | S2 | BE: API + 암호화 / FE: 모달 |
| F2 프로젝트 생성 | S2 | BE: API + 디렉토리 / FE: 폼 |
| F3 에이전트 자동 세팅 | S2 | BE: 템플릿 복사 |
| F4 기획 구체화 | S4 | BE: Planner spawn / FE: 채팅 |
| F5 기획 검증 플로우 | S4 | BE: 병렬 검토 + 취합 / FE: 승인 UI |
| F6 스프린트 플랜 | S5 | BE: Phase.md + 플로우 생성 |
| F7 구현 (PM 총괄) | S5 | BE: 순차 명령 + 태스크 관리 |
| F8 에이전트 버튼 바 | S3 | FE: 원형 버튼 + 상태 |
| F9 채팅 + 로그 패널 | S3 | BE: WS 엔드포인트 / FE: 채팅+로그 UI |
| F10 대시보드 (플로우) | S2(기본) → S4(동적) | FE: React Flow + dagre |
| F11 에러 자동 수정 | S5 | BE: 재시도 루프 |
| F12 앱 실행 | S6 | BE: Docker / FE: 실행 UI |
| F13 프로젝트 관리 | S2(기본) → S6(완성) | BE: CRUD / FE: 목록 |

---

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Claude Code CLI spawn 안정성 | S3 지연 | 초기에 PoC 선행, 타임아웃/재시도 방어 |
| 에이전트 간 컨텍스트 전달 품질 | S4~S5 품질 저하 | 에이전트 프롬프트 반복 튜닝, 문서 템플릿 정교화 |
| 병렬 에이전트 spawn 시 리소스 | S4 성능 | 동시 최대 프로세스 제한 (기본 3) |
| 생성된 앱 Docker 빌드 실패 | S6 지연 | Dockerfile 템플릿 사전 검증, 에러 수정 루프 활용 |

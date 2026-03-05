# App Builder Local — PRD

> 최종 수정일: 2026-03-06

## 1. 개요

### 1.1 한줄 요약
로컬 설치형 AI 개발팀 — Claude Code 에이전트 조직(PM/기획/백엔드/프론트/디자인)이 아이디어를 앱으로 만들어주는 플랫폼

### 1.2 배경
Bolt.new, Lovable 등 AI 앱 빌더는 단일 에이전트가 코드를 뱉는 구조다. 실제 개발은 기획 → 검토 → 구현 → 테스트를 **여러 역할이 협업**해서 진행한다.

App Builder Local은:
- **AI 에이전트 팀**이 실제 개발 조직처럼 협업
- PM이 총괄하고, 기획자/백엔드/프론트/디자이너가 각자 역할 수행
- 유저는 의사결정자(클라이언트) 역할 — 승인/피드백만 하면 됨
- 로컬에서 전부 실행, Claude API 토큰만 있으면 됨

### 1.3 타겟 유저
- **비개발자** — 아이디어는 있지만 코딩을 모르는 사람
- 유저 역할: 클라이언트 (아이디어 제공 + 승인/피드백)

### 1.4 핵심 가치

| 가치 | 설명 |
|------|------|
| AI 개발팀 | PM + 기획 + BE + FE + Design 5명의 에이전트 협업 |
| 로컬 전용 | 내 컴퓨터에서 전부 실행. 클라우드 없음 |
| 비용 투명 | Claude API 토큰 비용만 |
| 유저 = 클라이언트 | 코딩 몰라도 됨. 승인/피드백만 |

---

## 2. 기술 스택

### App Builder Local 자체 스택

| 레이어 | 기술 | 비고 |
|--------|------|------|
| 프론트엔드 | Next.js | 단일 페이지 (목록 + 대시보드 + 채팅) |
| 플로우 에디터 | React Flow + dagre | n8n 스타일 노드 그래프 시각화 + 자동 레이아웃 |
| 패널 리사이즈 | react-resizable-panels | 목록/대시보드/채팅 3패널 리사이즈 |
| 로그 가상 스크롤 | react-window | 대량 로그 메시지 렌더링 성능 최적화 |
| 백엔드 | Python (FastAPI) | 오케스트레이터 + API 서버 |
| 패키지 관리 | Poetry | 의존성 관리 + 가상환경 |
| ORM | SQLAlchemy 2.0 | 비동기 (async) + Alembic 마이그레이션 |
| DB | PostgreSQL | 프로젝트/에이전트/실행 이력 관리 |
| AI 에이전트 | Claude Code CLI | `claude --dangerously-skip-permissions` (pty spawn) |
| 실시간 통신 | WebSocket | 빌드 로그 + 채팅 실시간 스트리밍 |
| 앱 실행 | Docker Compose | 생성된 앱 로컬 실행 |

### 생성되는 앱의 스택
- **MVP: FastAPI (백엔드) + Next.js (프론트엔드) + PostgreSQL (DB)**
- Phase 2: 사용자 선택 가능 (멀티 스택 지원)

> ⚠️ **TODO:** MVP 고정 스택 확정 필요. 예: FastAPI + Next.js / Django + React 등. skills 파일 작성에 선행되어야 함.

---

## 3. 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────┐
│                    Next.js 단일 페이지                     │
│  ┌──────────┬────────────────────┬─────────────────────┐ │
│  │   목록    │     대시보드        │       채팅          │ │
│  │ (사이드)  │  (n8n 스타일 플로우) │  (Claude Code 연결) │ │
│  └──────────┴────────────────────┴─────────────────────┘ │
└────────────────────────┬─────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼─────────────────────────────────┐
│              Python 오케스트레이터 (FastAPI)               │
│                                                           │
│  ┌─────┐    ┌─────────┐                                  │
│  │ PM  │◄──►│  유저    │  (채팅으로 소통)                  │
│  │Agent│    └─────────┘                                  │
│  └──┬──┘                                                 │
│     │ 명령/보고                                           │
│  ┌──┴──────────────────────────────┐                     │
│  │  ┌────────┐ ┌────────┐ ┌──────┐│                     │
│  │  │Planner │ │Backend │ │Front ││                     │
│  │  │ Agent  │ │ Agent  │ │Agent ││                     │
│  │  └────────┘ └────────┘ └──────┘│                     │
│  │             ┌────────┐          │                     │
│  │             │Design  │          │                     │
│  │             │ Agent  │          │                     │
│  │             └────────┘          │                     │
│  └─────────────────────────────────┘                     │
└──────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│          프로젝트 디렉토리 (격리)                          │
│  root/kknaks_pr/{proj_name}/                              │
│  ├── idea.md                                              │
│  ├── PRD.md                                               │
│  ├── Phase.md                                             │
│  ├── .claude/                                             │
│  │   ├── agent/                                           │
│  │   │   ├── pm-agent.md                                  │
│  │   │   ├── planner-agent.md                             │
│  │   │   ├── backend-agent.md                             │
│  │   │   ├── frontend-agent.md                            │
│  │   │   └── design-agent.md                              │
│  │   └── skills/                                          │
│  │       ├── pm.md                                        │
│  │       ├── planner.md                                   │
│  │       ├── backend.md                                   │
│  │       ├── frontend.md                                  │
│  │       └── design.md                                    │
│  ├── backend/                                             │
│  ├── frontend/                                            │
│  └── docker-compose.yml                                   │
└──────────────────────────────────────────────────────────┘
```

---

## 4. 핵심 기능 (MVP)

| ID | 기능 | 설명 |
|----|------|------|
| F1 | 토큰 설정 | Claude API 토큰 입력 + 유효성 검증 + 암호화 저장 |
| F2 | 프로젝트 생성 | 이름 + 아이디어 입력 → DB 저장 + 디렉토리 생성 + idea.md 작성 |
| F3 | 에이전트 자동 세팅 | 5개 에이전트(PM/Planner/BE/FE/Design) + skills 파일 자동 생성 |
| F4 | 기획 구체화 | plan_form.md 기반 + 유저 대화로 아이디어 구체화 |
| F5 | 기획 검증 플로우 | Planner 작성 → PM 전달 → 3에이전트 검토 → PM 취합 → 유저 승인/피드백 루프 |
| F6 | 스프린트 플랜 | PRD.md + plan_phase.md → Phase.md 작성 + 대시보드 상세 플로우 자동 생성 |
| F7 | 구현 (PM 총괄) | PM 명령 → 각 에이전트 기능구현 → 테스트 → 수정 반복 → PM 보고 |
| F8 | 에이전트 탭 바 | 채팅 패널 상단 탭 5개, 클릭 시 채팅 전환 + 상태 색상 + unread badge |
| F9 | 채팅 + 로그 패널 | 상단 에이전트별 1:1 채팅 / 하단 전체 실행 로그 실시간 스트리밍 |
| F10 | 대시보드 (n8n 플로우) | 프로젝트 전체 플로우 노드 + 엣지 시각화, 실시간 상태 업데이트 |
| F11 | 에러 자동 수정 | 빌드/테스트 실패 시 에이전트 자동 수정 (최대 3회) |
| F12 | 앱 실행 | Docker Compose 자동 생성 + 원클릭 실행 → localhost URL |
| F13 | 프로젝트 관리 | 프로젝트 목록 조회 / 삭제 / 재실행 |

---

## 5. UI 구성 — 단일 페이지 3패널


```
┌──────────┬──────────────────────────┬──────────────────┐
│          │                          │                  │
│   목록    │        대시보드           │      채팅        │
│  (좌측)   │    (n8n 스타일 플로우)    │  (에이전트 대화)  │
│          │                          │                  │
│ ─────── │  [아이디어]               │ PM: 기획서 검토   │
│ 1.아이디어│     ↓                    │ 결과를 전달합니다  │
│ 2.기획서  │  [기획서]─→[BE검토]      │ ...              │
│  ├구체화  │     │   ─→[FE검토]      │                  │
│  ├검증   │     │   ─→[Design검토]  │                  │
│ 3.구현   │     ↓                    │──────────────────│
│  ├백엔드  │  [스프린트]               │ [로그]            │
│  ├프론트  │     ↓                    │ > planner: PRD   │
│ 4.검증   │  [BE구현]─→[FE구현]      │   작성 시작...    │
│  └테스트  │     ↓                    │ > backend: API   │
│          │  [검증/테스트]            │   설계 검토 중... │
│          │                          │                  │
│          │  ┌────────────────────┐  │                  │
│          │  │(PM)(BE)(FE)(PL)(DE)│  │                  │
│          │  └────────────────────┘  │                  │
└──────────┴──────────────────────────┴──────────────────┘
```

### 5.1 좌측: 목록 패널

프로젝트 진행 단계를 트리 구조로 표시. 클릭 시 대시보드 해당 노드 하이라이트 + 채팅 컨텍스트 전환.

```
1. 아이디어
2. 기획서
   ├── 기획 구체화
   └── 검증 (BE/FE/Design 검토)
3. 구현
   ├── 백엔드 구현
   └── 프론트엔드 구현
4. 검증
   └── 테스트
```

각 항목 상태 표시: ○ 대기 / ● 진행중 / ✅ 완료 / ❌ 실패

### 5.2 중앙: 대시보드 패널 (n8n 스타일 플로우)

프로젝트 전체 플로우를 **노드 + 엣지** 그래프로 시각화.
- 각 노드 = 작업 단계 (아이디어 → 기획 → 검토 → 스프린트 → 구현 → 테스트)
- 노드 색상: 회색(대기) / 파랑(진행중) / 초록(완료) / 빨강(에러)
- 노드 클릭 → 상세 정보 + 해당 단계 채팅 열기
- 스프린트 플랜 작성 후 → 상세 플로우 자동 생성 (각 기능별 BE/FE/테스트 노드)

#### 에이전트 탭 바 (채팅 패널 상단)

채팅 패널 상단에 탭 형태로 에이전트 5명을 표시. 시선 이동 최소화를 위해 대시보드가 아닌 채팅 패널 바로 위에 배치.

```
  ┌──────────────────────────────────────┐
  │  [PM🟢]  [BE🔵]  [FE⚪]  [PL🟡]  [DE⚪] │
  ├──────────────────────────────────────┤
  │  채팅 영역                            │
  └──────────────────────────────────────┘
```

- 각 탭 = 에이전트 (PM / Backend / Frontend / Planner / Design)
- **탭 클릭 → 채팅 패널이 해당 에이전트와의 대화로 전환**
- 탭 상태 색상:
  - 🟢 초록: 활성 (현재 작업 중)
  - 🔵 파랑: 대기 (작업 가능)
  - 🟡 노랑: 유저 입력 대기 (질문 있음)
  - ⚪ 회색: 비활성 (아직 단계 아님)
  - 🔴 빨강: 에러
- **Unread badge**: 현재 보고 있지 않은 에이전트에서 메시지 오면 탭에 빨간 dot 표시

### 5.3 우측: 채팅 + 로그 패널

우측 패널은 상/하로 분리:

```
┌──────────────────┐
│     채팅          │  ← 에이전트 탭에서 선택한 에이전트와 대화
│                  │
│ PM: 기획서 검토   │
│ 결과를 전달합니다  │
│                  │
│ > 승인합니다      │
│                  │
│──────────────────│
│     로그          │  ← 전체 에이전트 실행 로그 (실시간)
│                  │
│ [PM] 기획서 전달   │
│ [BE] API 설계 검토 │
│ [FE] 화면 구조 검토│
│ [PL] PRD 작성 시작 │
│                  │
└──────────────────┘
```

**채팅 영역 (상단):**
- 에이전트 탭 클릭 시 해당 에이전트와 1:1 대화
- 기본값: PM Agent (유저 ↔ PM 소통)
- 다른 에이전트 탭 클릭 시 직접 대화 가능 (예: Backend에게 직접 질문)
- 대화 히스토리는 에이전트별로 분리 유지

**로그 영역 (하단):**
- 전체 에이전트의 실행 로그 실시간 스트리밍
- 에이전트 태그 표시: `[PM]`, `[BE]`, `[FE]`, `[PL]`, `[DE]`
- 필터 가능: 특정 에이전트 로그만 보기

---

## 6. 프로젝트 플로우

### 6.1 프로젝트 생성

```
[새 프로젝트] 버튼
  → 프로젝트 이름 입력 + 아이디어 텍스트 입력
  → DB에 프로젝트 저장
  → root/kknaks_pr/{proj_name}/ 디렉토리 생성
  → Claude Code가 idea.md 작성
     → root/kknaks_pr/{proj_name}/idea.md
  → Claude Code 플러그인 설치 (코드 품질 도구)
  → 5개 에이전트 생성:
     → root/kknaks_pr/{proj_name}/.claude/agent/pm-agent.md
     → root/kknaks_pr/{proj_name}/.claude/agent/planner-agent.md
     → root/kknaks_pr/{proj_name}/.claude/agent/backend-agent.md
     → root/kknaks_pr/{proj_name}/.claude/agent/frontend-agent.md
     → root/kknaks_pr/{proj_name}/.claude/agent/design-agent.md
  → 에이전트 조직도 구성 (PM ↔ 각 에이전트 연결)
  → 각 에이전트 skills 파일 생성:
     → root/kknaks_pr/{proj_name}/.claude/skills/{part}.md
  → 대시보드 기본 플로우 생성 (기획 → BE/FE검증 → 구현)
```

### 6.2 기획하기

아이디어를 바탕으로 기획을 구체화하는 단계.

#### 기획 구체화
- 사전 정의된 기획 폼(`root/kknaks_pr/common/plan_form.md`)을 기반으로 아이디어 구체화
- 유저와 AI(Planner Agent)가 채팅으로 대화하며 내용 업데이트
  - 예: "유저 플로우에 대해 설명해줄 수 있나요?"
  - 예: "결제 기능도 필요해요"
- Claude Code 플러그인 활용하여 전문적 구체화
  - 예: [Superpowers](https://github.com/obra/superpowers) — brainstorming, planning, TDD 자동 적용

#### 기획 검증 플로우

```
Planner Agent: 기획 문서 작성
  ↓
[자체 평가] 기획 완성도 80% 이상?
  → NO → 계속 구체화 (유저와 대화)
  → YES ↓
  ↓
PM Agent에게 전달
  ↓
PM → Backend Agent: "백엔드 관점에서 검토해주세요"
PM → Frontend Agent: "프론트엔드 관점에서 검토해주세요"
PM → Design Agent: "디자인 관점에서 검토해주세요"
  ↓
각 에이전트 검토 결과 → PM에게 전달
  ↓
PM: 검토 결과 취합 → 유저에게 전달 (채팅)
  ↓
유저 선택:
  ├── [승인] → PRD.md 작성 → root/kknaks_pr/{proj_name}/PRD.md
  └── [추가 의견] → PM 전달 → 각 에이전트 수정
       → PM 전달 → Planner 기획 수정 → PM 취합 → 유저 재확인
       (승인될 때까지 반복)
```

### 6.3 스프린트 플랜

```
PRD.md 확정
  ↓
사전 정의된 스프린트 폼(root/kknaks_pr/common/plan_phase.md) + PRD.md
  ↓
PM Agent: 스프린트 Plan 작성
  → root/kknaks_pr/{proj_name}/Phase.md
  → 대시보드에 전체 상세 플로우 자동 생성
     (각 스프린트 → 기능별 BE/FE/Design/테스트 노드)
```

### 6.4 구현하기

스프린트 플랜 문서를 기반으로 스프린트 실행.

```
PM Agent: 총괄 관리
  │
  ├── 명령 하달 → Backend Agent: 기능 구현
  │                → 기능 구현 → 테스트 → 수정 (반복)
  │                → 완성 시 PM에게 보고
  │
  ├── 명령 하달 → Frontend Agent: 기능 구현
  │                → 기능 구현 → 테스트 → 수정 (반복)
  │                → 완성 시 PM에게 보고
  │
  ├── 명령 하달 → Design Agent: UI/UX 작업
  │                → 완성 시 PM에게 보고
  │
  ├── 에러/결정사항 발생
  │   → PM이 유저에게 질문 (채팅)
  │   → 유저 결정 → PM이 각 에이전트에 전달
  │
  └── 유저 질문 시
      → PM이 현재 상황 체크 + 보고 (언제든 가능)

대시보드: 전체 플로우 진행 상황 실시간 표시
  - 각 노드 상태 업데이트 (진행중/완료/에러)
  - 에이전트 간 통신 흐름 시각화
```

### 6.5 검증

```
각 에이전트 기능 구현 완료
  ↓
통합 테스트 실행
  → 성공 → Docker Compose 생성 + 앱 실행
  → 실패 → PM이 에러 분석 → 해당 에이전트에 수정 지시
```

---

## 7. 에이전트 설계

### 7.1 에이전트 조직도

```
                    ┌──────────┐
                    │   유저    │
                    │ (클라이언트)│
                    └────┬─────┘
                         │ 채팅 (승인/피드백)
                    ┌────▼─────┐
                    │    PM    │
                    │  (총괄)   │
                    └────┬─────┘
          ┌──────────┬───┼───┬──────────┐
          ▼          ▼       ▼          ▼
     ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
     │Planner │ │Backend │ │Frontend│ │Design  │
     │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
     └────────┘ └────────┘ └────────┘ └────────┘
```

- **기본 소통:** 유저 ↔ PM (채팅 패널 기본값)
- **직접 소통:** 유저가 에이전트 탭 클릭 시 해당 에이전트와 직접 대화 가능
- PM이 각 에이전트에게 명령/수신
- 에이전트 간 직접 통신 없음 — 전부 PM 경유

### 7.2 에이전트별 역할

**PM Agent (총괄 책임자)**
- 파일: `.claude/agent/pm-agent.md`
- 역할: 전체 프로젝트 관리, 에이전트 간 조율, 유저 소통 창구
- 권한: 모든 에이전트에게 명령, 유저에게 보고/질문
- 기능:
  - 기획 검토 결과 취합 → 유저 전달
  - 스프린트 플랜 작성
  - 구현 단계 명령 하달 + 진행 관리
  - 에러/결정사항 유저에게 에스컬레이션
  - 유저 질문 시 현재 상황 체크 + 보고

**Planner Agent (기획자)**
- 파일: `.claude/agent/planner-agent.md`
- 역할: 아이디어 → 기획서 구체화
- 입력: idea.md + plan_form.md + 유저 피드백
- 출력: 기획 문서 (→ 검토 통과 시 PRD.md)
- 도구: Superpowers 등 Claude Code 플러그인

**Backend Agent (백엔드 개발자)**
- 파일: `.claude/agent/backend-agent.md`
- 역할: 백엔드 코드 구현 + 기획 검토(백엔드 관점)
- 입력: PRD.md + Phase.md + PM 명령
- 출력: 백엔드 코드 + API 스펙
- 작업 루프: 기능 구현 → 테스트 → 수정 (반복)

**Frontend Agent (프론트엔드 개발자)**
- 파일: `.claude/agent/frontend-agent.md`
- 역할: 프론트엔드 코드 구현 + 기획 검토(프론트 관점)
- 입력: PRD.md + Phase.md + API 스펙 + PM 명령
- 출력: 프론트엔드 코드
- 작업 루프: 기능 구현 → 테스트 → 수정 (반복)

**Design Agent (UI/UX 렌더링 전문가)**
- 파일: `.claude/agent/design-agent.md`
- 역할: UI/UX 렌더링 특화. 화면 구현 품질 담당
- 입력: PRD.md + Phase.md + PM 명령
- 출력:
  - 디자인 시스템 정의 (컬러/타이포/스페이싱 토큰)
  - Tailwind CSS 컴포넌트 스타일 가이드
  - 페이지별 레이아웃 구조 (컴포넌트 트리)
  - 반응형 브레이크포인트 정의
  - 애니메이션/인터랙션 스펙
- 기획 검토 시: UI/UX 관점 피드백 (사용성, 화면 흐름, 정보 구조)
- 구현 단계: Frontend Agent가 만든 UI를 검토 + 스타일 개선 지시

### 7.3 에이전트 실행 방식

#### 라이프사이클: On-demand Spawn

에이전트는 **상시 연결이 아니다.** PM이 필요한 시점에 spawn → 작업 완료 → 프로세스 종료.

```
PM이 Backend Agent에게 작업 지시
  → agent_tasks에 태스크 생성 (status: pending)
  → Claude Code CLI 프로세스 spawn (pty)
  → 작업 수행 (실시간 로그 → WebSocket)
  → 작업 완료
  → agent_tasks 상태 업데이트 (status: completed)
  → 프로세스 종료 (메모리 해제)
```

#### 실행 규칙

- **기본: 순차 실행** — PM이 한 에이전트 작업 완료 후 다음 에이전트 spawn
- **병렬 실행** — PM이 명시적으로 병렬 지시할 때만 (예: BE/FE/Design 동시 검토)
- **동시 최대 프로세스**: 설정 가능 (기본값 3)

#### Python 구현

```python
import subprocess, pty, os, select, asyncio, re

# ANSI escape code 제거 정규식
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b\[.*?[@-~]")

def strip_ansi(text: str) -> str:
    """pty 출력에서 ANSI escape code, 스피너, 컬러 코드 제거"""
    return ANSI_ESCAPE.sub("", text)

async def spawn_agent(agent: str, prompt: str, project_dir: str, task_id: int):
    """에이전트 프로세스 spawn → 작업 완료 → 종료"""
    # 1. 태스크 상태 업데이트
    await update_task_status(task_id, "running")

    # 2. Claude Code CLI spawn
    master, slave = pty.openpty()
    proc = subprocess.Popen(
        ["claude", "--dangerously-skip-permissions", "-p", prompt],
        stdout=slave, stderr=slave, stdin=slave,
        cwd=project_dir
    )
    os.close(slave)

    # 3. 실시간 로그 → WebSocket (ANSI 제거 후 전송)
    while proc.poll() is None:
        if select.select([master], [], [], 0.1)[0]:
            raw = os.read(master, 1024).decode("utf-8", errors="replace")
            clean = strip_ansi(raw)
            if clean.strip():  # 빈 문자열 전송 방지
                await websocket.send_text(clean)
        await asyncio.sleep(0)  # 이벤트 루프 양보

    # 4. 완료 → 프로세스 종료 + 상태 업데이트
    os.close(master)
    status = "completed" if proc.returncode == 0 else "failed"
    await update_task_status(task_id, status)
    return proc.returncode

# 병렬 실행 예시 (기획 검토: BE/FE/Design 동시)
async def parallel_review(project_dir: str, tasks: list):
    await asyncio.gather(*[
        spawn_agent(t["agent"], t["prompt"], project_dir, t["task_id"])
        for t in tasks
    ])
```

#### 에러 복구 & 타임아웃

에이전트 프로세스 크래시/행 방지를 위한 안전장치:

- **태스크 타임아웃**: 기본 10분. 초과 시 프로세스 강제 종료 + `agent_tasks.status = "failed"`
- **좀비 프로세스 정리**: 서버 시작 시 `status = "running"` 상태인 태스크를 `"failed"`로 일괄 업데이트
- **자동 재시도**: 실패 시 최대 1회 재시도 (무한 루프 방지). `agent_tasks.retry_count` 컬럼으로 추적
- **Graceful shutdown**: 서버 종료 시 실행 중 프로세스에 SIGTERM → 5초 대기 → SIGKILL

#### 태스크 취소

유저가 실행 중 작업을 중단할 수 있어야 한다:

- `POST /api/projects/{id}/cancel` — 실행 중인 모든 에이전트 프로세스 종료
- `POST /api/projects/{id}/tasks/{task_id}/cancel` — 특정 태스크만 취소
- 취소 시: 프로세스 SIGTERM → `agent_tasks.status = "cancelled"` → WebSocket으로 `task_update` 전송

### 7.4 에이전트 간 통신

통신 채널을 **역할별로 분리:**

| 채널 | 용도 | 예시 |
|------|------|------|
| **파일 시스템** | 코드/문서 공유 전용 | idea.md, PRD.md, Phase.md, API_SPEC.md, 소스 코드 |
| **DB (agent_tasks)** | 명령/상태 관리 | PM → BE "API 구현해" (pending → running → completed) |
| **DB (chat_messages)** | 유저 ↔ 에이전트 대화 이력 | 채팅 패널 메시지 저장 |

- **파일 시스템**: 에이전트가 생성/수정하는 산출물. 코드, 문서, 설정 파일
- **agent_tasks**: PM이 에이전트에게 내리는 명령 큐. 상태 추적 (pending → running → completed/failed)
- **chat_messages**: 유저와 에이전트 간 대화 기록. 에이전트 전환해도 히스토리 유지

### 7.5 공통 리소스

```
root/kknaks_pr/common/
├── plan_form.md        # 기획 구체화 폼 (사전 정의)
└── plan_phase.md       # 스프린트 플랜 폼 (사전 정의)
```

### 7.6 에이전트 시스템 프롬프트

각 에이전트 `.md` 파일에 포함되는 시스템 프롬프트 핵심 구조.

**PM Agent (`pm-agent.md`)**
```
# 역할
너는 프로젝트 PM(총괄 책임자)이다. 유저(클라이언트)와 에이전트 팀 사이의 소통 창구.

# 규칙
- 유저에게는 기술 용어 최소화, 쉬운 말로 보고
- 에이전트에게는 명확한 태스크 단위로 명령
- 에러/결정사항 발생 시 즉시 유저에게 에스컬레이션
- 각 에이전트 결과를 검토하고 품질 기준 미달 시 재작업 지시
- 유저가 질문하면 현재 진행 상황을 정확히 보고

# 산출물
- 스프린트 플랜 (Phase.md)
- 에이전트 간 작업 조율 기록
```

**Planner Agent (`planner-agent.md`)**
```
# 역할
너는 기획 전문가다. 비개발자의 아이디어를 실행 가능한 PRD로 변환한다.

# 규칙
- plan_form.md 폼 구조를 반드시 따른다
- 모호한 아이디어는 구체적 질문으로 명확화
- MVP 우선 접근 — 핵심 기능만 먼저
- 기술 스택: 생성 앱은 FastAPI + Next.js + PostgreSQL 고정
- 기획 완성도 80% 이상이라고 판단되면 PM에게 검토 요청

# 산출물
- 기획 문서 → 검토 통과 시 PRD.md
- 기능 목록, 유저 플로우, DB 스키마, API 설계, 화면 구성
```

**Backend Agent (`backend-agent.md`)**
```
# 역할
너는 백엔드 개발자다. FastAPI + SQLAlchemy + PostgreSQL 전문.

# 규칙
- PRD.md와 Phase.md를 반드시 참조
- TDD: 테스트 먼저 작성 → 구현 → 통과 확인
- API 스펙 문서(API_SPEC.md) 자동 생성 (Frontend Agent용)
- Poetry로 의존성 관리
- Alembic 마이그레이션 자동 생성
- 기능 완성 시 PM에게 보고

# 기획 검토 시
- API 실현 가능성, 성능 병목, DB 설계 적절성 검토
- 기술적 리스크 식별 + 대안 제시

# 산출물
- backend/ 디렉토리 코드
- API_SPEC.md
- 테스트 코드 + 통과 결과
```

**Frontend Agent (`frontend-agent.md`)**
```
# 역할
너는 프론트엔드 개발자다. Next.js (App Router) + TypeScript + Tailwind CSS 전문.

# 규칙
- PRD.md, Phase.md, API_SPEC.md를 반드시 참조
- Design Agent의 디자인 가이드를 따른다
- 컴포넌트 단위 개발 + Storybook 고려
- 반응형 필수 (모바일/태블릿/데스크톱)
- 기능 완성 시 PM에게 보고

# 기획 검토 시
- 화면 구현 난이도, UX 흐름, 상태 관리 복잡도 검토

# 산출물
- frontend/ 디렉토리 코드
- 컴포넌트 구조
```

**Design Agent (`design-agent.md`)**
```
# 역할
너는 UI/UX 렌더링 전문가다. 화면의 시각적 품질과 사용성을 책임진다.

# 규칙
- Tailwind CSS 기반 디자인 시스템 정의
- 컬러 팔레트, 타이포그래피, 스페이싱 토큰 명세
- 페이지별 레이아웃 구조 (컴포넌트 트리) 설계
- 반응형 브레이크포인트 정의
- 애니메이션/트랜지션 스펙
- Frontend Agent가 만든 UI 검토 + 개선점 피드백

# 기획 검토 시
- 정보 구조, 네비게이션 흐름, 시각적 일관성 검토
- 사용성(UX) 관점 피드백

# 산출물
- design_system.md (디자인 토큰 + 컴포넌트 가이드)
- 페이지별 레이아웃 명세
- UI 검토 피드백
```

### 7.7 공통 폼 내용

**plan_form.md (기획 구체화 폼)**

Planner Agent가 이 구조에 맞춰 아이디어를 구체화한다.

```markdown
# {프로젝트명} — 기획서

## 1. 개요
- 한줄 요약:
- 해결하려는 문제:
- 타겟 유저:

## 2. 핵심 기능
| 우선순위 | 기능명 | 설명 |
|---------|--------|------|
| P0 (필수) | | |
| P1 (중요) | | |
| P2 (있으면 좋음) | | |

## 3. 유저 플로우
- 메인 플로우 (핵심 시나리오):
- 서브 플로우:

## 4. 화면 구성
| 화면 | 설명 | 주요 컴포넌트 |
|------|------|-------------|
| | | |

## 5. 데이터 모델
- 핵심 엔티티:
- 관계:

## 6. API 설계
| 메서드 | 경로 | 설명 |
|--------|------|------|
| | | |

## 7. 기술 스택
- 백엔드: FastAPI + SQLAlchemy + PostgreSQL
- 프론트: Next.js (App Router) + TypeScript + Tailwind CSS
- (추가 라이브러리가 필요하면 여기 명시)

## 8. MVP 범위
- 포함:
- 제외 (Phase 2):
```

**plan_phase.md (스프린트 플랜 폼)**

PM Agent가 PRD 기반으로 스프린트를 나눈다.

```markdown
# {프로젝트명} — 스프린트 플랜

## 스프린트 개요
| 스프린트 | 기간 | 목표 | 담당 에이전트 |
|---------|------|------|-------------|
| S1 | 1주 | | BE/FE/Design |

## 스프린트 상세

### S1: {목표}
**백엔드 태스크:**
- [ ] ...

**프론트엔드 태스크:**
- [ ] ...

**디자인 태스크:**
- [ ] ...

**완료 조건:**
- ...

**의존성:**
- ...
```

### 7.8 프로젝트 상태 전이

```
                    ┌─────────┐
                    │ created │ ← 프로젝트 생성 + 에이전트 세팅 완료
                    └────┬────┘
                         │ POST /plan
                    ┌────▼────┐
              ┌────▶│planning │ ← Planner Agent 기획 구체화 중
              │     └────┬────┘
              │          │ 기획 완성도 80%+ → PM 전달
              │     ┌────▼─────┐
              │     │reviewing │ ← BE/FE/Design 검토 중
              │     └────┬─────┘
              │          │
              │     ┌────▼──────┐
              │     │user_review│ ← 유저 승인 대기
              │     └────┬──────┘
              │          │
              │    승인?  ├──── YES ──→ ┌──────────────────┐
              │          │              │ sprint_planning  │ ← Phase.md 작성 중
              └── NO ────┘              └────────┬─────────┘
            (피드백 → planning)                   │ Phase.md 확정
                                           ┌─────▼──────┐
                                           │implementing│ ← 에이전트 코드 구현 중
                                           └─────┬──────┘
                                                  │ 구현 완료
                                           ┌──────▼──┐
                                           │ testing │ ← 통합 테스트
                                           └────┬────┘
                                                 │
                                        성공?    ├──── YES ──→ ┌──────────┐
                                                 │              │completed │ ✅
                                        NO ──────┘              └──────────┘
                                        (에러 수정 → implementing)

                                        3회 실패 ──→ ┌────────┐
                                                      │ failed │ ❌
                                                      └────────┘
```

**전이 조건:**

| 현재 상태 | → 다음 상태 | 트리거 |
|----------|------------|--------|
| created | planning | `POST /api/projects/{id}/plan` |
| planning | reviewing | Planner 자체 평가 80%+ → PM 전달 |
| reviewing | user_review | 3에이전트 검토 완료 → PM 취합 |
| user_review | sprint_planning | `POST /api/projects/{id}/approve` |
| user_review | planning | `POST /api/projects/{id}/feedback` |
| sprint_planning | implementing | Phase.md 확정 → `POST /api/projects/{id}/implement` |
| implementing | testing | 전체 기능 구현 완료 |
| testing | completed | 통합 테스트 성공 |
| testing | implementing | 테스트 실패 → 에러 수정 |
| implementing | failed | 에러 수정 3회 실패 |

---

## 8. 디렉토리 구조

```
root/kknaks_pr/
├── common/                          # 공통 템플릿
│   ├── plan_form.md                 # 기획 폼
│   └── plan_phase.md                # 스프린트 폼
│
└── {proj_name}/                     # 프로젝트별 디렉토리
    ├── idea.md                      # 아이디어 원문
    ├── PRD.md                       # 확정된 기획서
    ├── Phase.md                     # 스프린트 플랜
    ├── .claude/
    │   ├── agent/                   # 에이전트 정의
    │   │   ├── pm-agent.md
    │   │   ├── planner-agent.md
    │   │   ├── backend-agent.md
    │   │   ├── frontend-agent.md
    │   │   └── design-agent.md
    │   └── skills/                  # 플러그인/스킬 정의
    │       ├── pm.md
    │       ├── planner.md
    │       ├── backend.md
    │       ├── frontend.md
    │       └── design.md
    ├── backend/                     # 백엔드 코드
    ├── frontend/                    # 프론트엔드 코드
    └── docker-compose.yml           # 앱 실행
```

---

## 9. 데이터 모델

### ERD

```
projects (1) ──→ (N) agent_logs
    │
    ├──→ (N) flow_nodes ──→ (self) parent_node_id
    │
    ├──→ (N) chat_messages
    │
    ├──→ (N) agent_tasks ──→ (N) token_usage
    │
    └──→ (N) token_usage

settings (독립)
```

### ORM 구성

- **SQLAlchemy 2.0** (async mode) + **asyncpg** 드라이버
- **Alembic** 마이그레이션 (autogenerate 활용)
- 모델 위치: `backend/models/`
- DB 세션: `backend/core/database.py` (async session factory)

```
backend/
├── models/
│   ├── __init__.py
│   ├── base.py          # DeclarativeBase + 공통 mixin (id, created_at, updated_at)
│   ├── project.py       # Project
│   ├── agent_log.py     # AgentLog
│   ├── flow_node.py     # FlowNode
│   ├── chat_message.py  # ChatMessage
│   ├── agent_task.py    # AgentTask
│   ├── token_usage.py   # TokenUsage
│   └── setting.py       # Setting
├── core/
│   └── database.py      # async engine + session
└── alembic/
    └── versions/        # 마이그레이션 파일
```

### 테이블 정의

#### projects

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 프로젝트 ID |
| name | VARCHAR(100) NOT NULL | 프로젝트 이름 |
| idea_text | TEXT NOT NULL | 원본 아이디어 |
| status | VARCHAR(30) NOT NULL DEFAULT 'created' | 상태 |
| project_path | VARCHAR(500) NOT NULL | 로컬 경로 |
| current_phase | VARCHAR(30) | 현재 스프린트 |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

**status 값:** `created` → `planning` → `reviewing` → `user_review` → `sprint_planning` → `implementing` → `testing` → `completed` / `failed`

> 상세 전이 조건은 섹션 7.8 참고.

#### agent_logs

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 로그 ID |
| project_id | INT FK → projects.id | 프로젝트 |
| agent | VARCHAR(20) NOT NULL | `pm` / `planner` / `backend` / `frontend` / `design` |
| action | VARCHAR(50) NOT NULL | 수행 작업 |
| log_text | TEXT NOT NULL | 로그 내용 |
| log_type | VARCHAR(10) DEFAULT 'info' | `info` / `error` / `success` / `question` |
| created_at | TIMESTAMP DEFAULT NOW() | |

#### flow_nodes

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 노드 ID |
| project_id | INT FK → projects.id | 프로젝트 |
| node_type | VARCHAR(30) NOT NULL | 노드 유형 |
| label | VARCHAR(100) NOT NULL | 표시 이름 |
| status | VARCHAR(20) DEFAULT 'pending' | `pending` / `active` / `completed` / `error` |
| parent_node_id | INT FK → flow_nodes.id | 상위 노드 |
| position_x | INT | 대시보드 X 좌표 |
| position_y | INT | 대시보드 Y 좌표 |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

#### chat_messages

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 메시지 ID |
| project_id | INT FK → projects.id | 프로젝트 |
| agent | VARCHAR(20) NOT NULL | 대화 대상 에이전트 (`pm` / `planner` / `backend` / `frontend` / `design`) |
| role | VARCHAR(10) NOT NULL | `user` / `agent` |
| content | TEXT NOT NULL | 메시지 내용 |
| created_at | TIMESTAMP DEFAULT NOW() | |

> 에이전트별로 대화 히스토리 분리. 에이전트 탭 전환 시 해당 agent의 메시지만 조회.

#### agent_tasks

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 태스크 ID |
| project_id | INT FK → projects.id | 프로젝트 |
| agent | VARCHAR(20) NOT NULL | 대상 에이전트 |
| command | TEXT NOT NULL | PM이 내린 명령 내용 |
| status | VARCHAR(20) NOT NULL DEFAULT 'pending' | 상태 |
| result_summary | TEXT | 작업 결과 요약 |
| retry_count | INT NOT NULL DEFAULT 0 | 재시도 횟수 (최대 1) |
| timeout_seconds | INT NOT NULL DEFAULT 600 | 타임아웃 (기본 10분) |
| started_at | TIMESTAMP | 실행 시작 시간 |
| completed_at | TIMESTAMP | 완료 시간 |
| created_at | TIMESTAMP DEFAULT NOW() | |

**status 값:** `pending` → `running` → `completed` / `failed` / `cancelled`

#### token_usage

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| project_id | INT FK → projects.id | 프로젝트 |
| agent_task_id | INT FK → agent_tasks.id NULL | 연관 태스크 (없을 수 있음) |
| agent | VARCHAR(20) NOT NULL | 에이전트 |
| input_tokens | INT NOT NULL DEFAULT 0 | 입력 토큰 수 |
| output_tokens | INT NOT NULL DEFAULT 0 | 출력 토큰 수 |
| estimated_cost_usd | DECIMAL(10,4) | 추정 비용 (USD) |
| created_at | TIMESTAMP DEFAULT NOW() | |

> 프로젝트별/에이전트별 비용 추적. Claude Code CLI stdout에서 토큰 사용량 파싱하여 기록.

#### settings

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| key | VARCHAR(50) UNIQUE NOT NULL | 설정 키 |
| value | TEXT NOT NULL | 설정 값 (암호화) |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

---

## 10. API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/settings/token` | Claude API 토큰 저장 + 검증 |
| GET | `/api/settings/token/status` | 토큰 설정 여부 확인 |
| POST | `/api/projects` | 새 프로젝트 생성 (이름 + 아이디어) |
| GET | `/api/projects` | 프로젝트 목록 |
| GET | `/api/projects/{id}` | 프로젝트 상세 |
| DELETE | `/api/projects/{id}` | 프로젝트 삭제 |
| POST | `/api/projects/{id}/plan` | 기획 시작 (Planner Agent) |
| POST | `/api/projects/{id}/review` | 기획 검토 (BE/FE/Design) |
| POST | `/api/projects/{id}/approve` | 기획 승인 → PRD.md 확정 |
| POST | `/api/projects/{id}/feedback` | 기획 피드백 (추가 의견) |
| POST | `/api/projects/{id}/sprint` | 스프린트 플랜 생성 |
| POST | `/api/projects/{id}/implement` | 구현 시작 |
| POST | `/api/projects/{id}/run` | Docker Compose 실행 |
| POST | `/api/projects/{id}/stop` | Docker Compose 중지 |
| POST | `/api/projects/{id}/cancel` | 실행 중인 모든 에이전트 프로세스 종료 |
| POST | `/api/projects/{id}/tasks/{task_id}/cancel` | 특정 태스크만 취소 |
| GET | `/api/projects/{id}/cost` | 프로젝트 토큰 사용량 + 추정 비용 조회 |
| GET | `/api/projects/{id}/flow` | 대시보드 플로우 노드 조회 |
| GET | `/api/projects/{id}/agents` | 에이전트 상태 조회 |
| WS | `/ws/projects/{id}/chat` | 유저 ↔ 에이전트 실시간 채팅 |
| WS | `/ws/projects/{id}/logs` | 에이전트 로그 스트리밍 |

### 10.1 WebSocket 메시지 프로토콜

#### 채팅 WS (`/ws/projects/{id}/chat`)

**클라이언트 → 서버:**
```json
// 메시지 전송
{"type": "message", "agent": "pm", "content": "기획서 확인했습니다. 승인합니다."}

// 에이전트 전환
{"type": "switch_agent", "agent": "backend"}

// 채팅 히스토리 요청
{"type": "history", "agent": "planner", "limit": 50}
```

**서버 → 클라이언트:**
```json
// 에이전트 응답
{"type": "message", "agent": "pm", "role": "agent", "content": "검토 결과를 취합하겠습니다."}

// 에이전트 전환 확인
{"type": "agent_switched", "agent": "backend", "status": "idle"}

// 에이전트 상태 변경
{"type": "agent_status", "agent": "backend", "status": "running"}

// 히스토리 응답
{"type": "history", "agent": "planner", "messages": [...]}
```

#### 로그 WS (`/ws/projects/{id}/logs`)

**서버 → 클라이언트:**
```json
// 실행 로그
{"type": "log", "agent": "backend", "level": "info", "text": "API 엔드포인트 생성 중..."}

// 태스크 상태 변경
{"type": "task_update", "task_id": 12, "agent": "frontend", "status": "completed"}

// 플로우 노드 상태 변경
{"type": "flow_update", "node_id": 5, "status": "active"}
```

**`agent` 필드 값:** `pm` / `planner` / `backend` / `frontend` / `design`

---

## 10.2 프론트엔드 구현 요구사항

### 레이아웃
- **3패널 구조**: CSS Grid (`grid-template-columns: 250px 1fr 350px`)
- **패널 리사이즈**: `react-resizable-panels` 사용
- **데스크톱 전용**: 최소 1280px. 모바일/태블릿 미대응 (MVP)

### 플로우 에디터 (대시보드)
- **라이브러리**: React Flow (`reactflow`) — MIT, Next.js + TypeScript 호환
- **자동 레이아웃**: `dagre` 조합 (노드 위치 자동 계산, `flow_nodes.position_x/y`는 dagre 결과 캐시용)
- **실시간 업데이트**: WS `flow_update` 메시지 수신 시 노드 상태 색상 변경

### 채팅 패널
- **에이전트 전환**: WS 단일 연결에서 `agent` 필드로 라우팅 (연결 재생성 없음)
- **Unread badge**: 현재 보고 있지 않은 에이전트에서 메시지 오면 버튼에 빨간 dot 표시
- **스크롤 위치 보존**: 에이전트별로 스크롤 위치 저장, 전환 시 복원
- **에이전트 버튼 바 위치**: 채팅 패널 상단 탭 형태 (대시보드 하단 → 채팅 상단 이동 권장, 시선 이동 최소화)

### 로그 패널
- **가상 스크롤**: `@tanstack/react-virtual` 또는 `react-window` 사용 (장시간 실행 시 로그 수천 줄 → DOM 성능 보호)
- **에이전트별 필터**: 에이전트 태그 토글로 특정 에이전트 로그만 표시

### WebSocket
- **자동 재연결**: 지수 백오프 (1s → 2s → 4s, 최대 3회). 에이전트 실행 10~30분이므로 연결 유지 중요
- **연결 상태 UI**: 헤더에 연결 상태 표시 (🟢 연결 / 🟡 재연결 중 / 🔴 끊김)

### 비용 추적 UI
- 헤더 또는 사이드바에 **실시간 토큰 비용** 표시 (`GET /api/projects/{id}/cost` 폴링 또는 WS 이벤트)
- 에이전트별 비용 breakdown

### 상태 관리
- **zustand** — 프로젝트 상태, 채팅 메시지, 에이전트 상태, 로그 관리
- **에이전트 프로세스 상태 감지**: WS `agent_status` 이벤트로 UI 반영 + 에러 시 재시작 버튼 표시

---

## 11. 비기능 요구사항

### 11.1 보안
- Claude API 토큰: AES-256 암호화 저장
- `--dangerously-skip-permissions` → 프로젝트 디렉토리 격리 필수
- 생성된 코드: Docker 컨테이너 내 실행 (호스트 격리)

### 11.2 성능 예상
- 프로젝트 생성 + 에이전트 세팅: ~1~2분
- 기획 구체화: ~5~15분 (유저 대화 포함)
- 기획 검토 (3에이전트): ~3~5분
- 스프린트 플랜: ~2~3분
- 구현 (스프린트당): ~10~30분 (복잡도에 따라)
- **총: 기획~완성 ~1~2시간**

### 11.3 비용 (사용자 부담)
- Claude API 비용만 발생
- 에이전트 5개 × 여러 턴 → 프로젝트당 ~$5~20 예상
- 에러 수정 루프 추가 시 비용 증가

### 11.4 설치 요구사항
- Node.js 18+
- Python 3.10+
- PostgreSQL 15+
- Docker + Docker Compose
- Claude Code CLI (`claude` 명령어)

---

## 12. 마일스톤

> SPRINT_PLAN.md와 동기화. 6스프린트 11주 계획.

| 스프린트 | 기간 | 내용 | 병렬 |
|---------|------|------|------|
| S1 | 1주 | 프로젝트 세팅 + DB 스키마 + Docker 개발환경 | - |
| S2 | 2주 | 토큰 설정 + 프로젝트 CRUD + 3패널 레이아웃 | ⚡ BE/FE |
| S3 | 2주 | 에이전트 엔진 (pty spawn) + 채팅/로그 WebSocket | ⚡ BE/FE |
| S4 | 2주 | 기획 플로우 (Planner + 검토 + 승인) + 대시보드 시각화 | ⚡ BE/FE |
| S5 | 2주 | 구현 플로우 (PM 총괄 + 스프린트) + 에러 자동 수정 | - |
| S6 | 2주 | Docker 실행 + 통합 테스트 + UI 폴리싱 | - |

**총 예상: ~11주**

---

## 13. MVP 제외사항
- 멀티 스택 지원 (생성 앱 스택 선택)
- 대화형 수정 ("이 부분 바꿔줘" — 완성 후 수정)
- GitHub push / ZIP 내보내기
- 템플릿 라이브러리
- 멀티 유저 / 인증
- 클라우드 배포

---

## 14. 합의 사항
- 타겟 유저: 비개발자 (클라이언트 역할)
- 자체 스택: Next.js + Python(FastAPI) + PostgreSQL
- 생성 앱 스택: MVP FastAPI + Next.js + PostgreSQL 고정, Phase 2 가변
- UI: 단일 페이지 3패널 (목록 + 대시보드 + 채팅)
- 에이전트 5명: PM / Planner / Backend / Frontend / Design
- 유저 ↔ 에이전트 직접 대화 가능 (에이전트 탭 클릭으로 전환, 기본값은 PM)
- 에이전트 실행: Claude Code CLI pty spawn
- 에이전트 간 통신: 파일 시스템 기반
- 에이전트 정의: `.claude/agent/{part}-agent.md`
- 스킬 정의: `.claude/skills/{part}.md`
- 공통 폼: `root/kknaks_pr/common/plan_form.md`, `plan_phase.md`
- 기획 승인 플로우: Planner 작성 → PM 전달 → 3에이전트 검토 → PM 취합 → 유저 승인/피드백 루프
- 구현: PM 명령 → 에이전트 실행 → 기능구현→테스트→수정 반복 → PM 보고

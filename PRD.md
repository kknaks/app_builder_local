# App Builder Local — PRD

> 최종 수정일: 2026-03-05

## 1. 개요

### 1.1 한줄 요약
로컬 설치형 앱 빌더 — Claude API 토큰만 있으면 아이디어 입력 → 앱 자동 생성

### 1.2 배경
Bolt.new, Lovable, Cursor Composer 등 AI 앱 빌더가 등장했지만:
- **클라우드 의존**: 코드가 외부 서버에서 생성/실행됨
- **비용 불투명**: 월 구독 + 사용량 과금
- **커스텀 한계**: 정해진 템플릿/스택 안에서만 동작

**App Builder Local**은 내 로컬에서 전부 돌아가고, 사용자의 Claude API 토큰만 있으면 된다. 서버 비용 없음, 데이터 유출 없음.

### 1.3 타겟 유저
- **비개발자** — 아이디어는 있지만 코딩을 모르는 사람
- 프롬프트 엔지니어링, 기술 스택 선택, 프로젝트 구조 설계를 전부 시스템이 처리

### 1.4 핵심 가치
| 가치 | 설명 |
|------|------|
| 로컬 전용 | 내 컴퓨터에서 전부 실행. 클라우드 없음 |
| 비용 투명 | Claude API 토큰 비용만. 서버 비용 없음 |
| 원클릭 | 아이디어 입력 → 앱 완성까지 자동 |
| 에러 자가 수정 | 빌드/테스트 실패 시 자동 수정 루프 |

---

## 2. 기술 스택

### App Builder Local 자체 스택

| 레이어 | 기술 | 비고 |
|--------|------|------|
| 프론트엔드 | Next.js | 로컬 웹 대시보드 |
| 백엔드 | Python (FastAPI) | 오케스트레이터 + API 서버 |
| DB | PostgreSQL | 프로젝트/실행 이력/설정 관리 |
| AI 에이전트 | Claude Code CLI | `claude --dangerously-skip-permissions` (pty spawn) |
| 실시간 통신 | WebSocket | 빌드 로그 실시간 스트리밍 |
| 앱 실행 | Docker Compose | 생성된 앱 로컬 실행 |

### 생성되는 앱의 스택
- MVP: 고정 스택 (추후 결정)
- Phase 2: 사용자 선택 가능 (멀티 스택 지원)

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────┐
│              Next.js 웹 UI              │
│  (토큰 설정 / 아이디어 입력 / 대시보드)  │
└───────────────┬─────────────────────────┘
                │ REST + WebSocket
┌───────────────▼─────────────────────────┐
│         Python 오케스트레이터            │
│  (FastAPI + 에이전트 조율 + 상태 관리)   │
├─────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ Planner  │→│ Backend  │→│ Frontend ││
│  │ Agent    │ │ Agent    │ │ Agent    ││
│  └──────────┘ └──────────┘ └──────────┘│
│         ↓ 각 에이전트 = Claude Code CLI  │
├─────────────────────────────────────────┤
│         에러 감지 + 자동 수정 루프       │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│    프로젝트 디렉토리 (격리)              │
│    └── docker-compose.yml               │
│    └── backend/ frontend/ ...           │
└───────────────┬─────────────────────────┘
                │ docker compose up
┌───────────────▼─────────────────────────┐
│         생성된 앱 (localhost)            │
└─────────────────────────────────────────┘
```

---

## 4. 핵심 기능

### MVP (Phase 1)

| ID | 기능 | 설명 |
|----|------|------|
| F1 | 토큰 설정 | Claude API 토큰 입력 + 유효성 검증 + 로컬 저장 |
| F2 | 아이디어 입력 | 자연어로 앱 아이디어 입력 ("쇼핑몰 만들어줘" 수준) |
| F3 | 기획 에이전트 (Planner) | 아이디어 → PRD 자동 작성 (기능 목록, 기술 스택, DB 설계) |
| F4 | 백엔드 에이전트 (Backend) | PRD 기반 백엔드 코드 자동 생성 |
| F5 | 프론트엔드 에이전트 (Frontend) | PRD + 백엔드 API 스펙 기반 프론트엔드 코드 자동 생성 |
| F6 | 빌드 로그 스트리밍 | 에이전트 실행 로그 WebSocket으로 실시간 표시 |
| F7 | 에러 자동 수정 | 빌드/테스트 실패 시 에이전트가 자동으로 수정 시도 (최대 3회) |
| F8 | 앱 실행 | Docker Compose 자동 생성 + 원클릭 실행 → localhost URL 반환 |
| F9 | 프로젝트 관리 | 생성된 프로젝트 목록 조회 / 삭제 / 재실행 |

### Phase 2 (후순위)

| ID | 기능 | 설명 |
|----|------|------|
| F10 | 멀티 스택 지원 | 생성 앱 스택 사용자 선택 |
| F11 | 병렬 에이전트 실행 | Backend + Frontend 동시 실행 |
| F12 | 대화형 수정 | 생성된 앱에 "이 부분 바꿔줘" 자연어 수정 |
| F13 | 프로젝트 내보내기 | GitHub push / ZIP 다운로드 |
| F14 | 템플릿 라이브러리 | 자주 쓰는 앱 유형 템플릿 (쇼핑몰, 블로그, TODO 등) |

---

## 5. 사용자 플로우

### 5.1 최초 설정
```
앱 실행 (localhost:3000)
  → 토큰 입력 화면
  → Claude API 토큰 입력
  → [검증] 버튼 → API 호출로 유효성 확인
  → 성공 → 대시보드로 이동
  → 실패 → 에러 메시지 + 재입력
```

### 5.2 앱 생성 플로우
```
대시보드
  → [새 프로젝트] 버튼
  → 아이디어 입력 화면
    "어떤 앱을 만들고 싶으세요?"
    텍스트 에어리어 (자유 입력)
    예시: "카페 주문 관리 앱. 메뉴 등록, 주문 접수, 매출 통계"
  → [생성 시작] 버튼

빌드 화면 (3단계 진행 표시)
  ┌─────────────────────────────────────┐
  │ ● Step 1: 기획 중...               │ ← Planner Agent
  │   PRD 작성 중 (실시간 로그)         │
  │ ○ Step 2: 백엔드 생성 대기          │ ← Backend Agent
  │ ○ Step 3: 프론트엔드 생성 대기      │ ← Frontend Agent
  └─────────────────────────────────────┘
  하단: 실시간 터미널 로그 (WebSocket)

  → Step 1 완료: PRD 미리보기 표시
     [계속 진행] / [PRD 수정 후 진행] 선택
  → Step 2 완료: 백엔드 코드 생성 완료
  → Step 3 완료: 프론트엔드 코드 생성 완료

  → 에러 발생 시:
     "빌드 오류가 발생했습니다. 자동 수정 시도 중... (1/3)"
     → 수정 성공 → 계속 진행
     → 3회 실패 → 유저에게 알림 + 로그 표시

완료 화면
  → "앱이 완성되었습니다! 🎉"
  → [앱 실행] 버튼 → docker compose up → localhost URL 표시
  → [프로젝트 폴더 열기] 버튼
  → [대시보드로 돌아가기]
```

---

## 6. 에이전트 설계

### 6.1 에이전트 실행 방식
- 각 에이전트는 `claude --dangerously-skip-permissions` CLI를 pty로 spawn
- 프로젝트별 격리 디렉토리에서 실행: `~/app_builder_projects/{project_id}/`
- 에이전트 간 데이터 전달: 파일 시스템 기반 (PRD.md, API_SPEC.md 등)

#### Python 구현 상세

Claude Code는 CLI 도구이므로 Python `subprocess`로 직접 실행한다.

**기본 실행 (결과만 받기):**
```python
import subprocess

result = subprocess.run(
    ["claude", "--dangerously-skip-permissions", "-p", prompt],
    capture_output=True, text=True,
    cwd=f"projects/{project_id}/"
)
output = result.stdout
```

**실시간 스트리밍 (pty + WebSocket):**
```python
import pty, os, subprocess, select

master, slave = pty.openpty()
proc = subprocess.Popen(
    ["claude", "--dangerously-skip-permissions", "-p", prompt],
    stdout=slave, stderr=slave, stdin=slave,
    cwd=f"projects/{project_id}/"
)
os.close(slave)

# master fd에서 실시간 읽기 → WebSocket으로 프론트엔드 전달
while proc.poll() is None:
    if select.select([master], [], [], 0.1)[0]:
        chunk = os.read(master, 1024).decode("utf-8", errors="replace")
        await websocket.send_text(chunk)  # FastAPI WebSocket
```

**에이전트별 실행 예시:**
```python
# Planner Agent
proc = spawn_claude(
    prompt=f"이 아이디어로 PRD.md를 작성해: {idea_text}",
    cwd=f"projects/{project_id}/"
)

# Backend Agent
proc = spawn_claude(
    prompt="PRD.md를 읽고 백엔드를 구현해. 완료 후 API_SPEC.md를 생성해.",
    cwd=f"projects/{project_id}/"
)

# Frontend Agent
proc = spawn_claude(
    prompt="PRD.md와 API_SPEC.md를 읽고 프론트엔드를 구현해.",
    cwd=f"projects/{project_id}/"
)
```

> Claude Code CLI는 언어에 종속되지 않는 프로세스 spawn 방식. Python, Node.js, Go 등 어떤 언어든 subprocess로 실행 가능.

### 6.2 에이전트별 역할

**Planner Agent (F3)**
- 입력: 사용자 아이디어 (자연어)
- 출력: `PRD.md` (기능 목록, 기술 스택, DB 스키마, API 설계)
- 프롬프트: "비개발자의 아이디어를 실행 가능한 PRD로 변환하라"

**Backend Agent (F4)**
- 입력: `PRD.md`
- 출력: 백엔드 코드 + `API_SPEC.md` (프론트엔드 에이전트용)
- 프롬프트: "PRD를 기반으로 백엔드를 구현하라. 완료 후 API 스펙 문서를 생성하라"

**Frontend Agent (F5)**
- 입력: `PRD.md` + `API_SPEC.md`
- 출력: 프론트엔드 코드 + `docker-compose.yml`
- 프롬프트: "PRD와 API 스펙을 기반으로 프론트엔드를 구현하라"

### 6.3 에러 자동 수정 루프 (F7)

```
에이전트 실행 완료
  → 빌드 테스트 실행 (lint + build + 기본 테스트)
  → 성공 → 다음 단계로
  → 실패 → 에러 로그를 에이전트에게 전달
    → "다음 에러를 수정하라: {에러 로그}"
    → 수정 후 재빌드 (최대 3회)
    → 3회 실패 → 유저에게 수동 개입 요청
```

---

## 7. 화면 구성

### 7.1 화면 목록

| 화면 | 설명 |
|------|------|
| 토큰 설정 | API 토큰 입력 + 검증 |
| 대시보드 | 프로젝트 목록 + [새 프로젝트] 버튼 |
| 아이디어 입력 | 앱 아이디어 자연어 입력 |
| 빌드 진행 | 3단계 진행 표시 + 실시간 로그 |
| PRD 미리보기 | Planner 결과 확인 + 수정/계속 선택 |
| 완료 | 앱 실행 버튼 + 프로젝트 폴더 열기 |
| 프로젝트 상세 | 기존 프로젝트 상태 조회 / 재실행 / 삭제 |

### 7.2 대시보드

```
┌──────────────────────────────────────────────┐
│  App Builder Local                    ⚙️     │
├──────────────────────────────────────────────┤
│                                              │
│  내 프로젝트                    [+ 새 프로젝트]│
│                                              │
│  ┌────────────┐ ┌────────────┐               │
│  │ 카페 주문앱 │ │ TODO 앱    │               │
│  │ ✅ 완료     │ │ 🔄 빌드중   │               │
│  │ 2026-03-05 │ │ 2026-03-05 │               │
│  └────────────┘ └────────────┘               │
│                                              │
└──────────────────────────────────────────────┘
```

### 7.3 빌드 진행 화면

```
┌──────────────────────────────────────────────┐
│  ← 카페 주문 관리 앱                         │
├──────────────────────────────────────────────┤
│                                              │
│  ✅ Step 1: 기획 완료                         │
│  ● Step 2: 백엔드 생성 중...  ██████░░ 75%   │
│  ○ Step 3: 프론트엔드 대기                    │
│                                              │
│  ┌──────────────────────────────────────────┐│
│  │ $ claude "PRD를 기반으로 FastAPI..."      ││
│  │ > models.py 생성 중...                    ││
│  │ > routes/order.py 작성 완료               ││
│  │ > database.py 설정 중...                  ││
│  │ █                                        ││
│  └──────────────────────────────────────────┘│
│                                              │
│  예상 소요: ~5분          토큰 사용: 12,450   │
└──────────────────────────────────────────────┘
```

---

## 8. 데이터 모델

### 8.1 테이블

**projects**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 프로젝트 ID |
| name | VARCHAR(100) NOT NULL | 프로젝트 이름 (아이디어에서 자동 추출) |
| idea_text | TEXT NOT NULL | 원본 아이디어 텍스트 |
| status | VARCHAR(20) NOT NULL DEFAULT 'created' | 상태 |
| project_path | VARCHAR(500) NOT NULL | 로컬 프로젝트 경로 |
| docker_port | INT | Docker 실행 포트 |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

**status 값:** `created` → `planning` → `building_backend` → `building_frontend` → `testing` → `completed` / `failed`

**build_logs**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 로그 ID |
| project_id | INT FK → projects.id | 프로젝트 |
| step | VARCHAR(20) NOT NULL | `planner` / `backend` / `frontend` / `test` |
| log_text | TEXT NOT NULL | 로그 내용 |
| log_type | VARCHAR(10) DEFAULT 'info' | `info` / `error` / `success` |
| created_at | TIMESTAMP DEFAULT NOW() | |

**settings**

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | |
| key | VARCHAR(50) UNIQUE NOT NULL | 설정 키 |
| value | TEXT NOT NULL | 설정 값 (암호화) |
| created_at | TIMESTAMP DEFAULT NOW() | |
| updated_at | TIMESTAMP DEFAULT NOW() | |

> Claude API 토큰은 `settings` 테이블에 암호화 저장.

---

## 9. API 엔드포인트 (오케스트레이터)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/settings/token` | Claude API 토큰 저장 + 검증 |
| GET | `/api/settings/token/status` | 토큰 설정 여부 확인 |
| POST | `/api/projects` | 새 프로젝트 생성 (아이디어 입력) |
| GET | `/api/projects` | 프로젝트 목록 조회 |
| GET | `/api/projects/{id}` | 프로젝트 상세 조회 |
| DELETE | `/api/projects/{id}` | 프로젝트 삭제 |
| POST | `/api/projects/{id}/build` | 빌드 시작 (에이전트 순차 실행) |
| POST | `/api/projects/{id}/run` | Docker Compose 실행 |
| POST | `/api/projects/{id}/stop` | Docker Compose 중지 |
| WS | `/ws/projects/{id}/logs` | 빌드 로그 실시간 스트리밍 |

---

## 10. 비기능 요구사항

### 10.1 보안
- Claude API 토큰: AES-256 암호화 저장
- `--dangerously-skip-permissions` 사용 → 프로젝트 디렉토리 격리 필수
- 생성된 코드는 Docker 컨테이너 내에서만 실행 (호스트 격리)

### 10.2 성능
- Planner: ~1~2분 (아이디어 복잡도에 따라)
- Backend Agent: ~3~5분
- Frontend Agent: ~3~5분
- 총 예상 소요: **~10~15분/프로젝트**

### 10.3 비용 (사용자 부담)
- Claude API 비용만 발생
- 예상: 프로젝트 1개당 ~$1~5 (복잡도에 따라)
- 에러 수정 루프 추가 시 +$0.5~1/회

### 10.4 설치 요구사항
- Node.js 18+
- Python 3.10+
- PostgreSQL 15+
- Docker + Docker Compose
- Claude Code CLI (`claude` 명령어)

---

## 11. 마일스톤

| 단계 | 내용 | 예상 기간 |
|------|------|----------|
| M1 | 프로젝트 세팅 (Next.js + FastAPI + PostgreSQL + Docker) | 1주 |
| M2 | 토큰 설정 + 대시보드 UI + 프로젝트 CRUD | 1주 |
| M3 | Planner Agent 구현 + PRD 미리보기 | 1주 |
| M4 | Backend Agent + Frontend Agent 구현 | 2주 |
| M5 | 에러 자동 수정 루프 + 빌드 로그 스트리밍 | 1주 |
| M6 | Docker Compose 자동 생성 + 앱 실행 | 1주 |
| M7 | 통합 테스트 + UI 폴리싱 | 1주 |

**총 예상: ~8주**

---

## 12. MVP 제외사항
- 멀티 스택 지원 (생성 앱 스택 선택)
- 병렬 에이전트 실행
- 대화형 수정 ("이 부분 바꿔줘")
- GitHub push / ZIP 내보내기
- 템플릿 라이브러리
- n8n 스타일 GUI 에디터
- 멀티 유저 / 인증
- 클라우드 배포

---

## 13. 합의 사항
- 타겟 유저: 비개발자
- 자체 스택: Next.js + Python(FastAPI) + PostgreSQL
- 생성 앱 스택: MVP에서 고정 (추후 결정), Phase 2에서 가변
- 에러 자동 수정: MVP 필수 (최대 3회 재시도)
- 에이전트 실행: Claude Code CLI 직접 spawn (pty)
- 에이전트 간 통신: 파일 시스템 기반 (PRD.md, API_SPEC.md)

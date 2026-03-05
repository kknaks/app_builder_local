# 🏗️ App Builder Local

> 로컬 설치형 AI 개발팀 — Claude Code 에이전트 조직(PM/기획/백엔드/프론트/디자인)이 아이디어를 앱으로 만들어주는 플랫폼

AI 에이전트 5명이 실제 개발 조직처럼 협업하여, **아이디어 입력 한 번**으로 완성된 앱을 만들어줍니다.

## ✨ 주요 기능

- **AI 개발팀** — PM + 기획자 + 백엔드 + 프론트엔드 + 디자이너 5명의 에이전트 협업
- **로컬 전용** — 내 컴퓨터에서 전부 실행, 클라우드 없음
- **비용 투명** — Claude API 토큰 비용만 발생
- **유저 = 클라이언트** — 코딩 몰라도 OK, 승인/피드백만 하면 됨
- **원클릭 실행** — Docker Compose로 생성된 앱 바로 실행 + localhost URL 제공
- **실시간 대시보드** — n8n 스타일 플로우 노드로 진행 상황 시각화
- **에이전트 채팅** — 각 에이전트와 1:1 대화, 실시간 로그 스트리밍

## 📋 요구사항

| 소프트웨어 | 버전 | 비고 |
|-----------|------|------|
| Node.js | 18+ | 프론트엔드 빌드 |
| Python | 3.10+ | 백엔드 서버 |
| PostgreSQL | 15+ | 데이터베이스 |
| Docker & Docker Compose | 최신 | 생성된 앱 실행 |
| Claude Code CLI | 최신 | AI 에이전트 실행 (`claude` 명령어) |

## 🚀 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/kknaks/app_builder_local.git
cd app_builder_local
```

### 2. PostgreSQL 준비

Docker로 PostgreSQL을 실행하거나 로컬에 설치된 PostgreSQL을 사용하세요.

```bash
# Docker로 PostgreSQL 실행 (간편)
docker run -d \
  --name app-builder-pg \
  -e POSTGRES_USER=appbuilder \
  -e POSTGRES_PASSWORD=appbuilder \
  -e POSTGRES_DB=app_builder \
  -p 5432:5432 \
  postgres:15

# 또는 로컬 PostgreSQL에서 DB 생성
# createdb -U postgres app_builder
```

### 3. 백엔드 설정

```bash
cd backend

# Poetry 설치 (없는 경우)
pip install poetry

# 의존성 설치
poetry install

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 DATABASE_URL 등을 설정하세요
# DATABASE_URL=postgresql+asyncpg://appbuilder:appbuilder@localhost:5432/app_builder

# DB 마이그레이션
poetry run alembic upgrade head

# 백엔드 서버 실행 (포트 28888)
poetry run uvicorn app.main:app --host 0.0.0.0 --port 28888 --reload
```

### 4. 프론트엔드 설정

새 터미널을 열고:

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행 (포트 23000)
npm run dev
```

### 5. 브라우저에서 접속

```
http://localhost:23000
```

## 📖 사용법

### Step 1: API 토큰 설정

첫 접속 시 **Claude API 토큰 설정** 모달이 표시됩니다.

1. [Anthropic Console](https://console.anthropic.com/)에서 API 키를 발급
2. `sk-ant-...` 형식의 토큰을 입력
3. **저장** 클릭 → 토큰이 암호화되어 저장됩니다

> 💡 우측 상단 ⚙️ 설정 버튼으로 언제든 토큰을 변경할 수 있습니다.

### Step 2: 프로젝트 생성

1. 좌측 패널의 **+ 새 프로젝트** 버튼 클릭
2. 프로젝트 이름 입력 (예: "할일 관리 앱")
3. 아이디어를 자유롭게 작성 (예: "할일을 등록하고 완료 체크할 수 있는 간단한 앱")
4. **프로젝트 생성** 클릭

### Step 3: 기획 구체화

1. 채팅 패널에서 **📝 기획 시작** 클릭
2. Planner 에이전트가 아이디어를 기획서로 구체화합니다
3. 채팅으로 추가 요구사항이나 수정사항을 전달하세요
4. 기획이 완성되면 BE/FE/Design 에이전트가 검토합니다

### Step 4: 기획 승인

1. 검토 결과가 카드 형태로 표시됩니다
2. **✅ 승인** 또는 **💬 피드백** 선택
3. 피드백 시 → 기획이 수정된 후 다시 검토 → 승인까지 반복

### Step 5: 구현

1. 승인 후 **📋 스프린트 플랜** 클릭 → PM이 구현 계획 수립
2. **🔨 구현 시작** 클릭 → 백엔드/프론트엔드 에이전트가 코드 구현
3. 대시보드에서 실시간 진행 상황 확인 (노드 색상: 회색=대기, 파랑=진행중, 초록=완료, 빨강=에러)
4. 에이전트 탭(PM/BE/FE/PL/DE)으로 개별 에이전트와 대화 가능
5. PM에게 "현재 상황?" 메시지로 진행 현황 확인 가능

### Step 6: 앱 실행

1. 구현 완료 후 **🚀 앱 실행** 버튼이 표시됩니다
2. 클릭하면 Docker Compose로 앱이 빌드 & 실행됩니다
3. 실행 완료 시 **localhost URL** 링크가 서비스별로 표시됩니다
4. 링크 클릭으로 생성된 앱을 브라우저에서 확인!
5. 📦 버튼으로 각 컨테이너의 상태/포트 상세 정보 확인 가능
6. **⏹ 중지** 또는 **🔄 재시작** 버튼으로 앱을 제어할 수 있습니다

## 🖥️ UI 구성

3패널 단일 페이지 구조:

```
┌──────────┬──────────────────────┬──────────────────┐
│  프로젝트  │      대시보드         │      채팅/로그    │
│   목록    │  (n8n 스타일 플로우)   │  (에이전트 대화)  │
│          │                      │                  │
│  트리뷰   │  [아이디어]→[기획]→   │  [PM][BE][FE]... │
│  +상태    │  [검토]→[구현]→[실행] │  채팅 + 로그      │
└──────────┴──────────────────────┴──────────────────┘
```

- **좌측**: 프로젝트 목록 + 진행 단계 트리 (상태 아이콘 포함)
- **중앙**: 대시보드 (React Flow 노드 그래프, 실시간 상태 업데이트)
- **우측**: 에이전트 채팅 (탭 전환) + 실행 로그 (가상 스크롤)

### UI 기능 하이라이트

- **토스트 알림**: 성공/실패/정보/경고 4가지 타입, 자동 dismiss
- **네트워크 에러 감지**: 백엔드 연결 끊김 시 상단 배너 + 토스트 알림
- **로딩 스켈레톤**: 프로젝트 목록, 대시보드, 채팅 영역
- **빈 상태 화면**: 프로젝트 없을 때 안내 + CTA 버튼
- **삭제 확인 다이얼로그**: 프로젝트 삭제 시 모달 확인
- **버튼 로딩 스피너**: 모든 비동기 액션에 로딩 상태 표시
- **WebSocket 자동 재연결**: 지수 백오프, 연결 상태 배지 표시
- **패널 리사이즈**: 드래그로 3패널 크기 자유 조절

## 🛠️ 기술 스택

### App Builder 자체

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | Next.js 15 + TypeScript + Tailwind CSS 4 |
| 플로우 에디터 | React Flow + dagre |
| 패널 리사이즈 | react-resizable-panels |
| 로그 가상 스크롤 | react-window |
| 상태 관리 | Zustand |
| 백엔드 | Python (FastAPI) |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| DB | PostgreSQL |
| AI 에이전트 | Claude Code CLI (pty spawn) |
| 실시간 통신 | WebSocket |
| 앱 실행 | Docker Compose (자동 생성) |

### 생성되는 앱

- **백엔드**: FastAPI + SQLAlchemy + PostgreSQL
- **프론트엔드**: Next.js (App Router) + TypeScript + Tailwind CSS

## 📁 프로젝트 구조

```
app_builder_local/
├── backend/                  # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py           # FastAPI 앱 엔트리포인트
│   │   ├── routers/          # API 라우터
│   │   │   ├── projects.py   # 프로젝트 CRUD
│   │   │   ├── settings.py   # 토큰 설정
│   │   │   ├── agents.py     # 에이전트 제어
│   │   │   ├── docker.py     # 앱 실행/중지
│   │   │   └── websocket.py  # WS 엔드포인트
│   │   ├── core/             # 에러 핸들러, 설정
│   │   ├── database/         # DB 세션, 모델
│   │   └── services/         # 비즈니스 로직
│   ├── alembic/              # DB 마이그레이션
│   ├── tests/                # pytest 테스트
│   └── pyproject.toml
├── frontend/                 # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/              # App Router 페이지
│   │   ├── components/       # React 컴포넌트
│   │   │   ├── RunPanel.tsx          # 앱 실행/중지 UI
│   │   │   ├── DashboardPanel.tsx    # n8n 스타일 플로우
│   │   │   ├── ChatPanel.tsx         # 에이전트 채팅
│   │   │   ├── LogPanel.tsx          # 실행 로그 (가상 스크롤)
│   │   │   ├── ProjectListPanel.tsx  # 프로젝트 목록
│   │   │   ├── ToastContainer.tsx    # 토스트 알림
│   │   │   └── ...
│   │   ├── hooks/            # 커스텀 훅 (useWebSocket)
│   │   ├── lib/              # API 클라이언트
│   │   └── store/            # Zustand 스토어
│   └── package.json
├── .claude/                  # 에이전트 정의
│   └── agents/
│       ├── backend.md
│       └── frontend.md
├── .progress/                # 스프린트 진행 기록
│   ├── TOTAL_REQUEST.md
│   ├── S1.md ~ S6.md
├── PRD.md                    # 제품 요구사항 문서
└── README.md
```

## ⚙️ 포트 설정 (고정)

| 서비스 | 포트 |
|--------|------|
| 프론트엔드 (Next.js) | 23000 |
| 백엔드 (FastAPI) | 28888 |
| PostgreSQL | 5432 (Docker 내부) |
| 생성된 앱 | 30000~39999 (자동 할당, 충돌 방지) |

## 🔌 API 엔드포인트

### REST API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/settings/token` | Claude API 토큰 저장 |
| GET | `/api/settings/token/status` | 토큰 설정 여부 확인 |
| POST | `/api/projects` | 새 프로젝트 생성 |
| GET | `/api/projects` | 프로젝트 목록 |
| GET | `/api/projects/{id}` | 프로젝트 상세 |
| DELETE | `/api/projects/{id}` | 프로젝트 삭제 |
| POST | `/api/projects/{id}/plan` | 기획 시작 |
| POST | `/api/projects/{id}/review` | 기획 검토 |
| POST | `/api/projects/{id}/approve` | 기획 승인 |
| POST | `/api/projects/{id}/feedback` | 기획 피드백 |
| POST | `/api/projects/{id}/sprint` | 스프린트 플랜 생성 |
| POST | `/api/projects/{id}/implement` | 구현 시작 |
| POST | `/api/projects/{id}/run` | Docker Compose 실행 |
| POST | `/api/projects/{id}/stop` | Docker Compose 중지 |
| GET | `/api/projects/{id}/run/status` | 컨테이너 상태 + URL |
| POST | `/api/projects/{id}/cancel` | 실행 중인 에이전트 중지 |
| GET | `/api/projects/{id}/cost` | 토큰 사용량/비용 조회 |
| GET | `/api/projects/{id}/flow` | 플로우 노드 조회 |

### WebSocket

| 경로 | 설명 |
|------|------|
| `/ws/projects/{id}/chat` | 에이전트 채팅 (실시간) |
| `/ws/projects/{id}/logs` | 실행 로그 스트리밍 |
| `/ws/projects/{id}/flow` | 플로우 노드 상태 업데이트 |

## 💰 비용

- **App Builder 자체**: 무료 (로컬 실행)
- **Claude API**: 프로젝트당 약 $5~20 (복잡도에 따라 상이)
- 실시간 토큰 비용 추적 UI 제공

## 🔧 트러블슈팅

### 백엔드 서버 연결 안 됨
- 상단에 빨간 배너가 표시되면 백엔드가 실행 중인지 확인
- `poetry run uvicorn app.main:app --host 0.0.0.0 --port 28888`

### Docker 앱 실행 안 됨
- Docker Desktop이 실행 중인지 확인
- `docker ps`로 컨테이너 상태 확인
- 포트 충돌 시 자동으로 다른 포트가 할당됩니다

### WebSocket 연결 끊김
- 우측 상단 연결 상태 배지 확인 (🟢연결됨/🟡재연결중/🔴끊김)
- 자동 재연결 (지수 백오프: 1s→2s→4s, 최대 3회)

## 📝 라이선스

MIT

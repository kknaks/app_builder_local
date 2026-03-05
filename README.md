# 🏗️ App Builder Local

> 로컬 설치형 AI 개발팀 — Claude Code 에이전트 조직(PM/기획/백엔드/프론트/디자인)이 아이디어를 앱으로 만들어주는 플랫폼

AI 에이전트 5명이 실제 개발 조직처럼 협업하여, **아이디어 입력 한 번**으로 완성된 앱을 만들어줍니다.

## ✨ 주요 기능

- **AI 개발팀** — PM + 기획자 + 백엔드 + 프론트엔드 + 디자이너 5명의 에이전트 협업
- **로컬 전용** — 내 컴퓨터에서 전부 실행, 클라우드 없음
- **비용 투명** — Claude API 토큰 비용만 발생
- **유저 = 클라이언트** — 코딩 몰라도 OK, 승인/피드백만 하면 됨
- **원클릭 실행** — Docker Compose로 생성된 앱 바로 실행

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

### 2. 백엔드 설정

```bash
cd backend

# Poetry 설치 (없는 경우)
pip install poetry

# 의존성 설치
poetry install

# 환경변수 설정 (.env 파일 생성)
cp .env.example .env
# .env 파일에서 DATABASE_URL 등 설정

# DB 마이그레이션
poetry run alembic upgrade head

# 백엔드 서버 실행 (포트 28888)
poetry run uvicorn app.main:app --host 0.0.0.0 --port 28888 --reload
```

### 3. 프론트엔드 설정

```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행 (포트 23000)
npm run dev
```

### 4. 브라우저에서 접속

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
3. 대시보드에서 실시간 진행 상황 확인
4. 에이전트 탭(PM/BE/FE/PL/DE)으로 개별 에이전트와 대화 가능

### Step 6: 앱 실행

1. 구현 완료 후 **🚀 앱 실행** 버튼이 표시됩니다
2. 클릭하면 Docker Compose로 앱이 빌드 & 실행됩니다
3. 실행 완료 시 **localhost URL** 링크가 표시됩니다
4. 링크 클릭으로 생성된 앱을 브라우저에서 확인!
5. **⏹ 중지** 버튼으로 앱을 중지할 수 있습니다

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

- **좌측**: 프로젝트 목록 + 진행 단계 트리
- **중앙**: 대시보드 (React Flow 노드 그래프, 실시간 상태 업데이트)
- **우측**: 에이전트 채팅 + 실행 로그

## 🛠️ 기술 스택

### App Builder 자체

| 레이어 | 기술 |
|--------|------|
| 프론트엔드 | Next.js + TypeScript + Tailwind CSS |
| 플로우 에디터 | React Flow + dagre |
| 패널 리사이즈 | react-resizable-panels |
| 로그 가상 스크롤 | react-window |
| 상태 관리 | Zustand |
| 백엔드 | Python (FastAPI) |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| DB | PostgreSQL |
| AI 에이전트 | Claude Code CLI (pty spawn) |
| 실시간 통신 | WebSocket |
| 앱 실행 | Docker Compose |

### 생성되는 앱

- **백엔드**: FastAPI + SQLAlchemy + PostgreSQL
- **프론트엔드**: Next.js (App Router) + TypeScript + Tailwind CSS

## 📁 프로젝트 구조

```
app_builder_local/
├── backend/              # FastAPI 백엔드
│   ├── app/
│   │   ├── main.py       # FastAPI 앱 엔트리포인트
│   │   ├── api/          # API 라우터
│   │   ├── core/         # DB, 설정
│   │   ├── models/       # SQLAlchemy 모델
│   │   └── services/     # 비즈니스 로직
│   ├── alembic/          # DB 마이그레이션
│   └── pyproject.toml
├── frontend/             # Next.js 프론트엔드
│   ├── src/
│   │   ├── app/          # App Router 페이지
│   │   ├── components/   # React 컴포넌트
│   │   ├── hooks/        # 커스텀 훅
│   │   ├── lib/          # API 클라이언트
│   │   └── store/        # Zustand 스토어
│   └── package.json
├── .claude/              # 에이전트 정의
├── .progress/            # 스프린트 진행 기록
├── PRD.md                # 제품 요구사항 문서
└── README.md
```

## ⚙️ 포트 설정

| 서비스 | 포트 |
|--------|------|
| 프론트엔드 (Next.js) | 23000 |
| 백엔드 (FastAPI) | 28888 |
| PostgreSQL | 5432 (Docker 내부) |

## 💰 비용

- **App Builder 자체**: 무료 (로컬 실행)
- **Claude API**: 프로젝트당 약 $5~20 (복잡도에 따라 상이)
- 실시간 토큰 비용 추적 UI 제공

## 📝 라이선스

MIT

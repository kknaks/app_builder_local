# App Builder Local — Project Rules

## Overview
로컬 설치형 AI 개발팀 플랫폼. Claude Code 에이전트 조직(PM/Planner/BE/FE/Design)이 아이디어를 앱으로 만들어주는 시스템.
- 백엔드: Python FastAPI + PostgreSQL
- 프론트엔드: Next.js (App Router) + TypeScript + Tailwind CSS
- 실시간: WebSocket
- 에이전트: Claude Code CLI (pty spawn)

## Required Skills & Plugins

모든 에이전트는 작업 시 아래 스킬/플러그인을 **반드시** 활용한다. 스킬이 적용될 수 있는 상황이면 무조건 호출한다.

### 공통 (모든 에이전트)
- **superpowers:brainstorming** — 새 기능 구현, 설계 변경 전 반드시 실행
- **superpowers:writing-plans** — 멀티스텝 작업 전 계획 수립
- **superpowers:systematic-debugging** — 버그/테스트 실패 시 반드시 실행
- **superpowers:verification-before-completion** — 작업 완료 선언 전 반드시 검증
- **superpowers:test-driven-development** — 기능 구현 시 TDD 워크플로우 따르기
- **oh-my-claudecode:code-review** — 주요 기능 완성 후 코드 리뷰
- **oh-my-claudecode:build-fix** — 빌드/타입 에러 발생 시 자동 수정

### 작업 흐름
1. 기능 구현 요청 → brainstorming → writing-plans → TDD(테스트 먼저) → 구현 → verification
2. 버그 발견 → systematic-debugging → 수정 → verification
3. 빌드 에러 → build-fix → verification

## Agent Auto-Routing

유저 요청을 분석하여 적절한 에이전트 지침을 자동으로 따른다.

| 키워드/맥락 | 에이전트 | 파일 |
|-------------|---------|------|
| FastAPI, API, DB, 스키마, 마이그레이션, 라우터, 모델, WebSocket 서버, pty, spawn, PostgreSQL, pytest, 백엔드 | **Backend** | `.claude/agents/backend.md` |
| Next.js, 컴포넌트, 페이지, UI, 레이아웃, React Flow, 패널, 채팅 UI, 로그 UI, Tailwind, TypeScript, 프론트엔드 | **Frontend** | `.claude/agents/frontend.md` |
| 양쪽 모두 관련 (풀스택, 전체 구조, API 연동) | **둘 다** | 두 에이전트 지침 모두 참조 |

### 라우팅 규칙
1. 유저 요청에서 관련 도메인을 판단한다
2. 해당 에이전트 `.md` 파일의 지침(역할, 컨벤션, 스킬)을 읽고 따른다
3. 명시적으로 `@backend` 또는 `@frontend`로 지정하면 해당 에이전트만 따른다
4. 판단이 어려우면 유저에게 물어본다

## Project Structure
```
backend/          — FastAPI 백엔드
frontend/         — Next.js 프론트엔드
PRD.md            — 제품 요구사항 문서
.claude/
  agents/         — 에이전트 정의
  CLAUDE.md       — 이 파일 (프로젝트 룰)
```

## Conventions
- PRD.md를 항상 참조하여 기능 요구사항 확인
- 커밋 메시지: 한글 또는 영어 (일관성 유지)
- 코드 내 주석: 영어
- 변수/함수명: 영어 (snake_case for Python, camelCase for TypeScript)

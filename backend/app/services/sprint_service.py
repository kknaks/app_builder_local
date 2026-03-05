"""Sprint planning and implementation orchestration service.

Handles:
- Sprint plan creation (PM Agent spawn → Phase.md)
- Phase.md parsing → flow_nodes generation
- Implementation orchestration (PM → BE/FE Agent sequential spawn)
- Error auto-fix loop (max 3 retries)
- Escalation to user on repeated failure
"""

import asyncio
import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runner import process_manager
from app.core.ws_manager import ws_manager
from app.models.project import Project
from app.services import agent_task_service, chat_service, flow_node_service

logger = logging.getLogger(__name__)

# Max error auto-fix retries per agent step
DEFAULT_MAX_RETRIES = 3


def _get_common_dir() -> Path:
    """Get the common template directory."""
    return Path("/Users/kknaks/kknaks/git/app_builder_local/common")


def _get_db_session_factory():
    """Get a new DB session factory for background tasks."""
    from app.database.session import async_session

    return async_session


def _build_sprint_prompt(prd_content: str, plan_phase_template: str, additional: str | None = None) -> str:
    """Build the system prompt for PM Agent to create Phase.md."""
    prompt = f"""당신은 PM(프로젝트 매니저)입니다.

아래 PRD를 기반으로 스프린트 플랜(Phase.md)을 작성해주세요.
스프린트 플랜 폼 템플릿에 맞춰 구체적으로 작성합니다.

## PRD
{prd_content}

## 스프린트 플랜 폼
{plan_phase_template}

## 규칙
- 각 스프린트의 백엔드/프론트엔드/디자인 태스크를 구체적으로 나눕니다
- 태스크는 실행 가능한 수준으로 세분화합니다
- 의존성을 명확히 표시합니다
- 완료 조건을 구체적으로 명시합니다
- 기술 스택: 백엔드 FastAPI + PostgreSQL, 프론트엔드 Next.js + TypeScript + Tailwind CSS
- 스프린트명은 S1, S2, S3... 형식을 사용합니다
- 각 태스크 항목 앞에 [ ] 체크박스를 사용합니다

결과물은 Phase.md 파일로 프로젝트 루트에 저장해주세요.
"""
    if additional:
        prompt += f"\n## 추가 지시사항\n{additional}\n"

    return prompt


def _build_implement_prompt(
    agent: str,
    task_description: str,
    prd_content: str,
    phase_content: str,
    error_log: str | None = None,
    retry_count: int = 0,
) -> str:
    """Build implementation prompt for BE/FE agent."""
    role_desc = {
        "backend": "백엔드 개발자 (FastAPI + SQLAlchemy + PostgreSQL)",
        "frontend": "프론트엔드 개발자 (Next.js + TypeScript + Tailwind CSS)",
    }

    prompt = f"""당신은 {role_desc.get(agent, agent)}입니다.

아래 PRD와 스프린트 플랜에 따라 구현을 진행해주세요.

## 현재 태스크
{task_description}

## PRD
{prd_content}

## 스프린트 플랜 (Phase.md)
{phase_content}

## 규칙
- 코드를 실제로 작성하고 파일로 저장합니다
- 테스트 코드도 함께 작성합니다
- 기존 코드와의 호환성을 유지합니다
- 구현 완료 후 빌드/테스트를 실행하여 확인합니다
"""

    if error_log and retry_count > 0:
        prompt += f"""
## ⚠️ 이전 시도에서 에러 발생 (재시도 {retry_count}회차)
아래 에러를 수정해주세요:

```
{error_log}
```

에러를 분석하고 수정한 후 다시 빌드/테스트를 실행해주세요.
"""

    return prompt


def parse_phase_md(content: str) -> list[dict]:
    """Parse Phase.md content into structured flow nodes.

    Extracts sprints and their BE/FE/Design/Test tasks.
    Returns list of dicts with keys: node_type, label, agent, sprint, parent_node_type
    """
    nodes: list[dict] = []
    current_sprint: str | None = None
    current_section: str | None = None

    # Section header patterns
    sprint_pattern = re.compile(r"^###\s+(S\d+):\s*(.+)", re.MULTILINE)
    section_patterns = {
        "backend": re.compile(r"\*\*백엔드\s*태스크", re.IGNORECASE),
        "frontend": re.compile(r"\*\*프론트엔드\s*태스크", re.IGNORECASE),
        "design": re.compile(r"\*\*디자인\s*태스크", re.IGNORECASE),
        "test": re.compile(r"\*\*완료\s*조건", re.IGNORECASE),
    }
    task_pattern = re.compile(r"^[-*]\s*\[[ x]\]\s*(.+)", re.MULTILINE)

    lines = content.split("\n")
    task_counter = 0

    for line in lines:
        # Check for sprint header
        sprint_match = sprint_pattern.match(line.strip())
        if sprint_match:
            current_sprint = sprint_match.group(1)
            sprint_label = sprint_match.group(2).strip()
            # Add sprint node
            nodes.append(
                {
                    "node_type": f"sprint_{current_sprint.lower()}",
                    "label": f"{current_sprint}: {sprint_label}",
                    "agent": "pm",
                    "sprint": current_sprint,
                    "parent_node_type": "sprint_plan",
                }
            )
            current_section = None
            continue

        if not current_sprint:
            continue

        # Check for section headers
        for section_name, pattern in section_patterns.items():
            if pattern.search(line):
                current_section = section_name
                break

        # Check for task items
        if current_section:
            task_match = task_pattern.match(line.strip())
            if task_match:
                task_label = task_match.group(1).strip()
                task_counter += 1

                # Determine agent and parent
                agent = current_section if current_section != "test" else "pm"
                parent_type = f"sprint_{current_sprint.lower()}"

                nodes.append(
                    {
                        "node_type": f"impl_{current_sprint.lower()}_{current_section}_{task_counter}",
                        "label": task_label,
                        "agent": agent,
                        "sprint": current_sprint,
                        "parent_node_type": parent_type,
                    }
                )

    return nodes


async def _create_sprint_flow_nodes(
    db: AsyncSession,
    project_id: int,
    parsed_nodes: list[dict],
) -> list:
    """Create flow nodes from parsed Phase.md content.

    Creates a 'sprint_plan' root node, then sprint nodes and task nodes.
    """
    # Create root sprint_plan node
    sprint_plan_node = await flow_node_service.create_flow_node(
        db,
        project_id,
        node_type="sprint_plan",
        label="스프린트 플랜",
        status="completed",
        position_x=800,
        position_y=0,
    )

    # Track created nodes by type for parent linking
    node_map: dict[str, int] = {"sprint_plan": sprint_plan_node.id}

    base_x = 1000
    y_offset = 0
    y_step = 80

    for node_def in parsed_nodes:
        parent_id = node_map.get(node_def.get("parent_node_type", ""), None)

        # Calculate position based on type
        if node_def["node_type"].startswith("sprint_"):
            pos_x = base_x
            y_offset += y_step * 2
        else:
            pos_x = base_x + 200
            y_offset += y_step

        node = await flow_node_service.create_flow_node(
            db,
            project_id,
            node_type=node_def["node_type"],
            label=node_def["label"],
            status="pending",
            parent_node_id=parent_id,
            position_x=pos_x,
            position_y=y_offset,
        )
        node_map[node_def["node_type"]] = node.id

    # Broadcast flow update
    await ws_manager.broadcast(
        project_id,
        "logs",
        {
            "type": "flow_update",
            "node_id": sprint_plan_node.id,
            "node_type": "sprint_plan",
            "status": "completed",
            "label": "스프린트 플랜",
        },
    )

    return list(node_map.values())


async def _run_agent_task_bg(
    project_id: int,
    project_path: str,
    agent: str,
    prompt: str,
    node_type: str | None,
    task_id: int,
) -> tuple[int, str]:
    """Run an agent task in background with its own DB session.

    Returns (task_id, collected_output).
    """
    session_factory = _get_db_session_factory()

    async with session_factory() as db:
        await agent_task_service.update_task_status(db, task_id, "running")

        if node_type:
            await flow_node_service.update_node_status(db, project_id, node_type, "active")

    # Build agent md path
    agent_md_path = str(Path(project_path) / f".claude/agent/{agent}-agent.md")
    if not Path(agent_md_path).exists():
        agent_md_path = ""

    output_lines: list[str] = []
    try:
        async for line in process_manager.spawn_agent(
            agent_md_path=agent_md_path,
            prompt=prompt,
            project_dir=project_path,
            project_id=project_id,
            agent=agent,
            task_id=task_id,
        ):
            output_lines.append(line)

            await ws_manager.broadcast(
                project_id,
                "logs",
                {
                    "type": "log",
                    "agent": agent,
                    "text": line,
                    "log_type": "info",
                },
            )

        result_text = "\n".join(output_lines)
        async with session_factory() as db:
            await agent_task_service.update_task_status(
                db, task_id, "completed", result=result_text
            )
            if node_type:
                await flow_node_service.update_node_status(
                    db, project_id, node_type, "completed"
                )

        return task_id, result_text

    except TimeoutError as e:
        error_msg = str(e)
        async with session_factory() as db:
            await agent_task_service.update_task_status(
                db, task_id, "failed", error=error_msg
            )
            if node_type:
                await flow_node_service.update_node_status(
                    db, project_id, node_type, "error"
                )
        raise

    except Exception as e:
        error_msg = str(e)
        async with session_factory() as db:
            await agent_task_service.update_task_status(
                db, task_id, "failed", error=error_msg
            )
            if node_type:
                await flow_node_service.update_node_status(
                    db, project_id, node_type, "error"
                )
        raise


def _detect_error_in_output(output: str) -> str | None:
    """Detect build/test errors in agent output.

    Returns error text if errors found, None otherwise.
    """
    error_indicators = [
        "FAILED",
        "Error:",
        "error:",
        "ERROR",
        "SyntaxError",
        "TypeError",
        "ImportError",
        "ModuleNotFoundError",
        "Build failed",
        "build failed",
        "Test failed",
        "test failed",
        "ERRORS",
        "Traceback (most recent call last)",
        "exit code 1",
        "exit status 1",
    ]

    lines = output.split("\n")
    error_lines: list[str] = []
    capturing = False

    for line in lines:
        if any(indicator in line for indicator in error_indicators):
            capturing = True

        if capturing:
            error_lines.append(line)

        # Stop capturing after 50 lines of error context
        if capturing and len(error_lines) >= 50:
            break

    if error_lines:
        return "\n".join(error_lines)
    return None


# ─── Sprint Plan API ─────────────────────────────────────────────

async def start_sprint_planning(
    db: AsyncSession,
    project: Project,
    additional_instructions: str | None = None,
) -> int:
    """Start sprint planning: spawn PM Agent to create Phase.md.

    Returns the task ID.
    """
    # Update project status
    project.status = "sprint_planning"
    project.current_phase = "sprint_planning"
    await db.commit()

    # Load PRD.md
    prd_path = Path(project.project_path) / "PRD.md"
    prd_content = ""
    if prd_path.exists():
        prd_content = prd_path.read_text(encoding="utf-8")
    else:
        prd_content = f"# {project.name}\n\n{project.idea_text}"

    # Load plan_phase.md template
    common_dir = _get_common_dir()
    plan_phase_path = common_dir / "plan_phase.md"
    plan_phase_template = ""
    if plan_phase_path.exists():
        plan_phase_template = plan_phase_path.read_text(encoding="utf-8")

    # Build prompt
    prompt = _build_sprint_prompt(prd_content, plan_phase_template, additional_instructions)

    # Create task
    task = await agent_task_service.create_task(
        db, project.id, "pm", "스프린트 플랜 작성"
    )

    # Spawn in background
    asyncio.create_task(
        _sprint_planning_worker(
            project.id, project.project_path, prompt, task.id
        )
    )

    return task.id


async def _sprint_planning_worker(
    project_id: int,
    project_path: str,
    prompt: str,
    task_id: int,
) -> None:
    """Background worker for sprint planning."""
    session_factory = _get_db_session_factory()

    try:
        _task_id, result = await _run_agent_task_bg(
            project_id, project_path, "pm", prompt,
            node_type=None, task_id=task_id,
        )

        # Save Phase.md
        phase_path = Path(project_path) / "Phase.md"
        phase_path.write_text(result, encoding="utf-8")

        # Parse Phase.md and create flow nodes
        parsed = parse_phase_md(result)

        async with session_factory() as db:
            await _create_sprint_flow_nodes(db, project_id, parsed)

            # Save PM response as chat
            await chat_service.save_message(
                db, project_id, "pm", "assistant",
                f"스프린트 플랜이 작성되었습니다. Phase.md를 확인하세요.\n\n{result[:500]}..."
                if len(result) > 500 else f"스프린트 플랜이 작성되었습니다.\n\n{result}"
            )

        # Broadcast
        await ws_manager.broadcast(
            project_id,
            "chat",
            {
                "type": "message",
                "agent": "pm",
                "content": "✅ 스프린트 플랜이 완료되었습니다. 구현을 시작할 준비가 되었습니다.",
                "role": "assistant",
            },
        )

    except Exception as e:
        logger.error("Sprint planning worker error: %s", e)
        async with session_factory() as db:
            await chat_service.save_message(
                db, project_id, "pm", "assistant",
                f"❌ 스프린트 플랜 작성 중 오류가 발생했습니다: {e}",
            )

        await ws_manager.broadcast(
            project_id,
            "chat",
            {
                "type": "message",
                "agent": "pm",
                "content": f"❌ 스프린트 플랜 작성 중 오류 발생: {e}",
                "role": "assistant",
            },
        )


# ─── Implementation API ──────────────────────────────────────────

async def start_implementation(
    db: AsyncSession,
    project: Project,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> int:
    """Start implementation: PM orchestrates BE/FE agents.

    Returns the PM orchestration task ID.
    """
    # Update project status
    project.status = "implementing"
    project.current_phase = "implementing"
    await db.commit()

    # Create PM orchestration task
    task = await agent_task_service.create_task(
        db, project.id, "pm", "구현 총괄 오케스트레이션"
    )

    # Spawn background orchestrator
    asyncio.create_task(
        _implementation_orchestrator(
            project.id, project.project_path, project.idea_text, task.id, max_retries
        )
    )

    return task.id


async def _implementation_orchestrator(
    project_id: int,
    project_path: str,
    idea_text: str,
    pm_task_id: int,
    max_retries: int,
) -> None:
    """PM orchestrator: reads Phase.md, spawns BE/FE agents sequentially.

    For each agent step:
    1. Spawn agent with implementation prompt
    2. Check output for errors
    3. If error: re-spawn with error log (up to max_retries)
    4. If still failing: escalate to user via chat
    """
    session_factory = _get_db_session_factory()

    try:
        # Mark PM task as running
        async with session_factory() as db:
            await agent_task_service.update_task_status(db, pm_task_id, "running")

        # Load Phase.md
        phase_path = Path(project_path) / "Phase.md"
        phase_content = ""
        if phase_path.exists():
            phase_content = phase_path.read_text(encoding="utf-8")

        # Load PRD.md
        prd_path = Path(project_path) / "PRD.md"
        prd_content = ""
        if prd_path.exists():
            prd_content = prd_path.read_text(encoding="utf-8")

        if not phase_content:
            raise ValueError("Phase.md not found. Run sprint planning first.")

        # Parse Phase.md to get implementation steps
        parsed_nodes = parse_phase_md(phase_content)

        # Group tasks by agent (backend first, then frontend)
        be_tasks = [n for n in parsed_nodes if n["agent"] == "backend"]
        fe_tasks = [n for n in parsed_nodes if n["agent"] == "frontend"]

        # Notify start
        await ws_manager.broadcast(
            project_id,
            "chat",
            {
                "type": "message",
                "agent": "pm",
                "content": f"🚀 구현을 시작합니다. 백엔드 태스크 {len(be_tasks)}개, 프론트엔드 태스크 {len(fe_tasks)}개를 순차 실행합니다.",
                "role": "assistant",
            },
        )

        # Execute backend tasks
        if be_tasks:
            success = await _execute_agent_tasks(
                project_id, project_path, "backend",
                be_tasks, prd_content, phase_content, max_retries,
            )
            if not success:
                await _escalate_to_user(
                    project_id, "backend",
                    "백엔드 구현 중 반복 에러가 발생했습니다. 확인이 필요합니다.",
                )

        # Execute frontend tasks
        if fe_tasks:
            success = await _execute_agent_tasks(
                project_id, project_path, "frontend",
                fe_tasks, prd_content, phase_content, max_retries,
            )
            if not success:
                await _escalate_to_user(
                    project_id, "frontend",
                    "프론트엔드 구현 중 반복 에러가 발생했습니다. 확인이 필요합니다.",
                )

        # All done
        async with session_factory() as db:
            await agent_task_service.update_task_status(
                db, pm_task_id, "completed", result="구현 오케스트레이션 완료"
            )

            # Update project status
            stmt = select(Project).where(Project.id == project_id)
            res = await db.execute(stmt)
            proj = res.scalar_one_or_none()
            if proj:
                proj.status = "testing"
                proj.current_phase = "testing"
                await db.commit()

        await ws_manager.broadcast(
            project_id,
            "chat",
            {
                "type": "message",
                "agent": "pm",
                "content": "✅ 구현이 완료되었습니다. 테스트 단계로 이동합니다.",
                "role": "assistant",
            },
        )

    except Exception as e:
        logger.error("Implementation orchestrator error: %s", e)

        async with session_factory() as db:
            await agent_task_service.update_task_status(
                db, pm_task_id, "failed", error=str(e)
            )

        await _escalate_to_user(
            project_id, "pm",
            f"구현 오케스트레이션 중 오류 발생: {e}",
        )


async def _execute_agent_tasks(
    project_id: int,
    project_path: str,
    agent: str,
    tasks: list[dict],
    prd_content: str,
    phase_content: str,
    max_retries: int,
) -> bool:
    """Execute a list of tasks for a specific agent with retry loop.

    Returns True if all tasks completed successfully, False if any failed after max retries.
    """
    session_factory = _get_db_session_factory()

    # Combine all tasks into a single description for the agent
    task_descriptions = "\n".join(f"- {t['label']}" for t in tasks)
    last_error: str | None = None

    for retry in range(max_retries + 1):
        # Create agent task in DB
        async with session_factory() as db:
            task = await agent_task_service.create_task(
                db, project_id, agent,
                f"{agent} 구현 (시도 {retry + 1}/{max_retries + 1})"
            )

        # Update relevant flow nodes to active
        async with session_factory() as db:
            for t in tasks:
                await flow_node_service.update_node_status(
                    db, project_id, t["node_type"], "active"
                )

        # Notify via WS
        await ws_manager.broadcast(
            project_id,
            "chat",
            {
                "type": "message",
                "agent": "pm",
                "content": f"{'🔄 재시도 ' + str(retry) + '회차: ' if retry > 0 else '▶️ '}"
                f"{agent} 에이전트 구현 시작"
                f"{' (에러 수정 중)' if retry > 0 else ''}",
                "role": "assistant",
            },
        )

        # Build prompt (with error log if retry)
        prompt = _build_implement_prompt(
            agent, task_descriptions, prd_content, phase_content,
            error_log=last_error if retry > 0 else None,
            retry_count=retry,
        )

        try:
            _tid, output = await _run_agent_task_bg(
                project_id, project_path, agent, prompt,
                node_type=None, task_id=task.id,
            )

            # Check for errors in output
            error = _detect_error_in_output(output)
            if error and retry < max_retries:
                logger.warning(
                    "Errors detected in %s output (retry %d/%d): %s",
                    agent, retry + 1, max_retries, error[:200],
                )
                last_error = error

                # Update flow nodes to error
                async with session_factory() as db:
                    for t in tasks:
                        await flow_node_service.update_node_status(
                            db, project_id, t["node_type"], "error"
                        )

                await ws_manager.broadcast(
                    project_id,
                    "chat",
                    {
                        "type": "message",
                        "agent": "pm",
                        "content": f"⚠️ {agent} 에이전트에서 에러 감지. 자동 수정 시도 중... ({retry + 1}/{max_retries})",
                        "role": "assistant",
                    },
                )
                continue

            elif error and retry >= max_retries:
                # Max retries exhausted
                async with session_factory() as db:
                    for t in tasks:
                        await flow_node_service.update_node_status(
                            db, project_id, t["node_type"], "error"
                        )
                return False

            # Success — no errors
            async with session_factory() as db:
                for t in tasks:
                    await flow_node_service.update_node_status(
                        db, project_id, t["node_type"], "completed"
                    )

                await chat_service.save_message(
                    db, project_id, agent, "assistant",
                    f"✅ {agent} 구현 완료"
                )

            await ws_manager.broadcast(
                project_id,
                "chat",
                {
                    "type": "message",
                    "agent": agent,
                    "content": f"✅ {agent} 구현이 완료되었습니다.",
                    "role": "assistant",
                },
            )

            return True

        except (TimeoutError, Exception) as e:
            logger.error("%s agent task failed: %s", agent, e)
            last_error = str(e)

            if retry >= max_retries:
                return False

            await ws_manager.broadcast(
                project_id,
                "chat",
                {
                    "type": "message",
                    "agent": "pm",
                    "content": f"⚠️ {agent} 에이전트 실행 중 오류 발생: {e}. 재시도 중...",
                    "role": "assistant",
                },
            )

    return False


async def _escalate_to_user(
    project_id: int,
    agent: str,
    message: str,
) -> None:
    """PM escalates an issue to the user via chat WS."""
    session_factory = _get_db_session_factory()

    escalation_msg = f"🚨 **에스컬레이션** ({agent})\n\n{message}\n\n사용자 확인이 필요합니다. 채팅으로 지시해주세요."

    async with session_factory() as db:
        await chat_service.save_message(
            db, project_id, "pm", "assistant", escalation_msg
        )

    await ws_manager.broadcast(
        project_id,
        "chat",
        {
            "type": "message",
            "agent": "pm",
            "content": escalation_msg,
            "role": "assistant",
        },
    )

    # Also send agent_status update
    await ws_manager.broadcast(
        project_id,
        "logs",
        {
            "type": "agent_status",
            "agent": "pm",
            "status": "waiting_user",
        },
    )

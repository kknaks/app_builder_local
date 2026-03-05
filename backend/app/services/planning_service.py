"""Planning flow orchestration service.

Handles:
- Plan start (Planner Agent spawn)
- Review (BE/FE/Design parallel review with max 2 concurrent)
- Approve (PRD.md finalization)
- Feedback (re-review loop)
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_runner import process_manager
from app.core.ws_manager import ws_manager
from app.models.project import Project
from app.services import agent_task_service, chat_service, flow_node_service

logger = logging.getLogger(__name__)

# Max concurrent review agents (semaphore)
MAX_CONCURRENT_REVIEW = 2


def _get_common_dir() -> Path:
    """Get the common template directory."""
    return Path("/Users/kknaks/kknaks/git/app_builder_local/common")


def _build_planner_prompt(idea_text: str, plan_form: str, additional_context: str | None = None) -> str:
    """Build the system prompt for the Planner Agent."""
    prompt = f"""당신은 기획 전문가(Planner Agent)입니다.

아래 아이디어를 기반으로 다음 기획서 폼에 맞춰 구체적인 기획 문서를 작성해주세요.

## 아이디어
{idea_text}

## 기획서 폼
{plan_form}

## 규칙
- plan_form.md 폼 구조를 반드시 따릅니다
- MVP 우선 접근 — 핵심 기능만 먼저
- 기술 스택: FastAPI + Next.js + PostgreSQL 고정
- 각 섹션을 빠짐없이 구체적으로 작성합니다
- 비개발자도 이해할 수 있는 명확한 표현을 사용합니다
"""
    if additional_context:
        prompt += f"\n## 추가 컨텍스트\n{additional_context}\n"

    return prompt


def _build_review_prompt(agent_role: str, idea_text: str) -> str:
    """Build review prompt for a specific reviewer agent."""
    role_desc = {
        "backend": "백엔드 개발자 관점에서 (API 설계, DB 스키마, 성능, 보안)",
        "frontend": "프론트엔드 개발자 관점에서 (UI/UX, 컴포넌트 구조, 상태 관리, 반응형)",
        "design": "UI/UX 디자이너 관점에서 (사용성, 화면 흐름, 정보 구조, 디자인 시스템)",
    }

    return f"""당신은 {role_desc.get(agent_role, agent_role)} 기획서를 검토하는 전문가입니다.

프로젝트 디렉토리의 기획 문서를 검토하고 다음을 포함한 검토 의견을 작성해주세요:

1. **장점**: 잘 된 부분
2. **개선 필요**: 수정/보완이 필요한 부분
3. **리스크**: 잠재적 문제점
4. **제안**: 구체적인 개선 제안

## 프로젝트 아이디어
{idea_text}

검토 결과를 명확하고 구조적으로 작성해주세요.
"""


def _build_feedback_prompt(feedback: str, idea_text: str) -> str:
    """Build prompt for re-planning after feedback."""
    return f"""당신은 기획 전문가(Planner Agent)입니다.

유저로부터 기획서에 대한 피드백을 받았습니다. 피드백을 반영하여 기획서를 수정해주세요.

## 프로젝트 아이디어
{idea_text}

## 유저 피드백
{feedback}

## 규칙
- 기존 기획서의 구조를 유지하면서 피드백을 반영합니다
- 수정한 부분을 명확히 표시합니다
- MVP 범위를 벗어나지 않도록 합니다
"""


def _get_db_session_factory():
    """Get a new DB session factory for background tasks."""
    from app.database.session import async_session

    return async_session


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
        # Update task to running
        await agent_task_service.update_task_status(db, task_id, "running")

        # Update flow node to active
        if node_type:
            await flow_node_service.update_node_status(db, project_id, node_type, "active")

    # Build agent md path
    agent_md_path = str(Path(project_path) / f".claude/agent/{agent}-agent.md")
    if not Path(agent_md_path).exists():
        agent_md_path = ""

    # Collect output
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

            # Stream log via WS
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

        # Success
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
                    db, project_id, node_type, "failed"
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
                    db, project_id, node_type, "failed"
                )
        raise


async def start_planning(
    db: AsyncSession,
    project: Project,
    additional_context: str | None = None,
) -> int:
    """Start the planning phase: spawn Planner Agent.

    Returns the task ID. All DB work done synchronously in request context,
    background task spawned for actual agent execution.
    """
    # Initialize flow nodes
    await flow_node_service.initialize_planning_flow(db, project.id)

    # Update project status
    project.status = "planning"
    project.current_phase = "planning"
    await db.commit()

    # Load plan_form.md
    common_dir = _get_common_dir()
    plan_form_path = common_dir / "plan_form.md"
    plan_form = ""
    if plan_form_path.exists():
        plan_form = plan_form_path.read_text(encoding="utf-8")

    # Build prompt
    prompt = _build_planner_prompt(project.idea_text, plan_form, additional_context)

    # Create task
    task = await agent_task_service.create_task(
        db, project.id, "planner", "기획 구체화"
    )

    # Spawn agent in background (uses its own DB session)
    asyncio.create_task(
        _planning_worker(project.id, project.project_path, project.idea_text, prompt, task.id)
    )

    return task.id


async def _planning_worker(
    project_id: int,
    project_path: str,
    idea_text: str,
    prompt: str,
    task_id: int,
) -> None:
    """Background worker for planning task. Uses its own DB session."""
    try:
        _task_id, result = await _run_agent_task_bg(
            project_id, project_path, "planner", prompt,
            node_type="planning", task_id=task_id,
        )

        # Save planner response as chat message
        session_factory = _get_db_session_factory()
        async with session_factory() as db:
            await chat_service.save_message(
                db, project_id, "planner", "assistant", result
            )

        # Broadcast to chat WS
        await ws_manager.broadcast(
            project_id,
            "chat",
            {
                "type": "message",
                "agent": "planner",
                "content": result,
                "role": "assistant",
            },
        )

    except Exception as e:
        logger.error("Planning worker error: %s", e)
        await ws_manager.broadcast(
            project_id,
            "chat",
            {
                "type": "message",
                "agent": "pm",
                "content": f"기획 작성 중 오류가 발생했습니다: {e}",
                "role": "assistant",
            },
        )


async def start_review(
    db: AsyncSession,
    project: Project,
) -> list[int]:
    """Start the review phase: spawn BE/FE/Design agents in parallel.

    Uses a semaphore to limit concurrent agents to MAX_CONCURRENT_REVIEW.
    Returns list of task IDs. All DB work for task creation done in request context.
    """
    # Update project status
    project.status = "reviewing"
    project.current_phase = "reviewing"
    await db.commit()

    reviewers = [
        ("backend", "review_be"),
        ("frontend", "review_fe"),
        ("design", "review_design"),
    ]

    task_ids = []
    for agent, _node_type in reviewers:
        task = await agent_task_service.create_task(
            db, project.id, agent, f"{agent} 기획 검토"
        )
        task_ids.append(task.id)

    # Start review in background (uses its own DB sessions)
    asyncio.create_task(
        _review_worker(project.id, project.project_path, project.idea_text, reviewers, task_ids)
    )

    return task_ids


async def _review_worker(
    project_id: int,
    project_path: str,
    idea_text: str,
    reviewers: list[tuple[str, str]],
    task_ids: list[int],
) -> None:
    """Background worker for parallel review with concurrency limit."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REVIEW)
    results: dict[str, str] = {}

    async def _review_one(agent: str, node_type: str, task_id: int) -> None:
        async with semaphore:
            prompt = _build_review_prompt(agent, idea_text)
            try:
                _tid, result = await _run_agent_task_bg(
                    project_id, project_path, agent, prompt,
                    node_type=node_type, task_id=task_id,
                )
                results[agent] = result
            except Exception as e:
                logger.error("Review %s failed: %s", agent, e)
                results[agent] = f"검토 실패: {e}"

    # Run all reviewers with semaphore
    tasks = []
    for (agent, node_type), task_id in zip(reviewers, task_ids):
        tasks.append(_review_one(agent, node_type, task_id))

    await asyncio.gather(*tasks)

    # PM collects and sends summary
    await _send_review_summary(project_id, results)


async def _send_review_summary(
    project_id: int,
    results: dict[str, str],
) -> None:
    """PM collects review results and sends summary to user."""
    summary_parts = ["## 기획 검토 결과\n"]
    for agent, result in results.items():
        label = {"backend": "백엔드", "frontend": "프론트엔드", "design": "디자인"}.get(agent, agent)
        summary_parts.append(f"### {label} 검토\n{result}\n")

    summary_parts.append(
        "\n---\n검토가 완료되었습니다. "
        "**승인**하시거나 **피드백**을 주세요."
    )
    summary = "\n".join(summary_parts)

    # Save as PM message (with own session)
    session_factory = _get_db_session_factory()
    async with session_factory() as db:
        await chat_service.save_message(db, project_id, "pm", "assistant", summary)

    # Broadcast to chat
    await ws_manager.broadcast(
        project_id,
        "chat",
        {
            "type": "message",
            "agent": "pm",
            "content": summary,
            "role": "assistant",
        },
    )


async def approve_plan(
    db: AsyncSession,
    project: Project,
    prd_content: str | None = None,
) -> str:
    """Approve the plan: save PRD.md and update project status.

    Returns the PRD file path.
    """
    # If no content provided, use the latest planner output
    if not prd_content:
        # Get the latest planner task result
        tasks = await agent_task_service.get_tasks_for_project(
            db, project.id, status="completed"
        )
        planner_tasks = [t for t in tasks if t.agent == "planner"]
        if planner_tasks and planner_tasks[0].result:
            prd_content = planner_tasks[0].result
        else:
            prd_content = f"# {project.name} — PRD\n\n{project.idea_text}\n"

    # Save PRD.md to project directory
    prd_path = Path(project.project_path) / "PRD.md"
    prd_path.parent.mkdir(parents=True, exist_ok=True)
    prd_path.write_text(prd_content, encoding="utf-8")

    # Update project status
    project.status = "sprint_planning"
    project.current_phase = "sprint_planning"
    await db.commit()

    # Update flow node
    await flow_node_service.update_node_status(
        db, project.id, "approval", "completed"
    )

    # Notify via chat
    msg = f"✅ PRD가 승인되었습니다. PRD.md가 저장되었습니다.\n경로: {prd_path}"
    await chat_service.save_message(db, project.id, "pm", "assistant", msg)

    await ws_manager.broadcast(
        project.id,
        "chat",
        {
            "type": "message",
            "agent": "pm",
            "content": msg,
            "role": "assistant",
        },
    )

    return str(prd_path)


async def send_feedback(
    db: AsyncSession,
    project: Project,
    feedback: str,
) -> int:
    """Send feedback to re-plan: spawn Planner Agent with feedback.

    Returns the new task ID.
    """
    # Update project status back to planning
    project.status = "planning"
    project.current_phase = "planning"
    await db.commit()

    # Reset review nodes to pending
    for node_type in ["review_be", "review_fe", "review_design", "approval"]:
        await flow_node_service.update_node_status(
            db, project.id, node_type, "pending"
        )

    # Build feedback prompt
    prompt = _build_feedback_prompt(feedback, project.idea_text)

    # Create task
    task = await agent_task_service.create_task(
        db, project.id, "planner", f"피드백 반영: {feedback[:100]}"
    )

    # Save user feedback as chat message
    await chat_service.save_message(
        db, project.id, "pm", "user", f"[피드백] {feedback}"
    )

    # Spawn in background (uses its own DB session)
    asyncio.create_task(
        _planning_worker(project.id, project.project_path, project.idea_text, prompt, task.id)
    )

    return task.id

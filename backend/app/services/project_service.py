"""Project management service — CRUD + filesystem operations."""

import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import Project

# Agent template files to create in each project
AGENT_FILES = [
    ".claude/agent/pm-agent.md",
    ".claude/agent/planner-agent.md",
    ".claude/agent/backend-agent.md",
    ".claude/agent/frontend-agent.md",
    ".claude/agent/design-agent.md",
]

SKILL_FILES = [
    ".claude/skills/pm.md",
    ".claude/skills/planner.md",
    ".claude/skills/backend.md",
    ".claude/skills/frontend.md",
    ".claude/skills/design.md",
]

# Common template directory
COMMON_DIR = Path(settings.PROJECT_ROOT).parent / "common" if settings.PROJECT_ROOT else None


def _get_projects_base_dir() -> Path:
    """Get the base directory for project directories."""
    if settings.PROJECT_ROOT:
        return Path(settings.PROJECT_ROOT)
    # Fallback: use a default path
    return Path("/Users/kknaks/kknaks/git/app_builder_local/projects")


def _get_common_dir() -> Path:
    """Get the common template directory."""
    return Path("/Users/kknaks/kknaks/git/app_builder_local/common")


def _sanitize_project_name(name: str) -> str:
    """Sanitize project name for use as directory name."""
    # Replace spaces and special chars with underscores, lowercase
    sanitized = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return sanitized.lower().strip("_")


def _create_default_agent_content(filepath: str) -> str:
    """Generate default content for agent/skill template files."""
    filename = Path(filepath).stem
    if "agent" in filepath:
        return f"# {filename.replace('-', ' ').title()}\n\n> Auto-generated agent definition.\n"
    return f"# {filename.replace('-', ' ').title()} Skill\n\n> Auto-generated skill definition.\n"


def _setup_project_directory(project_path: Path, idea_text: str) -> None:
    """Create project directory structure with idea.md and agent files."""
    project_path.mkdir(parents=True, exist_ok=True)

    # Write idea.md
    idea_file = project_path / "idea.md"
    idea_file.write_text(f"# Project Idea\n\n{idea_text}\n", encoding="utf-8")

    common_dir = _get_common_dir()

    # Create agent files
    for agent_file in AGENT_FILES:
        dest = project_path / agent_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        source = common_dir / agent_file
        if source.exists():
            shutil.copy2(source, dest)
        else:
            dest.write_text(_create_default_agent_content(agent_file), encoding="utf-8")

    # Create skill files
    for skill_file in SKILL_FILES:
        dest = project_path / skill_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        source = common_dir / skill_file
        if source.exists():
            shutil.copy2(source, dest)
        else:
            dest.write_text(_create_default_agent_content(skill_file), encoding="utf-8")


async def create_project(db: AsyncSession, name: str, idea_text: str) -> Project:
    """Create a new project: DB record + directory + agent files."""
    dir_name = _sanitize_project_name(name)
    base_dir = _get_projects_base_dir()
    project_path = base_dir / dir_name

    # Create project in DB
    project = Project(
        name=name,
        idea_text=idea_text,
        status="created",
        project_path=str(project_path),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Create directory structure
    _setup_project_directory(project_path, idea_text)

    return project


async def list_projects(db: AsyncSession) -> list[Project]:
    """List all projects ordered by creation date (newest first)."""
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


async def get_project(db: AsyncSession, project_id: int) -> Project | None:
    """Get a single project by ID."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def delete_project(db: AsyncSession, project_id: int) -> bool:
    """Delete a project: remove DB record + directory.

    Returns True if deleted, False if not found.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        return False

    # Remove directory if it exists
    project_path = Path(project.project_path)
    if project_path.exists():
        shutil.rmtree(project_path)

    await db.delete(project)
    await db.commit()
    return True

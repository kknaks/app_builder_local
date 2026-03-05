"""Projects router — CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDeleteResponse,
    ProjectListResponse,
    ProjectResponse,
)
from app.services.project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_new_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new project with directory structure and agent files."""
    project = await create_project(db, request.name, request.idea_text)
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse)
async def get_projects(
    db: AsyncSession = Depends(get_db),
):
    """List all projects."""
    projects = await list_projects(db)
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=len(projects),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_detail(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get project details by ID."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
async def delete_existing_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a project and its directory."""
    deleted = await delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectDeleteResponse(id=project_id)

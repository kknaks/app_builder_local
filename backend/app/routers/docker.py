"""Docker run/stop/status router — manages project container lifecycle."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.docker import (
    ContainerInfo,
    DockerRunRequest,
    DockerRunResponse,
    DockerStatusResponse,
    DockerStopResponse,
)
from app.services.docker_service import (
    docker_compose_down,
    docker_compose_up,
    generate_docker_compose,
    get_container_status,
    save_docker_compose,
)
from app.services.project_service import get_project

router = APIRouter(prefix="/api/projects", tags=["docker"])


@router.post("/{project_id}/run", response_model=DockerRunResponse)
async def run_project(
    project_id: int,
    request: DockerRunRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Run a project via Docker Compose.

    Generates docker-compose.yml if not present, then runs docker compose up -d.
    Returns URLs for accessing the running services.
    """
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate docker-compose.yml
    try:
        backend_port = request.backend_port if request else None
        frontend_port = request.frontend_port if request else None
        db_port = request.db_port if request else None

        # Sanitize project name for Docker
        safe_name = project.name.lower().replace(" ", "_")
        safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in safe_name)

        compose_config = generate_docker_compose(
            project_path=project.project_path,
            project_name=safe_name,
            backend_port=backend_port,
            frontend_port=frontend_port,
            db_port=db_port,
        )

        save_docker_compose(project.project_path, compose_config)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate docker-compose.yml: {e}",
        )

    # Run docker compose up
    result = await docker_compose_up(project.project_path)

    if result["status"] == "error":
        return DockerRunResponse(
            status="error",
            error=result.get("error", "Unknown error"),
            message="Docker Compose 실행 중 오류가 발생했습니다.",
        )

    containers = [
        ContainerInfo(**c) for c in result.get("containers", [])
    ]

    return DockerRunResponse(
        status="running",
        urls=result.get("urls", {}),
        containers=containers,
        message="앱이 실행되었습니다.",
    )


@router.post("/{project_id}/stop", response_model=DockerStopResponse)
async def stop_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Stop a running project's Docker containers."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await docker_compose_down(project.project_path)

    if result["status"] == "error":
        return DockerStopResponse(
            status="error",
            error=result.get("error", "Unknown error"),
            message="Docker Compose 중지 중 오류가 발생했습니다.",
        )

    return DockerStopResponse(
        status="stopped",
        message="앱이 중지되었습니다.",
    )


@router.get("/{project_id}/run/status", response_model=DockerStatusResponse)
async def get_run_status(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the running status of a project's Docker containers."""
    project = await get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await get_container_status(project.project_path)

    containers = [
        ContainerInfo(**c) for c in result.get("containers", [])
    ]

    return DockerStatusResponse(
        status=result.get("status", "unknown"),
        urls=result.get("urls", {}),
        containers=containers,
        error=result.get("error"),
    )

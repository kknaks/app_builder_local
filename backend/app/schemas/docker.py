"""Schemas for Docker run/stop/status endpoints."""

from pydantic import BaseModel, Field


class DockerRunRequest(BaseModel):
    """Request body for running a project via Docker Compose."""

    backend_port: int | None = Field(None, description="External port for backend service")
    frontend_port: int | None = Field(None, description="External port for frontend service")
    db_port: int | None = Field(None, description="External port for PostgreSQL")


class ContainerInfo(BaseModel):
    """Information about a running container."""

    name: str
    service: str
    state: str
    status: str
    ports: str = ""


class DockerRunResponse(BaseModel):
    """Response for Docker run endpoint."""

    status: str
    urls: dict[str, str] = {}
    containers: list[ContainerInfo] = []
    message: str = ""
    error: str | None = None


class DockerStopResponse(BaseModel):
    """Response for Docker stop endpoint."""

    status: str
    message: str = ""
    error: str | None = None


class DockerStatusResponse(BaseModel):
    """Response for Docker status endpoint."""

    status: str
    urls: dict[str, str] = {}
    containers: list[ContainerInfo] = []
    error: str | None = None

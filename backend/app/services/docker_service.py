"""Docker Compose service — auto-generation, run, stop, status.

Generates docker-compose.yml for completed projects (FastAPI + Next.js + PostgreSQL).
Manages container lifecycle via docker compose CLI.
Auto-assigns ports to avoid collisions.
"""

import asyncio
import json
import logging
import random
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Port range for auto-assignment (avoid common ports)
PORT_RANGE_START = 30000
PORT_RANGE_END = 39999

# Container name prefix
CONTAINER_PREFIX = "appbuilder"

# Default timeout for docker operations (seconds)
DOCKER_TIMEOUT = 60


def _find_available_port(exclude: set[int] | None = None) -> int:
    """Find an available port in the configured range.

    Uses random selection within range, avoiding excluded ports.
    """
    exclude = exclude or set()
    attempts = 0
    while attempts < 100:
        port = random.randint(PORT_RANGE_START, PORT_RANGE_END)
        if port not in exclude:
            return port
        attempts += 1
    raise RuntimeError(f"Cannot find available port in range {PORT_RANGE_START}-{PORT_RANGE_END}")


def _detect_project_structure(project_path: Path) -> dict:
    """Detect the project structure (backend/frontend/db).

    Returns dict with detected components and their configs.
    """
    structure = {
        "has_backend": False,
        "has_frontend": False,
        "backend_type": None,
        "frontend_type": None,
    }

    backend_dir = project_path / "backend"
    if backend_dir.exists():
        structure["has_backend"] = True
        # Detect backend type
        if (backend_dir / "pyproject.toml").exists() or (backend_dir / "requirements.txt").exists():
            structure["backend_type"] = "fastapi"
        elif (backend_dir / "main.py").exists():
            structure["backend_type"] = "fastapi"

    frontend_dir = project_path / "frontend"
    if frontend_dir.exists():
        structure["has_frontend"] = True
        if (frontend_dir / "package.json").exists():
            structure["frontend_type"] = "nextjs"
        elif (frontend_dir / "next.config.js").exists() or (frontend_dir / "next.config.mjs").exists():
            structure["frontend_type"] = "nextjs"

    return structure


def generate_docker_compose(
    project_path: str,
    project_name: str,
    backend_port: int | None = None,
    frontend_port: int | None = None,
    db_port: int | None = None,
) -> dict:
    """Generate docker-compose.yml content for a project.

    Args:
        project_path: Absolute path to the project directory
        project_name: Sanitized project name for container naming
        backend_port: External port for backend (auto-assigned if None)
        frontend_port: External port for frontend (auto-assigned if None)
        db_port: External port for PostgreSQL (auto-assigned if None)

    Returns:
        dict representing docker-compose.yml content
    """
    path = Path(project_path)
    structure = _detect_project_structure(path)
    used_ports: set[int] = set()

    # Safe project name for Docker
    safe_name = project_name.lower().replace(" ", "_").replace("-", "_")

    # Assign ports
    if db_port is None:
        db_port = _find_available_port(used_ports)
    used_ports.add(db_port)

    if backend_port is None and structure["has_backend"]:
        backend_port = _find_available_port(used_ports)
    if backend_port:
        used_ports.add(backend_port)

    if frontend_port is None and structure["has_frontend"]:
        frontend_port = _find_available_port(used_ports)
    if frontend_port:
        used_ports.add(frontend_port)

    # Build compose config
    compose: dict = {
        "version": "3.8",
        "services": {},
        "networks": {
            "app_network": {
                "driver": "bridge",
            }
        },
        "volumes": {
            "postgres_data": {},
        },
    }

    # PostgreSQL service
    db_service_name = "db"
    compose["services"][db_service_name] = {
        "image": "postgres:15-alpine",
        "container_name": f"{CONTAINER_PREFIX}_{safe_name}_db",
        "environment": {
            "POSTGRES_DB": safe_name,
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "postgres",
        },
        "ports": [f"{db_port}:5432"],
        "volumes": ["postgres_data:/var/lib/postgresql/data"],
        "networks": ["app_network"],
        "healthcheck": {
            "test": ["CMD-SHELL", "pg_isready -U postgres"],
            "interval": "5s",
            "timeout": "5s",
            "retries": 5,
        },
    }

    # Backend service (FastAPI)
    if structure["has_backend"] and backend_port:
        compose["services"]["backend"] = {
            "build": {
                "context": "./backend",
                "dockerfile": "Dockerfile",
            },
            "container_name": f"{CONTAINER_PREFIX}_{safe_name}_backend",
            "ports": [f"{backend_port}:8000"],
            "environment": {
                "DATABASE_URL": f"postgresql+asyncpg://postgres:postgres@{db_service_name}:5432/{safe_name}",
                "PYTHONUNBUFFERED": "1",
            },
            "depends_on": {
                db_service_name: {"condition": "service_healthy"},
            },
            "networks": ["app_network"],
            "restart": "unless-stopped",
        }

    # Frontend service (Next.js)
    if structure["has_frontend"] and frontend_port:
        api_url = "http://backend:8000" if structure["has_backend"] else ""
        compose["services"]["frontend"] = {
            "build": {
                "context": "./frontend",
                "dockerfile": "Dockerfile",
            },
            "container_name": f"{CONTAINER_PREFIX}_{safe_name}_frontend",
            "ports": [f"{frontend_port}:3000"],
            "environment": {
                "NEXT_PUBLIC_API_URL": f"http://localhost:{backend_port}" if backend_port else "",
                "API_URL": api_url,
            },
            "depends_on": (["backend"] if structure["has_backend"] else []),
            "networks": ["app_network"],
            "restart": "unless-stopped",
        }

    return {
        "compose": compose,
        "ports": {
            "backend": backend_port,
            "frontend": frontend_port,
            "db": db_port,
        },
        "structure": structure,
    }


def _generate_backend_dockerfile(project_path: Path) -> str:
    """Generate a Dockerfile for the FastAPI backend if one doesn't exist.

    Returns the Dockerfile content (also writes it to disk).
    """
    backend_dir = project_path / "backend"
    dockerfile_path = backend_dir / "Dockerfile"

    if dockerfile_path.exists():
        return dockerfile_path.read_text(encoding="utf-8")

    # Check for requirements.txt or pyproject.toml
    has_requirements = (backend_dir / "requirements.txt").exists()
    has_pyproject = (backend_dir / "pyproject.toml").exists()

    if has_pyproject:
        content = """FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir poetry && \\
    poetry config virtualenvs.create false && \\
    poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    elif has_requirements:
        content = """FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    else:
        # Minimal Dockerfile
        content = """FROM python:3.12-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy asyncpg alembic

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

    dockerfile_path.write_text(content, encoding="utf-8")
    return content


def _generate_frontend_dockerfile(project_path: Path) -> str:
    """Generate a Dockerfile for the Next.js frontend if one doesn't exist.

    Returns the Dockerfile content (also writes it to disk).
    """
    frontend_dir = project_path / "frontend"
    dockerfile_path = frontend_dir / "Dockerfile"

    if dockerfile_path.exists():
        return dockerfile_path.read_text(encoding="utf-8")

    content = """FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Run the application
CMD ["npm", "start"]
"""

    dockerfile_path.write_text(content, encoding="utf-8")
    return content


def save_docker_compose(project_path: str, compose_config: dict) -> str:
    """Save docker-compose.yml to the project directory.

    Returns the path to the saved file.
    """
    path = Path(project_path)
    compose_file = path / "docker-compose.yml"

    # Also generate Dockerfiles if needed
    structure = compose_config.get("structure", {})
    if structure.get("has_backend"):
        _generate_backend_dockerfile(path)
    if structure.get("has_frontend"):
        _generate_frontend_dockerfile(path)

    # Write docker-compose.yml
    compose_data = compose_config["compose"]
    compose_file.write_text(
        yaml.dump(compose_data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )

    return str(compose_file)


async def docker_compose_up(project_path: str, timeout: int = DOCKER_TIMEOUT) -> dict:
    """Run docker compose up -d in the project directory.

    Returns dict with status, container info, and URLs.
    """
    path = Path(project_path)
    compose_file = path / "docker-compose.yml"

    if not compose_file.exists():
        raise FileNotFoundError(f"docker-compose.yml not found at {compose_file}")

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "up", "-d", "--build",
            cwd=str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        if proc.returncode != 0:
            error_text = stderr.decode("utf-8", errors="replace")
            return {
                "status": "error",
                "error": error_text,
                "return_code": proc.returncode,
            }

        # Get container status
        status = await get_container_status(project_path)
        return {
            "status": "running",
            "output": stdout.decode("utf-8", errors="replace"),
            "containers": status.get("containers", []),
            "urls": status.get("urls", {}),
        }

    except asyncio.TimeoutError:
        return {
            "status": "error",
            "error": f"Docker compose up timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": "Docker or docker compose not found. Is Docker installed?",
        }


async def docker_compose_down(project_path: str, timeout: int = DOCKER_TIMEOUT) -> dict:
    """Run docker compose down in the project directory.

    Returns dict with status info.
    """
    path = Path(project_path)
    compose_file = path / "docker-compose.yml"

    if not compose_file.exists():
        return {"status": "not_found", "message": "No docker-compose.yml found"}

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "down", "--remove-orphans",
            cwd=str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        if proc.returncode != 0:
            error_text = stderr.decode("utf-8", errors="replace")
            return {
                "status": "error",
                "error": error_text,
                "return_code": proc.returncode,
            }

        return {
            "status": "stopped",
            "output": stdout.decode("utf-8", errors="replace"),
        }

    except asyncio.TimeoutError:
        return {
            "status": "error",
            "error": f"Docker compose down timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": "Docker or docker compose not found. Is Docker installed?",
        }


async def get_container_status(project_path: str) -> dict:
    """Get status of containers for a project via docker compose ps.

    Returns dict with containers list and service URLs.
    """
    path = Path(project_path)
    compose_file = path / "docker-compose.yml"

    if not compose_file.exists():
        return {"status": "not_configured", "containers": [], "urls": {}}

    # Parse compose file for port info
    try:
        compose_data = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
    except Exception:
        compose_data = {}

    urls = _extract_urls_from_compose(compose_data)

    try:
        proc = await asyncio.create_subprocess_exec(
            "docker", "compose", "ps", "--format", "json",
            cwd=str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)

        if proc.returncode != 0:
            return {
                "status": "error",
                "containers": [],
                "urls": urls,
                "error": stderr.decode("utf-8", errors="replace"),
            }

        raw_output = stdout.decode("utf-8", errors="replace").strip()
        containers = []

        if raw_output:
            # docker compose ps --format json can output JSON lines
            for line in raw_output.split("\n"):
                line = line.strip()
                if not line:
                    continue
                try:
                    container = json.loads(line)
                    containers.append({
                        "name": container.get("Name", ""),
                        "service": container.get("Service", ""),
                        "state": container.get("State", ""),
                        "status": container.get("Status", ""),
                        "ports": container.get("Ports", ""),
                    })
                except json.JSONDecodeError:
                    continue

        # Determine overall status
        if not containers:
            overall_status = "stopped"
        elif all(c["state"] == "running" for c in containers):
            overall_status = "running"
        elif any(c["state"] == "running" for c in containers):
            overall_status = "partial"
        else:
            overall_status = "stopped"

        return {
            "status": overall_status,
            "containers": containers,
            "urls": urls,
        }

    except asyncio.TimeoutError:
        return {
            "status": "error",
            "containers": [],
            "urls": urls,
            "error": "Docker compose ps timed out",
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "containers": [],
            "urls": urls,
            "error": "Docker not found",
        }


def _extract_urls_from_compose(compose_data: dict) -> dict:
    """Extract service URLs from compose config based on port mappings."""
    urls = {}
    services = compose_data.get("services", {})

    for service_name, service_config in services.items():
        ports = service_config.get("ports", [])
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ":" in port_mapping:
                host_port = port_mapping.split(":")[0]
                try:
                    port_num = int(host_port)
                    urls[service_name] = f"http://localhost:{port_num}"
                except ValueError:
                    pass

    return urls

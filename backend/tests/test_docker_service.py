"""Tests for Docker service — compose generation, port assignment, structure detection."""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from app.services.docker_service import (
    _detect_project_structure,
    _extract_urls_from_compose,
    _find_available_port,
    _generate_backend_dockerfile,
    _generate_frontend_dockerfile,
    generate_docker_compose,
    save_docker_compose,
)


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    tmpdir = tempfile.mkdtemp(prefix="test_docker_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestPortAssignment:
    """Tests for port finding logic."""

    def test_find_available_port_in_range(self):
        """Should return a port within the configured range."""
        port = _find_available_port()
        assert 30000 <= port <= 39999

    def test_find_available_port_excludes(self):
        """Should not return excluded ports."""
        excluded = {30000, 30001, 30002}
        port = _find_available_port(excluded)
        assert port not in excluded

    def test_find_available_port_raises_on_full_range(self):
        """Should raise when all ports are excluded (edge case)."""
        # This won't actually fill the range but tests the retry limit
        huge_exclude = set(range(30000, 40000))
        with pytest.raises(RuntimeError, match="Cannot find available port"):
            _find_available_port(huge_exclude)


class TestProjectStructureDetection:
    """Tests for detecting project layout."""

    def test_detect_empty_project(self, temp_project_dir):
        """Empty project has no backend or frontend."""
        result = _detect_project_structure(temp_project_dir)
        assert result["has_backend"] is False
        assert result["has_frontend"] is False

    def test_detect_backend_with_pyproject(self, temp_project_dir):
        """Detects FastAPI backend with pyproject.toml."""
        backend = temp_project_dir / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").write_text("[project]\nname='test'\n")

        result = _detect_project_structure(temp_project_dir)
        assert result["has_backend"] is True
        assert result["backend_type"] == "fastapi"

    def test_detect_backend_with_requirements(self, temp_project_dir):
        """Detects FastAPI backend with requirements.txt."""
        backend = temp_project_dir / "backend"
        backend.mkdir()
        (backend / "requirements.txt").write_text("fastapi\n")

        result = _detect_project_structure(temp_project_dir)
        assert result["has_backend"] is True
        assert result["backend_type"] == "fastapi"

    def test_detect_backend_with_main_py(self, temp_project_dir):
        """Detects FastAPI backend with main.py."""
        backend = temp_project_dir / "backend"
        backend.mkdir()
        (backend / "main.py").write_text("from fastapi import FastAPI\n")

        result = _detect_project_structure(temp_project_dir)
        assert result["has_backend"] is True
        assert result["backend_type"] == "fastapi"

    def test_detect_frontend_with_package_json(self, temp_project_dir):
        """Detects Next.js frontend with package.json."""
        frontend = temp_project_dir / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text('{"name": "test"}\n')

        result = _detect_project_structure(temp_project_dir)
        assert result["has_frontend"] is True
        assert result["frontend_type"] == "nextjs"

    def test_detect_frontend_with_next_config(self, temp_project_dir):
        """Detects Next.js frontend with next.config.js."""
        frontend = temp_project_dir / "frontend"
        frontend.mkdir()
        (frontend / "next.config.js").write_text("module.exports = {}\n")

        result = _detect_project_structure(temp_project_dir)
        assert result["has_frontend"] is True
        assert result["frontend_type"] == "nextjs"

    def test_detect_full_stack(self, temp_project_dir):
        """Detects both backend and frontend."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "pyproject.toml").write_text("[project]\n")
        (temp_project_dir / "frontend").mkdir()
        (temp_project_dir / "frontend" / "package.json").write_text("{}\n")

        result = _detect_project_structure(temp_project_dir)
        assert result["has_backend"] is True
        assert result["has_frontend"] is True


class TestDockerComposeGeneration:
    """Tests for docker-compose.yml generation."""

    def test_generate_full_stack(self, temp_project_dir):
        """Generates compose with backend, frontend, and DB for full-stack project."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "pyproject.toml").write_text("[project]\n")
        (temp_project_dir / "frontend").mkdir()
        (temp_project_dir / "frontend" / "package.json").write_text("{}\n")

        result = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test_app",
            backend_port=31000,
            frontend_port=31001,
            db_port=31002,
        )

        compose = result["compose"]
        assert "db" in compose["services"]
        assert "backend" in compose["services"]
        assert "frontend" in compose["services"]
        assert result["ports"]["backend"] == 31000
        assert result["ports"]["frontend"] == 31001
        assert result["ports"]["db"] == 31002

    def test_generate_backend_only(self, temp_project_dir):
        """Generates compose with only backend + DB when no frontend."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "requirements.txt").write_text("fastapi\n")

        result = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="api_only",
            backend_port=31000,
            db_port=31002,
        )

        compose = result["compose"]
        assert "db" in compose["services"]
        assert "backend" in compose["services"]
        assert "frontend" not in compose["services"]

    def test_generate_with_auto_ports(self, temp_project_dir):
        """Auto-assigns ports when not specified."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "pyproject.toml").write_text("[project]\n")
        (temp_project_dir / "frontend").mkdir()
        (temp_project_dir / "frontend" / "package.json").write_text("{}\n")

        result = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="auto_port_app",
        )

        ports = result["ports"]
        assert ports["backend"] is not None
        assert ports["frontend"] is not None
        assert ports["db"] is not None
        # All ports should be different
        assert len({ports["backend"], ports["frontend"], ports["db"]}) == 3

    def test_compose_has_healthcheck(self, temp_project_dir):
        """PostgreSQL service should have a healthcheck."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "pyproject.toml").write_text("[project]\n")

        result = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test",
            db_port=31002,
        )

        db_service = result["compose"]["services"]["db"]
        assert "healthcheck" in db_service
        test_cmd = " ".join(db_service["healthcheck"]["test"])
        assert "pg_isready" in test_cmd

    def test_backend_depends_on_db(self, temp_project_dir):
        """Backend service should depend on DB with health condition."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "pyproject.toml").write_text("[project]\n")

        result = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test",
            backend_port=31000,
            db_port=31002,
        )

        backend = result["compose"]["services"]["backend"]
        assert "db" in backend["depends_on"]

    def test_frontend_depends_on_backend(self, temp_project_dir):
        """Frontend should depend on backend when both exist."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "pyproject.toml").write_text("[project]\n")
        (temp_project_dir / "frontend").mkdir()
        (temp_project_dir / "frontend" / "package.json").write_text("{}\n")

        result = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test",
            backend_port=31000,
            frontend_port=31001,
            db_port=31002,
        )

        frontend = result["compose"]["services"]["frontend"]
        assert "backend" in frontend["depends_on"]

    def test_compose_network(self, temp_project_dir):
        """All services should use the app_network."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "pyproject.toml").write_text("[project]\n")

        result = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test",
            backend_port=31000,
            db_port=31002,
        )

        compose = result["compose"]
        assert "app_network" in compose["networks"]
        for service_config in compose["services"].values():
            assert "app_network" in service_config["networks"]


class TestSaveDockerCompose:
    """Tests for saving docker-compose.yml to disk."""

    def test_save_creates_file(self, temp_project_dir):
        """Should create docker-compose.yml in project directory."""
        (temp_project_dir / "backend").mkdir()
        (temp_project_dir / "backend" / "pyproject.toml").write_text("[project]\n")

        config = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test",
            backend_port=31000,
            db_port=31002,
        )

        path = save_docker_compose(str(temp_project_dir), config)
        assert Path(path).exists()

        # Verify it's valid YAML
        content = Path(path).read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        assert "services" in parsed

    def test_save_generates_backend_dockerfile(self, temp_project_dir):
        """Should generate Dockerfile for backend if not present."""
        backend = temp_project_dir / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").write_text("[project]\n")

        config = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test",
            backend_port=31000,
            db_port=31002,
        )

        save_docker_compose(str(temp_project_dir), config)
        assert (backend / "Dockerfile").exists()

    def test_save_generates_frontend_dockerfile(self, temp_project_dir):
        """Should generate Dockerfile for frontend if not present."""
        frontend = temp_project_dir / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text("{}\n")

        config = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test",
            frontend_port=31001,
            db_port=31002,
        )

        save_docker_compose(str(temp_project_dir), config)
        assert (frontend / "Dockerfile").exists()

    def test_save_preserves_existing_dockerfile(self, temp_project_dir):
        """Should not overwrite existing Dockerfile."""
        backend = temp_project_dir / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").write_text("[project]\n")
        existing_content = "FROM custom:latest\nRUN echo custom\n"
        (backend / "Dockerfile").write_text(existing_content)

        config = generate_docker_compose(
            project_path=str(temp_project_dir),
            project_name="test",
            backend_port=31000,
            db_port=31002,
        )

        save_docker_compose(str(temp_project_dir), config)
        assert (backend / "Dockerfile").read_text() == existing_content


class TestDockerfileGeneration:
    """Tests for Dockerfile generation."""

    def test_backend_dockerfile_with_pyproject(self, temp_project_dir):
        """Generates poetry-based Dockerfile for pyproject.toml projects."""
        backend = temp_project_dir / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").write_text("[project]\n")

        content = _generate_backend_dockerfile(temp_project_dir)
        assert "poetry" in content
        assert "uvicorn" in content

    def test_backend_dockerfile_with_requirements(self, temp_project_dir):
        """Generates pip-based Dockerfile for requirements.txt projects."""
        backend = temp_project_dir / "backend"
        backend.mkdir()
        (backend / "requirements.txt").write_text("fastapi\n")

        content = _generate_backend_dockerfile(temp_project_dir)
        assert "requirements.txt" in content
        assert "pip install" in content

    def test_backend_dockerfile_minimal(self, temp_project_dir):
        """Generates minimal Dockerfile when no dependency file exists."""
        backend = temp_project_dir / "backend"
        backend.mkdir()

        content = _generate_backend_dockerfile(temp_project_dir)
        assert "pip install" in content
        assert "fastapi" in content

    def test_frontend_dockerfile(self, temp_project_dir):
        """Generates Node.js Dockerfile for frontend."""
        frontend = temp_project_dir / "frontend"
        frontend.mkdir()

        content = _generate_frontend_dockerfile(temp_project_dir)
        assert "node" in content.lower()
        assert "npm" in content


class TestExtractUrls:
    """Tests for URL extraction from compose config."""

    def test_extract_urls_full_stack(self):
        """Extracts URLs for all services with port mappings."""
        compose_data = {
            "services": {
                "backend": {"ports": ["31000:8000"]},
                "frontend": {"ports": ["31001:3000"]},
                "db": {"ports": ["31002:5432"]},
            }
        }
        urls = _extract_urls_from_compose(compose_data)
        assert urls["backend"] == "http://localhost:31000"
        assert urls["frontend"] == "http://localhost:31001"
        assert urls["db"] == "http://localhost:31002"

    def test_extract_urls_no_services(self):
        """Returns empty dict when no services exist."""
        urls = _extract_urls_from_compose({})
        assert urls == {}

    def test_extract_urls_no_ports(self):
        """Returns empty dict when services have no ports."""
        compose_data = {"services": {"backend": {}}}
        urls = _extract_urls_from_compose(compose_data)
        assert urls == {}

"""Project model."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Project(Base, TimestampMixin):
    """Projects table — tracks each app-building project."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    idea_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="created")
    project_path: Mapped[str] = mapped_column(String(500), nullable=False)
    current_phase: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Relationships
    agent_logs = relationship("AgentLog", back_populates="project", cascade="all, delete-orphan")
    flow_nodes = relationship("FlowNode", back_populates="project", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", back_populates="project", cascade="all, delete-orphan")
    token_usages = relationship("TokenUsage", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name!r}, status={self.status!r})>"

"""TokenUsage model."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin


class TokenUsage(Base, CreatedAtMixin):
    """Token usage tracking per agent per task."""

    __tablename__ = "token_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    agent: Mapped[str] = mapped_column(String(20), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Optional FK to agent_tasks
    agent_task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agent_tasks.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    project = relationship("Project", back_populates="token_usages")
    agent_task = relationship("AgentTask", back_populates="token_usages")

    def __repr__(self) -> str:
        return f"<TokenUsage(id={self.id}, agent={self.agent!r}, input={self.input_tokens}, output={self.output_tokens})>"

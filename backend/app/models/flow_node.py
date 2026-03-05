"""FlowNode model."""

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FlowNode(Base, TimestampMixin):
    """Dashboard flow nodes for project visualization."""

    __tablename__ = "flow_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    node_type: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    parent_node_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("flow_nodes.id", ondelete="SET NULL"), nullable=True
    )
    position_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_y: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="flow_nodes")
    parent_node = relationship("FlowNode", remote_side=[id], backref="child_nodes")

    def __repr__(self) -> str:
        return f"<FlowNode(id={self.id}, label={self.label!r}, status={self.status!r})>"

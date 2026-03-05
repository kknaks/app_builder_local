"""Model import and structure tests."""

import pytest

from app.models import (
    AgentLog,
    AgentTask,
    Base,
    ChatMessage,
    FlowNode,
    Project,
    Setting,
    TokenUsage,
)


def test_all_models_registered():
    """All 7 tables should be registered in Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "projects",
        "agent_logs",
        "flow_nodes",
        "settings",
        "chat_messages",
        "agent_tasks",
        "token_usage",
    }
    assert expected_tables == table_names


def test_project_tablename():
    """Project model should map to 'projects' table."""
    assert Project.__tablename__ == "projects"


def test_agent_log_tablename():
    """AgentLog model should map to 'agent_logs' table."""
    assert AgentLog.__tablename__ == "agent_logs"


def test_flow_node_tablename():
    """FlowNode model should map to 'flow_nodes' table."""
    assert FlowNode.__tablename__ == "flow_nodes"


def test_setting_tablename():
    """Setting model should map to 'settings' table."""
    assert Setting.__tablename__ == "settings"


def test_chat_message_tablename():
    """ChatMessage model should map to 'chat_messages' table."""
    assert ChatMessage.__tablename__ == "chat_messages"


def test_agent_task_tablename():
    """AgentTask model should map to 'agent_tasks' table."""
    assert AgentTask.__tablename__ == "agent_tasks"


def test_token_usage_tablename():
    """TokenUsage model should map to 'token_usage' table."""
    assert TokenUsage.__tablename__ == "token_usage"


@pytest.mark.parametrize(
    "model_cls,expected_columns",
    [
        (Project, {"id", "name", "idea_text", "status", "project_path", "current_phase", "created_at", "updated_at"}),
        (AgentLog, {"id", "project_id", "agent", "action", "log_text", "log_type", "created_at"}),
        (
            FlowNode,
            {
                "id",
                "project_id",
                "node_type",
                "label",
                "status",
                "parent_node_id",
                "position_x",
                "position_y",
                "created_at",
                "updated_at",
            },
        ),
        (Setting, {"id", "key", "value", "created_at", "updated_at"}),
        (ChatMessage, {"id", "project_id", "agent", "role", "content", "created_at"}),
        (
            AgentTask,
            {
                "id",
                "project_id",
                "agent",
                "command",
                "status",
                "result",
                "error",
                "created_at",
                "started_at",
                "updated_at",
            },
        ),
        (
            TokenUsage,
            {"id", "project_id", "agent", "input_tokens", "output_tokens", "cost_usd", "agent_task_id", "created_at"},
        ),
    ],
)
def test_model_columns(model_cls, expected_columns):
    """Each model should have the expected columns."""
    actual_columns = {c.name for c in model_cls.__table__.columns}
    assert expected_columns == actual_columns, f"{model_cls.__name__}: expected {expected_columns}, got {actual_columns}"

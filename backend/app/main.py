"""App Builder Local — FastAPI Application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.routers.agent_tasks import router as agent_tasks_router
from app.routers.chat import router as chat_router
from app.routers.cost import router as cost_router
from app.routers.docker import router as docker_router
from app.routers.flow_nodes import router as flow_nodes_router
from app.routers.planning import router as planning_router
from app.routers.projects import router as projects_router
from app.routers.settings import router as settings_router
from app.routers.sprint import router as sprint_router
from app.routers.websocket import router as ws_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    # Startup: cleanup stale tasks
    try:
        from app.database.session import async_session
        from app.services.agent_task_service import cleanup_stale_tasks

        async with async_session() as db:
            cleaned = await cleanup_stale_tasks(db)
            if cleaned:
                logger.info("Startup: cleaned %d stale tasks", cleaned)
    except Exception as e:
        logger.warning("Startup cleanup skipped: %s", e)

    yield

    # Shutdown: terminate all running agent processes
    try:
        from app.core.agent_runner import process_manager

        count = await process_manager.cleanup_all()
        if count:
            logger.info("Shutdown: terminated %d agent processes", count)
    except Exception as e:
        logger.warning("Shutdown cleanup error: %s", e)


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

# Register unified error handlers
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:23000",
        "http://127.0.0.1:23000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(settings_router)
app.include_router(projects_router)
app.include_router(agent_tasks_router)
app.include_router(chat_router)
app.include_router(cost_router)
app.include_router(planning_router)
app.include_router(flow_nodes_router)
app.include_router(sprint_router)
app.include_router(docker_router)
app.include_router(ws_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

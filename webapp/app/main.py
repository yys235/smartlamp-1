from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.gateway import SmartLampGateway
from app.frontend.routes import router as frontend_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    gateway = SmartLampGateway(settings)
    gateway.start()
    app.state.gateway = gateway
    app.state.settings = settings
    try:
        yield
    finally:
        gateway.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)
app.include_router(frontend_router)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).parent / "frontend" / "static")),
    name="static",
)

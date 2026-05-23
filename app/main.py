from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router as api_router
from app.config import get_settings
from app.database import init_db
from app.logging_config import configure_logging
from app.simulation.engine import SimulationEngine
from app.websocket.routes import router as websocket_router


configure_logging()
settings = get_settings()
templates = Jinja2Templates(directory=str(settings.base_dir / "app" / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.engine = SimulationEngine()
    yield
    app.state.engine.pause()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(settings.base_dir / "app" / "static")), name="static")
app.include_router(api_router)
app.include_router(websocket_router)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"app_name": settings.app_name})


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(settings.base_dir / "app" / "static" / "favicon.svg", media_type="image/svg+xml")

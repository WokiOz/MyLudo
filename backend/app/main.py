from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api import auth, bgg, exchange, games, health
from app.config import get_settings
from app.db import run_migrations


@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_migrations()
    yield


app = FastAPI(title="MyLudo", version="0.2.0", lifespan=lifespan)
for module in (health, auth, games, bgg, exchange):
    app.include_router(module.router)

static_dir = Path(get_settings().static_dir)

if static_dir.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Sert le frontend compilé, avec repli sur index.html pour le routage Vue."""
        file = (static_dir / path).resolve()
        if path and file.is_file() and file.is_relative_to(static_dir.resolve()):
            return FileResponse(file)
        return FileResponse(static_dir / "index.html")

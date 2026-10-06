from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api import health
from app.config import get_settings

app = FastAPI(title="MyLudo", version="0.1.0")
app.include_router(health.router)

static_dir = Path(get_settings().static_dir)

if static_dir.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        """Sert le frontend compilé, avec repli sur index.html pour le routage Vue."""
        file = (static_dir / path).resolve()
        if path and file.is_file() and file.is_relative_to(static_dir.resolve()):
            return FileResponse(file)
        return FileResponse(static_dir / "index.html")

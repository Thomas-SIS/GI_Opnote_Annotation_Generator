import inspect
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

from routes.image_route import router as image_router
from routes.opnote_route import router as opnote_router
from utils.database_init import AsyncDatabaseInitializer

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file if present


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager to initialize:
      - the SQLite database (always new on startup, at DATABASE_DIR/app.db)
      - the OpenAI async client
    and attach them to `app.state`.
    """
    # Initialize DB using DATABASE_DIR only.
    db_initializer = AsyncDatabaseInitializer()

    # This will delete any existing DB at db_path and create a fresh one.
    await db_initializer.ensure_database()
    app.state.db_initializer = db_initializer

    # Initialize OpenAI async client
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    try:
        openai_client = AsyncOpenAI()
    except Exception as exc:
        raise RuntimeError("Failed to initialize OpenAI Async client") from exc

    app.state.openai_client = openai_client

    try:
        yield
    finally:
        # Gracefully close the OpenAI client if it exposes a close/aclose method.
        client = getattr(app.state, "openai_client", None)
        if client is not None:
            aclose = getattr(client, "aclose", None) or getattr(client, "close", None)
            if aclose is not None:
                try:
                    if inspect.iscoroutinefunction(aclose):
                        await aclose()
                    else:
                        result = aclose()
                        if inspect.isawaitable(result):
                            await result
                except Exception:
                    # Ignore shutdown errors to avoid masking more important issues.
                    pass


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.
    """
    app = FastAPI(lifespan=lifespan)

    # Serve static assets from the public directory, if it exists.
    if PUBLIC_DIR.exists():
        app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """
        Serve the frontend index page from the public directory.
        """
        index_path = PUBLIC_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="Frontend not found")
        return FileResponse(index_path)

    @app.get("/health")
    async def health(request: Request):
        """
        Simple health check that verifies DB initializer and OpenAI client presence.
        """
        has_db = hasattr(request.app.state, "db_initializer")
        has_openai = (
            hasattr(request.app.state, "openai_client")
            and request.app.state.openai_client is not None
        )
        return {"ok": True, "db_initialized": has_db, "openai_available": has_openai}

    # Register application routers
    app.include_router(image_router)
    app.include_router(opnote_router)

    return app


app = create_app()

import inspect
import os
from contextlib import asynccontextmanager
from pathlib import Path
from openai import AsyncOpenAI
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from routes.image_route import router as image_router
from routes.opnote_route import router as opnote_router

from utils.database_init import AsyncDatabaseInitializer
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager to initialize DB and OpenAI async client.

    Attaches `db_initializer` and `openai_client` to `app.state`.
    """
    project_root = Path(__file__).resolve().parent

    # Initialize DB
    db_initializer = AsyncDatabaseInitializer(project_root)
    await db_initializer.ensure_database()
    app.state.db_initializer = db_initializer

    # Initialize OpenAI async client if library available and API key present
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key is None:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")
    else:
        try:
            openai_client = AsyncOpenAI()
        except Exception as exc:
            raise RuntimeError("Failed to initialize OpenAI Async client") from exc

    app.state.openai_client = openai_client

    try:
        yield
    finally:
        # Close OpenAI client if it has an async or sync close method
        client = getattr(app.state, "openai_client", None)
        if client is not None:
            aclose = getattr(client, "aclose", None) or getattr(client, "close", None)
            if aclose is not None:
                try:
                    # If the close method itself is an async function
                    if inspect.iscoroutinefunction(aclose):
                        await aclose()
                    else:
                        # It might be sync but still return an awaitable
                        result = aclose()
                        if inspect.isawaitable(result):
                            await result
                except Exception:
                    # Swallow errors on shutdown to avoid crashing the server
                    pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with lifespan-managed DB and OpenAI clients.
    """

    app = FastAPI(lifespan=lifespan)

    # Serve static assets under /public and root index.html
    if PUBLIC_DIR.exists():
        app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="public")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """Serve the frontend index page from the public directory."""
        index_path = PUBLIC_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="Frontend not found")
        return FileResponse(index_path)

    @app.get("/health")
    async def health(request: Request):
        """Simple health check that verifies DB initializer and OpenAI client presence."""
        has_db = hasattr(request.app.state, "db_initializer")
        has_openai = (
            hasattr(request.app.state, "openai_client")
            and request.app.state.openai_client is not None
        )
        return {"ok": True, "db_initialized": has_db, "openai_available": has_openai}

    # `public` is already mounted at root above; no additional mounts required here.

    # Register application routers
    app.include_router(image_router)
    app.include_router(opnote_router)

    return app


app = create_app()

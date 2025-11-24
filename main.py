"""Application entrypoint for the annotation generator.

This module creates a FastAPI app that serves the frontend files
located in the `public/` directory as static files and returns
`index.html` at the application root.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from dotenv import load_dotenv
from openai import AsyncOpenAI
import os
from contextlib import asynccontextmanager

from routes.image_label_route import router as image_label_router

# DB client and init utilities
from dal.image_manager_dal import AsyncSQLiteClient
from utils.sqlite_init import ensure_db


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: create and close shared DB and OpenAI clients."""
    # Ensure DB and create client
    db_path = await ensure_db()
    app.state.db_client = AsyncSQLiteClient(str(db_path))
    await app.state.db_client.connect()
    app.state.openai_client = AsyncOpenAI()
    try:
        yield
    finally:
        db_client = getattr(app.state, "db_client", None)
        if db_client is not None:
            await db_client.close()
        openai_client = getattr(app.state, "openai_client", None)
        if openai_client is not None:
            await openai_client.close()


app = FastAPI(lifespan=lifespan)

# Path to the public directory (relative to this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

app.include_router(image_label_router)

if os.path.isdir(PUBLIC_DIR):
    app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="public")


@app.get("/index.html", include_in_schema=False)
def index_html():
    """Return the index.html file from the public directory."""
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return RedirectResponse(url="/")


@app.get("/", include_in_schema=False)
def root():
    """Redirect root to the mounted static files or index page."""
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Public directory not found or index.html missing."}

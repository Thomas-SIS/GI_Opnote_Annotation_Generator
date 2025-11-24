"""SQLite initialization helpers.

Create the `data/` directory and ensure the sqlite file exists and
apply a minimal placeholder schema. The schema is intentionally
simple and marked TODO for domain-specific columns.
"""

from pathlib import Path
from typing import Optional

import aiosqlite
import os


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "database" / "app.db"

# Directory to store original image files on disk
ORIGINAL_IMAGE_DIR = Path(__file__).resolve().parent.parent / "database" / "images"


async def ensure_db(db_path: Optional[Path] = None) -> Path:
    """Ensure the sqlite database file exists and create placeholder tables.

    Returns the path to the database file.
    """
    db_path = db_path or DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    ORIGINAL_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    # Create file if missing and apply schema
    async with aiosqlite.connect(str(db_path)) as conn:
        # Placeholder schema retained for backward compatibility
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )

        # New table: image_segments
        # - id stored as TEXT UUID primary key
        # - label_json stored as TEXT (JSON) — SQLite supports JSON1 functions
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image_segments (
                id TEXT PRIMARY KEY,
                segment_key TEXT NOT NULL,
                original_url TEXT,
                thumbnail_url TEXT,
                thumbnail_blob BLOB,
                label_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )

        # Helpful index for lookups by segment_key
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_image_segments_segment_key ON image_segments(segment_key);"
        )

        await conn.commit()

    return db_path

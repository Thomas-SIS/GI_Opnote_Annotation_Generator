import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

import aiosqlite


class AsyncDatabaseInitializer:
    """
    Manage an async SQLite database using the DATABASE_DIR environment variable.

    The database file is located at: <DATABASE_DIR>/app.db. On first use the
    directory is created (if missing) and the schema for the IMAGE table is
    ensured without deleting any existing data.
    """

    def __init__(self, parent_folder: Optional[Path | str] = None) -> None:
        # parent_folder is accepted for backward compatibility but ignored;
        # we always rely on DATABASE_DIR as requested.
        env_dir = os.getenv("DATABASE_DIR")

        if env_dir is None or not env_dir.strip():
            raise RuntimeError(
                "DATABASE_DIR environment variable must be set to a writable "
                "directory path where the SQLite database file will be stored."
            )

        db_dir = Path(env_dir).expanduser()

        # If the path exists but is not a directory, that's a configuration error.
        if db_dir.exists() and not db_dir.is_dir():
            raise RuntimeError(
                f"DATABASE_DIR={env_dir!r} points to a file, not a directory "
                f"({db_dir}). Please set DATABASE_DIR to a directory path."
            )

        # Try to create the directory if it does not exist.
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to create or access database directory at {db_dir}"
            ) from exc

        # Attributes (keep names similar to older version for compatibility)
        # parent_folder is no longer used; but we still expose `parent`.
        self.parent = db_dir
        self.db_dir = db_dir
        self.db_path = self.db_dir / "app.db"

        # Internal flag to ensure schema setup runs only once per instance.
        self._initialized = False

    async def ensure_database(self) -> None:
        """
        Ensure the SQLite database file and IMAGE schema exist at `self.db_path`.

        On first call this will create the database file if missing, create the
        IMAGE table, add any missing columns (`label`, `created_at`), and create
        indexes. Subsequent calls on the same instance are no-ops.
        """
        if self._initialized:
            return

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute(
                        """
                        CREATE TABLE IF NOT EXISTS IMAGE (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            image_filename TEXT NOT NULL,
                            image_description TEXT,
                            image_thumbnail BLOB,
                            label TEXT,
                            created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
                        )
                        """
                    )

                    # Ensure columns exist for older schemas.
                    cur = await db.execute("PRAGMA table_info(IMAGE)")
                    cols = await cur.fetchall()
                    col_names = {col[1] for col in cols}
                    if "label" not in col_names:
                        await db.execute("ALTER TABLE IMAGE ADD COLUMN label TEXT")
                    if "created_at" not in col_names:
                        await db.execute(
                            "ALTER TABLE IMAGE ADD COLUMN created_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))"
                        )
                        await db.execute(
                            "UPDATE IMAGE SET created_at = strftime('%s','now') WHERE created_at IS NULL"
                        )

                    await db.execute(
                        "CREATE INDEX IF NOT EXISTS idx_image_created_at ON IMAGE(created_at)"
                    )

                    await db.commit()
                break
            except FileNotFoundError:
                # On some platforms a transient missing file error may occur; retry a few times.
                if attempt >= max_attempts:
                    raise
                await asyncio.sleep(0.1 * attempt)
            except Exception:
                # Re-raise unexpected exceptions for visibility.
                raise

        self._initialized = True

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """
        Async context manager yielding an `aiosqlite.Connection`.

        The database is created/verified on the first use via `ensure_database()`.
        """
        await self.ensure_database()
        conn = await aiosqlite.connect(self.db_path)
        try:
            yield conn
        finally:
            await conn.close()

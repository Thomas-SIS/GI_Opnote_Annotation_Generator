import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

import aiosqlite


class AsyncDatabaseInitializer:
    """
    Manage an async SQLite database using the DATABASE_DIR environment variable.

    - The database file is located at: <DATABASE_DIR>/app.db
    - DATABASE_DIR is required. A RuntimeError is raised if it is missing
      or invalid (not a directory and cannot be created).
    - On the first call to `ensure_database()` for a given instance:
        * Any existing database file at that path is deleted.
        * A new database file is created.
        * The IMAGE table is created (and the `label` column ensured).
    - Subsequent calls to `ensure_database()` on the same instance are no-ops,
      so it is safe for `connection()` to call it.
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

        # Internal flag to make the "wipe and recreate" behavior one-time per instance.
        self._initialized = False

    async def ensure_database(self) -> None:
        """
        Ensure a fresh SQLite database exists at `self.db_path`.

        On first call this will:
            - Delete any existing database file at `self.db_path`.
            - Create a new database file.
            - Create the IMAGE table (and add `label` column if missing).

        Subsequent calls on the same instance are no-ops.
        """
        if self._initialized:
            return

        # Delete old DB if present so we always start clean on app startup.
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to delete existing database at {self.db_path}"
                ) from exc

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                async with aiosqlite.connect(self.db_path) as db:
                    # Create table with label column present
                    await db.execute(
                        """
                        CREATE TABLE IF NOT EXISTS IMAGE (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            image_filename TEXT NOT NULL,
                            image_description TEXT,
                            image_thumbnail BLOB,
                            label TEXT
                        )
                        """
                    )

                    # For extra safety, ensure label column exists if the table
                    # was already present with an older schema.
                    cur = await db.execute("PRAGMA table_info(IMAGE)")
                    cols = await cur.fetchall()
                    col_names = {col[1] for col in cols}
                    if "label" not in col_names:
                        await db.execute("ALTER TABLE IMAGE ADD COLUMN label TEXT")

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

        The database is created/reset on the first use via `ensure_database()`.
        """
        await self.ensure_database()
        conn = await aiosqlite.connect(self.db_path)
        try:
            yield conn
        finally:
            await conn.close()

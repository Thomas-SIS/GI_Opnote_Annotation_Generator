"""Async SQLite database initializer utility.

Provides AsyncDatabaseInitializer which ensures a SQLite database file
exists at `parent_folder/database/app.db` and that the `IMAGE` table
is created with the specified schema.

Usage example:
	initializer = AsyncDatabaseInitializer(Path(__file__).parents[1])
	await initializer.ensure_database()
	async with initializer.connection() as conn:
		# use conn (aiosqlite.Connection)
"""

from __future__ import annotations

import os
import asyncio
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
from contextlib import asynccontextmanager


class AsyncDatabaseInitializer:
	"""Ensure an async SQLite database and required tables exist.

	Args:
		parent_folder: Path to the project parent folder. The database file
			will be created at `parent_folder/database/app.db`.

	Methods:
		ensure_database(): Create directory, file, and IMAGE table if missing.
		connection(): Async context manager yielding an `aiosqlite.Connection`.
	"""

	def __init__(self, parent_folder: Path | str) -> None:
		self.parent = Path(parent_folder)
		self.db_dir = self.parent / "database"
		self.db_path = self.db_dir / "app.db"
		# Allow overriding the database directory with the DATABASE_DIR env var.
		# If set, DATABASE_DIR should be a folder path where the DB file will live.
		env_dir = os.getenv("DATABASE_DIR")
		if env_dir:
			self.db_dir = Path(env_dir)
		else:
			if parent_folder is None:
				parent_folder = Path(__file__).resolve().parent
			self.parent = Path(parent_folder)
			self.db_dir = self.parent / "database"

		self.db_path = self.db_dir / "app.db"

	async def ensure_database(self) -> None:
		"""Create the database file and IMAGE table if they don't exist.

		This is safe to call multiple times and will add missing columns.
		"""
		# make sure directory exists
		self.db_dir.mkdir(parents=True, exist_ok=True)

		# open connection and create table if not exists
		async with aiosqlite.connect(self.db_path) as db:
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
			# Backfill older DBs missing the label column.
			cur = await db.execute("PRAGMA table_info(IMAGE)")
			cols = await cur.fetchall()
			col_names = {col[1] for col in cols}
			if "label" not in col_names:
				await db.execute("ALTER TABLE IMAGE ADD COLUMN label TEXT")
			await db.commit()

	@asynccontextmanager
	async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
		"""Async context manager that yields an aiosqlite connection.

		Example:
			async with initializer.connection() as conn:
				await conn.execute(...)
		"""

		# ensure DB initialized before handing out connections
		await self.ensure_database()
		conn = await aiosqlite.connect(self.db_path)
		try:
			yield conn
		finally:
			await conn.close()



"""Async SQLite database initializer utility.

This module provides AsyncDatabaseInitializer, which manages a SQLite database
located under the directory specified by the `DATABASE_DIR` environment variable.

Behavior:
    - On the first call to `ensure_database()` per AsyncDatabaseInitializer instance,
      any existing database file at `DATABASE_DIR/app.db` is deleted and a fresh
      database is created.
    - Subsequent calls to `ensure_database()` on the same instance are no-ops.
    - `DATABASE_DIR` is required; a clear RuntimeError is raised if it is not
      set or is not usable.

Usage example:
    initializer = AsyncDatabaseInitializer()
    await initializer.ensure_database()
    async with initializer.connection() as conn:
        # use conn (aiosqlite.Connection)
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite


class AsyncDatabaseInitializer:
    """Manage an async SQLite database using the DATABASE_DIR environment variable.

    The database file is located at:  <DATABASE_DIR>/app.db

    On first call to `ensure_database()`:
        * Any existing database file at that path is deleted.
        * A new database file is created.
        * The IMAGE table is created (and the `label` column ensured).

    On subsequent calls, `ensure_database()` is a no-op.
    """

    def __init__(self) -> None:
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

        # Try to create the directory if it doesn't exist.
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to create or access database directory at {db_dir}"
            ) from exc

        self.db_dir = db_dir
        self.db_path = self.db_dir / "app.db"

        # Internal flag to make the "wipe and recreate" behavior one-time per instance.
        self._initialized = False

    async def ensure_database(self) -> None:
        """Ensure a fresh SQLite database exists at `self.db_path`.

        On first call this will:
            - Delete any existing database file at `self.db_path`.
            - Create a new database file.
            - Create the IMAGE table (and add `label` column if missing).

        Subsequent calls on the same instance are no-ops.
        """
        if self._initialized:
            return

        # Delete the old DB if present so we always start clean on app startup.
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

                    # Ensure the `label` column exists (for safety with future changes).
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
                # Re-raise unexpected exceptions for visibility
                raise

        self._initialized = True

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Async context manager yielding an `aiosqlite.Connection`.

        The database is created/reset on the first use via `ensure_database()`.
        """
        await self.ensure_database()
        conn = await aiosqlite.connect(self.db_path)
        try:
            yield conn
        finally:
            await conn.close()

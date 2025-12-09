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




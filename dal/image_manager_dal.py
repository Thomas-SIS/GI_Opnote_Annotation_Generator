
"""Async SQLite data access layer.

This module provides an OOP async client for interacting with a
SQLite database file using `aiosqlite`.

The class `AsyncSQLiteClient` exposes async context management for the
connection and simple helpers for executing queries and fetching rows.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional

import aiosqlite
import json
import uuid
from pathlib import Path
import aiofiles


class AsyncSQLiteClient:
	"""Async client wrapper around an `aiosqlite` connection.

	Usage:
		client = AsyncSQLiteClient(db_path)
		await client.connect()
		await client.execute("CREATE TABLE ...")
		await client.close()

	The client is intentionally small — add additional domain methods
	(e.g. insert_image, get_image_by_id) in higher-level DAL modules.
	"""

	def __init__(self, db_path: str):
		self.db_path = db_path
		self._conn: Optional[aiosqlite.Connection] = None

	async def connect(self) -> None:
		"""Open an aiosqlite connection and enable WAL journaling.

		Args:
			db_path: Path to the sqlite file (provided at init).
		"""
		if self._conn:
			return
		os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
		self._conn = await aiosqlite.connect(self.db_path)
		await self._conn.execute("PRAGMA journal_mode=WAL;")
		await self._conn.execute("PRAGMA foreign_keys=ON;")
		await self._conn.commit()

	async def close(self) -> None:
		"""Close the underlying connection if open."""
		if self._conn:
			await self._conn.close()
			self._conn = None

	async def execute(self, sql: str, params: Optional[tuple] = None) -> None:
		"""Execute a statement (INSERT/UPDATE/DELETE or DDL) and commit.

		Args:
			sql: SQL statement to execute.
			params: Optional tuple of parameters for parameterized queries.
		"""
		if not self._conn:
			raise RuntimeError("Database connection is not open. Call connect() first.")
		async with self._conn.execute(sql, params or ()) as cur:
			await self._conn.commit()

	async def fetch_one(self, sql: str, params: Optional[tuple] = None) -> Optional[aiosqlite.Row]:
		"""Fetch a single row from the database.

		Returns None if no row matched.
		"""
		if not self._conn:
			raise RuntimeError("Database connection is not open. Call connect() first.")
		async with self._conn.execute(sql, params or ()) as cur:
			row = await cur.fetchone()
			return row

	async def fetch_all(self, sql: str, params: Optional[tuple] = None) -> List[aiosqlite.Row]:
		"""Fetch all rows for the given query."""
		if not self._conn:
			raise RuntimeError("Database connection is not open. Call connect() first.")
		async with self._conn.execute(sql, params or ()) as cur:
			rows = await cur.fetchall()
			return rows

	async def executemany(self, sql: str, seq_of_params: List[tuple]) -> None:
		"""Execute many parameterized statements and commit."""
		if not self._conn:
			raise RuntimeError("Database connection is not open. Call connect() first.")
		await self._conn.executemany(sql, seq_of_params)
		await self._conn.commit()

	# Domain helpers for image_segments
	async def insert_image_segment(self, segment_key: str, original_url: Optional[str], thumbnail_url: Optional[str], label_json: Optional[dict], id: Optional[str] = None) -> str:
		"""Insert a new image_segment row and return its UUID id.

		Args:
			segment_key: Logical key for the segment (e.g. 'ascending_colon').
			original_url: URL to the original image segment.
			thumbnail_url: URL to the thumbnail image.
			label_json: JSON-serializable dict with labels/findings.
			id: Optional UUID string to use; generated if omitted.
		"""
		if not self._conn:
			raise RuntimeError("Database connection is not open. Call connect() first.")
		id = id or str(uuid.uuid4())
		label_text = json.dumps(label_json) if label_json is not None else None
		await self._conn.execute(
			"""
			INSERT INTO image_segments (id, segment_key, original_url, thumbnail_url, label_json)
			VALUES (?, ?, ?, ?, ?)
			""",
			(id, segment_key, original_url, thumbnail_url, label_text),
		)
		await self._conn.commit()
		return id

	async def save_thumbnail_blob(self, id: str, thumb_bytes: bytes) -> None:
		"""Store thumbnail bytes into the `thumbnail_blob` column for the given segment id."""
		if not self._conn:
			raise RuntimeError("Database connection is not open. Call connect() first.")
		await self._conn.execute(
			"UPDATE image_segments SET thumbnail_blob = ? WHERE id = ?",
			(thumb_bytes, id),
		)
		await self._conn.commit()

	async def read_thumbnail_blob(self, id: str) -> Optional[bytes]:
		"""Read thumbnail blob bytes for a segment. Returns bytes or None."""
		if not self._conn:
			raise RuntimeError("Database connection is not open. Call connect() first.")
		row = await self.fetch_one("SELECT thumbnail_blob FROM image_segments WHERE id = ?", (id,))
		if not row:
			return None
		return row[0]

	async def save_original_file(self, filename: str, data: bytes, base_dir: Optional[str] = None) -> str:
		"""Save original image bytes under `database/images/` and return path.

		`filename` should be a safe filename (no path traversal). The file
		will be written under workspace `database/images/` by default.
		"""
		base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent / "database" / "images"
		base.mkdir(parents=True, exist_ok=True)
		safe_path = base / filename
		# Use aiofiles to write bytes asynchronously
		async with aiofiles.open(safe_path, "wb") as f:
			await f.write(data)
		return str(safe_path)

	async def get_image_segment(self, id: str) -> Optional[dict]:
		"""Retrieve a single image_segment by UUID id. Returns dict or None."""
		row = await self.fetch_one("SELECT id, segment_key, original_url, thumbnail_url, label_json, created_at FROM image_segments WHERE id = ?", (id,))
		if not row:
			return None
		label = None
		if row[4]:
			try:
				label = json.loads(row[4])
			except Exception:
				label = None
		return {
			"id": row[0],
			"segment_key": row[1],
			"original_url": row[2],
			"thumbnail_url": row[3],
			"label_json": label,
			"created_at": row[5],
		}

	async def list_image_segments(self, segment_key: Optional[str] = None, limit: int = 100) -> List[dict]:
		"""List image segments, optionally filtered by `segment_key`."""
		if segment_key:
			rows = await self.fetch_all("SELECT id, segment_key, original_url, thumbnail_url, label_json, created_at FROM image_segments WHERE segment_key = ? ORDER BY created_at DESC LIMIT ?", (segment_key, limit))
		else:
			rows = await self.fetch_all("SELECT id, segment_key, original_url, thumbnail_url, label_json, created_at FROM image_segments ORDER BY created_at DESC LIMIT ?", (limit,))

		results: List[dict] = []
		for row in rows:
			label = None
			if row[4]:
				try:
					label = json.loads(row[4])
				except Exception:
					label = None
			results.append({
				"id": row[0],
				"segment_key": row[1],
				"original_url": row[2],
				"thumbnail_url": row[3],
				"label_json": label,
				"created_at": row[5],
			})
		return results

	async def __aenter__(self) -> "AsyncSQLiteClient":
		await self.connect()
		return self

	async def __aexit__(self, exc_type, exc, tb) -> None:
		await self.close()


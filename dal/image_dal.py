"""Async Data Access Layer for IMAGE table.

Provides ImageDAL class with async CRUD operations compatible with
`utils.database_init.AsyncDatabaseInitializer`.
"""

from __future__ import annotations


from typing import AsyncIterator, List, Optional

import aiosqlite

from utils.database_init import AsyncDatabaseInitializer
from models.image_record import ImageRecord


class ImageDAL:
	"""Data access layer for IMAGE records.

	The constructor accepts an `AsyncDatabaseInitializer` (or any object
	exposing an async `connection()` context manager that yields an
	`aiosqlite.Connection`).
	"""

	def __init__(self, db_initializer: AsyncDatabaseInitializer) -> None:
		self._db = db_initializer

	async def create_image(self, record: ImageRecord) -> int:
		"""Insert a new IMAGE row and return the new id.

		Args:
			record: ImageRecord with `id=None` and fields to insert.

		Returns:
			The integer primary key of the created row.
		"""

		async with self._db.connection() as conn:
			cur = await conn.execute(
				"""INSERT INTO IMAGE (image_filename, image_description, image_thumbnail, label)
				VALUES (?, ?, ?, ?)""",
				(record.image_filename, record.image_description, record.image_thumbnail, record.label),
			)
			await conn.commit()
			return cur.lastrowid

	async def get_image_by_id(self, image_id: int) -> Optional[ImageRecord]:
		"""Return ImageRecord for `image_id`, or None if not found."""

		async with self._db.connection() as conn:
			cur = await conn.execute(
				"SELECT id, image_filename, image_description, image_thumbnail, label FROM IMAGE WHERE id = ?",
				(image_id,),
			)
			row = await cur.fetchone()
			if row is None:
				return None
			return ImageRecord(
				id=row[0],
				image_filename=row[1],
				image_description=row[2],
				image_thumbnail=row[3],
				label=row[4],
			)

	async def list_images(self, limit: int = 100, offset: int = 0) -> List[ImageRecord]:
		"""List IMAGE rows with optional paging.

		Args:
			limit: Maximum number of rows to return.
			offset: Rows to skip.
		"""

		async with self._db.connection() as conn:
			cur = await conn.execute(
				"SELECT id, image_filename, image_description, image_thumbnail, label FROM IMAGE ORDER BY id DESC LIMIT ? OFFSET ?",
				(limit, offset),
			)
			rows = await cur.fetchall()
			return [
				ImageRecord(id=r[0], image_filename=r[1], image_description=r[2], image_thumbnail=r[3], label=r[4])
				for r in rows
			]

	async def update_image(self, image_id: int, *, image_filename: Optional[str] = None,
						   image_description: Optional[str] = None,
						   image_thumbnail: Optional[bytes] = None,
						   label: Optional[str] = None) -> bool:
		"""Update fields of an IMAGE row. Returns True if a row was changed."""

		fields = []
		params: List[object] = []
		if image_filename is not None:
			fields.append("image_filename = ?")
			params.append(image_filename)
		if image_description is not None:
			fields.append("image_description = ?")
			params.append(image_description)
		if image_thumbnail is not None:
			fields.append("image_thumbnail = ?")
			params.append(image_thumbnail)
		if label is not None:
			fields.append("label = ?")
			params.append(label)

		if not fields:
			return False

		params.append(image_id)
		sql = f"UPDATE IMAGE SET {', '.join(fields)} WHERE id = ?"

		async with self._db.connection() as conn:
			await conn.execute(sql, tuple(params))
			await conn.commit()
			cur = await conn.execute("SELECT changes()")
			changed = await cur.fetchone()
			return bool(changed and changed[0] > 0)

	async def delete_image(self, image_id: int) -> bool:
		"""Delete IMAGE row by id. Returns True if a row was deleted."""

		async with self._db.connection() as conn:
			await conn.execute("DELETE FROM IMAGE WHERE id = ?", (image_id,))
			await conn.commit()
			cur = await conn.execute("SELECT changes()")
			changed = await cur.fetchone()
			return bool(changed and changed[0] > 0)


"""Async Data Access Layer for IMAGE table.

Provides ImageDAL class with async CRUD operations compatible with
`utils.database_init.AsyncDatabaseInitializer`.
"""

from __future__ import annotations

import time
from typing import List, Optional, Sequence

import aiosqlite

from models.image_record import ImageRecord
from utils.database_init import AsyncDatabaseInitializer


class ImageDAL:
    """Data access layer for IMAGE records.

    The constructor accepts an `AsyncDatabaseInitializer` (or any object
    exposing an async `connection()` context manager that yields an
    `aiosqlite.Connection`).
    """

    _COLUMNS = (
        "id",
        "image_filename",
        "image_description",
        "image_thumbnail",
        "label",
        "reasoning",
        "user_documentation",
        "created_at",
    )
    _COLUMN_LIST, _INSERT_COLUMNS = ", ".join(_COLUMNS), ", ".join(_COLUMNS[1:])

    def __init__(self, db_initializer: AsyncDatabaseInitializer) -> None:
        self._db = db_initializer

    async def create_image(self, record: ImageRecord) -> int:
        """Insert a new IMAGE row and return the new id.

        Args:
            record: ImageRecord with `id=None` and fields to insert.

        Returns:
            The integer primary key of the created row.
        """
        created_at = record.created_at or int(time.time())

        async with self._db.connection() as conn:
            cur = await conn.execute(
                f"INSERT INTO IMAGE ({self._INSERT_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    record.image_filename,
                    record.image_description,
                    record.image_thumbnail,
                    record.label,
                    record.reasoning,
                    record.user_documentation,
                    created_at,
                ),
            )
            await conn.commit()
            return cur.lastrowid

    async def get_image_by_id(self, image_id: int) -> Optional[ImageRecord]:
        """Return ImageRecord for `image_id`, or None if not found."""
        async with self._db.connection() as conn:
            cur = await conn.execute(
                f"SELECT {self._COLUMN_LIST} FROM IMAGE WHERE id = ?",
                (image_id,),
            )
            row = await cur.fetchone()
            return self._row_to_record(row) if row else None

    async def list_images(self, limit: int = 100, offset: int = 0) -> List[ImageRecord]:
        """List IMAGE rows with optional paging.

        Args:
            limit: Maximum number of rows to return.
            offset: Rows to skip.
        """
        async with self._db.connection() as conn:
            cur = await conn.execute(
                f"SELECT {self._COLUMN_LIST} FROM IMAGE ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cur.fetchall()
            return [self._row_to_record(r) for r in rows]

    async def update_image(
        self,
        image_id: int,
        *,
        image_filename: Optional[str] = None,
        image_description: Optional[str] = None,
        image_thumbnail: Optional[bytes] = None,
        label: Optional[str] = None,
        reasoning: Optional[str] = None,
        user_documentation: Optional[str] = None,
    ) -> bool:
        """Update fields of an IMAGE row. Returns True if a row was changed."""
        updates = {
            "image_filename": image_filename, "image_description": image_description,
            "image_thumbnail": image_thumbnail, "label": label,
            "reasoning": reasoning, "user_documentation": user_documentation,
        }
        fields = [f"{col} = ?" for col, val in updates.items() if val is not None]

        if not fields:
            return False

        params = [val for val in updates.values() if val is not None]
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

    @staticmethod
    def _row_to_record(row: Sequence[object]) -> ImageRecord:
        """Convert a DB row tuple into an ImageRecord."""
        return ImageRecord(
            id=row[0],
            image_filename=row[1],
            image_description=row[2],
            image_thumbnail=row[3],
            label=row[4],
            reasoning=row[5],
            user_documentation=row[6],
            created_at=row[7],
        )


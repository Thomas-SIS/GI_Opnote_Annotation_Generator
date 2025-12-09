"""Helpers to remove stale IMAGE rows from the SQLite database."""

import asyncio
import time

from utils.database_init import AsyncDatabaseInitializer


class DatabaseCleaner:
    """Delete IMAGE rows older than the configured retention window."""

    def __init__(self, db_initializer: AsyncDatabaseInitializer, retention_seconds: int = 86_400) -> None:
        """
        Args:
            db_initializer: Shared database initializer/connection provider.
            retention_seconds: Age threshold in seconds; rows older than this are removed.
        """
        self._db = db_initializer
        self.retention_seconds = retention_seconds

    async def prune_expired_images(self) -> int:
        """Delete IMAGE rows older than the retention window and return count removed."""
        cutoff = int(time.time()) - self.retention_seconds
        async with self._db.connection() as conn:
            await conn.execute("DELETE FROM IMAGE WHERE created_at < ?", (cutoff,))
            await conn.commit()
            cur = await conn.execute("SELECT changes()")
            deleted = await cur.fetchone()
            return int(deleted[0]) if deleted and deleted[0] is not None else 0

    async def run_periodic_cleanup(self, interval_seconds: int = 3_600) -> None:
        """
        Repeatedly prune expired rows at the given interval until cancelled.

        Args:
            interval_seconds: Seconds to sleep between cleanup runs.
        """
        while True:
            try:
                await self.prune_expired_images()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception:
                # Avoid crashing the loop; sleep before retrying on the next tick.
                await asyncio.sleep(interval_seconds)
